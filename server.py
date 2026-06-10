"""FastAPI production server — replaces ThreadingHTTPServer.

Supports:
  - Async AI calls (non-blocking LLM queries)
  - Connection pooling (PostgreSQL/Neon) via db.py
  - CORS, rate limiting, health checks
  - Background task processing
  - Static file serving
  - Gradually replaces CBSEHandler routes

Usage:
  DATABASE_URL=postgresql://user:pass@host/db uvicorn server:app --host 0.0.0.0 --port 9090 --workers 4
  DATABASE_URL=sqlite:///cbse_content.db uvicorn server:app --host 0.0.0.0 --port 9090 --reload
"""
import os
import json
import re
import html as htmlmod
import hashlib
import random
import logging
import functools
import time
import uuid
import urllib.parse
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field

from database import get_db, init_db, SCHEMA_SQL
from data import ALL_BOARDS, SUBJECTS
from chunking import get_chapter_tree, get_topic_with_context, search_chunks
from rag_engine import get_engine
from llm_client import get_client
import ai_tutor
import interactives
import ai_services
import content_enricher
import gamification

log = logging.getLogger("cbse")
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")

RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX = 120
_rate_limit_store = {}
_RAW_HTML_VARS = {"board_name", "content", "extra_css", "description", "title"}

DB = get_db()
RAG = get_engine()
LLM = get_client()


# ─── Rate Limiter ───────────────────────────────────────────────────────────

def rate_limit(requests_per_min: int = 60):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            ip = request.client.host if request.client else "unknown"
            now = time.time()
            window = int(now / RATE_LIMIT_WINDOW)
            key = f"{ip}:{window}"
            count = _rate_limit_store.get(key, 0)
            if count >= requests_per_min:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            _rate_limit_store[key] = count + 1
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


# ─── Helpers ────────────────────────────────────────────────────────────────

def esc_js(s):
    if s is None:
        return ""
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "").replace('"', '&quot;')


def _render(title="CBSE Class X", content="", extra_css="", body_class="", board_name="", description="") -> str:
    meta_desc = description or "CBSE Class 10 learning platform with AI tutor, quizzes, interactive tools"

    seo = f"""<link rel="canonical" href="https://cbse.app/" />
<meta name="description" content="{htmlmod.escape(meta_desc)}" />
<meta property="og:title" content="{htmlmod.escape(title)}" />
<meta property="og:description" content="{htmlmod.escape(meta_desc)}" />
<meta name="twitter:card" content="summary" />"""

    xp = "0"
    try:
        if DB.table_exists("learner"):
            learner = DB.query_one("SELECT xp FROM learner WHERE id=1")
            if learner:
                xp = str(learner.get("xp", 0))
    except Exception:
        pass

    gbar = f"""<div class="gbar">
  <div class="gbar-inner">
    <a href="/" class="gbar-brand">📚 CBSE Class X</a>
    <div class="gbar-nav">
      <a href="/">Home</a>
      <a href="/search">🔍 Search</a>
      <a href="/tutor">🧠 Tutor</a>
      <a href="/exams">🏆 Exams</a>
      <a href="/profile">👤 Profile</a>
      <a href="/about">ℹ️ About</a>
    </div>
    <div class="gbar-right">
      <span class="xp-badge">⭐ <span id="xp-display">{xp}</span> XP</span>
    </div>
  </div>
</div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no">
<title>{htmlmod.escape(title)}</title>
{seo}
<link rel="manifest" href="/manifest.json">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>📚</text></svg>">
<link rel="stylesheet" href="/style.css">
<style>
:root {{ --primary: #0f3460; --accent: #4361ee; --bg: #f0f2f5; --card-bg: #fff; --text: #1a1a2e; --text-muted: #666; --border: #e0e0e0; --radius: 12px; --transition: 0.2s; --bottom-safe: env(safe-area-inset-bottom, 0px); }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; overflow-x: hidden; }}
.sticky-wrapper {{ position: sticky; top: 0; z-index: 100; }}
.gbar {{ background: linear-gradient(135deg, var(--primary), #16213e); color: #fff; padding: 0.5rem 0; }}
.gbar-inner {{ display: flex; align-items: center; gap: 1rem; max-width: 1200px; margin: auto; padding: 0 1rem; flex-wrap: nowrap; }}
.gbar-brand {{ font-size: 1.1rem; font-weight: 700; color: #fff; text-decoration: none; white-space: nowrap; }}
.gbar-nav {{ display: flex; gap: 0.5rem; flex-wrap: nowrap; overflow-x: auto; scrollbar-width: none; }}
.gbar-nav a {{ color: #ccc; text-decoration: none; font-size: 0.82rem; padding: 0.3rem 0.5rem; border-radius: 6px; white-space: nowrap; transition: var(--transition); }}
.gbar-nav a:hover {{ background: rgba(255,255,255,0.1); color: #fff; }}
.gbar-right {{ margin-left: auto; display: flex; align-items: center; gap: 0.5rem; flex-shrink: 0; }}
.xp-badge {{ background: rgba(255,255,255,0.15); padding: 0.25rem 0.6rem; border-radius: 20px; font-size: 0.78rem; white-space: nowrap; }}
.container {{ max-width: 1000px; margin: auto; padding: 1rem; padding-bottom: calc(5rem + var(--bottom-safe)); }}
.breadcrumb {{ font-size: 0.82rem; color: var(--text-muted); margin-bottom: 0.8rem; overflow-x: auto; white-space: nowrap; scrollbar-width: none; }}
.breadcrumb a {{ color: var(--accent); text-decoration: none; }}
.breadcrumb .sep {{ margin: 0 0.3rem; color: #999; }}
.section {{ background: var(--card-bg); border-radius: var(--radius); padding: 1.2rem; margin-bottom: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }}
.section h2 {{ margin-top: 0; font-size: 1.3rem; color: var(--primary); word-break: break-word; }}
a {{ color: var(--accent); text-decoration: none; word-break: break-word; overflow-wrap: break-word; }}
a:hover {{ text-decoration: underline; }}
.tts-btn {{ display: inline-block; padding: 0.6rem 1.2rem; background: linear-gradient(135deg, var(--accent), #3a0ca3); color: #fff; border: none; border-radius: 8px; font-size: 0.88rem; cursor: pointer; text-decoration: none; transition: var(--transition); }}
.tts-btn:hover {{ opacity: 0.9; transform: translateY(-1px); text-decoration: none; }}
.chunk-view {{ padding: 0.8rem; margin-bottom: 0.5rem; background: #f8f9ff; border-radius: 8px; border: 1px solid var(--border); }}
.chunk-title {{ font-weight: 600; color: var(--primary); margin-bottom: 0.3rem; }}
.chunk-content {{ font-size: 0.9rem; line-height: 1.7; color: #333; word-break: break-word; overflow-wrap: break-word; }}
.chunk-content p {{ margin-bottom: 0.5rem; }}
.chapter-actions {{ display: flex; gap: 0.5rem; flex-wrap: wrap; margin: 1rem 0; }}
@media (max-width:640px) {{ .gbar-nav {{ gap: 0.3rem; }} .gbar-nav a {{ font-size: 0.75rem; padding: 0.2rem 0.4rem; }} .container {{ padding: 0.8rem; }} }}
</style>
{extra_css}</head>
<body class="{body_class}">
<div class="sticky-wrapper">{gbar}</div>
<div class="container">
{content}
</div>
</body>
</html>"""
    return html


