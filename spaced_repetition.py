import datetime
from database import get_conn

def init_review_tables():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS review_schedule (
            topic_id TEXT PRIMARY KEY,
            ease_factor REAL DEFAULT 2.5,
            interval_days INTEGER DEFAULT 0,
            repetitions INTEGER DEFAULT 0,
            next_review_date TEXT,
            last_reviewed TEXT,
            last_quality INTEGER,
            FOREIGN KEY (topic_id) REFERENCES topics(id)
        )
    """)
    conn.commit()


def _sm2_calc(quality, prev_ease, prev_interval, prev_repetitions):
    if quality < 3:
        return {
            "repetitions": 0,
            "interval": 1,
            "ease_factor": prev_ease,
            "next_review": (datetime.date.today() + datetime.timedelta(days=1)).isoformat(),
        }
    if prev_repetitions == 0:
        interval = 1
    elif prev_repetitions == 1:
        interval = 6
    else:
        interval = round(prev_interval * prev_ease)
    ease = max(1.3, prev_ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
    next_review = (datetime.date.today() + datetime.timedelta(days=interval)).isoformat()
    return {
        "repetitions": prev_repetitions + 1,
        "interval": interval,
        "ease_factor": round(ease, 2),
        "next_review": next_review,
    }


def schedule_review(topic_id, quality):
    conn = get_conn()
    existing = conn.execute(
        "SELECT * FROM review_schedule WHERE topic_id = ?", (topic_id,)
    ).fetchone()
    prev_ease = existing["ease_factor"] if existing else 2.5
    prev_interval = existing["interval_days"] if existing else 0
    prev_repetitions = existing["repetitions"] if existing else 0
    result = _sm2_calc(quality, prev_ease, prev_interval, prev_repetitions)
    conn.execute(
        """INSERT INTO review_schedule (topic_id, ease_factor, interval_days,
           repetitions, next_review_date, last_reviewed, last_quality)
           VALUES (?, ?, ?, ?, ?, date('now','localtime'), ?)
           ON CONFLICT(topic_id) DO UPDATE SET
           ease_factor=excluded.ease_factor,
           interval_days=excluded.interval_days,
           repetitions=excluded.repetitions,
           next_review_date=excluded.next_review_date,
           last_reviewed=date('now','localtime'),
           last_quality=excluded.last_quality""",
        (
            topic_id,
            result["ease_factor"],
            result["interval"],
            result["repetitions"],
            result["next_review"],
            quality,
        ),
    )
    conn.commit()
    from gamification import add_xp
    add_xp(5, "review", f"Reviewed topic (quality {quality}/5)", topic_id=topic_id)
    return result


def get_due_reviews(limit=20):
    conn = get_conn()
    rows = conn.execute(
        """SELECT rs.*, t.title as topic_title, t.chapter_id, ch.title as chapter_title,
                  ch.num as chapter_num, ch.board_id
           FROM review_schedule rs
           JOIN topics t ON rs.topic_id = t.id
           JOIN chapters ch ON t.chapter_id = ch.id
           WHERE rs.next_review_date <= date('now','localtime')
           ORDER BY rs.next_review_date ASC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_review_stats():
    conn = get_conn()
    due = conn.execute(
        "SELECT COUNT(*) FROM review_schedule WHERE next_review_date <= date('now','localtime')"
    ).fetchone()[0]
    total = conn.execute("SELECT COUNT(*) FROM review_schedule").fetchone()[0]
    today_due = conn.execute(
        "SELECT COUNT(*) FROM review_schedule WHERE next_review_date = date('now','localtime')"
    ).fetchone()[0]
    return {"due": due, "total": total, "today_due": today_due}


def get_topic_review_status(topic_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM review_schedule WHERE topic_id = ?", (topic_id,)
    ).fetchone()
    if not row:
        return {"scheduled": False}
    return dict(row)
