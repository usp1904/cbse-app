import math
import logging
from datetime import datetime, date
from database import get_conn

log = logging.getLogger("cbse.gamification")

LEVEL_THRESHOLDS = [0, 100, 280, 520, 840, 1260, 1820, 2560, 3520, 4760]
LIFE_REFILL_MINUTES = 20
MAX_LIVES = 5
STREAK_BONUS_MULTIPLIER = 2
LIFELINE_XP_COST = 3


def get_learner():
    conn = get_conn()
    learner = conn.execute("SELECT * FROM learner WHERE id = 1").fetchone()
    if not learner:
        conn.execute(
            "INSERT INTO learner (id,name,xp,level,streak,lives,max_lives,last_active,last_life_refill) "
            "VALUES (1,'Learner',0,1,0,5,5,date('now','localtime'),datetime('now','localtime'))"
        )
        conn.commit()
        learner = conn.execute("SELECT * FROM learner WHERE id = 1").fetchone()
    return dict(learner)


def add_xp(amount, reason, detail="", chapter_id="", topic_id=""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO xp_events (xp, reason, detail, chapter_id, topic_id) VALUES (?, ?, ?, ?, ?)",
        (amount, reason, detail, chapter_id, topic_id),
    )
    if amount > 0:
        conn.execute("UPDATE learner SET xp = xp + ?, total_xp_earned = total_xp_earned + ? WHERE id = 1",
                     (amount, amount))
    else:
        conn.execute("UPDATE learner SET xp = xp + ? WHERE id = 1", (amount,))
    learner = conn.execute("SELECT xp FROM learner WHERE id = 1").fetchone()
    new_level = calculate_level(learner["xp"])
    conn.execute("UPDATE learner SET level = ? WHERE id = 1", (new_level,))
    conn.commit()
    return new_level


def calculate_level(xp):
    for i, threshold in enumerate(LEVEL_THRESHOLDS):
        if xp < threshold:
            return i
    return len(LEVEL_THRESHOLDS)


def get_level_info(level):
    idx = min(level, len(LEVEL_THRESHOLDS) - 1)
    current = LEVEL_THRESHOLDS[idx]
    next_threshold = LEVEL_THRESHOLDS[idx + 1] if idx + 1 < len(LEVEL_THRESHOLDS) else current + 500
    return {"level": level, "current_xp": 0, "xp_for_next": next_threshold - current}


def check_streak():
    conn = get_conn()
    learner = get_learner()
    today = date.today().isoformat()
    last_active = learner.get("last_active", "")

    if last_active == today:
        return learner["streak"]

    yesterday = date.today()
    from datetime import timedelta
    yesterday = (yesterday - timedelta(days=1)).isoformat()

    if last_active == yesterday:
        new_streak = learner["streak"] + 1
    else:
        new_streak = 1

    longest = max(new_streak, learner["longest_streak"])
    conn.execute(
        "UPDATE learner SET streak = ?, longest_streak = ?, last_active = ? WHERE id = 1",
        (new_streak, longest, today),
    )
    conn.commit()

    bonus_xp = new_streak * STREAK_BONUS_MULTIPLIER
    add_xp(bonus_xp, "streak_bonus", f"Day {new_streak} streak bonus")
    return new_streak


def use_life():
    conn = get_conn()
    learner = get_learner()
    if learner["lives"] <= 0:
        return False, 0
    new_lives = learner["lives"] - 1
    conn.execute("UPDATE learner SET lives = ? WHERE id = 1", (new_lives,))
    conn.commit()
    return True, new_lives


def refill_lives():
    conn = get_conn()
    learner = get_learner()
    if learner["lives"] >= MAX_LIVES:
        return learner["lives"]

    last_refill = learner.get("last_life_refill", "")
    try:
        last_time = datetime.strptime(last_refill, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        last_time = datetime.now()

    elapsed_minutes = (datetime.now() - last_time).total_seconds() / 60
    lives_to_add = int(elapsed_minutes / LIFE_REFILL_MINUTES)

    if lives_to_add > 0:
        new_lives = min(MAX_LIVES, learner["lives"] + lives_to_add)
        conn.execute(
            "UPDATE learner SET lives = ?, last_life_refill = datetime('now','localtime') WHERE id = 1",
            (new_lives,),
        )
        conn.commit()
        return new_lives
    return learner["lives"]


def use_lifeline(lifeline_type, chapter_id="", topic_id=""):
    conn = get_conn()
    cost = LIFELINE_XP_COST
    conn.execute(
        "INSERT INTO lifeline_log (lifeline_type, chapter_id, topic_id, xp_cost) VALUES (?, ?, ?, ?)",
        (lifeline_type, chapter_id, topic_id, cost),
    )
    add_xp(-cost, "lifeline_used", f"Used {lifeline_type} (-{cost} XP)")
    return cost


def record_quiz_result(correct, total, chapter_id=""):
    conn = get_conn()
    xp_gained = correct * 5
    if correct == total and total > 0:
        xp_gained += 20
    add_xp(xp_gained, "quiz", f"Quiz: {correct}/{total} correct", chapter_id=chapter_id)
    conn.execute(
        "UPDATE learner SET quizzes_taken = quizzes_taken + 1, quiz_correct = quiz_correct + ?, quiz_total = quiz_total + ? WHERE id = 1",
        (correct, total),
    )
    conn.commit()
    return xp_gained


def mark_topic_progress(chapter_id, topic_id, status, xp=10):
    conn = get_conn()
    existing = conn.execute(
        "SELECT id FROM learning_progress WHERE chapter_id = ? AND topic_id = ?",
        (chapter_id, topic_id),
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE learning_progress SET status = ?, xp_earned = xp_earned + ?, last_accessed = datetime('now','localtime'), completions = completions + 1 WHERE id = ?",
            (status, xp, existing["id"]),
        )
    else:
        conn.execute(
            "INSERT INTO learning_progress (chapter_id, topic_id, status, xp_earned, last_accessed, completions) VALUES (?, ?, ?, ?, datetime('now','localtime'), 1)",
            (chapter_id, topic_id, status, xp),
        )
    add_xp(xp, "study", f"Studied topic", chapter_id=chapter_id, topic_id=topic_id)
    conn.execute(
        "UPDATE learner SET topics_completed = (SELECT COUNT(*) FROM learning_progress WHERE status = 'completed') WHERE id = 1"
    )
    conn.commit()


def get_leaderboard_data():
    conn = get_conn()
    learner = get_learner()
    return {
        "xp": learner["xp"],
        "level": learner["level"],
        "streak": learner["streak"],
        "longest_streak": learner["longest_streak"],
        "lives": learner["lives"],
        "max_lives": MAX_LIVES,
        "topics_completed": learner["topics_completed"],
        "quizzes_taken": learner["quizzes_taken"],
        "quiz_accuracy": round(learner["quiz_correct"] / max(learner["quiz_total"], 1) * 100, 1),
        "next_level_xp": LEVEL_THRESHOLDS[min(learner["level"], len(LEVEL_THRESHOLDS) - 1) + 1]
        if learner["level"] < len(LEVEL_THRESHOLDS) - 1
        else LEVEL_THRESHOLDS[-1] + 500,
        "current_level_xp": LEVEL_THRESHOLDS[min(learner["level"], len(LEVEL_THRESHOLDS) - 1)],
        "lifeline_cost": LIFELINE_XP_COST,
        "life_refill_minutes": LIFE_REFILL_MINUTES,
    }
