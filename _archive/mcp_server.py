import sys
import os
import json
import uuid
import logging
import traceback

# Ensure root dir is on path (works whether run from _archive/ or from project root)
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from rag_engine import get_engine
from llm_client import get_client
from chunking import get_chapter_tree, get_topic_with_context

log = logging.getLogger("cbse.mcp")


TOOLS = [
    {
        "name": "search",
        "description": "Search across all educational content using full-text search",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "board": {"type": "string", "description": "Board filter (cbse, ap, ts)", "enum": ["cbse", "ap", "ts"]},
                "subject": {"type": "string", "description": "Subject filter"},
                "limit": {"type": "integer", "description": "Max results (default 15)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_topic",
        "description": "Get detailed content for a specific topic including all chunks and problems",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic_id": {"type": "string", "description": "Topic ID"},
            },
            "required": ["topic_id"],
        },
    },
    {
        "name": "get_chapter",
        "description": "Get full chapter tree with all topics, chunks, and problems",
        "inputSchema": {
            "type": "object",
            "properties": {
                "chapter_id": {"type": "string", "description": "Chapter ID"},
            },
            "required": ["chapter_id"],
        },
    },
    {
        "name": "explain",
        "description": "Get AI-powered explanation of a topic",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic_name": {"type": "string", "description": "Topic name"},
                "chapter_name": {"type": "string", "description": "Chapter name"},
                "context": {"type": "string", "description": "Additional context"},
                "level": {"type": "string", "description": "Explanation level", "enum": ["simple", "detailed", "advanced"]},
            },
            "required": ["topic_name", "chapter_name"],
        },
    },
    {
        "name": "solve",
        "description": "Get step-by-step solution for a problem",
        "inputSchema": {
            "type": "object",
            "properties": {
                "problem": {"type": "string", "description": "Problem text"},
                "topic": {"type": "string", "description": "Topic name"},
                "context": {"type": "string", "description": "Additional context"},
            },
            "required": ["problem", "topic"],
        },
    },
    {
        "name": "retrieve_context",
        "description": "Retrieve relevant context chunks for RAG",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Query to find context for"},
                "max_chunks": {"type": "integer", "description": "Max chunks to retrieve"},
            },
            "required": ["query"],
        },
    },
]

PROMPTS = [
    {
        "name": "study_guide",
        "description": "Generate a study guide for a chapter",
        "arguments": [
            {"name": "chapter_title", "description": "Chapter name", "required": True},
            {"name": "subject", "description": "Subject name", "required": True},
        ],
    },
    {
        "name": "practice_session",
        "description": "Generate practice problems for a topic",
        "arguments": [
            {"name": "topic", "description": "Topic name", "required": True},
            {"name": "count", "description": "Number of problems", "required": False},
        ],
    },
]


def handle_request(request):
    req_id = request.get("id")
    method = request.get("method")
    params = request.get("params", {})

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}

    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        result = execute_tool(tool_name, arguments)
        return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": result}]}}

    elif method == "resources/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"resources": []}}

    elif method == "resources/read":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"contents": []}}

    elif method == "prompts/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"prompts": PROMPTS}}

    elif method == "prompts/get":
        prompt_name = params.get("name")
        args = params.get("arguments", {})
        return {"jsonrpc": "2.0", "id": req_id, "result": get_prompt_content(prompt_name, args)}

    elif method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "resources": {},
                    "prompts": {},
                },
                "serverInfo": {"name": "cbse-education-mcp", "version": "1.0.0"},
            },
        }

    elif method == "notifications/initialized":
        return None

    else:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}


