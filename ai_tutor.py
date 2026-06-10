import re
import json
import random
from datetime import datetime, timedelta
from database import get_conn

QUESTION_TEMPLATES = {
    'definition': [
        "Can you explain what {concept} means in your own words?",
        "How would you define {concept} to a classmate?",
        "What are the key features of {concept}?"
    ],
    'formula': [
        "Explain the meaning of {formula} and when you would apply it.",
        "How would you derive or prove {formula}?",
        "What real-world situation does {formula} help us understand?"
    ],
    'example': [
        "Why does the solution method in this example work?",
        "Can you think of a different approach to solve this?",
        "What principle is being demonstrated in this example?"
    ],
    'comparison': [
        "How are {c1} and {c2} related? What's the connection?",
        "What distinguishes {c1} from {c2}?",
        "When would you choose {c1} over {c2}?"
    ],
    'application': [
        "How would you use {concept} to solve a practical problem?",
        "Can you find an everyday example of {concept}?",
        "If you were teaching {concept}, what real example would you use?"
    ],
    'analysis': [
        "Why is {concept} important in understanding this topic?",
        "What assumptions underlie {concept}?",
        "What would change if {concept} were different?"
    ]
}

STARTER_PROMPTS = [
    "Let's explore this topic together. Here's a question to get you thinking:",
    "Before we dive deeper, consider this:",
    "Think about this for a moment:",
    "Here's an interesting question to test your understanding:",
    "Can you work through this idea?"
]

