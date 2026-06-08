import json
import random
import threading
from datetime import datetime

from question_bank import get_questions, generate_model_paper
from cbq_engine import get_cbqs
from database import get_conn

SECTION_CONFIG = {
    "MCQ": {"count": 20, "marks_per": 1, "label": "Section A - Multiple Choice Questions"},
    "VSA": {"count": 5, "marks_per": 2, "label": "Section B - Very Short Answer Questions"},
    "SA":  {"count": 6, "marks_per": 3, "label": "Section C - Short Answer Questions"},
    "LA":  {"count": 4, "marks_per": 5, "label": "Section D - Long Answer Questions"},
    "CBQ": {"count": 3, "marks_per": 4, "label": "Section E - Case Based Questions"},
}

TYPE_MAP_UP = {"MCQ": "MCQ", "VSA": "VSA", "SA": "SA", "LA": "LA", "CBQ": "CBQ",
               "mcq": "MCQ", "vsa": "VSA", "sa": "SA", "la": "LA", "cbq": "CBQ"}

TEMPLATES = {
    "A": {
        "name": "Balanced",
        "description": "Standard difficulty mix suitable for general practice",
        "difficulty_weights": {"easy": 0.30, "medium": 0.40, "hard": 0.30},
        "section_targets": {"MCQ": 18, "VSA": 4, "SA": 5, "LA": 3, "CBQ": 3},
    },
    "B": {
        "name": "Challenging",
        "description": "Higher proportion of difficult questions for advanced learners",
        "difficulty_weights": {"easy": 0.15, "medium": 0.35, "hard": 0.50},
        "section_targets": {"MCQ": 14, "VSA": 4, "SA": 6, "LA": 4, "CBQ": 3},
    },
    "C": {
        "name": "Easy",
        "description": "More simple questions for revision and confidence building",
        "difficulty_weights": {"easy": 0.50, "medium": 0.35, "hard": 0.15},
        "section_targets": {"MCQ": 22, "VSA": 5, "SA": 4, "LA": 2, "CBQ": 2},
    },
}

GRADE_TABLE = [
    (91, 100, "A1", "Outstanding"),
    (81, 90,  "A2", "Excellent"),
    (71, 80,  "B1", "Very Good"),
    (61, 70,  "B2", "Good"),
    (41, 60,  "C",  "Average"),
    (33, 40,  "D",  "Below Average"),
    (0,  32,  "E",  "Needs Improvement"),
]


def _calculate_grade(percentage):
    for low, high, grade, _ in GRADE_TABLE:
        if low <= percentage <= high:
            return grade
    if percentage > 100:
        return "A1"
    return "E"


def _normalise_q(q, section_type):
    qtype = TYPE_MAP_UP.get(q.get("type", ""), section_type)
    return {
        "id": q.get("id"),
        "type": qtype,
        "_section": section_type,
        "question": q.get("question_text", q.get("question", "")),
        "options": q.get("options"),
        "answer": q.get("correct_answer", q.get("answer", "")),
        "marks": q.get("marks", SECTION_CONFIG.get(section_type, {}).get("marks_per", 1)),
        "difficulty": q.get("difficulty", "medium"),
        "chapter": q.get("chapter", ""),
        "topic": q.get("topic", ""),
        "year": q.get("year"),
        "explanation": q.get("explanation", ""),
    }