def format_content(text):
    """Format AI/content text into safe HTML. Handles markdown-like syntax."""
    if not text:
        return ""
    text = str(text)
    text = htmlmod.escape(text)
    text = re.sub(r"\$\$(.*?)\$\$", r'<span class="math">\(\1\)</span>', text, flags=re.DOTALL)
    text = re.sub(r"!\[(.*?)\]\((.*?)\)", r'<img src="\2" alt="\1" style="max-width:100%;border-radius:6px;">', text)
    lines = text.split("\n")
    html_parts = []
    in_ol = False
    in_ul = False
    for line in lines:
        if re.match(r"^\d+[.)]\s", line):
            if not in_ol:
                if in_ul: html_parts.append("</ul>"); in_ul = False
                html_parts.append("<ol>"); in_ol = True
            html_parts.append(f"<li>{re.sub(r'^\d+[.)]\s', '', line)}</li>")
        elif re.match(r"^[-*]\s", line):
            if not in_ul:
                if in_ol: html_parts.append("</ol>"); in_ol = False
                html_parts.append("<ul>"); in_ul = True
            html_parts.append(f"<li>{re.sub(r'^[-*]\s', '', line)}</li>")
        elif re.match(r"^#{1,3}\s", line):
            if in_ol: html_parts.append("</ol>"); in_ol = False
            if in_ul: html_parts.append("</ul>"); in_ul = False
            html_parts.append(f"<h3>{re.sub(r'^#+\s', '', line)}</h3>")
        elif line.strip():
            if in_ol: html_parts.append("</ol>"); in_ol = False
            if in_ul: html_parts.append("</ul>"); in_ul = False
            html_parts.append(f"<p>{line}</p>")
        else:
            if in_ol: html_parts.append("</ol>"); in_ol = False
            if in_ul: html_parts.append("</ul>"); in_ul = False
    if in_ol: html_parts.append("</ol>")
    if in_ul: html_parts.append("</ul>")
    result = "".join(html_parts)
    return result


def _build_breadcrumb(items):
    """Build breadcrumb HTML from list of (label, url) tuples."""
    parts = []
    for label, url in items:
        if url:
            parts.append(f'<a href="{url}">{htmlmod.escape(label)}</a>')
        else:
            parts.append(htmlmod.escape(label))
    return '<span class="sep">›</span>'.join(parts)


def _get_topics(conn, chapter_id):
    return conn.query("SELECT * FROM topics WHERE chapter_id = ? ORDER BY seq, title", (chapter_id,))


