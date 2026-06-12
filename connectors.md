# Connectors

## External APIs

| Connector | Type | Config | Details |
|---|---|---|---|
| Mistral AI | Primary LLM | `MISTRAL_API_KEY`, `MISTRAL_MODEL` | Chat completions at `api.mistral.ai/v1/chat/completions`. Default model: `mistral-large-latest`. |
| Gemini API | Fallback LLM | `GEMINI_API_KEY` | Gemini API for AI features when Mistral unavailable. |
| Google YouTube Data API v3 | Video Search | `YOUTUBE_API_KEY` | Free tier search for educational videos. |

## Internal Connectors

| Connector | Source | Target | Purpose |
|---|---|---|---|
| MCP Client ↔ MCP Server | AI clients | `mcp_server.py` | JSON-RPC 2.0 over stdio or HTTP. Exposes tools (search, explain, solve) + prompts. |
| Web Browser ↔ FastAPI Server | Browser | `server.py` | REST-like HTTP with HTML responses. Mobile-first responsive design. |
| Load Balancer ↔ Workers | `mesh_lb.py` | Multiple `server.py` instances | Internal HTTP forwarding with round-robin and health checks. |

## Protocol Details

### MCP Transport
- Stdio JSON-RPC 2.0 (`python3 _archive/mcp_server.py`)
- HTTP JSON-RPC 2.0 (`python3 _archive/mcp_server.py --http 9095`)
- Headers: `Content-Length: <N>`
- Tools: search, get_topic, get_chapter, explain, solve, retrieve_context
- Prompts: study_guide, practice_session

### LLM Client Priority
1. Mistral AI API (if `MISTRAL_API_KEY` set)
2. Gemini API (if `GEMINI_API_KEY` set)
3. Fallback (offline explanation template)

### Voiceover & Video Sync
- Quillbot TTS via browser SpeechSynthesis
- Segmented time-coded output for voiceover-video sync
- YouTube clip generation with voiceover overlay

### Mesh Load Balancer
- Round-robin across 4 workers (default)
- Health checks every 15 seconds
- Auto-restart of failed workers
- X-Upstream and X-Response-Time headers
