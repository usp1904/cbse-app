# Tools

## CLI

```bash
# Web server
./run.sh app                    # Start on port 9090
./run.sh mesh                   # Start with load balancer
./run.sh mcp                    # Start MCP server (stdio)
./run.sh seed                   # Seed database only
./run.sh --reseed               # Force re-seed then start
```

## Programmatic API

### LLMClient (`llm_client.py`)
```python
from llm_client import get_client

client = get_client()

# AI explanations
client.explain_topic("Photosynthesis", "Life Processes", context, level="simple")

# Problem solving
client.solve_problem("Solve 2x+3=7", "Linear Equations")

# Raw query
client.query("What is Newton's first law?", system_prompt="...", max_tokens=1024)
```

### RAG Engine (`rag_engine.py`)
```python
from rag_engine import get_engine

engine = get_engine()
results = engine.search("quadratic equations", board="cbse", limit=5)
context = engine.retrieve_context("photosynthesis process", max_chunks=3)
```

### Database (`database.py`)
```python
from database import get_conn, init_db

init_db()  # Ensure tables exist
conn = get_conn()
rows = conn.execute("SELECT * FROM topics WHERE chapter_id = ?", (ch_id,)).fetchall()
```

### Chunking (`chunking.py`)
```python
from chunking import get_chapter_tree, get_topic_with_context, search_chunks

tree = get_chapter_tree("jemh1_ch1")  # Chapter with topic hierarchy
topic = get_topic_with_context("photosynthesis")  # Topic with chunks
results = search_chunks("ohms law")  # Full-text search in chunks
```

### AI Tutor (`ai_tutor.py`)
```python
import ai_tutor

session_id = ai_tutor.create_tutor_session(topic_id)
questions = ai_tutor.generate_questions(title, content, chunks, count=3)
answer_id = ai_tutor.save_answer(session_id, question, qtype, model_answer)
ai_tutor.update_answer(answer_id, student_answer, self_assessment)
xp = ai_tutor.complete_session(session_id)
```

### Gamification (`gamification.py`)
```python
from gamification import get_learner, add_xp, record_quiz_result

learner = get_learner()  # Current XP, level, streak
add_xp(10, "quiz_correct", "Scored 100% on quiz")
record_quiz_result(score=8, total=10, chapter_id="ch1")
```

### Mock Exam (`mock_exam.py`)
```python
from mock_exam import start_exam, submit_exam

exam = start_exam(subject_id="science", num_questions=30)
result = submit_exam(exam_id, answers)
# Returns: score, breakdown, time_spent, xp_earned
```

### Spaced Repetition (`spaced_repetition.py`)
```python
from spaced_repetition import get_due_reviews, submit_review

due = get_due_reviews(learner_id=1)  # Topics due for review
submit_review(topic_id, quality=4)  # Quality 0-5, reschedules next review
```

## HTTP API Tools

```
GET  /api/search?q=<query>&board=<board>&subject=<subj>&limit=<n>
GET  /api/explain?topic=<name>&chapter=<name>&level=<simple|detailed|advanced>
GET  /api/quiz?chapter_id=<id>&num_questions=<n>
POST /api/quiz (submit answers)
GET  /api/gamification (current learner state)
POST /api/tutor/start, /api/tutor/answer, /api/tutor/remedial, /api/tutor/complete
GET  /api/daily-challenge, /api/daily-challenge/history
GET  /api/badges
GET  /api/mock-exam/start, /api/mock-exam/submit, /api/mock-exam/history
GET  /api/review/due, /api/review/submit, /api/review/stats
GET  /api/streak/calendar
GET  /api/concept-map/<topic_id>
GET  /api/voiceover/languages (TTS language list)
GET  /api/monitor/generate (creates monitoring PIN)
```

## Supported Boards

| ID | Name |
|---|---|
| `cbse` | CBSE (Central Board of Secondary Education) |
| `ap` | Andhra Pradesh State Board |
| `ts` | Telangana State Board |

## Supported Subjects

- Mathematics
- Science
- Social Science
- English
- Hindi
- Sanskrit
- French ✅
- AI (Artificial Intelligence) ✅
- IT (Information Technology) ✅
