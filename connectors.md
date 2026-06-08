# Connectors

## External APIs

| Connector | Type | Config | Details |
|---|---|---|---|
| Anthropic Claude | Cloud LLM | `ANTHROPIC_API_KEY`, `CLAUDE_MODEL` | Messages API at `api.anthropic.com/v1/messages`. Used for explain/solve. Auth via `x-api-key` header. |
| Ollama | Local LLM | `OLLAMA_URL`, `OLLAMA_MODEL` | `/api/generate` endpoint. Supports any Ollama model (qwen3, llama3, phi, gemma). |
| Generic LLM Server | Local/Cloud | `LLAMA_SERVER_URL` | Tries multiple endpoint shapes (`/completions`, `/v1/completions`, `/v1/chat/completions`, `/api/generate`) for compatibility with llama.cpp, vLLM, TGI, etc. |
| Local llama.cpp | Local Binary | `LLAMA_MODEL_PATH` | Direct subprocess call to llama.cpp executable. |

## Internal Connectors

| Connector | Source | Target | Purpose |
|---|---|---|---|
| MCP Client ↔ MCP Server | AI client (Claude Desktop, etc.) | `mcp_server.py` | JSON-RPC over stdio. Exposes tools (search, explain, solve) and prompts. |
| Web Browser ↔ HTTP Server | Browser | `app.py` (`CBSEHandler`) | REST-like HTTP with HTML responses. Mobile-first responsive design. |
| Load Balancer ↔ Workers | `mesh_lb.py` | Multiple `app.py` instances | Internal HTTP forwarding with round-robin and health checks. |

## Protocol Details

### MCP Transport
- Stdio JSON-RPC 2.0
- Headers: `Content-Length: <N>`
- Tools: search, get_topic, get_chapter, explain, solve, retrieve_context
- Prompts: study_guide, practice_session

### LLM Client Priority
1. Claude API (if `ANTHROPIC_API_KEY` set)
2. Ollama (if `OLLAMA_URL` set)
3. Generic server (if `LLAMA_SERVER_URL` set)
4. Local llama.cpp (if `LLAMA_MODEL_PATH` set; method: `_query_local`)
5. Fallback (offline explanation template)