def init_tutor_tables():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tutor_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id TEXT NOT NULL,
            started_at TEXT DEFAULT (datetime('now','localtime')),
            ended_at TEXT,
            questions_asked INTEGER DEFAULT 0,
            correct_answers INTEGER DEFAULT 0,
            completed INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS tutor_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            question_type TEXT,
            student_answer TEXT,
            model_answer TEXT NOT NULL,
            self_assessment TEXT,
            remedial_shown INTEGER DEFAULT 0,
            asked_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (session_id) REFERENCES tutor_sessions(id)
        );
    """)
    conn.commit()

def extract_key_concepts(content):
    concepts = {'bold': [], 'caps': [], 'formulas': [], 'numbers': []}
    if not content:
        return concepts
    bold = re.findall(r'\*\*(.*?)\*\*', content)
    concepts['bold'] = list(set(bold))
    caps = re.findall(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', content)
    concepts['caps'] = list(set(caps))
    formulas = re.findall(r'[\w\s]+[=+\-×÷√][\w\s^²³₁₂₃₄₅₆₇₈₉₀()]+', content)
    concepts['formulas'] = [f.strip() for f in list(set(formulas)) if len(f.strip()) > 2]
    return concepts

def generate_questions(topic_title, topic_content, chunks, count=3):
    concepts = extract_key_concepts(topic_content)
    questions = []
    used = set()

    def add_q(qtype, question, concept, model_answer_seed):
        key = question[:40]
        if key in used or len(questions) >= count:
            return
        used.add(key)
        model_answers = {
            'definition': f"To understand this concept, focus on its key characteristics. {concept} relates to the core ideas in {topic_title}. Think about how it connects to what you already know.",
            'formula': f"This relationship is important in {topic_title}. Try to understand what each part represents and how they relate to each other. Practice applying it to different problems.",
            'example': f"Work through this step by step. Identify which principles from {topic_title} are being applied and why they work in this context.",
            'application': f"This connects {concept} to real-world thinking. Consider how the principles of {topic_title} apply beyond the textbook.",
            'analysis': f"Think critically about this. Understanding why {concept} matters in {topic_title} will deepen your grasp of the topic.",
            'comparison': f"Comparing these ideas helps build a mental framework. Look for underlying connections between them."
        }
        questions.append({
            'type': qtype,
            'question': question,
            'concept': concept,
            'model_answer': model_answers.get(qtype, f"Review the key ideas in {topic_title} and think about how {concept} fits in.")
        })

    # 1. Definition question from bold terms
    if concepts['bold']:
        for term in concepts['bold'][:2]:
            t = random.choice(QUESTION_TEMPLATES['definition'])
            add_q('definition', t.format(concept=term), term, term)

    # 2. Formula/relationship
    if concepts['formulas']:
        f = concepts['formulas'][0]
        t = random.choice(QUESTION_TEMPLATES['formula'])
        add_q('formula', t.format(formula=f), f, f)

    # 3. Application question from topic title
    t = random.choice(QUESTION_TEMPLATES['application'])
    add_q('application', t.format(concept=topic_title), topic_title, topic_title)

    # 4. Analysis question from content
    if concepts['bold']:
        term = concepts['bold'][0]
        t = random.choice(QUESTION_TEMPLATES['analysis'])
        add_q('analysis', t.format(concept=term), term, term)

    # 5. Example question from chunks
    example_chunks = [c for c in chunks if (c['content_type'] if isinstance(c, dict) else c['content_type']) == 'example']
    if example_chunks:
        t = random.choice(QUESTION_TEMPLATES['example'])
        add_q('example', t.format(concept=topic_title), topic_title, topic_title)

    # 6. Comparison if we have multiple bold terms
    if len(concepts['bold']) >= 2:
        t = random.choice(QUESTION_TEMPLATES['comparison'])
        add_q('comparison', t.format(c1=concepts['bold'][0], c2=concepts['bold'][1]), f"{concepts['bold'][0]} and {concepts['bold'][1]}", "")

    return questions[:count]

def get_remedial_content(topic_content, chunks, question_type, concept):
    conn = get_conn()
    remedial_parts = []

    # Try to get definition chunks
    for c in chunks:
        ct = c['content_type']
        cc = c['content'] or ''
        if ct in ('text', 'definition') and len(cc) > 60:
            text = cc[:300]
            if concept.lower() in text.lower():
                remedial_parts.append(text)
                break

    if not remedial_parts and topic_content:
        remedial_parts.append(topic_content[:500])

    if not remedial_parts and chunks:
        for c in chunks[:3]:
            remedial_parts.append((c['content'] or '')[:300])

    alt_explanations = {
        'definition': "Try re-reading the definition slowly. Break it into parts: what is the concept, what are its properties, and why does it matter?",
        'formula': "Formulas are easier to remember when you understand what each symbol represents. Try rewriting it in words first.",
        'example': "Work through each step of the example independently. Cover the solution and try to solve it yourself first.",
        'application': "Think about problems you've solved before that are similar. How did you approach them?",
        'analysis': "Ask yourself: why was this concept discovered? What problem does it solve?",
        'comparison': "Create a simple table comparing the two ideas side by side."
    }

    remedial = alt_explanations.get(question_type, "Take a step back. What do you already know about this topic?")
    if remedial_parts:
        remedial = remedial_parts[0] + "\n\n💡 " + remedial

    return remedial

def suggest_next_topics(learner_id=1):
    conn = get_conn()
    weak_areas = conn.execute("""
        SELECT t.id as topic_id, t.title as topic_title, ch.title as chapter_title,
               ch.id as chapter_id, ch.num as ch_num, ch.board_id, ch.subject_id,
               COALESCE(lp.quiz_score, 0) as quiz_score,
               COALESCE(rs.avg_quality, 0) as review_quality,
               COALESCE(lp.completions, 0) as completions
        FROM topics t
        JOIN chapters ch ON t.chapter_id = ch.id
        LEFT JOIN learning_progress lp ON lp.topic_id = t.id
        LEFT JOIN (
            SELECT topic_id, AVG(last_quality) as avg_quality
            FROM review_schedule GROUP BY topic_id
        ) rs ON rs.topic_id = t.id
        WHERE lp.status IS NULL OR lp.status = 'locked'
        ORDER BY
            CASE WHEN lp.last_accessed IS NULL THEN 0 ELSE 1 END,
            completions ASC,
            COALESCE(lp.quiz_score, 0) ASC,
            random()
        LIMIT 5
    """).fetchall()
    return [dict(r) for r in weak_areas]

def generate_parent_report(learner_id=1):
    conn = get_conn()
    learner = conn.execute("SELECT * FROM learner WHERE id = ?", (learner_id,)).fetchone()
    if not learner:
        return None

    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
    month_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')

    weekly_xp = conn.execute(
        "SELECT COALESCE(SUM(xp), 0) FROM xp_events WHERE created_at >= ?", (week_ago,)
    ).fetchone()[0]
    monthly_xp = conn.execute(
        "SELECT COALESCE(SUM(xp), 0) FROM xp_events WHERE created_at >= ?", (month_ago,)
    ).fetchone()[0]

    weekly_quizzes = conn.execute(
        "SELECT COUNT(*) FROM learning_progress WHERE last_accessed >= ? AND quiz_score IS NOT NULL", (week_ago,)
    ).fetchone()[0]

    weak_topics = conn.execute("""
        SELECT t.title, ch.title as chapter, COALESCE(lp.quiz_score, 0) as score,
               COALESCE(lp.completions, 0) as visits
        FROM topics t
        JOIN chapters ch ON t.chapter_id = ch.id
        LEFT JOIN learning_progress lp ON lp.topic_id = t.id
        ORDER BY COALESCE(lp.quiz_score, 0) ASC, visits ASC
        LIMIT 5
    """).fetchall()

    strong_topics = conn.execute("""
        SELECT t.title, ch.title as chapter, COALESCE(lp.quiz_score, 0) as score
        FROM topics t
        JOIN chapters ch ON t.chapter_id = ch.id
        LEFT JOIN learning_progress lp ON lp.topic_id = t.id
        WHERE lp.quiz_score >= 80
        ORDER BY lp.quiz_score DESC
        LIMIT 5
    """).fetchall()

    badges_earned = conn.execute("""
        SELECT b.name FROM badges b
        JOIN learner_badges lb ON b.id = lb.badge_id
        LIMIT 10
    """).fetchall()

    report = {
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'learner_name': learner['name'],
        'level': learner['level'],
        'total_xp': learner['total_xp_earned'],
        'weekly_xp': weekly_xp,
        'monthly_xp': monthly_xp,
        'weekly_quizzes': weekly_quizzes,
        'streak': learner['streak'],
        'longest_streak': learner['longest_streak'],
        'quizzes_taken': learner['quizzes_taken'],
        'topics_completed': learner['topics_completed'],
        'weak_areas': [dict(t) for t in weak_topics],
        'strong_areas': [dict(t) for t in strong_topics],
        'badges': [b[0] for b in badges_earned],
        'recommendations': []
    }

    if weak_topics:
        t = weak_topics[0]
        report['recommendations'].append(
            f"Focus on '{t['title']}' in {t['chapter']} — currently the weakest area."
        )
    if weekly_quizzes == 0:
        report['recommendations'].append("No quizzes taken this week. Regular testing builds strong recall.")
    if learner['streak'] <= 1:
        report['recommendations'].append("Encourage daily practice to build a learning streak.")
    if weak_topics and len(weak_topics) >= 2:
        report['recommendations'].append(
            f"Consider reviewing {weak_topics[0]['chapter']} and {weak_topics[1]['chapter']} for concept clarity."
        )
    if learner['total_xp_earned'] > 0 and monthly_xp < 50:
        report['recommendations'].append("Activity has decreased this month. Try daily challenges to stay consistent.")

    return report

def create_tutor_session(topic_id):
    conn = get_conn()
    conn.execute("INSERT INTO tutor_sessions (topic_id) VALUES (?)", (topic_id,))
    conn.commit()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

def save_answer(session_id, question, qtype, model_answer, student_answer=""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO tutor_answers (session_id, question, question_type, model_answer, student_answer) VALUES (?, ?, ?, ?, ?)",
        (session_id, question, qtype, model_answer, student_answer)
    )
    conn.commit()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

def update_answer(answer_id, student_answer, self_assessment):
    conn = get_conn()
    conn.execute(
        "UPDATE tutor_answers SET student_answer = COALESCE(NULLIF(?, ''), student_answer), self_assessment = ? WHERE id = ?",
        (student_answer, self_assessment, answer_id)
    )
    conn.execute("UPDATE tutor_sessions SET questions_asked = (SELECT COUNT(*) FROM tutor_answers WHERE session_id = tutor_sessions.id) WHERE id = (SELECT session_id FROM tutor_answers WHERE id = ?)", (answer_id,))
    if self_assessment == 'correct':
        conn.execute("UPDATE tutor_sessions SET correct_answers = (SELECT COUNT(*) FROM tutor_answers WHERE session_id = tutor_sessions.id AND self_assessment = 'correct') WHERE id = (SELECT session_id FROM tutor_answers WHERE id = ?)", (answer_id,))
    conn.commit()

def complete_session(session_id):
    conn = get_conn()
    conn.execute(
        "UPDATE tutor_sessions SET completed = 1, ended_at = datetime('now','localtime') WHERE id = ?",
        (session_id,)
    )
    # Award XP for completion
    row = conn.execute("SELECT correct_answers, questions_asked FROM tutor_sessions WHERE id = ?", (session_id,)).fetchone()
    if row:
        xp = row['correct_answers'] * 10 + row['questions_asked'] * 3
        conn.execute("UPDATE learner SET xp = xp + ?, total_xp_earned = total_xp_earned + ? WHERE id = 1", (xp, xp))
        conn.execute("INSERT INTO xp_events (xp, reason, detail) VALUES (?, 'tutor_session', ?)",
                     (xp, f"Tutor session completed: {row['correct_answers']}/{row['questions_asked']} correct"))
    conn.commit()
    return xp if row else 0
