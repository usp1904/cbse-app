import re
from database import get_conn


def generate_mind_map(topic_id):
    conn = get_conn()
    topic = conn.execute("SELECT * FROM topics WHERE id = ?", (topic_id,)).fetchone()
    if not topic:
        return None
    chapter = conn.execute("SELECT * FROM chapters WHERE id = ?", (topic["chapter_id"],)).fetchone()
    chunks = conn.execute("SELECT * FROM chunks WHERE topic_id = ? ORDER BY seq", (topic_id,)).fetchall()
    problems = conn.execute("SELECT * FROM problems WHERE topic_id = ? ORDER BY seq", (topic_id,)).fetchall()

    lines = []
    lines.append(f"# {topic['title']}")
    lines.append(f"├─ Chapter: {chapter['title'] if chapter else 'General'}")
    lines.append("│")

    concepts = set()
    formulas = set()
    examples = []
    key_terms = set()

    for c in chunks:
        text = c["content"]
        if c["content_type"] == "example":
            examples.append(c["title"] or "Example")
        words = re.findall(r'\b[A-Z][a-z]{2,}\b', text)
        for w in words:
            if len(w) > 3 and w.lower() not in {"this", "that", "with", "from", "they", "their", "them",
                                                  "have", "been", "were", "what", "when", "where", "which",
                                                  "each", "step", "into", "also", "than", "then", "some",
                                                  "more", "such", "very", "just", "about", "being", "understand",
                                                  "remember", "important", "between", "without", "after", "before",
                                                  "other", "should", "could", "first", "second", "third", "next",
                                                  "last", "basic", "common", "following", "above", "below",
                                                  "concept", "definition", "property", "formula", "theorem",
                                                  "principle", "method", "rule", "example", "practice", "problem",
                                                  "solution", "chapter", "topic", "section", "figure", "table"}:
                key_terms.add(w)

    if key_terms:
        lines.append("├─ Key Concepts")
        for kt in sorted(list(key_terms))[:8]:
            lines.append(f"│  ├─ {kt}")

    if formulas:
        lines.append("│")
        lines.append("├─ Formulas")
        for f in formulas:
            lines.append(f"│  ├─ {f}")

    if examples:
        lines.append("│")
        lines.append("├─ Examples")
        for e in examples[:3]:
            lines.append(f"│  ├─ {e}")

    if problems:
        lines.append("│")
        lines.append("├─ Practice Problems")
        for p in problems[:3]:
            ptext = p["problem_text"][:60]
            lines.append(f"│  ├─ {ptext}...")

    lines.append("│")
    lines.append("└─ Related Topics")
    siblings = conn.execute(
        "SELECT * FROM topics WHERE chapter_id = ? AND id != ? ORDER BY num LIMIT 5",
        (topic["chapter_id"], topic_id),
    ).fetchall()
    for s in siblings:
        lines.append(f"   ├─ {s['title']}")

    return "\n".join(lines)


def generate_chapter_mind_map(chapter_id):
    conn = get_conn()
    chapter = conn.execute("SELECT * FROM chapters WHERE id = ?", (chapter_id,)).fetchone()
    if not chapter:
        return None
    topics = conn.execute("SELECT * FROM topics WHERE chapter_id = ? ORDER BY num", (chapter_id,)).fetchall()

    lines = []
    lines.append(f"# Chapter {chapter['num']}: {chapter['title']}")
    lines.append("│")

    total_topics = len(topics)
    for i, t in enumerate(topics):
        prefix = "├─" if i < total_topics - 1 else "└─"
        lines.append(f"{prefix} {t['num']}. {t['title']}")
        chunks = conn.execute(
            "SELECT content_type, COUNT(*) as cnt FROM chunks WHERE topic_id = ? GROUP BY content_type",
            (t["id"],),
        ).fetchall()
        for c in chunks:
            sub_prefix = "│  ├─" if i < total_topics - 1 else "   ├─"
            lines.append(f"{sub_prefix} {c['content_type']} ({c['cnt']})")
        has_problems = conn.execute(
            "SELECT COUNT(*) as cnt FROM problems WHERE topic_id = ?", (t["id"],)
        ).fetchone()["cnt"]
        if has_problems:
            sub_prefix = "│  └─" if i < total_topics - 1 else "   └─"
            lines.append(f"{sub_prefix} Practice Problems ({has_problems})")

    return "\n".join(lines)