def execute_tool(name, args):
    engine = get_engine()
    client = get_client()

    try:
        if name == "search":
            results = engine.search(
                query=args.get("query", ""),
                board=args.get("board"),
                subject=args.get("subject"),
                limit=args.get("limit", 15),
            )
            return json.dumps(results, ensure_ascii=False, indent=2)

        elif name == "get_topic":
            data = engine.get_topic_detail(args.get("topic_id", ""))
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)

        elif name == "get_chapter":
            data = engine.get_chapter_detail(args.get("chapter_id", ""))
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)

        elif name == "explain":
            context = args.get("context", "")
            if not context:
                search_results = engine.search(args.get("topic_name", ""), limit=3)
                context = "\n".join(r["content"] for r in search_results)
            result = client.explain_topic(
                topic_name=args.get("topic_name", ""),
                chapter_name=args.get("chapter_name", ""),
                context_text=context,
                level=args.get("level", "simple"),
            )
            return result

        elif name == "solve":
            context = args.get("context", "")
            if not context:
                search_results = engine.search(args.get("problem", ""), limit=2)
                context = "\n".join(r["content"] for r in search_results)
            result = client.solve_problem(
                problem_text=args.get("problem", ""),
                topic_name=args.get("topic", ""),
                context_text=context,
            )
            return result

        elif name == "retrieve_context":
            context = engine.retrieve_context(
                query=args.get("query", ""),
                max_chunks=args.get("max_chunks", 5),
            )
            return context

        return json.dumps({"error": f"Unknown tool: {name}"})
    except Exception as e:
        log.error("Tool execution error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "traceback": traceback.format_exc()})


def get_prompt_content(name, args):
    if name == "study_guide":
        chapter = args.get("chapter_title", "")
        subject = args.get("subject", "")
        return {
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": f"Create a comprehensive study guide for {subject} - Chapter: {chapter}. Include key concepts, important formulas, common exam questions, and revision tips.",
                    },
                }
            ],
            "description": f"Study guide for {chapter}",
        }
    elif name == "practice_session":
        topic = args.get("topic", "")
        count = args.get("count", 5)
        return {
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": f"Generate {count} practice problems about {topic} for CBSE Class X. Include a mix of conceptual questions, numerical problems, and application-based questions. Provide answers separately.",
                    },
                }
            ],
            "description": f"Practice session for {topic}",
        }
    return {"messages": []}


def run_mcp_server():
    content_length = 0
    buffer = ""

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            line = line.strip()

            if line.startswith("Content-Length:"):
                try:
                    content_length = int(line.split(":")[1].strip())
                except (ValueError, IndexError) as e:
                    log.warning("Malformed Content-Length header: %s — %s", line, e)
                    content_length = 0
            elif line == "" and content_length > 0:
                raw = sys.stdin.read(content_length)
                request = json.loads(raw)
                response = handle_request(request)
                if response is not None:
                    resp_str = json.dumps(response, ensure_ascii=False)
                    sys.stdout.write(f"Content-Length: {len(resp_str.encode())}\r\n\r\n{resp_str}")
                    sys.stdout.flush()
                content_length = 0
        except json.JSONDecodeError:
            content_length = 0
            continue
        except EOFError:
            break
        except Exception as e:
            log.error("MCP server error: %s", e, exc_info=True)
            content_length = 0
            continue


def run_http_server(host="0.0.0.0", port=9095):
    """Run MCP server over HTTP (JSON-RPC 2.0 over POST)."""
    import http.server
    import urllib.parse

    class MCPHTTPHandler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            cl = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(cl) if cl > 0 else b"{}"
            try:
                req = json.loads(body)
                resp = handle_request(req)
                if resp is None:
                    resp = {"jsonrpc": "2.0", "id": None, "result": {}}
                data = json.dumps(resp, ensure_ascii=False).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                err = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(e)}}
                data = json.dumps(err).encode()
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        def do_GET(self):
            if self.path == "/health":
                data = b'{"status":"ok","server":"cbse-education-mcp","version":"1.0.0"}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            else:
                # Serve minimal tool listing at /
                info = {
                    "server": "cbse-education-mcp",
                    "version": "1.0.0",
                    "tools": len(TOOLS),
                    "prompts": len(PROMPTS),
                    "usage": "POST JSON-RPC 2.0 request to /",
                }
                data = json.dumps(info, indent=2).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        def log_message(self, fmt, *args):
            log.info("HTTP %s", fmt % args)

    server = http.server.HTTPServer((host, port), MCPHTTPHandler)
    log.info("MCP HTTP server listening on http://%s:%s", host, port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("MCP HTTP server shutting down")
        server.server_close()


if __name__ == "__main__":
    if "--http" in sys.argv:
        idx = sys.argv.index("--http")
        port = int(sys.argv[idx + 1]) if idx + 1 < len(sys.argv) else 9095
        host = sys.argv[idx + 2] if idx + 2 < len(sys.argv) else "0.0.0.0"
        run_http_server(host, port)
    else:
        run_mcp_server()
