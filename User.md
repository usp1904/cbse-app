# User Guide

## Quick Start

```bash
# Start web app
./run.sh app

# With Ollama (local AI)
OLLAMA_URL=http://localhost:11434 OLLAMA_MODEL=qwen3:latest ./run.sh app

# With Claude API
ANTHROPIC_API_KEY=sk-ant-... ./run.sh app
```

## Features

### Learning
- Browse subjects, chapters, and topics by board (CBSE/AP/TS)
- View chunked content with type badges (text, example, exercise, formula, etc.)
- Full-text search across all content
- AI-powered topic explanations (3 levels: simple, detailed, advanced)
- Step-by-step problem solving

### Practice
- Chapter-wise quizzes with instant feedback
- Interactive exercises: matching, ordering, flip cards
- AI Tutor: question-based learning with self-assessment
- Question bank with model papers
- Mock exams with timer and scoring
- Competency-based questions (CBQ) with real-world scenarios

### Gamification
- XP points and leveling system
- Daily streaks with calendar
- Lives system (5 lives, refills over time)
- Leaderboard
- Badges for achievements
- Daily challenges with bonus XP

### Progress & Review
- Learning progress tracking per topic
- Spaced repetition review scheduling
- Parent report with weak/strong areas and recommendations
- Monitoring dashboard (PIN-protected)

### Accessibility
- Text-to-speech with Indian language support (Hindi, Telugu, Tamil, etc.)
- Mobile-first responsive design
- Offline-capable via service worker
- NotebookLM export for study guides

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /` | Home page |
| `GET /board/{board_id}` | Board subjects |
| `GET /chapter/{chapter_id}` | Chapter content |
| `GET /topic/{topic_id}` | Topic detail |
| `GET /search?q=` | Search content |
| `GET /api/explain?topic=&chapter=&level=` | AI explanation |
| `GET /api/search?q=` | JSON search results |
| `GET /quiz/{chapter_id}` | Chapter quiz |
| `GET /profile` | Learner profile & stats |
| `GET /exams` | Mock exam hub |
| `GET /tutor/{topic_id}` | AI tutor session |
| `GET /api/tutor/parent-report` | Parent progress report |

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | 9090 | Web server port |
| `OLLAMA_URL` | - | Ollama server URL |
| `OLLAMA_MODEL` | qwen3:latest | Ollama model name |
| `ANTHROPIC_API_KEY` | - | Claude API key |
| `CLAUDE_MODEL` | claude-sonnet-4-20250514 | Claude model name |
| `LLAMA_MODEL_PATH` | - | Local llama.cpp binary path |
| `LLAMA_SERVER_URL` | - | Generic LLM server URL |
