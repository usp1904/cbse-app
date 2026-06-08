import random
from datetime import datetime, date
from database import get_conn

BADGES = [
    {"id": "first_steps", "name": "First Steps", "desc": "Complete your first topic", "icon": "🌱",
     "nep_skill": "Learning by Doing", "condition": lambda l: l["topics_completed"] >= 1},
    {"id": "quick_learner", "name": "Quick Learner", "desc": "Complete 10 topics", "icon": "⚡",
     "nep_skill": "Self-Awareness", "condition": lambda l: l["topics_completed"] >= 10},
    {"id": "scholar", "name": "Scholar", "desc": "Complete 50 topics", "icon": "🎓",
     "nep_skill": "Critical Thinking", "condition": lambda l: l["topics_completed"] >= 50},
    {"id": "quiz_master", "name": "Quiz Master", "desc": "Score 100% on any quiz", "icon": "🏆",
     "nep_skill": "Problem Solving", "condition": lambda l: False},
    {"id": "streak_3", "name": "Dedicated", "desc": "3-day learning streak", "icon": "🔥",
     "nep_skill": "Discipline", "condition": lambda l: l["streak"] >= 3},
    {"id": "streak_7", "name": "Consistent", "desc": "7-day learning streak", "icon": "💪",
     "nep_skill": "Consistency", "condition": lambda l: l["streak"] >= 7},
    {"id": "streak_30", "name": "Relentless", "desc": "30-day learning streak", "icon": "🌟",
     "nep_skill": "Perseverance", "condition": lambda l: l["streak"] >= 30},
    {"id": "level_5", "name": "Apprentice", "desc": "Reach Level 5", "icon": "⭐",
     "nep_skill": "Self-Development", "condition": lambda l: l["level"] >= 5},
    {"id": "level_10", "name": "Expert", "desc": "Reach Level 10", "icon": "👑",
     "nep_skill": "Mastery", "condition": lambda l: l["level"] >= 10},
    {"id": "math_wiz", "name": "Math Wizard", "desc": "Complete all Math chapters", "icon": "🔢",
     "nep_skill": "Quantitative Reasoning", "condition": lambda l: False},
    {"id": "science_star", "name": "Science Star", "desc": "Complete all Science chapters", "icon": "🔬",
     "nep_skill": "Scientific Temper", "condition": lambda l: False},
    {"id": "perfectionist", "name": "Perfectionist", "desc": "Get 3 perfect quiz scores", "icon": "💎",
     "nep_skill": "Excellence", "condition": lambda l: False},
    {"id": "explorer", "name": "Explorer", "desc": "Study topics from all 3 boards", "icon": "🌍",
     "nep_skill": "Global Citizenship", "condition": lambda l: False},
    {"id": "mock_exam_veteran", "name": "Mock Exam Veteran", "desc": "Complete 5 mock exams", "icon": "📝",
     "nep_skill": "Assessment & Evaluation", "condition": lambda l: False},
    {"id": "champion", "name": "Champion", "desc": "Score 90%+ in a mock exam", "icon": "🥇",
     "nep_skill": "Achievement", "condition": lambda l: False},
]


def init_badges_table():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS badges (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            icon TEXT,
            nep_skill TEXT
        );
        CREATE TABLE IF NOT EXISTS learner_badges (
            learner_id INTEGER DEFAULT 1,
            badge_id TEXT NOT NULL,
            earned_at TEXT DEFAULT (datetime('now','localtime')),
            PRIMARY KEY (learner_id, badge_id)
        );
    """)
    for b in BADGES:
        conn.execute(
            "INSERT OR IGNORE INTO badges (id, name, description, icon, nep_skill) VALUES (?, ?, ?, ?, ?)",
            (b["id"], b["name"], b["desc"], b["icon"], b["nep_skill"]),
        )
    conn.commit()


def check_and_award_badges():
    conn = get_conn()
    learner = conn.execute("SELECT * FROM learner WHERE id = 1").fetchone()
    if not learner:
        return []
    learner = dict(learner)
    new_badges = []
    for badge in BADGES:
        existing = conn.execute(
            "SELECT 1 FROM learner_badges WHERE learner_id = 1 AND badge_id = ?",
            (badge["id"],),
        ).fetchone()
        if existing:
            continue
        try:
            if badge["condition"](learner):
                conn.execute(
                    "INSERT INTO learner_badges (learner_id, badge_id) VALUES (1, ?)",
                    (badge["id"],),
                )
                new_badges.append(badge)
        except Exception:
            continue
    if new_badges:
        conn.commit()
    return new_badges


def get_earned_badges():
    conn = get_conn()
    rows = conn.execute("""
        SELECT b.*, lb.earned_at FROM badges b
        JOIN learner_badges lb ON b.id = lb.badge_id
        WHERE lb.learner_id = 1
        ORDER BY lb.earned_at DESC
    """).fetchall()
    return [dict(r) for r in rows]


def get_nep_skills_summary():
    conn = get_conn()
    earned = get_earned_badges()
    skills = {}
    for b in earned:
        skill = b.get("nep_skill", "Other")
        if skill not in skills:
            skills[skill] = {"count": 0, "badges": []}
        skills[skill]["count"] += 1
        skills[skill]["badges"].append(b["name"])
    return skills


def award_quiz_perfect():
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO learner_badges (learner_id, badge_id) VALUES (1, 'quiz_master')"
    )
    conn.commit()


def award_mock_complete():
    conn = get_conn()
    learner = conn.execute("SELECT * FROM learner WHERE id = 1").fetchone()
    if not learner:
        return
    conn.execute("UPDATE learner SET mock_exams_taken = COALESCE(mock_exams_taken, 0) + 1 WHERE id = 1")
    conn.commit()
    count = conn.execute("SELECT COALESCE(mock_exams_taken, 0) as c FROM learner WHERE id = 1").fetchone()["c"]
    if count >= 5:
        conn.execute(
            "INSERT OR IGNORE INTO learner_badges (learner_id, badge_id) VALUES (1, 'mock_exam_veteran')"
        )
        conn.commit()
