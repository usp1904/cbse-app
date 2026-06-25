"""Database layer — delegates to db.py abstraction (SQLite or PostgreSQL/Neon).

Set DATABASE_URL to switch backends:
  sqlite:///cbse_content.db    → SQLite (local dev, default)
  postgresql://user:pass@host/db  → PostgreSQL / Neon (production)
"""
import os
import json
import logging
from db import get_db, DatabaseError as DbError

log = logging.getLogger("cbse.db")

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "cbse_content.db"))
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS boards (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    ncert_url TEXT
);

CREATE TABLE IF NOT EXISTS subjects (
    id TEXT PRIMARY KEY,
    board_id TEXT NOT NULL,
    name TEXT NOT NULL,
    code TEXT,
    description TEXT,
    ncert_url TEXT,
    class TEXT DEFAULT 'X'
);

CREATE TABLE IF NOT EXISTS books (
    id TEXT PRIMARY KEY,
    subject_id TEXT NOT NULL,
    name TEXT NOT NULL,
    code TEXT,
    ncert_url TEXT
);

CREATE TABLE IF NOT EXISTS chapters (
    id TEXT PRIMARY KEY,
    book_id TEXT,
    subject_id TEXT NOT NULL,
    board_id TEXT NOT NULL,
    num INTEGER NOT NULL,
    title TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS topics (
    id TEXT PRIMARY KEY,
    chapter_id TEXT NOT NULL,
    num INTEGER,
    title TEXT NOT NULL,
    content TEXT
);

CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    topic_id TEXT,
    chapter_id TEXT,
    parent_id TEXT,
    level INTEGER NOT NULL,
    title TEXT,
    content TEXT NOT NULL,
    content_type TEXT DEFAULT 'text',
    seq INTEGER
);

CREATE TABLE IF NOT EXISTS problems (
    id TEXT PRIMARY KEY,
    topic_id TEXT,
    chapter_id TEXT NOT NULL,
    problem_text TEXT NOT NULL,
    solution_text TEXT,
    problem_type TEXT,
    seq INTEGER
);

CREATE TABLE IF NOT EXISTS content_meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    title,
    content,
    content='chunks'
);

CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, title, content) VALUES (new.rowid, new.title, new.content);
END;

CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, title, content) VALUES('delete', old.rowid, old.title, old.content);
END;

CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, title, content) VALUES('delete', old.rowid, old.title, old.content);
    INSERT INTO chunks_fts(rowid, title, content) VALUES (new.rowid, new.title, new.content);
END;

CREATE TABLE IF NOT EXISTS learner (
    id INTEGER PRIMARY KEY,
    name TEXT DEFAULT 'Learner',
    email TEXT,
    password_hash TEXT,
    xp INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    streak INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0,
    last_active TEXT,
    lives INTEGER DEFAULT 5,
    max_lives INTEGER DEFAULT 5,
    last_life_refill TEXT,
    total_xp_earned INTEGER DEFAULT 0,
    topics_completed INTEGER DEFAULT 0,
    quizzes_taken INTEGER DEFAULT 0,
    quiz_correct INTEGER DEFAULT 0,
    quiz_total INTEGER DEFAULT 0,
    mock_exams_taken INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    learner_id INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    expires_at TEXT DEFAULT (datetime('now','localtime', '+7 days'))
);

CREATE TABLE IF NOT EXISTS xp_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    xp INTEGER NOT NULL,
    reason TEXT NOT NULL,
    detail TEXT,
    chapter_id TEXT,
    topic_id TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS learning_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chapter_id TEXT NOT NULL,
    topic_id TEXT,
    status TEXT DEFAULT 'locked',
    xp_earned INTEGER DEFAULT 0,
    time_spent INTEGER DEFAULT 0,
    last_accessed TEXT,
    completions INTEGER DEFAULT 0,
    quiz_score REAL,
    UNIQUE(chapter_id, topic_id)
);

