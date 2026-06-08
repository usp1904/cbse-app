import math
import random
from database import get_conn

PILLARS = {
    "main-subjects": {"name": "Main Subjects", "icon": "📚", "color": "#0f3460", "description": "Video lessons and theory for all CBSE subjects"},
    "practice": {"name": "Practice", "icon": "📝", "color": "#e94560", "description": "Online MCQ tests, past year papers, and worksheets"},
    "revision": {"name": "Revision", "icon": "🔄", "color": "#16a34a", "description": "Chapter notes, mind maps, and flashcards"},
    "skill-building": {"name": "Skill Building", "icon": "🌟", "color": "#f59e0b", "description": "Vedic maths, coding, and mental maths"},
}


def init_pillar_tables():
    conn = get_conn()
    for pid, p in PILLARS.items():
        conn.execute(
            "INSERT OR IGNORE INTO content_pillars (id, name, icon, description, color, sort_order) VALUES (?, ?, ?, ?, ?, ?)",
            (pid, p["name"], p["icon"], p["description"], p["color"], list(PILLARS.keys()).index(pid)),
        )
    conn.commit()


def get_pillars():
    conn = get_conn()
    return conn.execute("SELECT * FROM content_pillars ORDER BY sort_order").fetchall()


def assign_to_pillar(pillar_id, content_type, content_id, label=None, sort_order=0):
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO pillar_content (pillar_id, content_type, content_id, label, sort_order) VALUES (?, ?, ?, ?, ?)",
        (pillar_id, content_type, content_id, label, sort_order),
    )
    conn.commit()


def get_pillar_content(pillar_id, limit=50):
    conn = get_conn()
    rows = conn.execute(
        "SELECT pc.* FROM pillar_content pc WHERE pc.pillar_id = ? ORDER BY pc.sort_order LIMIT ?",
        (pillar_id, limit),
    ).fetchall()
    enriched = []
    for r in rows:
        item = dict(r)
        if r["content_type"] == "subject":
            subj = conn.execute("SELECT id, name, board_id FROM subjects WHERE id = ?", (r["content_id"],)).fetchone()
            if subj:
                item["name"] = subj["name"]
                item["board_id"] = subj["board_id"]
                item["url"] = f"/board/{subj['board_id']}/{subj['id']}"
        elif r["content_type"] == "chapter":
            ch = conn.execute("SELECT id, num, title, subject_id FROM chapters WHERE id = ?", (r["content_id"],)).fetchone()
            if ch:
                item["name"] = f"Ch {ch['num']}: {ch['title']}"
                item["url"] = f"/chapter/{ch['id']}"
        elif r["content_type"] == "topic":
            t = conn.execute("SELECT id, title, chapter_id FROM topics WHERE id = ?", (r["content_id"],)).fetchone()
            if t:
                item["name"] = t["title"]
                item["url"] = f"/topic/{t['id']}"
        elif r["content_type"] == "resource":
            item["name"] = item.get("label") or r["content_id"]
            item["url"] = r["content_id"]
        if item.get("name"):
            enriched.append(item)
    return enriched


def add_concept(concept_id, subject_id, concept_name, difficulty=1, parent_concept_id=None, description="",
                chapter_id=None, topic_id=None):
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO knowledge_graph (id, subject_id, chapter_id, topic_id, concept_name, difficulty, parent_concept_id, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (concept_id, subject_id, chapter_id, topic_id, concept_name, difficulty, parent_concept_id, description),
    )
    conn.commit()


def get_concept(concept_id):
    conn = get_conn()
    c = conn.execute("SELECT * FROM knowledge_graph WHERE id = ?", (concept_id,)).fetchone()
    if not c:
        return None
    c = dict(c)
    c["children"] = [dict(r) for r in conn.execute(
        "SELECT * FROM knowledge_graph WHERE parent_concept_id = ? ORDER BY difficulty", (concept_id,)
    ).fetchall()]
    c["mastery"] = get_mastery(concept_id)
    return c


