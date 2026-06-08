# Skills

## Curriculum & Content

| Skill | File(s) | Description |
|---|---|---|
| Content Generation | `seed_content.py`, `gen_seed.py`, `seed_content_remaining.py` | Database seeding with NCERT-aligned content for Science, Math, and other subjects |
| Content Scraping | `scraper.py`, `gen_data.py` | Web scraping NCERT textbooks and structured data generation |
| Content Chunking | `chunking.py` | Hierarchical content parsing into typed chunks (text, example, exercise, formula, etc.) |
| RAG Search | `rag_engine.py` | Full-text search and context retrieval using SQLite FTS5 |

## Pedagogy

| Skill | File(s) | Description |
|---|---|---|
| AI Tutoring | `ai_tutor.py` | Question-based learning with self-assessment and remedial paths |
| Quiz Engine | `app.py` (quiz routes) | Chapter-wise multiple choice quizzes with instant feedback |
| Interactive Exercises | `interactives.py` | Drag-to-match, reorder, and flip-card exercises |
| Competency Questions | `cbq_engine.py` | Real-world scenario-based competency questions |
| Mock Exams | `mock_exam.py` | Timed full-length exam simulation with scoring |
| Question Bank | `question_bank.py` | Curated question bank with model paper generation |
| Spaced Repetition | `spaced_repetition.py` | Review scheduling with quality-based rescheduling |

## Gamification

| Skill | File(s) | Description |
|---|---|---|
| XP & Levels | `gamification.py` | XP tracking, leveling, and streak management |
| Lives System | `gamification.py` | Life-based progression with auto-refill |
| Badges | `badges.py` | Achievement badges for milestones |
| Daily Challenges | `daily_challenge.py` | Daily curated challenges with bonus XP |
| Leaderboard | `gamification.py` | Competitive ranking across learners |

## LLM Integration

| Skill | File(s) | Description |
|---|---|---|
| Claude API | `llm_client.py` | Anthropic Claude cloud integration |
| Ollama | `llm_client.py` | Local Ollama model serving (Qwen3, etc.) |
| Generic Server | `llm_client.py` | OpenAI-compatible or llama.cpp server |
| Local llama.cpp | `llm_client.py` | Direct subprocess llama.cpp binary |

## System

| Skill | File(s) | Description |
|---|---|---|
| Database | `database.py` | SQLite with WAL mode, FTS5, schema management |
| Web Server | `app.py` | HTTP server with mobile-first responsive UI |
| MCP Server | `mcp_server.py` | Model Context Protocol for AI tool integration |
| Load Balancing | `mesh_lb.py`, `nginx.conf` | Multi-worker mesh LB for production scaling |
| Monitoring | `app.py` (monitor routes) | PIN-protected live monitoring dashboard |
| Service Worker | `app.py` (sw.js) | Offline caching via service worker |