def _get_chapters(conn, subject_id):
    return conn.query("SELECT * FROM chapters WHERE subject_id = ? ORDER BY num", (subject_id,))


# ─── Lifespan ───────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("FastAPI server starting...")
    log.info("Database: %s", "PostgreSQL/Neon" if DB.is_postgresql else "SQLite")
    log.info("LLM: %s (%s)", LLM.backend_name, LLM.model_name)
    init_db()
    yield
    log.info("Server shutting down.")


# ─── FastAPI App ────────────────────────────────────────────────────────────

app = FastAPI(
    title="CBSE Class X Education Platform",
    version="3.0.0",
    lifespan=lifespan,
    docs_url="/docs" if os.environ.get("ENV") == "dev" else None,
    redoc_url=None,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=os.environ.get("ALLOWED_HOSTS", "*").split(","))


# ═══════════════════════════════════════════════════════════════════════════
# HEALTH & STATUS
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/health")
async def health():
    return {"status": "ok", "db": DB.backend, "llm": LLM.backend_name, "model": LLM.model_name, "boards": len(ALL_BOARDS)}


@app.get("/api/ai/status")
async def ai_status():
    return LLM.get_status()


@app.get("/style.css")
async def style_css():
    return FileResponse("style.css") if os.path.exists("style.css") else PlainTextResponse("", status_code=404)


@app.get("/manifest.json")
async def manifest_json():
    return FileResponse("manifest.json") if os.path.exists("manifest.json") else JSONResponse({})


# ═══════════════════════════════════════════════════════════════════════════
# PAGE ROUTES
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def home():
    conn = DB
    boards_html = ""
    if conn.table_exists("subjects"):
        boards = conn.query("SELECT id, name, board_id FROM subjects ORDER BY board_id, name")
        current_board = ""
        for s in boards:
            if s["board_id"] != current_board:
                if current_board:
                    boards_html += "</div>"
                current_board = s["board_id"]
                board_name = current_board.upper()
                boards_html += f'<div class="section"><h2>📘 {board_name} Board</h2>'
            chs = _get_chapters(conn, s["id"])
            ch_links = "".join(f'<a href="/chapter/{ch["id"]}" class="chunk-view"><div class="chunk-title">Ch {ch["num"]}: {ch["title"]}</div></a>' for ch in chs)
            boards_html += f'<h3>{s["name"]}</h3><div style="margin-bottom:0.8rem;">{ch_links}</div>'
        if current_board:
            boards_html += "</div>"
    if not boards_html:
        boards_html = '<div class="section"><p style="color:#666;">No content available yet.</p></div>'

    content = f"""<div class="section"><h2>📚 CBSE Class X</h2>
<p style="color:#666;margin-bottom:1rem;">Complete learning platform with AI tutor, interactive quizzes, and smart revision. Multiple boards: CBSE, AP (Andhra Pradesh), TS (Telangana).</p>
<div style="display:flex;gap:0.5rem;flex-wrap:wrap;">
<a href="/search" class="tts-btn">🔍 Search Topics</a>
<a href="/tutor" class="tts-btn">🧠 AI Tutor</a>
<a href="/exams" class="tts-btn">🏆 Mock Exams</a>
<a href="/profile" class="tts-btn">👤 Profile</a>
</div></div>{boards_html}"""
    return HTMLResponse(_render(title="CBSE Class X - Home", content=content))


@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request):
    q = request.query_params.get("q", "")
    results_html = ""
    if q:
        try:
            results = RAG.search(q, limit=20)
        except Exception:
            results = []
        for r in results:
            topic_url = f"/topic/{r.get('id','')}"
            results_html += f"""<div class="chunk-view">
<div class="chunk-title"><a href="{topic_url}" style="color:var(--accent);">{htmlmod.escape(r.get('chapter_title',''))} › {htmlmod.escape(r.get('title',''))}</a></div>
<div class="chunk-content">{htmlmod.escape(r.get('excerpt','')[:300])}</div>
</div>"""
        if not results_html:
            results_html = '<p style="color:#666;">No results found.</p>'
    content = f"""<div class="breadcrumb">{_build_breadcrumb([("Home", "/"), ("Search", None)])}</div>
<div class="section">
<h2>🔍 Search</h2>
<form method="get" action="/search" style="display:flex;gap:0.5rem;margin:1rem 0;">
<input type="text" name="q" value="{htmlmod.escape(q)}" placeholder="Search topics, formulas..." style="flex:1;padding:0.7rem;border:2px solid var(--border);border-radius:8px;font-size:0.9rem;">
<button type="submit" class="tts-btn">Search</button>
</form>
{results_html}
</div>"""
    return HTMLResponse(_render(title=f"Search: {q}" if q else "Search - CBSE Class X", content=content))