def _ensure_schema():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS mock_exam_papers (
            id TEXT PRIMARY KEY,
            board_id TEXT NOT NULL,
            subject_id TEXT NOT NULL,
            duration_minutes INTEGER NOT NULL,
            total_marks INTEGER NOT NULL DEFAULT 80,
            template TEXT,
            section_config TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS mock_exam_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id TEXT NOT NULL,
            paper_id TEXT NOT NULL,
            board_id TEXT NOT NULL,
            subject_id TEXT NOT NULL,
            score REAL NOT NULL,
            percentage REAL NOT NULL,
            grade TEXT NOT NULL,
            section_scores TEXT,
            answers TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE INDEX IF NOT EXISTS idx_mock_scores_learner ON mock_exam_scores(learner_id);
        CREATE INDEX IF NOT EXISTS idx_mock_scores_board ON mock_exam_scores(board_id, subject_id);
    """)
    conn.commit()


def init_exam_tables():
    """Wrapper called by database.py init_db() to ensure mock exam tables exist."""
    _ensure_schema()


class MockExam:
    _paper_counter = 0
    _lock = threading.Lock()

    def __init__(self, board_id, subject_id, duration_minutes=180):
        self.board_id = board_id
        self.subject_id = subject_id
        self.duration_minutes = duration_minutes
        _ensure_schema()

    def _next_paper_id(self):
        with self._lock:
            MockExam._paper_counter += 1
            ts = datetime.now().strftime("%Y%m%d%H%M%S")
            return f"ME_{self.board_id}_{self.subject_id}_{ts}_{MockExam._paper_counter}"

    def generate_paper(self, num_questions=30, template="A"):
        tmpl = TEMPLATES.get(template, TEMPLATES["A"])
        paper_id = self._next_paper_id()
        diff_weights = tmpl["difficulty_weights"]
        section_targets = tmpl["section_targets"]
        rng = random.Random(hash((paper_id, template)) & 0x7fffffff)

        selected = []
        used_ids = set()

        for qtype_upper in ["MCQ", "VSA", "SA", "LA"]:
            target = max(2, section_targets.get(qtype_upper, 4))
            try:
                pool = list(get_questions(self.board_id, self.subject_id, question_type=qtype_upper.lower()))
            except (ValueError, KeyError):
                pool = []
            eligible = [q for q in pool if q["id"] not in used_ids]
            if not eligible:
                try:
                    eligible = list(get_questions(self.board_id, self.subject_id))
                except (ValueError, KeyError):
                    eligible = []

            buckets = {"easy": [], "medium": [], "hard": []}
            for q in eligible:
                d = q.get("difficulty", "medium")
                buckets.setdefault(d, []).append(q)

            picked = []
            for diff, weight in diff_weights.items():
                candidates = buckets.get(diff, [])
                n = max(1, int(weight * target))
                rng.shuffle(candidates)
                for q in candidates[:n]:
                    if q["id"] not in used_ids:
                        norm = _normalise_q(q, qtype_upper)
                        picked.append(norm)
                        used_ids.add(q["id"])

            remaining = target - len(picked)
            if remaining > 0:
                fallback = [q for q in eligible if q["id"] not in used_ids]
                rng.shuffle(fallback)
                for q in fallback[:remaining]:
                    norm = _normalise_q(q, qtype_upper)
                    picked.append(norm)
                    used_ids.add(q["id"])

            rng.shuffle(picked)
            selected.extend(picked)

        cbq_target = max(1, section_targets.get("CBQ", 2))
        try:
            cbq_result = get_cbqs(self.board_id, self.subject_id, count=max(5, cbq_target))
        except Exception:
            cbq_result = {"scenarios": []}
        raw_cbqs = []
        if isinstance(cbq_result, dict):
            raw_cbqs = cbq_result.get("scenarios", [])
        elif isinstance(cbq_result, list):
            raw_cbqs = cbq_result

        for cbq in raw_cbqs[:cbq_target]:
            cid = cbq.get("id", f"cbq_{rng.randint(1000,9999)}")
            if cid in used_ids:
                continue
            used_ids.add(cid)

            sub_qs = []
            for sq in cbq.get("questions", []):
                sub_qs.append({
                    "id": sq["id"],
                    "question": sq.get("text", ""),
                    "marks": sq.get("marks", 1),
                    "type": sq.get("type", "mcq"),
                    "options": sq.get("options"),
                    "answer": sq.get("correct_answer", ""),
                    "difficulty": "medium",
                })
            total_sub = sum(sq["marks"] for sq in sub_qs) or 4
            selected.append({
                "id": cid,
                "_section": "CBQ",
                "type": "CBQ",
                "question": cbq.get("case_text", ""),
                "marks": total_sub,
                "difficulty": "medium",
                "chapter": cbq.get("chapter", ""),
                "topic": (cbq.get("topics") or [""])[0],
                "sub_questions": sub_qs,
                "answer": "\n".join(f"{i+1}. {sq['answer']}" for i, sq in enumerate(sub_qs)),
            })

        rng.shuffle(selected)

        sections = {}
        total_marks = 0
        for i, q in enumerate(selected):
            qtype = q.get("_section", q.get("type", "MCQ"))
            q["seq"] = i + 1

            if qtype not in sections:
                cfg = SECTION_CONFIG.get(qtype, {"marks_per": 1, "label": qtype})
                sections[qtype] = {
                    "label": cfg["label"],
                    "questions": [],
                    "count": 0,
                    "marks_per_question": cfg["marks_per"],
                    "total_marks": 0,
                }

            marks = q.get("marks", SECTION_CONFIG.get(qtype, {}).get("marks_per", 1))
            sections[qtype]["questions"].append({"id": q["id"], "marks": marks})
            sections[qtype]["count"] += 1
            sections[qtype]["total_marks"] += marks
            total_marks += marks

        result = {
            "id": paper_id,
            "board": self.board_id,
            "subject": self.subject_id,
            "duration": self.duration_minutes,
            "template": template,
            "template_name": tmpl["name"],
            "sections": sections,
            "questions": selected,
            "total_marks": total_marks,
            "num_questions": len(selected),
            "created_at": datetime.now().isoformat(),
        }

        conn = get_conn()
        conn.execute(
            "INSERT INTO mock_exam_papers (id, board_id, subject_id, duration_minutes, total_marks, template, section_config, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (paper_id, self.board_id, self.subject_id, self.duration_minutes, total_marks, template, json.dumps(sections), datetime.now().isoformat()),
        )
        conn.commit()

        return result


def calculate_score(paper_id, answers):
    conn = get_conn()
    row = conn.execute(
        "SELECT total_marks, section_config FROM mock_exam_papers WHERE id = ?",
        (paper_id,)
    ).fetchone()
    if not row:
        return None

    total_marks_possible = row["total_marks"]
    section_config = json.loads(row["section_config"])

    qid_to_marks = {}
    for sec_name, sec_data in section_config.items():
        for qinfo in sec_data.get("questions", []):
            if isinstance(qinfo, dict):
                qid_to_marks[qinfo["id"]] = qinfo.get("marks", 1)
            else:
                qid_to_marks[qinfo] = sec_data.get("marks_per_question", 1)

    section_scores = {}
    total_score = 0.0

    for qid, qmarks in qid_to_marks.items():
        user_answer = answers.get(qid, "")
        sec = None
        for sec_name, sec_data in section_config.items():
            found = False
            for qinfo in sec_data.get("questions", []):
                qid_in_sec = qinfo["id"] if isinstance(qinfo, dict) else qinfo
                if qid_in_sec == qid:
                    sec = sec_name
                    found = True
                    break
            if found:
                break
        sec = sec or "unknown"
        section_scores.setdefault(sec, {"scored": 0.0, "max": 0})
        section_scores[sec]["max"] += qmarks
        if isinstance(user_answer, str) and user_answer.strip():
            section_scores[sec]["scored"] += qmarks
            total_score += qmarks

    percentage = round((total_score / total_marks_possible * 100), 2) if total_marks_possible > 0 else 0
    grade = _calculate_grade(percentage)

    return {
        "section_scores": section_scores,
        "total": total_score,
        "max_marks": total_marks_possible,
        "percentage": percentage,
        "grade": grade,
    }


def get_percentile(score, board_id, subject_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) as total, "
        "SUM(CASE WHEN percentage < ? THEN 1 ELSE 0 END) as below "
        "FROM mock_exam_scores WHERE board_id = ? AND subject_id = ?",
        (score, board_id, subject_id)
    ).fetchone()
    total = row["total"] if row and row["total"] else 0
    below = row["below"] if row and row["below"] else 0
    if total == 0:
        return 50.0
    return round(below / total * 100, 2)


def save_exam_result(learner_id, paper_id, score, percentage, grade, answers):
    _ensure_schema()
    conn = get_conn()
    paper = conn.execute(
        "SELECT board_id, subject_id FROM mock_exam_papers WHERE id = ?",
        (paper_id,)
    ).fetchone()
    if not paper:
        return False
    conn.execute(
        "INSERT INTO mock_exam_scores (learner_id, paper_id, board_id, subject_id, score, percentage, grade, answers) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (learner_id, paper_id, paper["board_id"], paper["subject_id"],
         score, percentage, grade, json.dumps(answers))
    )
    conn.commit()
    return True


def get_exam_history(learner_id, limit=10):
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, paper_id, board_id, subject_id, score, percentage, grade, created_at "
        "FROM mock_exam_scores WHERE learner_id = ? "
        "ORDER BY created_at DESC LIMIT ?",
        (learner_id, limit)
    ).fetchall()
    return [dict(row) for row in rows]