CREATE TABLE IF NOT EXISTS lifeline_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lifeline_type TEXT NOT NULL,
    chapter_id TEXT,
    topic_id TEXT,
    xp_cost INTEGER DEFAULT 5,
    used_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS daily_challenges (
    challenge_date TEXT PRIMARY KEY,
    board_id TEXT,
    subject_id TEXT,
    type_id TEXT,
    question_ids TEXT,
    bonus_xp INTEGER DEFAULT 0,
    completed INTEGER DEFAULT 0,
    score INTEGER DEFAULT 0,
    total INTEGER DEFAULT 0,
    xp_earned INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS monitoring_pins (
    pin TEXT PRIMARY KEY,
    learner_id INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    expires_at TEXT,
    is_active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS concept_views (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id TEXT,
    viewed_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS content_pillars (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    icon TEXT,
    description TEXT,
    color TEXT,
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS pillar_content (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pillar_id TEXT NOT NULL,
    content_type TEXT NOT NULL,
    content_id TEXT NOT NULL,
    label TEXT,
    sort_order INTEGER DEFAULT 0,
    UNIQUE(pillar_id, content_type, content_id)
);

CREATE TABLE IF NOT EXISTS knowledge_graph (
    id TEXT PRIMARY KEY,
    subject_id TEXT,
    chapter_id TEXT,
    topic_id TEXT,
    concept_name TEXT NOT NULL,
    difficulty INTEGER DEFAULT 1,
    parent_concept_id TEXT,
    description TEXT
);

CREATE TABLE IF NOT EXISTS user_mastery (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    concept_id TEXT NOT NULL,
    learner_id INTEGER DEFAULT 1,
    mastery_level REAL DEFAULT 0.0,
    attempts INTEGER DEFAULT 0,
    correct INTEGER DEFAULT 0,
    total INTEGER DEFAULT 0,
    last_practiced TEXT,
    streak INTEGER DEFAULT 0,
    UNIQUE(concept_id, learner_id)
);

CREATE TABLE IF NOT EXISTS ai_content_cache (
    cache_key TEXT PRIMARY KEY,
    result_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def get_conn():
    """Return a database handle (backward-compatible with existing code).

    Returns the db.Database singleton which provides execute/query/insert
    methods and dict-like Row objects (row['col'] or row.col).
    """
    return get_db()


def get_db():
    from db import get_db as _get_db
    return _get_db()


def init_db():
    db = get_db()
    db.executescript(SCHEMA_SQL)

    # Safety ALTER TABLE for subjects table
    try:
        db.execute("ALTER TABLE subjects ADD COLUMN class TEXT DEFAULT 'X'")
    except Exception as e:
        log.debug("Column class already exists in subjects: %s", e)

    # central indices for query optimization
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_chapters_subject ON chapters(subject_id)",
        "CREATE INDEX IF NOT EXISTS idx_chapters_board ON chapters(board_id)",
        "CREATE INDEX IF NOT EXISTS idx_topics_chapter ON topics(chapter_id)",
        "CREATE INDEX IF NOT EXISTS idx_chunks_topic ON chunks(topic_id)",
        "CREATE INDEX IF NOT EXISTS idx_chunks_chapter ON chunks(chapter_id)",
        "CREATE INDEX IF NOT EXISTS idx_problems_chapter ON problems(chapter_id)",
        "CREATE INDEX IF NOT EXISTS idx_problems_topic ON problems(topic_id)"
    ]
    for idx_sql in indexes:
        try:
            db.execute(idx_sql)
        except Exception as e:
            log.warning("Failed to create index (%s): %s", idx_sql, e)

    for col in ("email", "password_hash"):
        try:
            db.execute(f"ALTER TABLE learner ADD COLUMN {col} TEXT")
        except Exception as e:
            log.debug("Column %s already exists: %s", col, e)

    try:
        db.execute("INSERT INTO learner (id, name, xp, level, streak, lives, max_lives, last_active, last_life_refill) "
                    "VALUES (1, 'Learner', 0, 1, 0, 5, 5, date('now','localtime'), datetime('now','localtime')) "
                    "ON CONFLICT (id) DO NOTHING")
    except Exception as e:
        try:
            db.execute("INSERT OR IGNORE INTO learner (id, name, xp, level, streak, lives, max_lives, last_active, last_life_refill) "
                        "VALUES (1, 'Learner', 0, 1, 0, 5, 5, date('now','localtime'), datetime('now','localtime'))")
        except Exception as e2:
            log.warning("Failed to insert default learner: %s / %s", e, e2)

    try:
        db.execute("INSERT OR IGNORE INTO content_meta (key, value) VALUES ('schema_version', '2.0')")
        db.execute("INSERT OR IGNORE INTO content_meta (key, value) VALUES ('total_chunks', '0')")
        db.execute("INSERT OR IGNORE INTO content_meta (key, value) VALUES ('last_indexed', '')")
    except Exception as e:
        log.warning("Failed to insert content_meta: %s", e)

    from db import rebuild_fts as _rebuild_fts
    _rebuild_fts(db)

    try:
        from badges import init_badges_table
        init_badges_table()
    except Exception as e:
        log.warning("Badges table init skipped: %s", e)
    try:
        from mock_exam import init_exam_tables
        init_exam_tables()
    except Exception as e:
        log.warning("Exam tables init skipped: %s", e)
    try:
        from spaced_repetition import init_review_tables
        init_review_tables()
    except Exception as e:
        log.warning("Review tables init skipped: %s", e)

    # Invalidate syllabus cache
    try:
        import os
        cache_file = os.path.join(os.path.dirname(__file__), "syllabus_index.json")
        if os.path.exists(cache_file):
            os.remove(cache_file)
    except Exception as e:
        log.warning("Failed to invalidate syllabus cache: %s", e)


def close():
    db = get_db()
    db.close()