@app.get("/tutor", response_class=HTMLResponse)
async def tutor_hub():
    conn = DB
    rows = ""
    if conn.table_exists("subjects"):
        subjects = conn.query(
            "SELECT DISTINCT s.id, s.name, s.board_id FROM subjects s "
            "JOIN chapters c ON c.subject_id = s.id "
            "JOIN topics t ON t.chapter_id = c.id "
            "WHERE t.id IS NOT NULL "
            "ORDER BY s.board_id, s.name"
        )
        for s in subjects:
            chapters = conn.query(
                "SELECT c.id, c.num, c.title FROM chapters c "
                "JOIN topics t ON t.chapter_id = c.id "
                "WHERE c.subject_id = ? GROUP BY c.id ORDER BY c.num",
                (s["id"],)
            )
            ch_links = "".join(f'<li><a href="/chapter/{ch["id"]}">Ch {ch["num"]}: {ch["title"]}</a></li>' for ch in chapters)
            if ch_links:
                rows += f'<div class="book-section"><h3>{s["name"]}</h3><ul style="columns:2;column-gap:2rem;padding-left:1.2rem;">{ch_links}</ul></div>'
    if not rows:
        rows = '<p style="text-align:center;padding:2rem;color:#666;">No topics available yet.</p>'
    content = f"""<div class="breadcrumb">{_build_breadcrumb([("Home", "/"), ("AI Tutor Hub", None)])}</div>
<div class="section"><h2>🧠 AI Tutor Hub</h2><p>Select a chapter to start a question-based learning session.</p>{rows}</div>"""
    return HTMLResponse(_render(title="AI Tutor Hub - CBSE Class X", content=content))


