import sqlite3
import os
import json
import threading

DB_PATH = os.path.join(os.path.dirname(__file__), "cbse_content.db")
_local = threading.local()

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
    FOREIGN KEY (board_id) REFERENCES boards(id)
);

CREATE TABLE IF NOT EXISTS books (
    id TEXT PRIMARY KEY,
    subject_id TEXT NOT NULL,
    name TEXT NOT NULL,
    code TEXT,
    ncert_url TEXT,
    FOREIGN KEY (subject_id) REFERENCES subjects(id)
);

CREATE TABLE IF NOT EXISTS chapters (
    id TEXT PRIMARY KEY,
    book_id TEXT,
    subject_id TEXT NOT NULL,
    board_id TEXT NOT NULL,
    num INTEGER NOT NULL,
    title TEXT NOT NULL,
    FOREIGN KEY (book_id) REFERENCES books(id),
    FOREIGN KEY (subject_id) REFERENCES subjects(id),
    FOREIGN KEY (board_id) REFERENCES boards(id)
);

CREATE TABLE IF NOT EXISTS topics (
    id TEXT PRIMARY KEY,
    chapter_id TEXT NOT NULL,
    num INTEGER,
    title TEXT NOT NULL,
    content TEXT,
    FOREIGN KEY (chapter_id) REFERENCES chapters(id)
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
    seq INTEGER,
    FOREIGN KEY (topic_id) REFERENCES topics(id),
    FOREIGN KEY (chapter_id) REFERENCES chapters(id),
    FOREIGN KEY (parent_id) REFERENCES chunks(id)
);

CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    content, title,
    content='chunks',
    content_rowid='rowid',
    tokenize='unicode61'
);

CREATE TABLE IF NOT EXISTS problems (
    id TEXT PRIMARY KEY,
    topic_id TEXT,
    chapter_id TEXT NOT NULL,
    problem_text TEXT NOT NULL,
    solution_text TEXT,
    problem_type TEXT,
    seq INTEGER,
    FOREIGN KEY (topic_id) REFERENCES topics(id),
    FOREIGN KEY (chapter_id) REFERENCES chapters(id)
);

CREATE TABLE IF NOT EXISTS content_meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

INSERT OR IGNORE INTO content_meta (key, value) VALUES ('schema_version', '2.0');
INSERT OR IGNORE INTO content_meta (key, value) VALUES ('total_chunks', '0');
INSERT OR IGNORE INTO content_meta (key, value) VALUES ('last_indexed', '');

CREATE TABLE IF NOT EXISTS learner (
    id INTEGER PRIMARY KEY CHECK (id = 1),
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

INSERT OR IGNORE INTO learner (id, name, xp, level, streak, lives, max_lives, last_active, last_life_refill)
VALUES (1, 'Learner', 0, 1, 0, 5, 5, date('now','localtime'), datetime('now','localtime'));

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
    FOREIGN KEY (pillar_id) REFERENCES content_pillars(id),
    UNIQUE(pillar_id, content_type, content_id)
);

CREATE TABLE IF NOT EXISTS knowledge_graph (
    id TEXT PRIMARY KEY,
    subject_id TEXT,
    chapter_id TEXT,
    topic_id TEXT,
    concept_name TEXT NOT NULL,
    difficulty INTEGER DEFAULT 1 CHECK (difficulty BETWEEN 1 AND 5),
    parent_concept_id TEXT,
    description TEXT,
    FOREIGN KEY (subject_id) REFERENCES subjects(id),
    FOREIGN KEY (chapter_id) REFERENCES chapters(id),
    FOREIGN KEY (topic_id) REFERENCES topics(id),
    FOREIGN KEY (parent_concept_id) REFERENCES knowledge_graph(id)
);

CREATE TABLE IF NOT EXISTS user_mastery (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    concept_id TEXT NOT NULL,
    learner_id INTEGER DEFAULT 1,
    mastery_level REAL DEFAULT 0.0 CHECK (mastery_level BETWEEN 0.0 AND 1.0),
    attempts INTEGER DEFAULT 0,
    correct INTEGER DEFAULT 0,
    total INTEGER DEFAULT 0,
    last_practiced TEXT,
    streak INTEGER DEFAULT 0,
    FOREIGN KEY (concept_id) REFERENCES knowledge_graph(id),
    UNIQUE(concept_id, learner_id)
);
"""

TRIGGERS_SQL = """
CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, content, title) VALUES (new.rowid, new.content, new.title);
END;

CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, content, title) VALUES('delete', old.rowid, old.content, old.title);
END;

CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, content, title) VALUES('delete', old.rowid, old.content, old.title);
    INSERT INTO chunks_fts(rowid, content, title) VALUES (new.rowid, new.content, new.title);
END;
"""


def get_conn():
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(DB_PATH)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA synchronous=NORMAL")
        _local.conn.execute("PRAGMA cache_size=-8000")
    return _local.conn


def init_db():
    conn = get_conn()
    conn.executescript(SCHEMA_SQL)
    # Migrate: add email/password_hash columns if missing
    for col in ("email", "password_hash"):
        try:
            conn.execute(f"ALTER TABLE learner ADD COLUMN {col} TEXT")
        except Exception:
            pass
    conn.commit()
    rebuild_fts_if_needed()
    try:
        from badges import init_badges_table
        init_badges_table()
    except Exception:
        pass
    try:
        from mock_exam import init_exam_tables
        init_exam_tables()
    except Exception:
        pass
    try:
        from spaced_repetition import init_review_tables
        init_review_tables()
    except Exception:
        pass


def rebuild_fts_if_needed():
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    fts_count = conn.execute("SELECT COUNT(*) FROM chunks_fts").fetchone()[0]
    if count > 0 and fts_count == 0:
        conn.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')")
        conn.commit()


def close():
    if hasattr(_local, "conn") and _local.conn:
        _local.conn.close()
        _local.conn = None
