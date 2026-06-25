"""JSON Index Engine — vectorless, in-memory search index built from the database.

Pre-loads all content into structured JSON at startup for fast filtering,
searching, and browsing without FTS or vector embeddings.
"""

import json
import re
import os
import time
import logging
import threading
from database import get_conn

log = logging.getLogger("cbse.index")

_REFRESH_INTERVAL = 300
_INDEX_LOCK = threading.Lock()

_SUBJECT_LANGUAGE = {
    "mathematics": "English", "science": "English", "english": "English",
    "social-science": "English", "ai": "English", "it": "English",
    "french": "French", "hindi": "Hindi", "sanskrit": "Sanskrit",
    "ap-mathematics": "English", "ap-science": "English", "ap-english": "English",
    "ap-social-studies": "English", "ap-biology": "English",
    "ap-physical-science": "English",
    "ts-mathematics": "English", "ts-science": "English",
    "ts-social-studies": "English", "ts-biology": "English",
    "ts-physical-science": "English",
}

_INDIAN_LANGUAGES = [
    "English", "Hindi", "Telugu", "Tamil", "Kannada", "Malayalam",
    "Bengali", "Marathi", "Gujarati", "Punjabi", "Urdu", "Odia",
    "Assamese", "Maithili", "Santali", "Kashmiri", "Nepali",
    "Sindhi", "Dogri", "Konkani", "Manipuri", "Bodo", "Sanskrit",
    "French",
]

_CLASSES = ["XII", "XI", "X", "IX", "VIII", "VII", "VI", "V"]