@app.get("/tutor/{topic_id}", response_class=HTMLResponse)
async def tutor_page(topic_id: str):
    conn = DB
    topic = conn.query_one("SELECT * FROM topics WHERE id = ?", (topic_id,))
    if not topic:
        return HTMLResponse(
            _render(title="Topic Not Found", content='<div class="section"><h2>Topic Not Found</h2><p><a href="/">Go Home</a></p></div>'),
            status_code=404
        )
    chapter = conn.query_one("SELECT * FROM chapters WHERE id = ?", (topic["chapter_id"],))
    chunks = conn.query("SELECT * FROM chunks WHERE topic_id = ? ORDER BY seq", (topic_id,))
    questions = ai_tutor.generate_questions(topic["title"], topic.get("content", ""), chunks, 3)
    session_id = ai_tutor.create_tutor_session(topic_id)

    questions_json = json.dumps(questions)
    starter_prompt = random.choice(ai_tutor.STARTER_PROMPTS) if hasattr(ai_tutor, "STARTER_PROMPTS") else "Let's learn!"

    content = f"""<div class="breadcrumb">{_build_breadcrumb([
        ("Home", "/"),
        (chapter.get("board_id", "").upper(), f"/board/{chapter['board_id']}"),
        (f"Ch {chapter['num']}: {chapter['title']}", f"/chapter/{chapter['id']}"),
        (topic["title"], f"/topic/{topic_id}"),
        ("AI Tutor", None)
    ])}</div>
<div class="section" id="tutor-section">
<h2>🧠 AI Tutor: {topic['title']}</h2>
<p style="color:#666;margin-bottom:1rem;">Question-Based Learning</p>
<div id="tutor-progress" style="margin-bottom:1rem;font-size:0.85rem;color:var(--text-muted);">Question 1 of {len(questions)}</div>
<div id="tutor-content">
<div class="tutor-question-card">
<p class="tutor-prompt">{starter_prompt}</p>
<p class="tutor-question-text" id="tutor-question">{questions[0]["question"] if questions else "No questions available."}</p>
<textarea id="tutor-answer" class="tutor-input" rows="4" placeholder="Type your answer here..."></textarea>
<div style="display:flex;gap:0.5rem;margin-top:0.8rem;flex-wrap:wrap;">
<button class="tts-btn" onclick="submitTutorAnswer({session_id})">Submit Answer</button>
<button class="tts-btn" onclick="skipTutorQuestion({session_id})" style="opacity:0.7;">Skip</button>
</div></div>
<div id="tutor-feedback" style="display:none;"></div></div>
<div id="tutor-complete" style="display:none;"></div></div>
<script>
var tutorQuestions = {questions_json};
var tutorSessionId = {session_id};
var tutorQIndex = 0;
var topicId = '{topic_id}';
function submitTutorAnswer(sessionId){{
    var answer = document.getElementById('tutor-answer').value.trim();
    if(!answer){{ alert('Please write your answer first.'); return; }}
    var q = tutorQuestions[tutorQIndex];
    fetch('/api/tutor/answer',{{
        method:'POST', headers:{{'Content-Type':'application/x-www-form-urlencoded'}},
        body:'session_id='+sessionId+'&question='+encodeURIComponent(q.question)+'&qtype='+q.type+'&model_answer='+encodeURIComponent(q.model_answer)+'&student_answer='+encodeURIComponent(answer)
    }}).then(r=>r.json()).then(data=>{{
        var fb = document.getElementById('tutor-feedback');
        fb.style.display='block';
        fb.innerHTML='<div class="tutor-feedback-card"><h4 style="margin-top:0;">Your Answer</h4><p style="background:#f8f9ff;padding:0.8rem;border-radius:6px;">'+answer.replace(/</g,'&lt;')+'</p><h4>How did you do?</h4><div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-top:0.5rem;"><button class="tts-btn" style="background:#dcfce7;" onclick="selfAssess('+data.answer_id+',\\'correct\\','+sessionId+')">✅ Got it right</button><button class="tts-btn" style="background:#fef9c3;" onclick="selfAssess('+data.answer_id+',\\'partial\\','+sessionId+')">🟡 Partially correct</button><button class="tts-btn" style="background:#fee2e2;" onclick="selfAssess('+data.answer_id+',\\'wrong\\','+sessionId+')">❌ Needs work</button></div></div>';
        document.getElementById('tutor-answer').disabled=true;
    }});
}}
function selfAssess(answerId,assessment,sessionId){{
    fetch('/api/tutor/remedial',{{
        method:'POST', headers:{{'Content-Type':'application/x-www-form-urlencoded'}},
        body:'answer_id='+answerId+'&self_assessment='+assessment+'&session_id='+sessionId
    }}).then(r=>r.json()).then(data=>{{
        var fb = document.getElementById('tutor-feedback');
        var q = tutorQuestions[tutorQIndex];
        var showModel = '<h4 style="margin-top:0.8rem;">Model Answer</h4><div class="tutor-model-answer"><p>'+q.model_answer+'</p></div>';
        if(assessment=='correct'){{ fb.innerHTML+='<p style="color:#16a34a;">Great job!</p>'+showModel; }}
        else {{ fb.innerHTML+=showModel+(data.remedial_html||''); }}
        document.getElementById('tutor-answer').value=''; document.getElementById('tutor-answer').disabled=false;
        tutorQIndex++;
        if(tutorQIndex<tutorQuestions.length){{
            document.getElementById('tutor-question').textContent=tutorQuestions[tutorQIndex].question;
            document.getElementById('tutor-progress').textContent='Question '+(tutorQIndex+1)+' of '+tutorQuestions.length;
        }}else{{
            fetch('/api/tutor/complete',{{
                method:'POST', headers:{{'Content-Type':'application/x-www-form-urlencoded'}},
                body:'session_id='+sessionId
            }}).then(r=>r.json()).then(d=>{{ document.getElementById('tutor-content').innerHTML='<div style="text-align:center;padding:2rem;"><h3>🎉 Session Complete!</h3><p>+'+d.xp+' XP</p><a class="tts-btn" href="/topic/'+topicId+'">Back to Topic</a></div>'; }}));
        }}
    }}));
}}
function skipTutorQuestion(sessionId){{
    if(confirm('Skip this question?')){{
        var q = tutorQuestions[tutorQIndex];
        fetch('/api/tutor/answer',{{
            method:'POST', headers:{{'Content-Type':'application/x-www-form-urlencoded'}},
            body:'session_id='+sessionId+'&question='+encodeURIComponent(q.question)+'&qtype='+q.type+'&model_answer='+encodeURIComponent(q.model_answer)+'&student_answer=[skipped]'
        }}).then(function(){{
            tutorQIndex++;
            if(tutorQIndex<tutorQuestions.length){{
                document.getElementById('tutor-question').textContent=tutorQuestions[tutorQIndex].question;
                document.getElementById('tutor-progress').textContent='Question '+(tutorQIndex+1)+' of '+tutorQuestions.length;
            }}else{{
                fetch('/api/tutor/complete',{{
                    method:'POST', headers:{{'Content-Type':'application/x-www-form-urlencoded'}},
                    body:'session_id='+sessionId
                }}).then(r=>r.json()).then(d=>{{ document.getElementById('tutor-content').innerHTML='<div style="text-align:center;padding:2rem;"><h3>🎉 Session Complete!</h3><p>+'+d.xp+' XP</p><a class="tts-btn" href="/topic/'+topicId+'">Back to Topic</a></div>'; }}));
            }}
        }});
    }}
}}
</script>"""
    return HTMLResponse(_render(title=f"AI Tutor: {topic['title']}", content=content))


@app.get("/board/{board_id}", response_class=HTMLResponse)
async def board_page(board_id: str):
    conn = DB
    board_id = board_id.lower()
    subjects = conn.query("SELECT id, name, board_id FROM subjects WHERE LOWER(board_id) = ? ORDER BY name", (board_id,))
    if not subjects:
        return HTMLResponse(
            _render(title="Board Not Found", content=f'<div class="section"><h2>Board Not Found</h2><p>No board found for "{board_id}". <a href="/">Go Home</a></p></div>'),
            status_code=404
        )
    rows = ""
    for s in subjects:
        chs = _get_chapters(conn, s["id"])
        ch_links = "".join(f'<a href="/chapter/{ch["id"]}" class="chunk-view"><div class="chunk-title">Ch {ch["num"]}: {ch["title"]}</div></a>' for ch in chs)
        rows += f'<div class="book-section"><h3><a href="/board/{board_id}/{s["name"].lower().replace(" ","-")}" style="color:var(--primary);">{s["name"]}</a></h3><div style="margin-bottom:0.8rem;">{ch_links}</div></div>'
    content = f"""<div class="breadcrumb">{_build_breadcrumb([("Home", "/"), (board_id.upper(), None)])}</div>
<div class="section"><h2>📘 {board_id.upper()} Board</h2><p style="color:#666;margin-bottom:1rem;">Select a subject to begin learning.</p>{rows}</div>"""
    return HTMLResponse(_render(title=f"{board_id.upper()} Board - CBSE Class X", content=content))