def get_subject_graph(subject_id):
    conn = get_conn()
    top_level = conn.execute(
        "SELECT * FROM knowledge_graph WHERE subject_id = ? AND parent_concept_id IS NULL ORDER BY difficulty",
        (subject_id,),
    ).fetchall()
    result = []
    for c in top_level:
        entry = dict(c)
        entry["children"] = [dict(r) for r in conn.execute(
            "SELECT * FROM knowledge_graph WHERE parent_concept_id = ? ORDER BY difficulty", (c["id"],)
        ).fetchall()]
        entry["mastery"] = get_mastery(c["id"])
        result.append(entry)
    return result


def get_full_graph():
    conn = get_conn()
    subjects = conn.execute("SELECT id, name FROM subjects WHERE board_id='cbse'").fetchall()
    result = {}
    for s in subjects:
        result[s["name"]] = get_subject_graph(s["id"])
    return result


def get_mastery(concept_id, learner_id=1):
    conn = get_conn()
    m = conn.execute(
        "SELECT * FROM user_mastery WHERE concept_id = ? AND learner_id = ?",
        (concept_id, learner_id),
    ).fetchone()
    if not m:
        return {"mastery_level": 0.0, "attempts": 0, "correct": 0, "total": 0, "streak": 0}
    return dict(m)


def record_attempt(concept_id, correct_count, total_count, learner_id=1):
    conn = get_conn()
    existing = conn.execute(
        "SELECT * FROM user_mastery WHERE concept_id = ? AND learner_id = ?",
        (concept_id, learner_id),
    ).fetchone()

    if existing:
        new_total = existing["total"] + total_count
        new_correct = existing["correct"] + correct_count
        new_attempts = existing["attempts"] + 1
        mastery = new_correct / max(new_total, 1)
        streak = existing["streak"] + 1 if correct_count == total_count else 0
        conn.execute(
            "UPDATE user_mastery SET mastery_level=?, attempts=?, correct=?, total=?, last_practiced=datetime('now','localtime'), streak=? WHERE concept_id=? AND learner_id=?",
            (mastery, new_attempts, new_correct, new_total, streak, concept_id, learner_id),
        )
    else:
        mastery = correct_count / max(total_count, 1)
        conn.execute(
            "INSERT INTO user_mastery (concept_id, learner_id, mastery_level, attempts, correct, total, last_practiced, streak) VALUES (?, ?, ?, 1, ?, ?, datetime('now','localtime'), ?)",
            (concept_id, learner_id, mastery, correct_count, total_count, 1 if correct_count == total_count else 0),
        )
    conn.commit()
    return get_mastery(concept_id, learner_id)


def get_weaknesses(learner_id=1, threshold=0.4):
    conn = get_conn()
    conn.row_factory = lambda c, r: dict(sqlite3.Row(c, r))
    import sqlite3
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT kg.*, um.mastery_level, um.attempts, um.correct, um.total "
        "FROM knowledge_graph kg "
        "LEFT JOIN user_mastery um ON kg.id = um.concept_id AND um.learner_id = ? "
        "WHERE um.mastery_level IS NULL OR um.mastery_level < ? "
        "ORDER BY COALESCE(um.mastery_level, 0) ASC, kg.difficulty ASC",
        (learner_id, threshold),
    ).fetchall()
    return [dict(r) for r in rows]


def get_strengths(learner_id=1, threshold=0.8):
    conn = get_conn()
    import sqlite3
    rows = conn.execute(
        "SELECT kg.*, um.mastery_level, um.attempts "
        "FROM knowledge_graph kg "
        "JOIN user_mastery um ON kg.id = um.concept_id AND um.learner_id = ? "
        "WHERE um.mastery_level >= ? "
        "ORDER BY um.mastery_level DESC",
        (learner_id, threshold),
    ).fetchall()
    return [dict(r) for r in rows]


