# Agents

## AI Tutor (`ai_tutor.py`)
Question-based learning agent that generates conceptual questions, evaluates student answers, and provides remedial content for weak areas.

- Generates questions: definition, formula, example, comparison, application, analysis
- Templates extract key concepts from topic content (bold terms, formulas)
- Self-assessment workflow with XP rewards
- Tracks sessions, answers, and progress per topic

## RAG Engine (`rag_engine.py`)
Retrieval-Augmented Generation engine for semantic search across educational content.

- Full-text search via SQLite FTS5
- Context retrieval for explain/solve pipelines
- Feed chunks to LLM for grounded answers

## MCP Server (`mcp_server.py`)
Model Context Protocol server exposing tools, resources, and prompts for AI integration.

- Tools: search, get_topic, get_chapter, explain, solve, retrieve_context
- Prompts: study_guide, practice_session
- Communicates via stdio using JSON-RPC 2.0

## LLM Client (`llm_client.py`)
Unified LLM client supporting multiple backends.

- Priority: Claude API > Ollama > generic OpenAI-compatible server > local llama.cpp -> fallback
- Methods: `query()`, `explain_topic()`, `solve_problem()`
- Singleton via `get_client()`