@app.get("/board/{board_id}/{subject_slug}", response_class=HTMLResponse)
async def subject_page(board_id: str, subject_slug: str):
    conn = DB
    board_id = board_id.lower()
    subject_name = subject_slug.replace("-", " ").title()
    subjects = conn.query(
        "SELECT id, name, board_id FROM subjects WHERE LOWER(board_id) = ? AND LOWER(name) LIKE ? ORDER BY name",
        (board_id, f"%{subject_name.lower()}%")
    )
    if not subjects:
        subjects = conn.query(
            "SELECT id, name, board_id FROM subjects WHERE LOWER(board_id) = ? ORDER BY name",
            (board_id,)
        )
        if not subjects:
            return HTMLResponse(
                _render(title="Not Found", content='<div class="section"><h2>Not Found</h2><p><a href="/">Go Home</a></p></div>'),
                status_code=404
            )
    rows = ""
    for s in subjects:
        chs = _get_chapters(conn, s["id"])
        ch_links = "".join(f'<a href="/chapter/{ch["id"]}" class="chunk-view"><div class="chunk-title">Ch {ch["num"]}: {ch["title"]}</div></a>' for ch in chs)
        rows += f'<h3>{s["name"]}</h3><div style="margin-bottom:1.2rem;">{ch_links}</div>'
    content = f"""<div class="breadcrumb">{_build_breadcrumb([("Home", "/"), (board_id.upper(), f"/board/{board_id}"), (subject_name, None)])}</div>
<div class="section"><h2>📘 {board_id.upper()} › {subject_name}</h2>{rows}</div>"""
    return HTMLResponse(_render(title=f"{board_id.upper()} - {subject_name} - CBSE Class X", content=content))


@app.get("/chapter/{chapter_id}", response_class=HTMLResponse)
async def chapter_page(chapter_id: str):
    conn = DB
    chapter = conn.query_one("SELECT * FROM chapters WHERE id = ?", (chapter_id,))
    if not chapter:
        return HTMLResponse(
            _render(title="Chapter Not Found", content='<div class="section"><h2>Chapter Not Found</h2><p><a href="/">Go Home</a></p></div>'),
            status_code=404
        )
    subject = conn.query_one("SELECT * FROM subjects WHERE id = ?", (chapter["subject_id"],))
    topics = _get_topics(conn, chapter_id)

    topics_html = ""
    for t in topics:
        chunks = conn.query("SELECT * FROM chunks WHERE topic_id = ? ORDER BY seq", (t["id"],))
        content_html = format_content(t.get("content", ""))
        chunks_html = "".join(f'<div class="chunk-view"><div class="chunk-title">{htmlmod.escape(c.get("title",""))}</div><div class="chunk-content">{format_content(c.get("content",""))}</div></div>' for c in chunks)
        topics_html += f"""<div class="section" id="topic-{t['id']}">
<h2><a href="/topic/{t['id']}" style="color:var(--primary);">{htmlmod.escape(t['title'])}</a></h2>
{content_html or chunks_html}
<div class="chapter-actions">
<a href="/topic/{t['id']}" class="tts-btn" style="font-size:0.8rem;">📖 Study</a>
<a href="/tutor/{t['id']}" class="tts-btn" style="font-size:0.8rem;">🧠 AI Tutor</a>
<a href="/quiz/{chapter_id}" class="tts-btn" style="font-size:0.8rem;">📝 Quiz</a>
<a href="/interactives/matching/{t['id']}" class="tts-btn" style="font-size:0.8rem;">🔄 Matching</a>
</div></div>"""

    subj_name = subject["name"] if subject else ""
    board_id = (subject["board_id"] if subject else "").upper()
    content = f"""<div class="breadcrumb">{_build_breadcrumb([
        ("Home", "/"),
        (board_id, f"/board/{subject['board_id'].lower() if subject else ''}"),
        (subj_name, None),
        (f"Ch {chapter['num']}: {chapter['title']}", None)
    ])}</div>
<div class="section">
<h2>📖 Ch {chapter['num']}: {chapter['title']}</h2>
<p style="color:#666;margin-bottom:1rem;">{subject["name"] if subject else ""}</p>
<div class="chapter-actions">
<a href="/notes/{chapter_id}" class="tts-btn" style="font-size:0.8rem;">📝 Notes</a>
<a href="/revision/{chapter_id}" class="tts-btn" style="font-size:0.8rem;">🔄 Revision</a>
<a href="/quiz/{chapter_id}" class="tts-btn" style="font-size:0.8rem;">📝 Quiz</a>
</div>
</div>{topics_html}"""
    return HTMLResponse(_render(title=f"Ch {chapter['num']}: {chapter['title']} - CBSE Class X", content=content))


