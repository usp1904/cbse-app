import json
import re
import time
import hashlib
import logging
from chunking import search_chunks, get_topic_with_context, get_chapter_tree, get_chunk_ancestors

log = logging.getLogger("cbse.rag")

BOARD_NAMES = {"cbse": "CBSE", "ap": "AP Board", "ts": "TS Board"}
_CACHE_TTL = 300  # 5 minutes
_CACHE_MAXSIZE = 500


def _get_db_cached(cache_key_tuple):
    try:
        from database import get_db
        db = get_db()
        key_str = json.dumps(cache_key_tuple, sort_keys=True)
        hash_key = "rag_" + hashlib.sha256(key_str.encode()).hexdigest()
        
        if db.table_exists("ai_content_cache"):
            row = db.query_one("SELECT result_json FROM ai_content_cache WHERE cache_key = ?", (hash_key,))
            if row:
                return json.loads(row["result_json"])
    except Exception as e:
        log.debug("RAG DB cache read error: %s", e)
    return None


def _set_db_cached(cache_key_tuple, val):
    try:
        from database import get_db
        db = get_db()
        key_str = json.dumps(cache_key_tuple, sort_keys=True)
        hash_key = "rag_" + hashlib.sha256(key_str.encode()).hexdigest()
        
        if db.table_exists("ai_content_cache"):
            if db.is_sqlite:
                db.execute("INSERT OR REPLACE INTO ai_content_cache (cache_key, result_json) VALUES (?, ?)", (hash_key, json.dumps(val)))
            else:
                db.execute("INSERT INTO ai_content_cache (cache_key, result_json) VALUES (%s, %s) ON CONFLICT (cache_key) DO UPDATE SET result_json = EXCLUDED.result_json", (hash_key, json.dumps(val)))
    except Exception as e:
        log.debug("RAG DB cache write error: %s", e)


class RAGEngine:
    def __init__(self):
        self.search_cache = {}
        self.hybrid_cache = {}

    def _cache_get(self, cache, key):
        val = cache.get(key)
        if val is None:
            return None
        entry_time, data = val
        if time.time() - entry_time > _CACHE_TTL:
            del cache[key]
            return None
        return data

    def _cache_set(self, cache, key, val):
        if len(cache) >= _CACHE_MAXSIZE:
            try:
                oldest = min(cache.keys(), key=lambda k: cache[k][0])
                del cache[oldest]
            except (ValueError, KeyError):
                cache.clear()
        cache[key] = (time.time(), val)

    def search(self, query, board=None, subject=None, limit=15):
        cache_key = (query, board, subject, limit, "fts")
        cached = self._cache_get(self.search_cache, cache_key)
        if cached is not None:
            return cached

        cached_db = _get_db_cached(cache_key)
        if cached_db is not None:
            self._cache_set(self.search_cache, cache_key, cached_db)
            return cached_db

        results = search_chunks(query, board_id=board, subject_id=subject, limit=limit)
        enriched = []
        seen = set()
        for r in results:
            dedup_key = (r["id"], r.get("chapter_id", ""))
            if dedup_key in seen:
                continue
            seen.add(dedup_key)
            entry = {
                "id": r["id"],
                "title": r["title"],
                "content": r["content"],
                "content_type": r["content_type"],
                "level": r["level"],
                "chapter_title": r["chapter_title"],
                "chapter_num": r["chapter_num"],
                "chapter_id": r.get("chapter_id", ""),
                "parent_title": r["parent_title"],
                "rank": r["rank"],
                "board": board or "cbse",
                "excerpt": self._make_excerpt(r["content"], query),
            }
            enriched.append(entry)

        self._cache_set(self.search_cache, cache_key, enriched)
        _set_db_cached(cache_key, enriched)
        return enriched

    def hybrid_search(self, query, board=None, subject=None, limit=15):
        cache_key = (query, board, subject, limit, "hybrid")
        cached = self._cache_get(self.hybrid_cache, cache_key)
        if cached is not None:
            return cached

        cached_db = _get_db_cached(cache_key)
        if cached_db is not None:
            self._cache_set(self.hybrid_cache, cache_key, cached_db)
            return cached_db

        fts_results = self.search(query, board=board, subject=subject, limit=limit * 2)

        keywords = [w.lower() for w in re.findall(r'\w+', query) if len(w) > 2]
        scored = {}
        for r in fts_results:
            base_score = 1.0 / (r["rank"] + 1) if r["rank"] > 0 else 1.0
            text = (r["title"] + " " + r["content"]).lower()
            keyword_matches = sum(1 for kw in keywords if kw in text)
            title_bonus = 2.0 if any(kw in r["title"].lower() for kw in keywords) else 0.0
            weighted = base_score + (keyword_matches * 0.3) + title_bonus
            if r["id"] not in scored or weighted > scored[r["id"]][1]:
                scored[r["id"]] = (r, weighted)

        sorted_results = sorted(scored.values(), key=lambda x: -x[1])[:limit]
        results = [r for r, _ in sorted_results]

        self._cache_set(self.hybrid_cache, cache_key, results)
        _set_db_cached(cache_key, results)
        return results

    def search_by_board(self, query, board="cbse", limit=10):
        return self.hybrid_search(query, board=board, limit=limit)

    def search_by_subject(self, query, board="cbse", subject=None, limit=10):
        return self.hybrid_search(query, board=board, subject=subject, limit=limit)

    def get_topic_detail(self, topic_id):
        return get_topic_with_context(topic_id)

    def get_chapter_detail(self, chapter_id):
        return get_chapter_tree(chapter_id)

    def retrieve_context(self, query, max_chunks=5):
        results = self.hybrid_search(query, limit=max_chunks)
        context_parts = []
        for r in results:
            level_name = {3: "Chapter", 4: "Topic", 5: "Subtopic", 6: "Example"}.get(r["level"], "Content")
            header = f"[{level_name}: {r['chapter_title']} > {r['title']}]"
            context_parts.append(f"{header}\n{r['content']}")
        return "\n\n".join(context_parts)

    def retrieve_context_for_llm(self, query, max_chunks=5, include_metadata=True):
        results = self.hybrid_search(query, limit=max_chunks)
        if not results:
            return ""
        parts = []
        for r in results:
            meta = f"(from {r['chapter_title']}, {r['content_type']})" if include_metadata else ""
            parts.append(f"{r['excerpt']} {meta}".strip())
        return "\n\n".join(parts)

    def _make_excerpt(self, text, query, max_len=250):
        text = re.sub(r'\s+', ' ', text).strip()
        words = query.lower().split()
        text_lower = text.lower()
        best_pos = 0
        for w in words:
            pos = text_lower.find(w)
            if pos >= 0:
                best_pos = max(best_pos, pos)
        if best_pos > 0:
            start = max(0, best_pos - 100)
            end = min(len(text), best_pos + 150)
            excerpt = text[start:end]
            if start > 0:
                excerpt = "... " + excerpt
            if end < len(text):
                excerpt = excerpt + " ..."
        else:
            excerpt = text[:max_len]
            if len(text) > max_len:
                excerpt += "..."
        return excerpt

    def clear_cache(self):
        self.search_cache.clear()
        self.hybrid_cache.clear()


_engine = None

def get_engine():
    global _engine
    if _engine is None:
        _engine = RAGEngine()
    return _engine