class JsonIndex:
    def __init__(self):
        self._data = {
            "boards": {},
            "subjects": {},
            "chapters": {},
            "topics": {},
            "chunks": [],
            "problems": [],
            "search_terms": {},
            "built_at": 0,
        }
        self._last_refresh = 0
        self._frozen = False
        self._all_boards_tree_cache = None

    def build(self):
        """Build the full index from the database. Called once at startup."""
        with _INDEX_LOCK:
            self._all_boards_tree_cache = None
            conn = get_conn()
            boards = conn.execute("SELECT * FROM boards ORDER BY name").fetchall()
            for b in boards:
                b = dict(b)
                self._data["boards"][b["id"]] = b

            subjects = conn.execute("SELECT * FROM subjects ORDER BY board_id, name").fetchall()
            for s in subjects:
                s = dict(s)
                self._data["subjects"][s["id"]] = s

            chapters = conn.execute("SELECT * FROM chapters ORDER BY board_id, subject_id, num").fetchall()
            for c in chapters:
                c = dict(c)
                self._data["chapters"][c["id"]] = c

            topics = conn.execute("SELECT * FROM topics ORDER BY chapter_id, num").fetchall()
            for t in topics:
                t = dict(t)
                self._data["topics"][t["id"]] = t

            chunks = conn.execute(
                "SELECT c.*, ch.title AS chapter_title, ch.num AS chapter_num "
                "FROM chunks c LEFT JOIN chapters ch ON c.chapter_id = ch.id "
                "ORDER BY c.chapter_id, c.topic_id, c.seq"
            ).fetchall()
            self._data["chunks"] = [dict(r) for r in chunks]

            problems = conn.execute(
                "SELECT p.*, ch.title AS chapter_title FROM problems p "
                "LEFT JOIN chapters ch ON p.chapter_id = ch.id "
                "ORDER BY p.chapter_id, p.topic_id, p.seq"
            ).fetchall()
            self._data["problems"] = [dict(r) for r in problems]

            self._build_search_terms()

            # Group chapters, topics, chunks, and problems to build hierarchy in O(N)
            chapters_by_subject = {}
            for ch in self._data["chapters"].values():
                chapters_by_subject.setdefault(ch["subject_id"], []).append(ch)

            topics_by_chapter = {}
            for t in self._data["topics"].values():
                topics_by_chapter.setdefault(t["chapter_id"], []).append(t)

            chunks_by_topic = {}
            for c in self._data["chunks"]:
                chunks_by_topic.setdefault(c["topic_id"], []).append(c)

            problems_by_topic = {}
            for p in self._data["problems"]:
                problems_by_topic.setdefault(p["topic_id"], []).append(p)

            # Build board > subject > chapter > topic tree
            for board_id in self._data["boards"]:
                board_subjects = [
                    s for s in self._data["subjects"].values()
                    if s["board_id"] == board_id
                ]
                for s in board_subjects:
                    s["chapters"] = chapters_by_subject.get(s["id"], [])
                    for ch in s["chapters"]:
                        ch["topics"] = topics_by_chapter.get(ch["id"], [])
                        for t in ch["topics"]:
                            t["chunks"] = chunks_by_topic.get(t["id"], [])
                            t["problems"] = problems_by_topic.get(t["id"], [])

            self._data["built_at"] = time.time()
            self._last_refresh = time.time()
            log.info(
                "Index built: %d boards, %d subjects, %d chapters, %d topics, %d chunks, %d problems",
                len(self._data["boards"]),
                len(self._data["subjects"]),
                len(self._data["chapters"]),
                len(self._data["topics"]),
                len(self._data["chunks"]),
                len(self._data["problems"]),
            )
            self._frozen = True

    def _build_search_terms(self):
        terms = {}
        for t in self._data["topics"].values():
            for word in re.findall(r"\w+", t.get("title", "")):
                word = word.lower()
                if len(word) < 3:
                    continue
                terms.setdefault(word, []).append({
                    "type": "topic",
                    "id": t["id"],
                    "title": t["title"],
                    "chapter_id": t["chapter_id"],
                })
        for c in self._data["chunks"]:
            for word in re.findall(r"\w+", c.get("title", "")):
                word = word.lower()
                if len(word) < 3:
                    continue
                terms.setdefault(word, []).append({
                    "type": "chunk",
                    "id": c["id"],
                    "title": c["title"],
                    "chapter_id": c["chapter_id"],
                    "topic_id": c["topic_id"],
                })
        self._data["search_terms"] = terms

    def get_boards(self):
        return list(self._data["boards"].values())

    def get_subjects(self, board_id=None):
        if board_id:
            return [s for s in self._data["subjects"].values() if s["board_id"] == board_id]
        return list(self._data["subjects"].values())

    def get_chapters(self, subject_id=None, board_id=None):
        chapters = list(self._data["chapters"].values())
        if subject_id:
            chapters = [c for c in chapters if c["subject_id"] == subject_id]
        if board_id:
            chapters = [c for c in chapters if c["board_id"] == board_id]
        return chapters

    def get_topics(self, chapter_id=None, subject_id=None):
        topics = list(self._data["topics"].values())
        if chapter_id:
            topics = [t for t in topics if t["chapter_id"] == chapter_id]
        if subject_id:
            ch_ids = {c["id"] for c in self._data["chapters"].values() if c["subject_id"] == subject_id}
            topics = [t for t in topics if t["chapter_id"] in ch_ids]
        return topics

    def get_chunks(self, topic_id=None, chapter_id=None):
        chunks = self._data["chunks"]
        if topic_id:
            chunks = [c for c in chunks if c["topic_id"] == topic_id]
        if chapter_id:
            chunks = [c for c in chunks if c["chapter_id"] == chapter_id]
        return chunks

    def get_problems(self, topic_id=None, chapter_id=None):
        problems = self._data["problems"]
        if topic_id:
            problems = [p for p in problems if p["topic_id"] == topic_id]
        if chapter_id:
            problems = [p for p in problems if p["chapter_id"] == chapter_id]
        return problems

    def get_topic(self, topic_id):
        t = self._data["topics"].get(topic_id)
        if not t:
            return None
        result = dict(t)
        chapter = self._data["chapters"].get(t["chapter_id"], {})
        result["chapter"] = dict(chapter) if chapter else {}
        result["chunks"] = self.get_chunks(topic_id=topic_id)
        result["problems"] = self.get_problems(topic_id=topic_id)
        result["sibling_topics"] = self.get_topics(chapter_id=t["chapter_id"])
        return result

    def get_chapter(self, chapter_id):
        c = self._data["chapters"].get(chapter_id)
        if not c:
            return None
        result = dict(c)
        result["topics"] = self.get_topics(chapter_id=chapter_id)
        return result

    def search(self, query, board=None, subject=None, limit=15):
        words = [w.lower() for w in re.findall(r"\w+", query) if len(w) >= 2]
        if not words:
            return []

        scored = {}
        for word in words:
            for entry in self._data["search_terms"].get(word, []):
                if board and entry.get("board_id") and entry["board_id"] != board:
                    continue
                if subject and entry.get("subject_id") and entry["subject_id"] != subject:
                    continue
                key = (entry["type"], entry["id"])
                scored[key] = scored.get(key, 0) + 1 + (2 if word in entry["title"].lower() else 0)

        # Apply title-level matching for topic titles
        for t in self._data["topics"].values():
            title_lower = t["title"].lower()
            match_count = sum(1 for w in words if w in title_lower)
            if match_count > 0:
                key = ("topic", t["id"])
                scored[key] = max(scored.get(key, 0), match_count * 3)

        sorted_results = sorted(scored.items(), key=lambda x: -x[1])[:limit]
        results = []
        for (typ, tid), score in sorted_results:
            if typ == "topic":
                t = self._data["topics"].get(tid)
                if not t:
                    continue
                ch = self._data["chapters"].get(t["chapter_id"], {})
                results.append({
                    "id": tid,
                    "title": t["title"],
                    "type": "topic",
                    "chapter_title": ch.get("title", ""),
                    "chapter_id": t["chapter_id"],
                    "score": score,
                    "excerpt": (t.get("content") or "")[:200],
                })
            elif typ == "chunk":
                c = next((x for x in self._data["chunks"] if x["id"] == tid), None)
                if not c:
                    continue
                results.append({
                    "id": tid,
                    "title": c.get("title", ""),
                    "type": "chunk",
                    "chapter_title": c.get("chapter_title", ""),
                    "chapter_id": c.get("chapter_id", ""),
                    "topic_id": c.get("topic_id", ""),
                    "content": (c.get("content") or "")[:200],
                    "score": score,
                })
        return results

    def get_board_tree(self, board_id):
        """Return full board > subject > chapter > topic tree for dropdown menus."""
        board = self._data["boards"].get(board_id)
        if not board:
            return None
        subjects = [s for s in self._data["subjects"].values() if s["board_id"] == board_id]
        result = {
            "id": board_id,
            "name": board.get("name", board_id.upper()),
            "subjects": [],
        }
        for s in subjects:
            chapters = s.get("chapters", [])
            topic_count = sum(len(ch.get("topics", [])) for ch in chapters)
            result["subjects"].append({
                "id": s["id"],
                "name": s["name"],
                "chapter_count": len(chapters),
                "topic_count": topic_count,
                "language": _SUBJECT_LANGUAGE.get(re.sub(r'-(v|vi|vii|viii|ix|x|xi|xii)$', '', s["id"].lower()), _SUBJECT_LANGUAGE.get(s["id"], "English")),
                "class": s.get("class", "X"),
            })
        return result

    def get_all_boards_tree(self):
        if self._all_boards_tree_cache is None:
            self._all_boards_tree_cache = [self.get_board_tree(bid) for bid in self._data["boards"]]
        return self._all_boards_tree_cache

    def get_languages(self):
        langs = {"English"}
        for s in self._data["subjects"].values():
            lang = _SUBJECT_LANGUAGE.get(re.sub(r'-(v|vi|vii|viii|ix|x|xi|xii)$', '', s["id"].lower()), _SUBJECT_LANGUAGE.get(s["id"], "English"))
            langs.add(lang)
        return sorted(langs)

    def get_classes(self):
        return list(_CLASSES)

    def get_stats(self):
        return {
            "boards": len(self._data["boards"]),
            "subjects": len(self._data["subjects"]),
            "chapters": len(self._data["chapters"]),
            "topics": len(self._data["topics"]),
            "chunks": len(self._data["chunks"]),
            "problems": len(self._data["problems"]),
            "search_terms": len(self._data["search_terms"]),
            "built_at": self._data["built_at"],
        }

    def to_json(self):
        return json.dumps(self._data, default=str, indent=2)


_index = None


def get_index():
    global _index
    if _index is None:
        _index = JsonIndex()
        _index.build()
    return _index
