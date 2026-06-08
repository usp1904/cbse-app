import json
import hashlib
import re
from database import get_conn, init_db


LEVEL_NAMES = {
    0: "board",
    1: "subject",
    2: "book",
    3: "chapter",
    4: "topic",
    5: "subtopic",
    6: "example",
    7: "exercise",
    8: "problem",
    9: "solution",
}


def make_id(*parts):
    raw = "/".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def insert_board(board_id, name, description="", ncert_url=""):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO boards (id, name, description, ncert_url) VALUES (?, ?, ?, ?)",
        (board_id, name, description, ncert_url),
    )
    conn.commit()


def insert_subject(subject_id, board_id, name, code="", description="", ncert_url=""):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO subjects (id, board_id, name, code, description, ncert_url) VALUES (?, ?, ?, ?, ?, ?)",
        (subject_id, board_id, name, code, description, ncert_url),
    )
    conn.commit()


def insert_book(book_id, subject_id, name, code="", ncert_url=""):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO books (id, subject_id, name, code, ncert_url) VALUES (?, ?, ?, ?, ?)",
        (book_id, subject_id, name, code, ncert_url),
    )
    conn.commit()


def insert_chapter(chapter_id, book_id, subject_id, board_id, num, title):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO chapters (id, book_id, subject_id, board_id, num, title) VALUES (?, ?, ?, ?, ?, ?)",
        (chapter_id, book_id, subject_id, board_id, num, title),
    )
    conn.commit()


def insert_topic(topic_id, chapter_id, num, title, content=""):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO topics (id, chapter_id, num, title, content) VALUES (?, ?, ?, ?, ?)",
        (topic_id, chapter_id, num, title, content),
    )
    conn.commit()


def insert_chunk(chunk_id, topic_id, chapter_id, parent_id, level, title, content, content_type="text", seq=0):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO chunks (id, topic_id, chapter_id, parent_id, level, title, content, content_type, seq) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (chunk_id, topic_id, chapter_id, parent_id, level, title, content, content_type, seq),
    )
    conn.commit()


def insert_problem(problem_id, topic_id, chapter_id, problem_text, solution_text="", problem_type="", seq=0):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO problems (id, topic_id, chapter_id, problem_text, solution_text, problem_type, seq) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (problem_id, topic_id, chapter_id, problem_text, solution_text, problem_type, seq),
    )
    conn.commit()


def get_chapter_tree(chapter_id):
    conn = get_conn()
    chapter = conn.execute("SELECT * FROM chapters WHERE id = ?", (chapter_id,)).fetchone()
    if not chapter:
        return None
    topics = conn.execute("SELECT * FROM topics WHERE chapter_id = ? ORDER BY num", (chapter_id,)).fetchall()
    result = {"chapter": dict(chapter), "topics": []}
    for topic in topics:
        t = dict(topic)
        chunks = conn.execute(
            "SELECT * FROM chunks WHERE topic_id = ? ORDER BY seq", (topic["id"],)
        ).fetchall()
        t["chunks"] = [dict(c) for c in chunks]
        problems = conn.execute(
            "SELECT * FROM problems WHERE topic_id = ? ORDER BY seq", (topic["id"],)
        ).fetchall()
        t["problems"] = [dict(p) for p in problems]
        result["topics"].append(t)
    return result


def get_topic_with_context(topic_id):
    conn = get_conn()
    topic = conn.execute("SELECT * FROM topics WHERE id = ?", (topic_id,)).fetchone()
    if not topic:
        return None
    result = dict(topic)
    result["chapter"] = dict(conn.execute("SELECT * FROM chapters WHERE id = ?", (topic["chapter_id"],)).fetchone() or {})
    chunks = conn.execute("SELECT * FROM chunks WHERE topic_id = ? ORDER BY seq", (topic_id,)).fetchall()
    result["chunks"] = [dict(c) for c in chunks]
    problems = conn.execute("SELECT * FROM problems WHERE topic_id = ? ORDER BY seq", (topic_id,)).fetchall()
    result["problems"] = [dict(p) for p in problems]
    sibling_topics = conn.execute(
        "SELECT * FROM topics WHERE chapter_id = ? ORDER BY num", (topic["chapter_id"],)
    ).fetchall()
    result["sibling_topics"] = [dict(t) for t in sibling_topics]
    return result


def get_chunk_ancestors(chunk_id):
    conn = get_conn()
    ancestors = []
    current = conn.execute("SELECT * FROM chunks WHERE id = ?", (chunk_id,)).fetchone()
    while current:
        ancestors.append(dict(current))
        if current["parent_id"]:
            current = conn.execute("SELECT * FROM chunks WHERE id = ?", (current["parent_id"],)).fetchone()
        else:
            current = None
    return ancestors


def get_chunk_descendants(chunk_id, max_depth=3):
    conn = get_conn()
    all_descendants = []
    def recurse(cid, depth):
        if depth > max_depth:
            return
        children = conn.execute("SELECT * FROM chunks WHERE parent_id = ? ORDER BY seq", (cid,)).fetchall()
        for child in children:
            all_descendants.append(dict(child))
            recurse(child["id"], depth + 1)
    recurse(chunk_id, 0)
    return all_descendants


def search_chunks(query, board_id=None, subject_id=None, limit=20):
    conn = get_conn()
    params = []
    sql = """
        SELECT c.*, rank FROM chunks_fts
        JOIN chunks c ON chunks_fts.rowid = c.rowid
        WHERE chunks_fts MATCH ?
    """
    params.append(query)
    if board_id:
        sql += " AND c.chapter_id IN (SELECT id FROM chapters WHERE board_id = ?)"
        params.append(board_id)
    if subject_id:
        sql += " AND c.chapter_id IN (SELECT id FROM chapters WHERE subject_id = ?)"
        params.append(subject_id)
    sql += " ORDER BY rank LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    results = []
    for row in rows:
        r = dict(row)
        parent = conn.execute("SELECT title, content_type FROM chunks WHERE id = ?", (r["parent_id"],)).fetchone() if r["parent_id"] else None
        r["parent_title"] = parent["title"] if parent else None
        chapter = conn.execute("SELECT title, num FROM chapters WHERE id = ?", (r["chapter_id"],)).fetchone()
        r["chapter_title"] = chapter["title"] if chapter else ""
        r["chapter_num"] = chapter["num"] if chapter else 0
        results.append(r)
    return results