def get_recommended_next(learner_id=1, count=5):
    conn = get_conn()
    weak = get_weaknesses(learner_id, threshold=0.5)
    unstarted = conn.execute(
        "SELECT kg.* FROM knowledge_graph kg "
        "LEFT JOIN user_mastery um ON kg.id = um.concept_id AND um.learner_id = ? "
        "WHERE um.id IS NULL AND kg.difficulty <= 3 "
        "ORDER BY kg.difficulty ASC LIMIT ?",
        (learner_id, count),
    ).fetchall()
    return [dict(r) for r in unstarted[:count]] + weak[:count]


def seed_knowledge_graph():
    conn = get_conn()
    existing = conn.execute("SELECT COUNT(*) FROM knowledge_graph").fetchone()[0]
    if existing > 0:
        return

    concepts = [
        # Mathematics
        ("math-numbers", "mathematics", "Number Systems", 1, None, "Real numbers, rational and irrational numbers"),
        ("math-euclid", "mathematics", "Euclid's Division Lemma", 1, "math-numbers", "Fundamental lemma for division"),
        ("math-arithmetic", "mathematics", "Fundamental Theorem of Arithmetic", 2, "math-euclid", "Prime factorization"),
        ("math-polynomials", "mathematics", "Polynomials", 2, "math-numbers", "Zeroes, coefficients, division algorithm"),
        ("math-linear-eq", "mathematics", "Linear Equations", 2, "math-numbers", "Pair of linear equations in two variables"),
        ("math-quadratic", "mathematics", "Quadratic Equations", 3, "math-polynomials", "Factorisation, completing square, nature of roots"),
        ("math-ap", "mathematics", "Arithmetic Progressions", 2, "math-numbers", "nth term, sum of n terms"),
        ("math-triangles", "mathematics", "Triangles", 3, "math-polynomials", "Similarity, Pythagoras theorem"),
        ("math-coordinate", "mathematics", "Coordinate Geometry", 2, "math-numbers", "Distance formula, section formula"),
        ("math-trigonometry", "mathematics", "Trigonometry", 3, "math-triangles", "Ratios, identities, heights and distances"),
        ("math-circles", "mathematics", "Circles", 3, "math-triangles", "Tangents, secants"),
        ("math-mensuration", "mathematics", "Mensuration", 4, "math-quadratic", "Areas, surface areas, volumes"),
        ("math-statistics", "mathematics", "Statistics", 3, "math-numbers", "Mean, mode, median, ogive"),
        ("math-probability", "mathematics", "Probability", 4, "math-statistics", "Theoretical approach, complementary events"),

        # Science
        ("sci-chemical", "science", "Chemical Reactions", 1, None, "Types of reactions, balancing equations"),
        ("sci-acids", "science", "Acids, Bases and Salts", 2, "sci-chemical", "pH scale, neutralisation, salts"),
        ("sci-metals", "science", "Metals and Non-metals", 2, "sci-chemical", "Properties, reactivity series, corrosion"),
        ("sci-carbon", "science", "Carbon and its Compounds", 3, "sci-chemical", "Covalent bonds, functional groups"),
        ("sci-life", "science", "Life Processes", 1, None, "Nutrition, respiration, transportation, excretion"),
        ("sci-control", "science", "Control and Coordination", 2, "sci-life", "Nervous system, hormones, plant coordination"),
        ("sci-reproduction", "science", "Reproduction", 3, "sci-life", "Asexual, sexual, human reproduction"),
        ("sci-heredity", "science", "Heredity and Evolution", 3, "sci-reproduction", "Mendelian genetics, evolution"),
        ("sci-light", "science", "Light", 2, None, "Reflection, refraction, lenses"),
        ("sci-electricity", "science", "Electricity", 3, "sci-light", "Ohm's law, resistance, power"),
        ("sci-magnetism", "science", "Magnetic Effects", 3, "sci-electricity", "Magnetic field, motor, generator"),
        ("sci-environment", "science", "Our Environment", 2, None, "Ecosystem, food chains, waste management"),

        # English
        ("eng-prose", "english", "Prose Comprehension", 1, None, "Reading and understanding prose passages"),
        ("eng-poetry", "english", "Poetry Analysis", 2, "eng-prose", "Poetic devices, themes and interpretation"),
        ("eng-writing", "english", "Writing Skills", 2, None, "Letter writing, article, story writing"),
        ("eng-grammar", "english", "Grammar", 1, None, "Tenses, voice, narration, modals"),
        ("eng-literature", "english", "Literature", 2, "eng-prose", "First Flight and Footprints without Feet"),

        # Social Science
        ("ss-history", "social-science", "History", 1, None, "Nationalism, world wars, industrialization"),
        ("ss-geography", "social-science", "Geography", 1, None, "Resources, agriculture, industries"),
        ("ss-political", "social-science", "Political Science", 2, "ss-history", "Democracy, federalism, political parties"),
        ("ss-economics", "social-science", "Economics", 2, "ss-geography", "Development, sectors, money and credit"),
    ]

    seen_ids = set()
    for c in concepts:
        cid, sid, name, diff, parent, desc = c
        if cid in seen_ids:
            continue
        seen_ids.add(cid)
        conn.execute(
            "INSERT OR IGNORE INTO knowledge_graph (id, subject_id, concept_name, difficulty, parent_concept_id, description) VALUES (?, ?, ?, ?, ?, ?)",
            (cid, sid, name, diff, parent, desc),
        )
    conn.commit()