@app.get("/topic/{topic_id}", response_class=HTMLResponse)
async def topic_page(topic_id: str):
    conn = DB
    topic = conn.query_one("SELECT * FROM topics WHERE id = ?", (topic_id,))
    if not topic:
        return HTMLResponse(
            _render(title="Topic Not Found", content='<div class="section"><h2>Topic Not Found</h2><p><a href="/">Go Home</a></p></div>'),
            status_code=404
        )
    chapter = conn.query_one("SELECT * FROM chapters WHERE id = ?", (topic["chapter_id"],))
    subject = conn.query_one("SELECT * FROM subjects WHERE id = ?", (chapter["subject_id"],)) if chapter else None
    chunks = conn.query("SELECT * FROM chunks WHERE topic_id = ? ORDER BY seq", (topic_id,))

    content_html = format_content(topic.get("content", ""))
    chunks_html = ""
    for c in chunks:
        chunks_html += f"""<div class="section" id="chunk-{c['id']}">
<h3>{htmlmod.escape(c.get("title",""))}</h3>
<div class="chunk-content">{format_content(c.get("content",""))}</div>
</div>"""

    bc_items = [("Home", "/")]
    if subject:
        bc_items.append((subject.get("board_id", "").upper(), f"/board/{subject['board_id'].lower()}"))
        bc_items.append((subject.get("name", ""), None))
    bc_items.append((f"Ch {chapter['num']}: {chapter['title']}", f"/chapter/{chapter['id']}"))
    bc_items.append((topic["title"], None))

    content = f"""<div class="breadcrumb">{_build_breadcrumb(bc_items)}</div>
<div class="section">
<h2>{htmlmod.escape(topic['title'])}</h2>
<div class="chapter-actions">
<a href="/tutor/{topic_id}" class="tts-btn" style="font-size:0.8rem;">🧠 AI Tutor</a>
<a href="/mindmap/{topic_id}" class="tts-btn" style="font-size:0.8rem;">🗺️ Mind Map</a>
<a href="/interactives/cards/{topic_id}" class="tts-btn" style="font-size:0.8rem;">🃏 Flashcards</a>
</div>
{content_html}
</div>
{chunks_html}"""
    return HTMLResponse(_render(title=f"{topic['title']} - CBSE Class X", content=content))


# ═══════════════════════════════════════════════════════════════════════════
# API ROUTES — ASYNC
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/tutor/start")
@rate_limit(30)
async def api_tutor_start(request: Request):
    data = await request.form()
    topic_id = data.get("topic_id", "")
    if not topic_id:
        return JSONResponse({"error": "Missing topic_id"}, status_code=400)
    conn = DB
    topic = conn.query_one("SELECT * FROM topics WHERE id = ?", (topic_id,))
    if not topic:
        return JSONResponse({"error": "Topic not found"}, status_code=404)
    chunks = conn.query("SELECT * FROM chunks WHERE topic_id = ? ORDER BY seq", (topic_id,))
    questions = ai_tutor.generate_questions(topic["title"], topic.get("content", ""), chunks, 3)
    session_id = ai_tutor.create_tutor_session(topic_id)
    return {"session_id": session_id, "questions": questions, "topic_title": topic["title"]}


@app.post("/api/tutor/answer")
@rate_limit(60)
async def api_tutor_answer(request: Request):
    data = await request.form()
    try:
        session_id = int(data.get("session_id", 0))
    except (ValueError, TypeError):
        return JSONResponse({"error": "Invalid session_id"}, status_code=400)
    question = data.get("question", "")
    qtype = data.get("qtype", "")
    model_answer = data.get("model_answer", "")
    student_answer = data.get("student_answer", "")
    if not session_id or not question:
        return JSONResponse({"error": "Missing fields"}, status_code=400)
    session = DB.query_one("SELECT id FROM tutor_sessions WHERE id = ?", (session_id,))
    if not session:
        return JSONResponse({"error": "Invalid session"}, status_code=400)
    answer_id = ai_tutor.save_answer(session_id, question, qtype, model_answer, student_answer)
    return {"answer_id": answer_id, "status": "ok"}


