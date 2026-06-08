import random
import json
from datetime import date, timedelta
from database import get_conn
from question_bank import get_questions


CHALLENGE_TYPES = [
    {"id": "quick_5", "name": "Quick 5", "desc": "Answer 5 questions fast", "count": 5, "multiplier": 2},
    {"id": "mixed_bag", "name": "Mixed Bag", "desc": "Mix of all difficulty levels", "count": 7, "multiplier": 3},
    {"id": "challenge_10", "name": "Daily Challenge", "desc": "10 questions across subjects", "count": 10, "multiplier": 4},
]


def get_today_challenge():
    conn = get_conn()
    today = date.today().isoformat()
    challenge = conn.execute(
        "SELECT * FROM daily_challenges WHERE challenge_date = ?", (today,)
    ).fetchone()
    if challenge:
        return dict(challenge)
    return _generate_challenge(today)


def _generate_challenge(today_str):
    conn = get_conn()
    challenge_type = random.choice(CHALLENGE_TYPES)
    boards = ["cbse", "ap", "ts"]
    board_weights = {"cbse": 0.5, "ap": 0.25, "ts": 0.25}
    board_id = random.choices(boards, weights=[board_weights[b] for b in boards])[0]
    subjects_map = {
        "cbse": ["mathematics", "science"],
        "ap": ["ap-mathematics", "ap-physical-science"],
        "ts": ["ts-mathematics", "ts-physical-science"],
    }
    subject_ids = subjects_map.get(board_id, ["mathematics"])
    subject_id = random.choice(subject_ids)

    questions = get_questions(board_id=board_id, subject_id=subject_id,
                              question_type=None, limit=challenge_type["count"])
    if len(questions) < challenge_type["count"]:
        questions = get_questions(board_id=board_id, subject_id=subject_id,
                                  question_type=None, limit=50)[:challenge_type["count"]]

    question_ids = [q["id"] for q in questions]
    bonus_xp = challenge_type["multiplier"] * 5 * challenge_type["count"]

    conn.execute(
        "INSERT INTO daily_challenges (challenge_date, board_id, subject_id, type_id, question_ids, bonus_xp, completed) "
        "VALUES (?, ?, ?, ?, ?, ?, 0)",
        (today_str, board_id, subject_id, challenge_type["id"],
         json.dumps(question_ids), bonus_xp),
    )
    conn.commit()
    return {
        "challenge_date": today_str,
        "board_id": board_id,
        "subject_id": subject_id,
        "type_id": challenge_type["id"],
        "type_name": challenge_type["name"],
        "type_desc": challenge_type["desc"],
        "question_ids": question_ids,
        "bonus_xp": bonus_xp,
        "completed": 0,
    }


def complete_challenge(score, total):
    conn = get_conn()
    today = date.today().isoformat()
    challenge = conn.execute(
        "SELECT * FROM daily_challenges WHERE challenge_date = ?", (today,)
    ).fetchone()
    if not challenge or challenge["completed"]:
        return 0
    challenge = dict(challenge)
    pct = score / max(total, 1)
    earned_xp = int(challenge["bonus_xp"] * pct)
    from gamification import add_xp, check_streak
    add_xp(earned_xp, "daily_challenge", f"Daily challenge: {score}/{total}")
    streak = check_streak()
    if pct >= 0.8:
        streak_bonus = streak * 2
        add_xp(streak_bonus, "streak_bonus", f"Challenge streak bonus x{streak}")
        earned_xp += streak_bonus
    conn.execute(
        "UPDATE daily_challenges SET completed = 1, score = ?, total = ?, xp_earned = ? WHERE challenge_date = ?",
        (score, total, earned_xp, today),
    )
    conn.commit()
    return earned_xp


def get_challenge_history(limit=7):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM daily_challenges ORDER BY challenge_date DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]