def seed_pillar_content():
    conn = get_conn()
    existing = conn.execute("SELECT COUNT(*) FROM pillar_content").fetchone()[0]
    if existing > 0:
        return

    cbse_subjects = conn.execute("SELECT id, name FROM subjects WHERE board_id='cbse'").fetchall()
    for s in cbse_subjects:
        assign_to_pillar("main-subjects", "subject", s["id"], s["name"])

    chapters = conn.execute("SELECT id, title, subject_id FROM chapters WHERE board_id='cbse' ORDER BY subject_id, num").fetchall()
    for ch in chapters:
        subj = conn.execute("SELECT name FROM subjects WHERE id = ?", (ch["subject_id"],)).fetchone()
        assign_to_pillar("main-subjects", "chapter", ch["id"], f"{subj['name']} - Ch: {ch['title']}")

    assign_to_pillar("practice", "resource", "/exams", "Mock Board Exams")
    assign_to_pillar("practice", "resource", "/cbq", "Case-Based Questions")
    assign_to_pillar("practice", "resource", "/api/question-bank", "Question Bank")
    assign_to_pillar("practice", "resource", "/quiz/", "Chapter Quizzes")
    assign_to_pillar("practice", "resource", "/api/model-paper", "Model Papers")

    assign_to_pillar("revision", "resource", "/review", "Spaced Repetition Review")
    assign_to_pillar("revision", "resource", "/mindmap/", "Mind Maps")
    assign_to_pillar("revision", "resource", "/notes/", "Chapter Notes")
    assign_to_pillar("revision", "resource", "/api/notebooklm", "NotebookLM Export")
    revision_chapters = conn.execute(
        "SELECT id, title, subject_id FROM chapters WHERE board_id='cbse' LIMIT 30"
    ).fetchall()
    for ch in revision_chapters:
        assign_to_pillar("revision", "chapter", ch["id"], f"Notes for {ch['title']}")

    assign_to_pillar("skill-building", "resource", "/electives", "Skill Electives Hub")
    assign_to_pillar("skill-building", "resource", "/electives/vedic-maths", "Vedic Mathematics")
    assign_to_pillar("skill-building", "resource", "/electives/mental-maths", "Mental Maths")
    assign_to_pillar("skill-building", "resource", "/electives/python-basics", "Python Programming")
    assign_to_pillar("skill-building", "resource", "/competitive", "Competitive Exam Prep")
    conn.commit()