@app.post("/api/tutor/remedial")
@rate_limit(30)
async def api_tutor_remedial(request: Request):
    data = await request.form()
    try:
        answer_id = int(data.get("answer_id", 0))
        session_id = int(data.get("session_id", 0))
    except (ValueError, TypeError):
        return JSONResponse({"error": "Invalid params"}, status_code=400)
    self_assessment = data.get("self_assessment", "")
    if not answer_id or not self_assessment:
        return JSONResponse({"error": "Missing fields"}, status_code=400)
    ai_tutor.update_answer(answer_id, data.get("student_answer", ""), self_assessment)
    if self_assessment == "correct":
        return {"status": "ok", "remedial_html": ""}
    answer = DB.query_one(
        "SELECT ta.*, ts.topic_id FROM tutor_answers ta "
        "JOIN tutor_sessions ts ON ta.session_id = ts.id WHERE ta.id = ?",
        (answer_id,)
    )
    if not answer:
        return {"status": "ok", "remedial_html": ""}
    topic = DB.query_one("SELECT * FROM topics WHERE id = ?", (answer["topic_id"],))
    chunks = DB.query("SELECT * FROM chunks WHERE topic_id = ? ORDER BY seq", (answer["topic_id"],))
    remedial = ai_tutor.get_remedial_content(
        topic["content"] if topic else "",
        chunks,
        answer["question_type"],
        answer["question"]
    )
    html = f'<div class="tutor-remedial"><h4>📚 Let\'s Review This</h4><div class="tutor-remedial-content">{format_content(remedial)}</div></div>'
    return {"status": "ok", "remedial_html": html}


@app.post("/api/tutor/complete")
@rate_limit(30)
async def api_tutor_complete(request: Request):
    data = await request.form()
    try:
        session_id = int(data.get("session_id", 0))
    except (ValueError, TypeError):
        return JSONResponse({"error": "Invalid session_id"}, status_code=400)
    xp = ai_tutor.complete_session(session_id)
    return {"status": "ok", "xp": xp}


@app.get("/api/ai/enrich")
@rate_limit(20)
async def api_ai_enrich(topic: str = Query(...), chapter: str = Query(""), subject: str = Query(""), topic_type: str = Query("concept")):
    import asyncio
    loop = asyncio.get_event_loop()
    enriched = await loop.run_in_executor(
        None, content_enricher.enrich_topic_content,
        topic, chapter, subject, "", topic_type
    )
    html = content_enricher.format_ai_content(enriched)
    return {"html": html, "cached": bool(enriched.get("explanation"))}


@app.get("/api/search")
@rate_limit(60)
async def api_search(q: str = Query(""), board: Optional[str] = None, limit: int = Query(15, le=50)):
    if not q:
        return {"results": []}
    try:
        results = RAG.search(q, board=board, limit=limit)
    except Exception:
        results = []
    return {"results": results}


@app.get("/api/gamification")
async def api_gamification():
    try:
        learner = gamification.get_learner()
    except Exception:
        learner = {"xp": 0, "level": 1, "streak": 0, "lives": 5, "topics_completed": 0}
    return {
        "xp": learner.get("xp", 0),
        "level": learner.get("level", 1),
        "streak": learner.get("streak", 0),
        "lives": learner.get("lives", 5),
        "topics_completed": learner.get("topics_completed", 0)
    }


@app.api_route("/{path:path}", methods=["GET", "POST"], response_class=HTMLResponse, include_in_schema=False)
async def catch_all(request: Request, path: str):
    """Fallback to the original CBSEHandler for unmigrated routes."""
    from app import CBSEHandler
    import io

    class FakeWriter:
        def __init__(self):
            self.status = 200
            self.headers = {}
            self.body = b""
        def send_response(self, code, msg=None):
            self.status = code
        def send_header(self, key, val):
            self.headers[key] = val
        def end_headers(self):
            pass
        def write(self, data):
            self.body += data if isinstance(data, bytes) else data.encode()

    fake_writer = FakeWriter()
    raw_path = request.url.path
    if request.query_params:
        raw_path += "?" + str(request.query_params)

    handler = CBSEHandler.__new__(CBSEHandler)
    handler.command = request.method
    handler.path = raw_path
    handler.headers = dict(request.headers)
    handler.rfile = io.BytesIO(await request.body()) if request.method == "POST" else io.BytesIO()
    handler.wfile = fake_writer
    handler.send_response = fake_writer.send_response
    handler.send_header = fake_writer.send_header
    handler.end_headers = fake_writer.end_headers
    handler.requestline = f"{request.method} {raw_path} HTTP/1.1"
    handler.client_address = (request.client.host if request.client else "0.0.0.0", 0)
    handler.close_connection = True
    handler.server_version = "FastAPI/3.0"

    try:
        if request.method == "GET":
            handler.do_GET()
        else:
            handler.do_POST()
    except Exception as e:
        log.error("Legacy handler error for %s: %s", raw_path, e)

    content_type = fake_writer.headers.get("Content-Type", "text/html; charset=utf-8")
    return Response(
        content=fake_writer.body,
        status_code=fake_writer.status,
        media_type=content_type.split(";")[0].strip()
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "9090"))
    workers = int(os.environ.get("UVICORN_WORKERS", "4"))
    log.info("Starting FastAPI on 0.0.0.0:%d with %d workers", port, workers)
    uvicorn.run("server:app", host="0.0.0.0", port=port, workers=workers, log_level="info")
