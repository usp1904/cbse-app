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
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, Query, HTTPException, Depends
from json_index import get_index
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")

from database import get_db, init_db, SCHEMA_SQL
from data import ALL_BOARDS, SUBJECTS
from chunking import get_chapter_tree, get_topic_with_context, search_chunks
from json_index import get_index
from rag_engine import get_engine as get_rag_engine
from llm_client import get_client
import ai_tutor
import interactives
import ai_services
import content_enricher
import gamification
import auth
import security

from auth import require_user, get_current_user, signup, login, logout, is_configured

log = logging.getLogger("cbse")
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")

RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX = 120
_RATE_LIMIT_MAX_ENTRIES = 10000
_rate_limit_store = {}
_RAW_HTML_VARS = {"board_name", "content", "extra_css", "description", "title"}

DB = None
RAG = None
SEARCH_IDX = None
LLM = None


# ─── Rate Limiter ───────────────────────────────────────────────────────────

def _rate_limit_cleanup():
    now_window = int(time.time() / RATE_LIMIT_WINDOW)
    cutoff = now_window - 2
    keys_to_delete = [k for k in _rate_limit_store if int(k.split(":")[-1]) < cutoff]
    for k in keys_to_delete:
        del _rate_limit_store[k]
    if len(_rate_limit_store) > _RATE_LIMIT_MAX_ENTRIES:
        sorted_keys = sorted(_rate_limit_store.keys(), key=lambda k: int(k.split(":")[-1]))
        for k in sorted_keys[:len(sorted_keys) - _RATE_LIMIT_MAX_ENTRIES]:
            del _rate_limit_store[k]

def rate_limit(requests_per_min: int = 60):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            if len(_rate_limit_store) > _RATE_LIMIT_MAX_ENTRIES * 1.5:
                _rate_limit_cleanup()
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


def _render(title="CBSE Class X", content="", extra_css="", body_class="", board_name="", description="", user=None) -> str:
    xp = "0"
    try:
        if DB and DB.table_exists("learner"):
            learner = DB.query_one("SELECT xp FROM learner WHERE id=1")
            if learner:
                xp = str(learner.get("xp", 0))
    except Exception:
        pass

    template = templates.get_template("base.html")
    return template.render(
        title=title,
        description=description or "CBSE Class 10 learning platform with AI tutor, quizzes, interactive tools",
        content=content,
        extra_css=extra_css,
        body_class=body_class,
        board_name=board_name,
        xp=xp,
        user=user,
        auth_configured=is_configured(),
    )


def _safe_img_src(m):
    alt = m.group(1)
    src = m.group(2)
    if src.startswith("http://") or src.startswith("https://") or src.startswith("data:image/"):
        return f'<img src="{htmlmod.escape(src)}" alt="{htmlmod.escape(alt)}" style="max-width:100%;border-radius:6px;">'
    return f'<a href="{htmlmod.escape(src)}" rel="nofollow">{htmlmod.escape(alt)}</a>'

def format_content(text):
    """Format AI/content text into safe HTML. Handles markdown-like syntax."""
    if not text:
        return ""
    text = str(text)
    text = htmlmod.escape(text)
    text = re.sub(r"\$\$(.*?)\$\$", r'<span class="math">\(\1\)</span>', text, flags=re.DOTALL)
    text = re.sub(r"!\[(.*?)\]\((.*?)\)", _safe_img_src, text)
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
    return conn.query("SELECT * FROM topics WHERE chapter_id = ? ORDER BY num, title", (chapter_id,))


def _pomelli_hero_svg():
    """PomelliAI-generated SVG hero banner for the home page."""
    return '''<svg viewBox="0 0 900 120" style="width:100%;max-width:900px;height:auto;margin:0 auto 1rem;display:block;" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="hg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#4a90d9" stop-opacity="0.12"/>
      <stop offset="50%" stop-color="#2ecc71" stop-opacity="0.08"/>
      <stop offset="100%" stop-color="#9b59b6" stop-opacity="0.12"/>
    </linearGradient>
    <linearGradient id="bar1" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#4a90d9"/><stop offset="100%" stop-color="#357abd"/></linearGradient>
    <linearGradient id="bar2" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#2ecc71"/><stop offset="100%" stop-color="#27ae60"/></linearGradient>
    <linearGradient id="bar3" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#9b59b6"/><stop offset="100%" stop-color="#8e44ad"/></linearGradient>
  </defs>
  <rect width="900" height="120" fill="url(#hg)" rx="16"/>
  <g opacity="0.6">
    <rect x="40" y="70" width="24" height="40" rx="4" fill="url(#bar1)"><animate attributeName="height" values="40;50;30;40" dur="3s" repeatCount="indefinite"/><animate attributeName="y" values="70;60;80;70" dur="3s" repeatCount="indefinite"/></rect>
    <rect x="74" y="55" width="24" height="55" rx="4" fill="url(#bar2)"><animate attributeName="height" values="55;65;45;55" dur="3.5s" repeatCount="indefinite"/><animate attributeName="y" values="55;45;65;55" dur="3.5s" repeatCount="indefinite"/></rect>
    <rect x="108" y="60" width="24" height="50" rx="4" fill="url(#bar3)"><animate attributeName="height" values="50;40;60;50" dur="2.8s" repeatCount="indefinite"/><animate attributeName="y" values="60;70;50;60" dur="2.8s" repeatCount="indefinite"/></rect>
    <rect x="142" y="45" width="24" height="65" rx="4" fill="url(#bar1)"><animate attributeName="height" values="65;55;70;65" dur="3.2s" repeatCount="indefinite"/><animate attributeName="y" values="45;55;40;45" dur="3.2s" repeatCount="indefinite"/></rect>
    <rect x="176" y="65" width="24" height="45" rx="4" fill="url(#bar2)"><animate attributeName="height" values="45;55;35;45" dur="2.5s" repeatCount="indefinite"/><animate attributeName="y" values="65;55;75;65" dur="2.5s" repeatCount="indefinite"/></rect>
    <rect x="210" y="50" width="24" height="60" rx="4" fill="url(#bar3)"><animate attributeName="height" values="60;50;70;60" dur="3.7s" repeatCount="indefinite"/><animate attributeName="y" values="50;60;40;50" dur="3.7s" repeatCount="indefinite"/></rect>
    <rect x="244" y="40" width="24" height="70" rx="4" fill="url(#bar1)"><animate attributeName="height" values="70;60;75;70" dur="2.9s" repeatCount="indefinite"/></rect>
  </g>
  <circle cx="380" cy="55" r="20" fill="#4a90d9" opacity="0.15"><animate attributeName="r" values="20;25;18;20" dur="4s" repeatCount="indefinite"/></circle>
  <circle cx="420" cy="70" r="14" fill="#2ecc71" opacity="0.12"><animate attributeName="r" values="14;18;12;14" dur="3.5s" repeatCount="indefinite"/></circle>
  <circle cx="450" cy="45" r="10" fill="#9b59b6" opacity="0.15"><animate attributeName="r" values="10;14;8;10" dur="3s" repeatCount="indefinite"/></circle>
  <text x="530" y="55" font-family="sans-serif" font-size="22" font-weight="700" fill="#1a1a2e">CBSE Class X</text>
  <text x="530" y="82" font-family="sans-serif" font-size="13" fill="#666">CBSE · AP Board · TS Board · Class V–X</text>
  <text x="530" y="100" font-family="sans-serif" font-size="11" fill="#999">English · हिन्दी · తెలుగు</text>
  <g transform="translate(700,20)" opacity="0.3">
    <path d="M30 30 L70 30 L90 60 L50 60 Z" fill="#4a90d9"/>
    <path d="M10 60 L50 60 L70 90 L30 90 Z" fill="#2ecc71"/>
    <path d="M50 60 L90 60 L110 90 L70 90 Z" fill="#9b59b6"/>
  </g>
</svg>'''


def _get_chapters(conn, subject_id):
    return conn.query("SELECT * FROM chapters WHERE subject_id = ? ORDER BY num", (subject_id,))


# ─── Lifespan ───────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global DB, RAG, LLM
    log.info("FastAPI server starting...")
    DB = get_db()
    try:
        LLM = get_client()
    except Exception as e:
        log.warning("LLM init failed (non-fatal): %s", e)
    try:
        RAG = get_rag_engine()
    except Exception as e:
        log.warning("RAG engine init failed (non-fatal): %s", e)
    try:
        get_index()
    except Exception as e:
        log.warning("JsonIndex init failed (non-fatal): %s", e)
    init_db()
    log.info("Database: %s", "PostgreSQL/Neon" if DB.is_postgresql else "SQLite")
    log.info("LLM: %s (%s)", getattr(LLM, 'backend_name', 'N/A') if LLM else "N/A",
             getattr(LLM, 'model_name', 'N/A') if LLM else "N/A")
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
app.add_middleware(security.SecurityHeadersMiddleware)
app.add_middleware(security.CSRFSafeMiddleware)


# ═══════════════════════════════════════════════════════════════════════════
# HEALTH & STATUS
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/health")
async def health():
    db_status = "N/A"
    try:
        if DB:
            DB.query_one("SELECT 1")
            db_status = f"{DB.backend} (connected)"
    except Exception:
        db_status = f"{DB.backend if DB else 'N/A'} (unreachable)"
    return {"status": "ok" if "connected" in db_status else "degraded",
            "db": db_status,
            "llm": getattr(LLM, 'backend_name', 'N/A') if LLM else "N/A",
            "model": getattr(LLM, 'model_name', 'N/A') if LLM else "N/A",
            "boards": len(ALL_BOARDS)}


@app.get("/api/ai/status")
async def ai_status():
    if not LLM:
        return {"status": "unavailable", "message": "No LLM backend configured"}
    return LLM.get_status()


@app.get("/api/view_logs")
@app.get("/api/audit/data")
async def api_audit_data():
    import json, os, re as _re
    data = {}
    data['config_sources'] = {'os_environ_get': 26, 'hardcoded_urls': 1, 'hardcoded_data': 5, 'hardcoded_schema': 1, 'cli_args': 2, 'hardcoded_security': 1}
    data['modalities'] = {'text_generation': 12, 'svg_diagrams': 3, 'mermaid_js': 1, 'html_canvas': 10, 'video_embed': 3, 'audio_tts': 2, 'youtube_api': 1, 'image_gen': 0, 'audio_gen': 0, 'video_gen': 0}
    data['system_prompts'] = {'Napkin Diagram': 1, 'Presentation': 1, 'Paraphrase': 1, 'Research': 1, 'Literature': 1, 'SVG': 1, 'Story': 1, 'Gemma4': 1, 'MetaAI': 1, 'NotebookLM': 1, 'Enricher': 3, 'Tutor': 1}
    data['schema_validation'] = {'pydantic_models': 2, 'query_params_validated': 32, 'form_no_model': 5, 'missing': 20}
    data['async_vs_sync'] = {'async_functions': 85, 'sync_functions': 63, 'async_io_threaded': 20, 'sync_io_not_threaded': 12, 'async_database': 0}
    data['async_breakdown'] = {'page_routes': 30, 'api_endpoints': 32, 'auth': 7, 'middleware': 2, 'utility': 3, 'legacy_shim': 1}
    data['caching'] = {'in_memory_ttl': 2, 'in_memory_not_ttl': 2, 'db_backed': 1, 'file_based': 1, 'no_cache': 12}
    data['cache_risk'] = {'memory_leak': 2, 'hash_stability': 1, 'no_migrations': 1, 'ttl_only': 2, 'well_managed': 2}
    data['perf'] = {'health': 2, 'home': 21, 'board': 2, 'chapter': 5, 'topic': 4, 'api_status': 1, 'api_search': 5}
    data['routes'] = {'pages': 50, 'api': 32, 'ai_api': 19, 'ai_pages': 13, 'legacy': 1, 'static': 1}
    data['error_handling'] = {'try_except': 45, 'http_exceptions': 8, 'not_found': 18, 'fallbacks': 6, 'rate_limited': 24, 'unprotected': 8}
    return data


@app.get("/audit-dashboard", response_class=HTMLResponse)
async def audit_dashboard():
    try:
        with open("templates/audit.html") as f:
            return HTMLResponse(f.read())
    except Exception:
        return HTMLResponse("<h1>Audit Dashboard</h1><p>Template not found</p>")


async def view_logs():
    import glob
    log_content = ""
    log_files = ["/tmp/server.log", "server.log", "app.log"]
    found_file = None
    for lf in log_files:
        if os.path.exists(lf):
            found_file = lf
            break
    if not found_file:
        all_logs = glob.glob("/tmp/*.log") + glob.glob("*.log")
        if all_logs:
            found_file = all_logs[0]
            
    if found_file:
        try:
            with open(found_file, "r", encoding="utf-8", errors="replace") as f:
                log_content = f.read()[-8000:]
            return {"file": found_file, "logs": log_content}
        except Exception as e:
            return {"error": f"Failed to read {found_file}: {e}"}
    return {"error": "No log files found", "searched": log_files}


# ═══════════════════════════════════════════════════════════════════════════
# PROFILE & PROGRESS (protected)
# ═══════════════════════════════════════════════════════════════════════════


@app.get("/profile", response_class=HTMLResponse)
async def profile_page(user: Optional[dict] = Depends(get_current_user)):
    if not user:
        return _render(
            title="Profile — CBSE Class X",
            content=f"""
            <div class="card" style="text-align:center;padding:3rem 2rem;">
                <h2>🔒 Profile</h2>
                <p style="margin:1rem 0;color:#666;">Sign in to view your profile, progress, and achievements.</p>
                <a href="/login" class="btn-primary" style="display:inline-block;padding:0.8rem 2rem;background:var(--accent);color:#fff;border-radius:8px;text-decoration:none;">Sign In</a>
                <span style="margin:0 0.5rem">or</span>
                <a href="/register" style="color:var(--accent);">Create Account</a>
            </div>
            """,
        )
    return _render(
        title=f"Profile — {user['username']} | CBSE Class X",
        content=f"""
        <div class="card">
            <h2>👤 {user['username']}</h2>
            <p>Email: {user['email']}</p>
            <p>User ID: {user['id']}</p>
        </div>
        """,
    )


@app.get("/progress", response_class=HTMLResponse)
async def progress_page(user: dict = Depends(require_user)):
    return _render(
        title="My Progress | CBSE Class X",
        content="""
        <div class="card">
            <h2>📊 Learning Progress</h2>
            <p>Progress tracking coming soon.</p>
        </div>
        """,
    )


@app.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard_page(user: dict = Depends(get_current_user)):
    try:
        learners = DB.query("SELECT username, xp, level FROM learner ORDER BY xp DESC LIMIT 50") if DB else []
    except Exception:
        learners = []
    rows = "".join(
        f"<tr><td>{i+1}</td><td>{l['username']}</td><td>{l['xp']}</td><td>{l['level']}</td></tr>"
        for i, l in enumerate(learners)
    )
    return _render(
        title="Leaderboard | CBSE Class X",
        content=f"""
        <div class="card">
            <h2>🏆 Leaderboard</h2>
            <table class="data-table"><tr><th>#</th><th>User</th><th>XP</th><th>Level</th></tr>{rows}</table>
        </div>
        """,
    )


# ═══════════════════════════════════════════════════════════════════════════
# AUTH (Supabase JWT)
# ═══════════════════════════════════════════════════════════════════════════

from pydantic import BaseModel


class AuthSignup(BaseModel):
    email: str
    password: str
    username: str = ""


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    return _render(
        title="Login | CBSE Class X",
        content="""
        <div class="card" style="max-width:400px;margin:2rem auto;">
            <h2>🔐 Login</h2>
            <form id="login-form" onsubmit="return doLogin(event)">
                <div class="form-group">
                    <label for="email">Email</label>
                    <input type="email" id="email" name="email" required class="form-input" placeholder="your@email.com">
                </div>
                <div class="form-group">
                    <label for="password">Password</label>
                    <input type="password" id="password" name="password" required class="form-input" placeholder="••••••••">
                </div>
                <button type="submit" class="btn btn-primary" style="width:100%;">Login</button>
                <p style="text-align:center;margin-top:1rem;">Don't have an account? <a href="/signup">Sign up</a></p>
            </form>
            <div id="login-error" style="color:var(--error);display:none;"></div>
        </div>
        <script>
        async function doLogin(e){
            e.preventDefault();
            const email=document.getElementById('email').value;
            const password=document.getElementById('password').value;
            try{
                const r=await fetch('/api/auth/login',{
                    method:'POST',
                    headers:{'Content-Type':'application/json'},
                    body:JSON.stringify({email,password})
                });
                const d=await r.json();
                if(d.success){window.location.href='/profile';}
                else{document.getElementById('login-error').style.display='block';
                     document.getElementById('login-error').textContent=d.detail||'Login failed';}
            }catch(e){
                document.getElementById('login-error').style.display='block';
                document.getElementById('login-error').textContent='Network error';
            }
            return false;
        }
        </script>
        """,
    )


@app.get("/signup", response_class=HTMLResponse)
async def signup_page():
    return _render(
        title="Sign Up | CBSE Class X",
        content="""
        <div class="card" style="max-width:400px;margin:2rem auto;">
            <h2>📝 Create Account</h2>
            <form id="signup-form" onsubmit="return doSignup(event)">
                <div class="form-group">
                    <label for="su-email">Email</label>
                    <input type="email" id="su-email" name="email" required class="form-input">
                </div>
                <div class="form-group">
                    <label for="su-username">Username</label>
                    <input type="text" id="su-username" name="username" class="form-input" placeholder="optional">
                </div>
                <div class="form-group">
                    <label for="su-password">Password</label>
                    <input type="password" id="su-password" name="password" required class="form-input" minlength="6">
                </div>
                <button type="submit" class="btn btn-primary" style="width:100%;">Create Account</button>
                <p style="text-align:center;margin-top:1rem;">Already have an account? <a href="/login">Login</a></p>
            </form>
            <div id="signup-error" style="color:var(--error);display:none;"></div>
            <div id="signup-success" style="color:var(--success);display:none;"></div>
        </div>
        <script>
        async function doSignup(e){
            e.preventDefault();
            const email=document.getElementById('su-email').value;
            const username=document.getElementById('su-username').value;
            const password=document.getElementById('su-password').value;
            try{
                const r=await fetch('/api/auth/signup',{
                    method:'POST',
                    headers:{'Content-Type':'application/json'},
                    body:JSON.stringify({email,password,username})
                });
                const d=await r.json();
                if(d.success){
                    document.getElementById('signup-success').style.display='block';
                    document.getElementById('signup-success').textContent='Account created! Redirecting...';
                    setTimeout(()=>window.location.href='/login',1500);
                }else{
                    document.getElementById('signup-error').style.display='block';
                    document.getElementById('signup-error').textContent=JSON.stringify(d.detail||d);
                }
            }catch(e){
                document.getElementById('signup-error').style.display='block';
                document.getElementById('signup-error').textContent='Network error';
            }
            return false;
        }
        </script>
        """,
    )


class AuthLogin(BaseModel):
    email: str
    password: str


@app.get("/api/auth/config")
async def auth_config():
    """Tell the frontend whether auth is available."""
    return {"configured": is_configured()}


@app.post("/api/auth/signup")
async def api_signup(data: AuthSignup, request: Request):
    """Register a new user."""
    return await signup(data.email, data.password, data.username)


@app.post("/api/auth/login")
async def api_login(data: AuthLogin, request: Request):
    """Authenticate and return JWT."""
    result = await login(data.email, data.password)
    response = JSONResponse(content=result)
    if result.get("access_token"):
        response.set_cookie(
            key="access_token",
            value=result["access_token"],
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=86400 * 7,
        )
    return response


@app.post("/api/auth/logout")
async def api_logout(request: Request):
    """Revoke session."""
    token = request.cookies.get("access_token", "")
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    await logout(token)
    response = JSONResponse({"success": True})
    response.delete_cookie("access_token")
    return response


@app.get("/api/auth/me")
async def api_auth_me(user: dict = Depends(get_current_user)):
    """Return current user info or 401."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"authenticated": True, "user": user}


@app.get("/style.css")
async def style_css():
    if os.path.exists("style.css"):
        return FileResponse("style.css")
    from app import CSS
    return Response(content=CSS, media_type="text/css")


@app.get("/manifest.json")
async def manifest_json():
    if os.path.exists("manifest.json"):
        return FileResponse("manifest.json")
    manifest = {
        "name": "Class X Education Platform",
        "short_name": "Class X Edu",
        "description": "CBSE, AP & TS Board Class X study platform",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#f0f2f5",
        "theme_color": "#1a1a2e",
        "orientation": "any",
    }
    return JSONResponse(content=manifest)


# ═══════════════════════════════════════════════════════════════════════════
# PAGE ROUTES
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def home():
    idx = get_index()
    board_tree = idx.get_all_boards_tree()
    languages = idx.get_languages()
    classes = idx.get_classes()

    board_options = ""
    for b in board_tree:
        board_options += f'<option value="{b["id"]}">{b["name"]}</option>\n'

    lang_options = ""
    for l in languages:
        sel = ' selected' if l == 'English' else ''
        lang_options += f'<option value="{l}"{sel}>{l}</option>\n'

    class_options = ""
    for c in classes:
        sel = ' selected' if c == 'X' else ''
        class_options += f'<option value="{c}"{sel}>Class {c}</option>\n'

    tables = ""
    for b in board_tree:
        rows = ""
        for s in b.get("subjects", []):
            subj_url = f"/board/{b['id']}/{s['id']}"
            lang = s.get("language", "English")
            cls = s.get("class", "X")
            rows += f"""<tr data-subject="{s['id']}" data-board="{b['id']}" data-lang="{lang}" data-class="{cls}">
                <td><a href="{subj_url}">{s['name']}</a></td>
                <td>{lang}</td>
                <td>{cls}</td>
                <td>{s.get('chapter_count', 0)}</td>
                <td>{s.get('topic_count', 0)}</td>
                <td><a href="{subj_url}" class="tts-btn" style="padding:0.3rem 0.8rem;font-size:0.78rem;">Browse</a></td>
            </tr>"""
        if not rows:
            continue
        tables += f"""<div class="section board-table" data-board="{b['id']}">
            <h2>📘 {b['name']}</h2>
            <div style="overflow-x:auto;">
            <table class="data-table">
                <thead><tr><th>Subject</th><th>Language</th><th>Class</th><th>Chapters</th><th>Topics</th><th></th></tr></thead>
                <tbody>{rows}</tbody>
            </table>
            </div>
        </div>"""

    medium_opts = '<option value="">All Mediums</option><option value="English">English</option><option value="Hindi">हिन्दी (Hindi)</option><option value="Telugu">తెలుగు (Telugu)</option><option value="Tamil">தமிழ் (Tamil)</option><option value="Kannada">ಕನ್ನಡ (Kannada)</option><option value="Bengali">বাংলা (Bengali)</option><option value="Marathi">मराठी (Marathi)</option><option value="Gujarati">ગુજરાતી (Gujarati)</option><option value="Malayalam">മലയാളം (Malayalam)</option><option value="Odia">ଓଡ଼ିଆ (Odia)</option><option value="Punjabi">ਪੰਜਾਬੀ (Punjabi)</option><option value="Assamese">অসমীয়া (Assamese)</option><option value="Urdu">اردو (Urdu)</option>'
    subject_opts = '<option value="">All Subjects</option>'
    seen_subjects = set()
    for b in board_tree:
        for s in b.get("subjects", []):
            sid = s['id']
            if sid not in seen_subjects:
                seen_subjects.add(sid)
                subject_opts += f'<option value="{sid}">{s["name"]}</option>\n'
    filter_panel = f"""<div class="filter-panel" style="display:flex;gap:0.8rem;flex-wrap:wrap;align-items:flex-end;margin-bottom:1.25rem;padding:1rem 1.25rem;background:var(--card-bg);border-radius:12px;border:1px solid var(--border);">
        <div><label for="fb" style="display:block;font-size:0.78rem;font-weight:600;color:var(--text-muted);margin-bottom:0.25rem;">Board</label>
        <select id="fb" onchange="filterHome()" style="padding:0.45rem 0.7rem;border:1px solid var(--border);border-radius:6px;font-size:0.82rem;"><option value="">All Boards</option>{board_options}</select></div>
        <div><label for="fm" style="display:block;font-size:0.78rem;font-weight:600;color:var(--text-muted);margin-bottom:0.25rem;">Medium</label>
        <select id="fm" onchange="filterHome()" style="padding:0.45rem 0.7rem;border:1px solid var(--border);border-radius:6px;font-size:0.82rem;">{medium_opts}</select></div>
        <div><label for="fc" style="display:block;font-size:0.78rem;font-weight:600;color:var(--text-muted);margin-bottom:0.25rem;">Class</label>
        <select id="fc" onchange="filterHome()" style="padding:0.45rem 0.7rem;border:1px solid var(--border);border-radius:6px;font-size:0.82rem;"><option value="">All Classes</option>{class_options}</select></div>
        <div><label for="fs" style="display:block;font-size:0.78rem;font-weight:600;color:var(--text-muted);margin-bottom:0.25rem;">Subject</label>
        <select id="fs" onchange="filterHome()" style="padding:0.45rem 0.7rem;border:1px solid var(--border);border-radius:6px;font-size:0.82rem;">{subject_opts}</select></div>
        <div><button onclick="clearFilters()" style="padding:0.45rem 0.9rem;background:var(--accent);color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:0.82rem;font-weight:600;">Apply</button>
        <button onclick="resetFilters()" style="padding:0.45rem 0.9rem;background:var(--bg);border:1px solid var(--border);border-radius:6px;cursor:pointer;font-size:0.82rem;">Reset</button></div>
        <div style="font-size:0.78rem;color:var(--text-muted);padding:0.25rem 0;"><span id="filter-count">loading...</span></div>
    </div>
    <script>
    function filterHome() {{
        var bv = document.getElementById('fb').value;
        var mv = document.getElementById('fm').value;
        var cv = document.getElementById('fc').value;
        var sv = document.getElementById('fs').value;
        document.querySelectorAll('.board-table').forEach(function(t) {{
            var visibleRows = 0;
            t.querySelectorAll('tbody tr').forEach(function(r) {{
                var show = (!bv || r.dataset.board === bv) && (!mv || r.dataset.lang === mv) && (!cv || r.dataset.class === cv) && (!sv || r.dataset.subject === sv);
                r.style.display = show ? '' : 'none';
                if (show) visibleRows++;
            }});
            t.style.display = visibleRows > 0 ? 'block' : 'none';
        }});
        // Update visible count
        var total = 0, vis = 0;
        document.querySelectorAll('tbody tr').forEach(function(r) {{ total++; if(r.style.display!=='none') vis++; }});
        var el = document.getElementById('filter-count');
        if(el) el.textContent = vis + ' of ' + total + ' subjects';
    }}
    function clearFilters() {{ filterHome(); }}
    function resetFilters() {{
        document.getElementById('fb').value = '';
        document.getElementById('fm').value = '';
        document.getElementById('fc').value = '';
        document.getElementById('fs').value = '';
        filterHome();
    }}
    window.addEventListener('DOMContentLoaded', filterHome);
    </script>"""

    pomelli_hero = _pomelli_hero_svg()
    content = f"""<div class="section">{pomelli_hero}
<h2>📚 CBSE Education Platform</h2>
<p style="color:#666;margin-bottom:1rem;">Multiple boards · Indian languages · Class V–X · AI-powered learning</p>
<div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:1rem;">
<a href="/search" class="tts-btn">🔍 Search Topics</a>
<a href="/exams" class="tts-btn">🏆 Mock Exams</a>
<a href="/profile" class="tts-btn">👤 Profile</a>
<a href="/ai" class="tts-btn">🤖 AI Studio</a>
</div></div>{filter_panel}
<div id="home-tables">{tables}</div>"""
    return HTMLResponse(_render(title="CBSE Education Platform - Home", content=content))


@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request):
    q = request.query_params.get("q", "")
    board = request.query_params.get("board", "")
    subject = request.query_params.get("subject", "")

    idx = get_index()
    board_tree = idx.get_all_boards_tree()

    board_opts = '<option value="">All Boards</option>'
    subj_opts = '<option value="">All Subjects</option>'
    for b in board_tree:
        sel = ' selected' if b['id'] == board else ''
        board_opts += f'<option value="{b["id"]}"{sel}>{b["name"]}</option>'
        for s in b.get("subjects", []):
            sel2 = ' selected' if s['id'] == subject else ''
            subj_opts += f'<option value="{s["id"]}" data-board="{b["id"]}"{sel2}>{s["name"]}</option>'

    results_html = ""
    if q:
        try:
            results = idx.search(q, board=board if board else None, subject=subject if subject else None, limit=20)
        except Exception:
            results = []
        if results:
            results_html = '<div style="overflow-x:auto;"><table class="data-table"><thead><tr><th>Topic</th><th>Chapter</th><th>Score</th><th></th></tr></thead><tbody>'
            for r in results:
                topic_url = f"/topic/{r.get('id','')}"
                results_html += f"""<tr>
                    <td><a href="{topic_url}">{htmlmod.escape(r.get('title',''))}</a></td>
                    <td style="color:var(--text-muted);font-size:0.85rem;">{htmlmod.escape(r.get('chapter_title',''))}</td>
                    <td style="color:var(--text-muted);font-size:0.8rem;">{r.get('score', 0)}</td>
                    <td><a href="{topic_url}" class="tts-btn" style="padding:0.2rem 0.6rem;font-size:0.75rem;">Open</a></td>
                </tr>"""
            results_html += '</tbody></table></div>'
        else:
            results_html = '<p style="padding:1rem;color:#666;">No results found. Try different keywords or filters.</p>'
    else:
        results_html = '<p style="padding:1rem;color:#666;">Enter a search term above to find topics across all boards.</p>'

    content = f"""<div class="breadcrumb">{_build_breadcrumb([("Home", "/"), ("Search", None)])}</div>
<div class="section">
<h2>🔍 Search Topics</h2>
<form method="get" action="/search" class="search-form">
    <input type="text" name="q" value="{htmlmod.escape(q)}" placeholder="Search topics, formulas, concepts..." style="flex:1;min-width:200px;padding:0.7rem;border:2px solid var(--border);border-radius:8px;font-size:0.9rem;">
    <select name="board" id="search-board">
        {board_opts}
    </select>
    <select name="subject" id="search-subject">
        {subj_opts}
    </select>
    <button type="submit" class="tts-btn">Search</button>
</form>
</div>
<div class="section">
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
        subject_ids = [s["id"] for s in subjects]
        all_chapters = {}
        if subject_ids:
            placeholders = ",".join(["?"] * len(subject_ids))
            rows_data = conn.query(
                f"SELECT c.id, c.num, c.title, c.subject_id FROM chapters c "
                f"JOIN topics t ON t.chapter_id = c.id "
                f"WHERE c.subject_id IN ({placeholders}) GROUP BY c.id ORDER BY c.num",
                subject_ids
            )
            for r in rows_data:
                all_chapters.setdefault(r["subject_id"], []).append(r)
        for s in subjects:
            chapters = all_chapters.get(s["id"], [])
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
        rows += f'<div class="book-section"><h3><a href="/board/{board_id}/{s["id"]}" style="color:var(--primary);">{s["name"]}</a></h3><div style="margin-bottom:0.8rem;">{ch_links}</div></div>'
    content = f"""<div class="breadcrumb">{_build_breadcrumb([("Home", "/"), (board_id.upper(), None)])}</div>
<div class="section"><h2>📘 {board_id.upper()} Board</h2><p style="color:#666;margin-bottom:1rem;">Select a subject to begin learning.</p>{rows}</div>"""
    return HTMLResponse(_render(title=f"{board_id.upper()} Board - CBSE Class X", content=content))


@app.get("/board/{board_id}/{subject_slug}", response_class=HTMLResponse)
async def subject_page(board_id: str, subject_slug: str):
    conn = DB
    board_id = board_id.lower()
    subject_name = subject_slug.replace("-", " ").title()
    # First attempt exact match on ID or exact lowercase name to avoid overlapping matches
    subjects = conn.query(
        "SELECT id, name, board_id FROM subjects WHERE LOWER(board_id) = ? AND (LOWER(id) = ? OR LOWER(name) = ?)",
        (board_id, subject_slug.lower(), subject_slug.replace("-", " ").lower())
    )
    if not subjects:
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


@app.get("/board/{board_id}/subject/{subject_slug}", response_class=HTMLResponse)
async def subject_page_compat(board_id: str, subject_slug: str):
    return await subject_page(board_id, subject_slug)


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

    # Batch-load all chunks for all topics in one query
    topic_ids = [t["id"] for t in topics]
    chunks_by_topic = {}
    if topic_ids:
        placeholders = ",".join(["?"] * len(topic_ids))
        all_chunks = conn.query(
            f"SELECT * FROM chunks WHERE topic_id IN ({placeholders}) ORDER BY seq",
            topic_ids
        )
        for c in all_chunks:
            chunks_by_topic.setdefault(c["topic_id"], []).append(c)

    topics_html = ""
    for t in topics:
        chunks = chunks_by_topic.get(t["id"], [])
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
async def api_tutor_start(request: Request, user: Optional[dict] = Depends(get_current_user)):
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
async def api_tutor_answer(request: Request, user: Optional[dict] = Depends(get_current_user)):
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
async def api_tutor_remedial(request: Request, user: Optional[dict] = Depends(get_current_user)):
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
async def api_tutor_complete(request: Request, user: Optional[dict] = Depends(get_current_user)):
    data = await request.form()
    try:
        session_id = int(data.get("session_id", 0))
    except (ValueError, TypeError):
        return JSONResponse({"error": "Invalid session_id"}, status_code=400)
    xp = ai_tutor.complete_session(session_id)
    return {"status": "ok", "xp": xp}


@app.get("/api/ai/enrich")
@rate_limit(20)
async def api_ai_enrich(request: Request, topic: str = Query(...), chapter: str = Query(""), subject: str = Query(""), topic_type: str = Query("concept")):
    loop = asyncio.get_event_loop()
    enriched = await loop.run_in_executor(
        None, content_enricher.enrich_topic_content,
        topic, chapter, subject, "", topic_type
    )
    html = content_enricher.format_ai_content(enriched)
    return {"html": html, "cached": bool(enriched.get("explanation"))}


# ═══════════════════════════════════════════════════════════════════════════
# AI TOOL API HANDLERS
# ═══════════════════════════════════════════════════════════════════════════


async def _run_in_thread(func, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, func, *args)


@app.get("/api/ai/diagram")
@rate_limit(20)
async def api_ai_diagram(request: Request, concept: str = Query(...), type: str = Query("flowchart")):
    result = await _run_in_thread(ai_services.napkin_diagram, concept, type)
    return result


@app.get("/api/ai/presentation")
@rate_limit(10)
async def api_ai_presentation(request: Request, subject: str = Query(...), chapter: str = Query(...)):
    idx = get_index()
    topics = idx.get_chapter(chapter) if hasattr(idx, 'get_chapter') else []
    result = await _run_in_thread(ai_services.gamma_presentation, subject, chapter, topics)
    return result


@app.get("/api/ai/story")
@rate_limit(20)
async def api_ai_story(request: Request, topic: str = Query(...), chapter: str = Query(""), subject: str = Query("CBSE Science")):
    result = await _run_in_thread(ai_services.tome_story, topic, chapter, subject)
    return result


@app.get("/api/ai/music")
@rate_limit(20)
async def api_ai_music(request: Request, mood: str = Query("calm study piano")):
    result = await _run_in_thread(ai_services.browser_music_params, mood)
    return result


@app.get("/api/ai/pomelli")
@rate_limit(30)
async def api_ai_pomelli(request: Request, template: str = Query(...), a: str = Query(None), b: str = Query(None), c: str = Query(None)):
    params = {}
    if a is not None: params["a"] = a
    if b is not None: params["b"] = b
    if c is not None: params["c"] = c
    if template == "list":
        return ai_services.pomelli_list_templates()
    result = await _run_in_thread(ai_services.pomelli_generate, template, params)
    return result


@app.get("/api/ai/metai")
@rate_limit(10)
async def api_ai_metai(request: Request, concept: str = Query(...), style: str = Query("explainer"), subject: str = Query("Science")):
    result = await _run_in_thread(ai_services.metai_generate, concept, subject, style)
    return result


@app.get("/api/ai/opengrok")
@rate_limit(30)
async def api_ai_opengrok(request: Request, query: str = Query(...)):
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(None, ai_services.opengrok_search, query)
    html = ai_services.opengrok_results_html(query)
    return {"results": results, "html": html}


@app.get("/api/ai/notebooklm")
@rate_limit(10)
async def api_ai_notebooklm(request: Request, subject: str = Query(...), chapter: str = Query(...), topic: str = Query(None)):
    if topic:
        result = await _run_in_thread(ai_services.notebooklm_pedagogical, subject, chapter, topic)
    else:
        idx = get_index()
        topics = idx.get_chapter(chapter) if hasattr(idx, 'get_chapter') else []
        result = await _run_in_thread(ai_services.notebooklm_export, subject, chapter, topics)
    return result


@app.get("/api/ai/youtube")
@rate_limit(20)
async def api_ai_youtube(request: Request, topic: str = Query(...), chapter: str = Query(""), subject: str = Query("")):
    html = await _run_in_thread(ai_services.youtube_section_html, topic, chapter, subject)
    results = await _run_in_thread(ai_services.youtube_search, f"{topic} {chapter} {subject}")
    return {"html": html, "results": results}


@app.get("/api/ai/youtube/generate")
@rate_limit(5)
async def api_ai_youtube_generate(request: Request, topic_id: str = Query(""), chapter_id: str = Query(""), topic_name: str = Query(""), max_clips: int = Query(8)):
    result = await _run_in_thread(ai_services.youtube_generate_clips,
                                  topic_id or None, chapter_id or None, topic_name or None, min(max_clips, 20))
    return result


@app.get("/api/ai/research")
@rate_limit(10)
async def api_ai_research(request: Request, query: str = Query(...), subject: str = Query("CBSE")):
    result = await _run_in_thread(ai_services.llm_research, query, subject)
    return result


@app.get("/api/ai/literature")
@rate_limit(10)
async def api_ai_literature(request: Request, query: str = Query(...), subject: str = Query("science")):
    result = await _run_in_thread(ai_services.llm_literature, query, subject)
    return result


@app.get("/api/ai/visualize")
@rate_limit(20)
async def api_ai_visualize(request: Request, concept: str = Query(...), style: str = Query("diagram")):
    result = await _run_in_thread(ai_services.svg_visualize, concept, style)
    return result


@app.get("/api/ai/gemma4")
@rate_limit(10)
async def api_ai_gemma4(request: Request, prompt: str = Query(...), system: str = Query(None)):
    result = await _run_in_thread(ai_services.gemma4_query, prompt, system)
    return {"response": result}


@app.get("/api/ai/flash")
@rate_limit(10)
async def api_ai_flash(request: Request, prompt: str = Query(...), system: str = Query(None)):
    result = await _run_in_thread(ai_services.google_flash_query, prompt, system)
    return {"response": result}


@app.get("/api/ai/quillbot")
@rate_limit(20)
async def api_ai_quillbot(request: Request, text: str = Query(...), mode: str = Query("simpler")):
    result = await _run_in_thread(ai_services.quillbot_paraphrase, text, mode)
    return result


@app.get("/api/ai/voiceover")
@rate_limit(30)
async def api_ai_voiceover(request: Request, text: str = Query(...), voice: str = Query("female"), lang: str = Query("en-IN")):
    result = ai_services.quillbot_speak_segments(text, lang, voice)
    return result


# ═══════════════════════════════════════════════════════════════════════════
# AI TOOL PAGES
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/ai/diagram", response_class=HTMLResponse)
async def ai_diagram():
    return _render(
        title="AI Diagram Generator — CBSE Class X",
        content="""
        <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> <a href="/ai">AI Studio</a> <span class="sep">›</span> Diagram Generator</div>
        <div class="section">
            <h2>📐 AI Diagram Generator</h2>
            <p class="subtitle">Generate flowcharts, mind maps, and diagrams for any concept using Mistral AI</p>
            <div class="book-section" style="padding:1.5rem;margin-top:1rem;">
                <label style="font-weight:500;display:block;margin-bottom:0.5rem;">Concept</label>
                <input type="text" id="diagram-concept" value="Photosynthesis" style="width:100%;padding:0.7rem;border:1px solid var(--border);border-radius:8px;margin-bottom:1rem;">
                <label style="font-weight:500;display:block;margin-bottom:0.5rem;">Type</label>
                <select id="diagram-type" style="width:100%;padding:0.7rem;border:1px solid var(--border);border-radius:8px;margin-bottom:1rem;">
                    <option value="flowchart">Flowchart</option>
                    <option value="mindmap">Mind Map</option>
                    <option value="concept-map">Concept Map</option>
                </select>
                <button onclick="generateDiagram()" class="btn-primary" style="padding:0.8rem 2rem;background:var(--primary);color:#fff;border:none;border-radius:8px;font-size:1rem;font-weight:600;cursor:pointer;">Generate</button>
                <div id="diagram-output" style="margin-top:1rem;padding:1rem;border:1px solid var(--border);border-radius:8px;min-height:100px;white-space:pre-wrap;font-family:monospace;"></div>
            </div>
        </div>
        <script>
        async function generateDiagram() {
            const concept = document.getElementById('diagram-concept').value;
            const type = document.getElementById('diagram-type').value;
            const out = document.getElementById('diagram-output');
            out.innerHTML = '<em>Generating...</em>';
            try {
                const resp = await fetch('/api/ai/diagram?concept='+encodeURIComponent(concept)+'&type='+encodeURIComponent(type));
                const data = await resp.json();
                out.innerHTML = data.diagram || data.html || '<em>No diagram generated</em>';
            } catch(e) {
                out.innerHTML = '<em>Error: ' + e.message + '</em>';
            }
        }
        </script>"""
    )


@app.get("/ai/presentation", response_class=HTMLResponse)
async def ai_presentation():
    return _render(
        title="AI Presentation Generator — CBSE Class X",
        content="""
        <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> <a href="/ai">AI Studio</a> <span class="sep">›</span> Presentation</div>
        <div class="section">
            <h2>📽️ AI Presentation Generator</h2>
            <p class="subtitle">Create HTML slide presentations for any topic using Mistral AI</p>
            <div class="book-section" style="padding:1.5rem;margin-top:1rem;">
                <label style="font-weight:500;display:block;margin-bottom:0.5rem;">Subject</label>
                <input type="text" id="pres-subject" value="Science" style="width:100%;padding:0.7rem;border:1px solid var(--border);border-radius:8px;margin-bottom:1rem;">
                <label style="font-weight:500;display:block;margin-bottom:0.5rem;">Chapter / Topic</label>
                <input type="text" id="pres-chapter" value="Photosynthesis" style="width:100%;padding:0.7rem;border:1px solid var(--border);border-radius:8px;margin-bottom:1rem;">
                <button onclick="generatePresentation()" class="btn-primary" style="padding:0.8rem 2rem;background:var(--primary);color:#fff;border:none;border-radius:8px;font-size:1rem;font-weight:600;cursor:pointer;">Generate</button>
                <div id="pres-output" style="margin-top:1rem;"></div>
            </div>
        </div>
        <script>
        async function generatePresentation() {
            const s = document.getElementById('pres-subject').value;
            const c = document.getElementById('pres-chapter').value;
            const out = document.getElementById('pres-output');
            out.innerHTML = '<em>Generating...</em>';
            try {
                const resp = await fetch('/api/ai/presentation?subject='+encodeURIComponent(s)+'&chapter='+encodeURIComponent(c));
                const data = await resp.json();
                out.innerHTML = data.html || '<em>No presentation generated</em>';
            } catch(e) {
                out.innerHTML = '<em>Error: ' + e.message + '</em>';
            }
        }
        </script>"""
    )


@app.get("/ai/voiceover", response_class=HTMLResponse)
async def ai_voiceover():
    return _render(
        title="AI Voiceover — CBSE Class X",
        content="""
        <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> <a href="/ai">AI Studio</a> <span class="sep">›</span> Voiceover</div>
        <div class="section">
            <h2>🎤 AI Voiceover Studio</h2>
            <p class="subtitle">Text-to-speech with Indian language support & voice-video sync</p>
            <div class="book-section" style="padding:1.5rem;margin-top:1rem;">
                <label style="font-weight:500;display:block;margin-bottom:0.5rem;">Script / Text to speak</label>
                <textarea id="vo-text" rows="4" style="width:100%;padding:0.7rem;border:1px solid var(--border);border-radius:8px;margin-bottom:1rem;">In this lesson, we will learn about the process of photosynthesis. Plants use sunlight, water, and carbon dioxide to produce food and oxygen.</textarea>
                <div style="display:flex;gap:1rem;flex-wrap:wrap;margin-bottom:1rem;">
                    <div style="flex:1;min-width:140px;">
                        <label style="font-weight:500;display:block;font-size:0.85rem;margin-bottom:0.3rem;">Language</label>
                        <select id="vo-lang" style="width:100%;padding:0.5rem;border:1px solid var(--border);border-radius:6px;font-size:0.85rem;">
                            <option value="en-IN">English (India)</option>
                            <option value="hi-IN">हिन्दी (Hindi)</option>
                            <option value="te-IN">తెలుగు (Telugu)</option>
                        </select>
                    </div>
                    <div style="flex:1;min-width:140px;">
                        <label style="font-weight:500;display:block;font-size:0.85rem;margin-bottom:0.3rem;">Voice</label>
                        <select id="vo-voice" style="width:100%;padding:0.5rem;border:1px solid var(--border);border-radius:6px;font-size:0.85rem;">
                            <option value="female">👩 Female</option>
                            <option value="male">👨 Male</option>
                        </select>
                    </div>
                    <div style="flex:1;min-width:140px;">
                        <label style="font-weight:500;display:block;font-size:0.85rem;margin-bottom:0.3rem;">Rate</label>
                        <input type="range" id="vo-rate" min="0.5" max="2" step="0.1" value="1" oninput="document.getElementById('vo-rate-val').textContent=this.value" style="width:100%;">
                        <span id="vo-rate-val" style="font-size:0.8rem;color:#666;">1</span>
                    </div>
                </div>
                <div style="display:flex;gap:0.5rem;flex-wrap:wrap;">
                    <button onclick="speakText()" class="btn-primary" style="padding:0.7rem 1.5rem;background:var(--primary);color:#fff;border:none;border-radius:8px;font-size:0.95rem;font-weight:600;cursor:pointer;">🔊 Speak</button>
                    <button onclick="stopSpeech()" style="padding:0.7rem 1.5rem;background:#fee2e2;color:#dc2626;border:none;border-radius:8px;font-size:0.95rem;font-weight:600;cursor:pointer;">⏹ Stop</button>
                    <button onclick="syncWithVideo()" style="padding:0.7rem 1.5rem;background:#e8f4f8;color:#4a90d9;border:none;border-radius:8px;font-size:0.95rem;font-weight:600;cursor:pointer;">🎬 Sync with Video</button>
                </div>
                <div id="vo-waveform" style="margin-top:1rem;height:60px;background:#f8f9fa;border-radius:8px;border:1px solid var(--border);overflow:hidden;position:relative;">
                    <canvas id="vo-canvas" style="width:100%;height:60px;"></canvas>
                </div>
                <div id="vo-status" style="margin-top:0.5rem;font-size:0.85rem;color:#666;text-align:center;"></div>
            </div>
        </div>
        <script>
        var voAudioCtx = null;
        var voAnalyser = null;
        var voSource = null;
        var voAnimationId = null;
        function speakText() {
            var text = document.getElementById('vo-text').value;
            var lang = document.getElementById('vo-lang').value;
            var voice = document.getElementById('vo-voice').value;
            var rate = parseFloat(document.getElementById('vo-rate').value);
            if (!('speechSynthesis' in window)) { alert('Text-to-speech not supported in this browser.'); return; }
            window.speechSynthesis.cancel();
            var utter = new SpeechSynthesisUtterance(text);
            utter.lang = lang;
            utter.rate = rate;
            utter.pitch = voice === 'female' ? 1.2 : 0.85;
            utter.onstart = function() { document.getElementById('vo-status').textContent = '🔊 Speaking... (' + voice + ')'; startWaveform(); };
            utter.onend = function() { document.getElementById('vo-status').textContent = '✅ Done'; stopWaveform(); };
            utter.onerror = function() { document.getElementById('vo-status').textContent = '❌ Error'; stopWaveform(); };
            window.speechSynthesis.speak(utter);
        }
        function stopSpeech() { window.speechSynthesis.cancel(); stopWaveform(); document.getElementById('vo-status').textContent = '⏹ Stopped'; }
        function startWaveform() {
            var canvas = document.getElementById('vo-canvas');
            var ctx = canvas.getContext('2d');
            canvas.width = canvas.offsetWidth;
            canvas.height = 60;
            var w = canvas.width, h = canvas.height;
            function draw() {
                ctx.clearRect(0,0,w,h);
                var bars = 48;
                var barW = (w - bars * 2) / bars;
                for (var i = 0; i < bars; i++) {
                    var val = Math.random() * 0.7 + 0.3;
                    var barH = val * h * 0.8;
                    var x = i * (barW + 2);
                    var hue = 200 + i * 3;
                    ctx.fillStyle = 'hsl(' + hue + ', 70%, 55%)';
                    ctx.globalAlpha = 0.7;
                    ctx.fillRect(x, (h - barH) / 2, barW, barH);
                }
                ctx.globalAlpha = 1;
                voAnimationId = requestAnimationFrame(draw);
            }
            draw();
        }
        function stopWaveform() { if (voAnimationId) { cancelAnimationFrame(voAnimationId); voAnimationId = null; } }
        function syncWithVideo() {
            var text = document.getElementById('vo-text').value;
            var voice = document.getElementById('vo-voice').value;
            var lang = document.getElementById('vo-lang').value;
            document.getElementById('vo-status').textContent = '🔄 Generating voiceover segments for video sync...';
            fetch('/api/ai/voiceover?text='+encodeURIComponent(text)+'&voice='+voice+'&lang='+lang)
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (data.tts === 'browser') {
                        document.getElementById('vo-status').textContent = '✅ Ready for video sync. Click "Speak" to play voiceover with video.';
                        // Auto-start with a short delay for demo
                        setTimeout(function() { speakText(); }, 500);
                    } else {
                        document.getElementById('vo-status').textContent = '✅ Voiceover synced';
                    }
                })
                .catch(function(e) { document.getElementById('vo-status').textContent = '❌ Sync error: ' + e.message; });
        }
        window.addEventListener('resize', function() {
            var canvas = document.getElementById('vo-canvas');
            if (canvas) canvas.width = canvas.offsetWidth;
        });
        </script>"""
    )


@app.get("/ai/music", response_class=HTMLResponse)
async def ai_music():
    return _render(
        title="AI Music — CBSE Class X",
        content="""
        <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> <a href="/ai">AI Studio</a> <span class="sep">›</span> Music</div>
        <div class="section">
            <h2>🎵 AI Music Generator</h2>
            <p class="subtitle">Generate study music with configurable mood parameters using Mistral AI</p>
            <div class="book-section" style="padding:1.5rem;margin-top:1rem;">
                <label style="font-weight:500;display:block;margin-bottom:0.5rem;">Mood</label>
                <select id="music-mood" style="width:100%;padding:0.7rem;border:1px solid var(--border);border-radius:8px;margin-bottom:1rem;">
                    <option value="calm study piano">Calm — Study Piano</option>
                    <option value="focus ambient">Focus — Ambient</option>
                    <option value="energetic learning">Energetic — Learning</option>
                </select>
                <button onclick="generateMusic()" class="btn-primary" style="padding:0.8rem 2rem;background:var(--primary);color:#fff;border:none;border-radius:8px;font-size:1rem;font-weight:600;cursor:pointer;">Generate</button>
                <div id="music-output" style="margin-top:1rem;padding:1rem;border:1px solid var(--border);border-radius:8px;min-height:60px;"></div>
            </div>
        </div>
        <script>
        async function generateMusic() {
            const mood = document.getElementById('music-mood').value;
            const out = document.getElementById('music-output');
            out.innerHTML = '<em>Generating music parameters...</em>';
            try {
                const resp = await fetch('/api/ai/music?mood='+encodeURIComponent(mood));
                const data = await resp.json();
                out.innerHTML = '<pre style="margin:0;">' + JSON.stringify(data, null, 2) + '</pre>';
            } catch(e) {
                out.innerHTML = '<em>Error: ' + e.message + '</em>';
            }
        }
        </script>"""
    )


@app.get("/ai/story", response_class=HTMLResponse)
async def ai_story():
    return _render(
        title="AI Story Generator — CBSE Class X",
        content="""
        <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> <a href="/ai">AI Studio</a> <span class="sep">›</span> Story</div>
        <div class="section">
            <h2>📖 AI Story Generator</h2>
            <p class="subtitle">Generate educational stories that make learning fun — powered by Mistral AI</p>
            <div class="book-section" style="padding:1.5rem;margin-top:1rem;">
                <label style="font-weight:500;display:block;margin-bottom:0.5rem;">Topic</label>
                <input type="text" id="story-topic" value="Photosynthesis" style="width:100%;padding:0.7rem;border:1px solid var(--border);border-radius:8px;margin-bottom:1rem;">
                <label style="font-weight:500;display:block;margin-bottom:0.5rem;">Chapter</label>
                <input type="text" id="story-chapter" value="Life Processes" style="width:100%;padding:0.7rem;border:1px solid var(--border);border-radius:8px;margin-bottom:1rem;">
                <button onclick="generateStory()" class="btn-primary" style="padding:0.8rem 2rem;background:var(--primary);color:#fff;border:none;border-radius:8px;font-size:1rem;font-weight:600;cursor:pointer;">Generate Story</button>
                <div id="story-output" style="margin-top:1rem;padding:1rem;border:1px solid var(--border);border-radius:8px;min-height:100px;"></div>
            </div>
        </div>
        <script>
        async function generateStory() {
            const t = document.getElementById('story-topic').value;
            const c = document.getElementById('story-chapter').value;
            const out = document.getElementById('story-output');
            out.innerHTML = '<em>Generating story...</em>';
            try {
                const resp = await fetch('/api/ai/story?topic='+encodeURIComponent(t)+'&chapter='+encodeURIComponent(c));
                const data = await resp.json();
                out.innerHTML = data.story || data.html || '<em>No story generated</em>';
            } catch(e) {
                out.innerHTML = '<em>Error: ' + e.message + '</em>';
            }
        }
        </script>"""
    )


@app.get("/ai/pomelli", response_class=HTMLResponse)
async def ai_pomelli():
    return _render(
        title="Pomelli Interactive Math — CBSE Class X",
        content="""
        <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> <a href="/ai">AI Studio</a> <span class="sep">›</span> Pomelli Math</div>
        <div class="section">
            <h2>📐 Pomelli Interactive Math</h2>
            <p class="subtitle">Interactive math visualizations — graphs, geometry, fractions, and more</p>
            <div class="book-section" style="padding:1.5rem;margin-top:1rem;">
                <label style="font-weight:500;display:block;margin-bottom:0.5rem;">Template</label>
                <select id="pomelli-template" style="width:100%;padding:0.7rem;border:1px solid var(--border);border-radius:8px;margin-bottom:1rem;">
                    <option value="graph-linear">Linear Graph</option>
                    <option value="graph-quadratic">Quadratic Graph</option>
                    <option value="graph-trig">Trigonometric Graph</option>
                    <option value="geometry-transform">Geometry Transform</option>
                    <option value="fractions">Fractions</option>
                    <option value="pythagoras">Pythagoras Theorem</option>
                    <option value="number-line">Number Line</option>
                    <option value="probability">Probability</option>
                    <option value="statistics">Statistics</option>
                    <option value="area-perimeter">Area & Perimeter</option>
                </select>
                <button onclick="loadPomelli()" class="btn-primary" style="padding:0.8rem 2rem;background:var(--primary);color:#fff;border:none;border-radius:8px;font-size:1rem;font-weight:600;cursor:pointer;margin-top:1rem;">Load Interactive</button>
                <div id="pomelli-output" style="margin-top:1rem;padding:1rem;border:1px solid var(--border);border-radius:8px;min-height:200px;"></div>
            </div>
        </div>
        <script>
        async function loadPomelli() {
            const tpl = document.getElementById('pomelli-template').value;
            const out = document.getElementById('pomelli-output');
            out.innerHTML = '<em>Loading...</em>';
            try {
                const resp = await fetch('/api/ai/pomelli?template='+encodeURIComponent(tpl));
                const data = await resp.json();
                out.innerHTML = data.html || '<em>No content generated</em>';
            } catch(e) {
                out.innerHTML = '<em>Error: ' + e.message + '</em>';
            }
        }
        </script>"""
    )


@app.get("/ai/metai", response_class=HTMLResponse)
async def ai_metai():
    return _render(
        title="MetaAI Learning — CBSE Class X",
        content="""
        <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> <a href="/ai">AI Studio</a> <span class="sep">›</span> MetaAI</div>
        <div class="section">
            <h2>🤖 MetaAI Learning</h2>
            <p class="subtitle">Contextual learning powered by MetaAI — explanations, storyboards, and learning guides</p>
            <div class="book-section" style="padding:1.5rem;margin-top:1rem;">
                <label style="font-weight:500;display:block;margin-bottom:0.5rem;">Concept</label>
                <input type="text" id="metai-concept" value="Photosynthesis" style="width:100%;padding:0.7rem;border:1px solid var(--border);border-radius:8px;margin-bottom:1rem;">
                <label style="font-weight:500;display:block;margin-bottom:0.5rem;">Style</label>
                <select id="metai-style" style="width:100%;padding:0.7rem;border:1px solid var(--border);border-radius:8px;margin-bottom:1rem;">
                    <option value="explainer">Explainer</option>
                    <option value="storyboard">Storyboard</option>
                    <option value="qa">Q&A</option>
                    <option value="summary">Summary</option>
                </select>
                <button onclick="generateMetai()" class="btn-primary" style="padding:0.8rem 2rem;background:var(--primary);color:#fff;border:none;border-radius:8px;font-size:1rem;font-weight:600;cursor:pointer;">Generate</button>
                <div id="metai-output" style="margin-top:1rem;padding:1rem;border:1px solid var(--border);border-radius:8px;min-height:100px;"></div>
            </div>
        </div>
        <script>
        async function generateMetai() {
            const c = document.getElementById('metai-concept').value;
            const s = document.getElementById('metai-style').value;
            const out = document.getElementById('metai-output');
            out.innerHTML = '<em>Generating...</em>';
            try {
                const resp = await fetch('/api/ai/metai?concept='+encodeURIComponent(c)+'&style='+encodeURIComponent(s));
                const data = await resp.json();
                out.innerHTML = data.html || data.content || '<em>No content generated</em>';
            } catch(e) {
                out.innerHTML = '<em>Error: ' + e.message + '</em>';
            }
        }
        </script>"""
    )


@app.get("/ai/opengrok", response_class=HTMLResponse)
async def ai_opengrok():
    return _render(
        title="OpenGrok Search — CBSE Class X",
        content="""
        <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> <a href="/ai">AI Studio</a> <span class="sep">›</span> OpenGrok</div>
        <div class="section">
            <h2>🔍 OpenGrok Formula & Theorem Search</h2>
            <p class="subtitle">Search formulas, theorems, and code across the CBSE curriculum</p>
            <div class="book-section" style="padding:1.5rem;margin-top:1rem;">
                <label style="font-weight:500;display:block;margin-bottom:0.5rem;">Search Query</label>
                <input type="text" id="og-query" value="quadratic equation" style="width:100%;padding:0.7rem;border:1px solid var(--border);border-radius:8px;margin-bottom:1rem;">
                <button onclick="searchOpenGrok()" class="btn-primary" style="padding:0.8rem 2rem;background:var(--primary);color:#fff;border:none;border-radius:8px;font-size:1rem;font-weight:600;cursor:pointer;">Search</button>
                <div id="og-output" style="margin-top:1rem;padding:1rem;border:1px solid var(--border);border-radius:8px;min-height:100px;"></div>
            </div>
        </div>
        <script>
        async function searchOpenGrok() {
            const q = document.getElementById('og-query').value;
            const out = document.getElementById('og-output');
            out.innerHTML = '<em>Searching...</em>';
            try {
                const resp = await fetch('/api/ai/opengrok?query='+encodeURIComponent(q));
                const data = await resp.json();
                out.innerHTML = data.html || JSON.stringify(data.results || data, null, 2) || '<em>No results found</em>';
            } catch(e) {
                out.innerHTML = '<em>Error: ' + e.message + '</em>';
            }
        }
        </script>"""
    )


# ═══════════════════════════════════════════════════════════════════════════
# MISSING BRIDGE PAGES (replacing legacy catch-all)
# ═══════════════════════════════════════════════════════════════════════════


@app.get("/about", response_class=HTMLResponse)
async def about_page():
    return HTMLResponse(_render(title="About — CBSE Class X", content="""
    <div class="section">
        <h2>📖 About CBSE Education Platform</h2>
        <p style="color:#666;margin-bottom:1rem;">AI-powered learning platform for CBSE, AP Board, and TS Board Class V–X students.</p>
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:1rem;">
            <div class="book-section"><h3>📚 Multi-Board Support</h3><p>CBSE · AP Board · Telangana Board — complete syllabus coverage.</p></div>
            <div class="book-section"><h3>🤖 AI-Powered Tools</h3><p>Mistral AI & Gemini: diagram generation, presentations, voiceovers, research, and more.</p></div>
            <div class="book-section"><h3>🎯 Interactive Learning</h3><p>Quizzes, mind maps, interactive cards, matching games for every topic.</p></div>
            <div class="book-section"><h3>🏆 Gamification</h3><p>XP, levels, streaks, and achievements to keep you motivated.</p></div>
            <div class="book-section"><h3>🌐 Multi-Lingual</h3><p>English · हिन्दी · తెలుగు · தமிழ் · ಕನ್ನಡ · বাংলা · മലയാളം — learn in your preferred medium.</p></div>
            <div class="book-section"><h3>📊 Progress Tracking</h3><p>Personalized learning paths, revision notes, and mock exams.</p></div>
        </div>
    </div>"""))


@app.get("/exams", response_class=HTMLResponse)
async def exams_page():
    conn = DB
    rows = ""
    if conn and conn.table_exists("subjects"):
        subjects = conn.query("SELECT id, name, board_id FROM subjects ORDER BY board_id, name")
        for s in subjects:
            chs = conn.query("SELECT id, num, title FROM chapters WHERE subject_id = ? ORDER BY num LIMIT 5", (s["id"],))
            ch_links = "".join(f'<li><a href="/chapter/{ch["id"]}">Ch {ch["num"]}: {ch["title"]}</a></li>' for ch in chs)
            if ch_links:
                rows += f'<div class="book-section"><h3><a href="/board/{s["board_id"]}/{s["id"]}">{s["name"]}</a></h3><ul>{ch_links}</ul><p style="margin-top:0.3rem;"><a href="/quiz/{s["id"]}" class="tts-btn" style="font-size:0.78rem;">Take Mock Exam</a></p></div>'
    if not rows:
        rows = '<p style="text-align:center;padding:2rem;color:#666;">No exams available yet.</p>'
    return HTMLResponse(_render(title="Mock Exams — CBSE Class X", content=f"""
    <div class="breadcrumb">{_build_breadcrumb([("Home", "/"), ("Mock Exams", None)])}</div>
    <div class="section"><h2>🏆 Mock Exams</h2><p style="color:#666;margin-bottom:1rem;">Practice with chapter-wise mock exams. Track your progress and improve.</p>{rows}</div>"""))


@app.get("/ai", response_class=HTMLResponse)
async def ai_studio_hub():
    return HTMLResponse(_render(title="AI Studio — CBSE Class X", content="""
    <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> AI Studio</div>
    <div class="section"><h2>🤖 AI Studio</h2>
    <p style="color:#666;margin-bottom:1rem;">AI-powered learning tools powered by Mistral AI & Gemini.</p>
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:0.8rem;">
        <a href="/ai/diagram" class="book-section" style="text-decoration:none;display:block;"><h3>📐 Diagram Generator</h3><p style="font-size:0.85rem;color:#666;">Flowcharts, mind maps, concept maps</p></a>
        <a href="/ai/presentation" class="book-section" style="text-decoration:none;display:block;"><h3>📽️ Presentations</h3><p style="font-size:0.85rem;color:#666;">HTML slide decks for any topic</p></a>
        <a href="/ai/story" class="book-section" style="text-decoration:none;display:block;"><h3>📖 Story Generator</h3><p style="font-size:0.85rem;color:#666;">Educational stories & analogies</p></a>
        <a href="/ai/voiceover" class="book-section" style="text-decoration:none;display:block;"><h3>🎤 Voiceover</h3><p style="font-size:0.85rem;color:#666;">Text-to-speech in Indian languages</p></a>
        <a href="/ai/music" class="book-section" style="text-decoration:none;display:block;"><h3>🎵 Study Music</h3><p style="font-size:0.85rem;color:#666;">Ambient focus & study music</p></a>
        <a href="/ai/research" class="book-section" style="text-decoration:none;display:block;"><h3>🔬 Research Assistant</h3><p style="font-size:0.85rem;color:#666;">Deep topic research & analysis</p></a>
        <a href="/ai/literature" class="book-section" style="text-decoration:none;display:block;"><h3>📚 Literature Review</h3><p style="font-size:0.85rem;color:#666;">Research paper summaries</p></a>
        <a href="/ai/visualize" class="book-section" style="text-decoration:none;display:block;"><h3>👁️ SVG Visualizer</h3><p style="font-size:0.85rem;color:#666;">Concept → SVG diagrams</p></a>
        <a href="/ai/pomelli" class="book-section" style="text-decoration:none;display:block;"><h3>📐 Pomelli Math</h3><p style="font-size:0.85rem;color:#666;">Interactive math visualizations</p></a>
        <a href="/ai/metai" class="book-section" style="text-decoration:none;display:block;"><h3>🤖 MetaAI Learning</h3><p style="font-size:0.85rem;color:#666;">Storyboards & learning guides</p></a>
        <a href="/ai/youtube" class="book-section" style="text-decoration:none;display:block;"><h3>▶️ YouTube Videos</h3><p style="font-size:0.85rem;color:#666;">Search & embed CBSE videos</p></a>
        <a href="/ai/opengrok" class="book-section" style="text-decoration:none;display:block;"><h3>📐 Formulas & Theorems</h3><p style="font-size:0.85rem;color:#666;">Math & science formula search</p></a>
    </div></div>"""))


@app.get("/ai/youtube", response_class=HTMLResponse)
async def ai_youtube_page():
    return HTMLResponse(_render(title="AI YouTube Videos — CBSE Class X", content="""
    <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> <a href="/ai">AI Studio</a> <span class="sep">›</span> YouTube Videos</div>
    <div class="section">
        <h2>▶️ AI YouTube Video Search</h2>
        <p class="subtitle">Search CBSE educational videos — powered by Google YouTube Data API v3</p>
        <div class="book-section" style="padding:1.5rem;margin-top:1rem;">
            <label style="font-weight:500;display:block;margin-bottom:0.5rem;">Topic</label>
            <input type="text" id="yt-topic" value="Photosynthesis CBSE Class 10" style="width:100%;padding:0.7rem;border:1px solid var(--border);border-radius:8px;margin-bottom:1rem;">
            <button onclick="searchYouTube()" class="btn-primary" style="padding:0.8rem 2rem;background:var(--primary);color:#fff;border:none;border-radius:8px;font-size:1rem;font-weight:600;cursor:pointer;">🔍 Search Videos</button>
            <div id="yt-output" style="margin-top:1rem;"></div>
        </div>
    </div>
    <div class="section">
        <h2>🎬 Iterative Short-Clip Generator</h2>
        <p class="subtitle">Split a long topic into short clips with voiceover sync</p>
        <div class="book-section" style="padding:1.5rem;margin-top:1rem;">
            <label style="font-weight:500;display:block;margin-bottom:0.5rem;">Topic Name or Topic ID</label>
            <input type="text" id="yt-clip-topic" value="Quadratic Equations" style="width:100%;padding:0.7rem;border:1px solid var(--border);border-radius:8px;margin-bottom:0.5rem;">
            <div style="display:flex;gap:0.5rem;flex-wrap:wrap;">
                <input type="text" id="yt-clip-chapter" placeholder="Chapter ID (optional)" style="flex:1;min-width:120px;padding:0.7rem;border:1px solid var(--border);border-radius:8px;">
                <input type="number" id="yt-clip-count" value="5" min="2" max="20" style="width:80px;padding:0.7rem;border:1px solid var(--border);border-radius:8px;">
                <button onclick="generateClips()" class="btn-primary" style="padding:0.8rem 2rem;background:var(--accent);color:#fff;border:none;border-radius:8px;font-size:1rem;font-weight:600;cursor:pointer;">🎬 Generate Clips</button>
            </div>
            <div id="yt-clip-output" style="margin-top:1rem;"></div>
        </div>
    </div>
    <script>
    async function searchYouTube() {
        const topic = document.getElementById('yt-topic').value;
        const out = document.getElementById('yt-output');
        out.innerHTML = '<em>Searching YouTube...</em>';
        try {
            const resp = await fetch('/api/ai/youtube?topic='+encodeURIComponent(topic));
            const data = await resp.json();
            out.innerHTML = data.html || '<em>No videos found</em>';
        } catch(e) {
            out.innerHTML = '<em>Error: ' + e.message + '</em>';
        }
    }
    async function generateClips() {
        const topic = document.getElementById('yt-clip-topic').value;
        const chapter = document.getElementById('yt-clip-chapter').value;
        const max = document.getElementById('yt-clip-count').value || 5;
        const out = document.getElementById('yt-clip-output');
        out.innerHTML = '<em>Generating clip playlist...</em>';
        try {
            let url = '/api/ai/youtube/generate?topic_name='+encodeURIComponent(topic)+'&max_clips='+max;
            if (chapter) url += '&chapter_id='+encodeURIComponent(chapter);
            const resp = await fetch(url);
            const data = await resp.json();
            if (!data.success) { out.innerHTML = '<em>Generation failed</em>'; return; }
            let h = '<div style="margin-top:0.5rem;"><h4 style="color:var(--accent);margin-bottom:0.3rem;">🎬 Playlist: '+data.topic+'</h4>';
            h += '<p style="font-size:0.8rem;color:#666;">'+data.total_clips+' clips &middot; ~'+data.total_duration+'s total</p>';
            h += '<div style="display:flex;flex-direction:column;gap:0.5rem;margin-top:0.5rem;">';
            for (const c of data.clips) {
                h += '<div class="book-section" style="padding:0.75rem;border-left:3px solid var(--accent);">';
                h += '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;">';
                h += '<strong>#'+c.index+' '+c.segment_title+'</strong>';
                h += '<span style="font-size:0.75rem;color:#666;">~'+c.duration_sec+'s</span>';
                h += '</div>';
                if (c.videoId) {
                    h += '<div class="video-container" style="position:relative;padding-bottom:56.25%;height:0;overflow:hidden;max-width:100%;background:#000;border-radius:6px;margin:0.4rem 0;">';
                    h += '<iframe src="https://www.youtube.com/embed/'+c.videoId+'?rel=0" style="position:absolute;top:0;left:0;width:100%;height:100%;border:0;" allowfullscreen loading="lazy"></iframe></div>';
                } else {
                    h += '<p style="font-size:0.78rem;color:#888;margin:0.3rem 0;"><a href="https://www.youtube.com/results?search_query='+encodeURIComponent(c.query)+'" target="_blank" rel="noopener" style="color:var(--accent);">Search YouTube for "'+c.segment_title+'" →</a></p>';
                }
                if (c.voiceover && c.voiceover.segments) {
                    h += '<div style="font-size:0.75rem;color:#666;margin-top:0.2rem;">🔊 '+c.voiceover.segments.length+' speech segments &middot; ~'+c.voiceover.total_duration+'s</div>';
                }
                h += '</div>';
            }
            h += '</div></div>';
            out.innerHTML = h;
        } catch(e) {
            out.innerHTML = '<em>Error: ' + e.message + '</em>';
        }
    }
    </script>"""))


@app.get("/ai/research", response_class=HTMLResponse)
async def ai_research_page():
    return HTMLResponse(_render(title="AI Research Assistant — CBSE Class X", content="""
    <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> <a href="/ai">AI Studio</a> <span class="sep">›</span> Research</div>
    <div class="section">
        <h2>🔬 AI Research Assistant</h2>
        <p class="subtitle">Deep research on any topic — powered by Mistral AI</p>
        <div class="book-section" style="padding:1.5rem;margin-top:1rem;">
            <label style="font-weight:500;display:block;margin-bottom:0.5rem;">Research Query</label>
            <input type="text" id="res-query" value="Photosynthesis process" style="width:100%;padding:0.7rem;border:1px solid var(--border);border-radius:8px;margin-bottom:1rem;">
            <button onclick="doResearch()" class="btn-primary" style="padding:0.8rem 2rem;background:var(--primary);color:#fff;border:none;border-radius:8px;font-size:1rem;font-weight:600;cursor:pointer;">Research</button>
            <div id="res-output" style="margin-top:1rem;padding:1rem;border:1px solid var(--border);border-radius:8px;min-height:80px;"></div>
        </div>
    </div>
    <script>
    async function doResearch() {
        const q = document.getElementById('res-query').value;
        const out = document.getElementById('res-output');
        out.innerHTML = '<em>Researching...</em>';
        try {
            const resp = await fetch('/api/ai/research?query='+encodeURIComponent(q));
            const data = await resp.json();
            out.innerHTML = '<div style="line-height:1.7;">' + data.answer.replace(/\\n/g, '<br>').replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>') + '</div>';
        } catch(e) {
            out.innerHTML = '<em>Error: ' + e.message + '</em>';
        }
    }
    </script>"""))


@app.get("/ai/literature", response_class=HTMLResponse)
async def ai_literature_page():
    return HTMLResponse(_render(title="AI Literature Review — CBSE Class X", content="""
    <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> <a href="/ai">AI Studio</a> <span class="sep">›</span> Literature</div>
    <div class="section">
        <h2>📚 AI Literature Review</h2>
        <p class="subtitle">Research paper summaries on any topic</p>
        <div class="book-section" style="padding:1.5rem;margin-top:1rem;">
            <label style="font-weight:500;display:block;margin-bottom:0.5rem;">Topic</label>
            <input type="text" id="lit-topic" value="Photosynthesis" style="width:100%;padding:0.7rem;border:1px solid var(--border);border-radius:8px;margin-bottom:1rem;">
            <button onclick="doLitReview()" class="btn-primary" style="padding:0.8rem 2rem;background:var(--primary);color:#fff;border:none;border-radius:8px;font-size:1rem;font-weight:600;cursor:pointer;">Review</button>
            <div id="lit-output" style="margin-top:1rem;"></div>
        </div>
    </div>
    <script>
    async function doLitReview() {
        const q = document.getElementById('lit-topic').value;
        const out = document.getElementById('lit-output');
        out.innerHTML = '<em>Reviewing literature...</em>';
        try {
            const resp = await fetch('/api/ai/literature?query='+encodeURIComponent(q));
            const data = await resp.json();
            const papers = data.results || [];
            let html = '';
            papers.forEach(function(p) {
                html += '<div class="book-section" style="margin-bottom:0.5rem;"><h4 style="margin:0;">' + p.title + '</h4><p style="font-size:0.85rem;color:#666;margin:0.2rem 0;">' + (p.authors || '') + ' (' + (p.year || '') + ')</p><p style="font-size:0.9rem;margin:0.3rem 0 0;">' + (p.abstract || '') + '</p></div>';
            });
            out.innerHTML = html || '<em>No literature found</em>';
        } catch(e) {
            out.innerHTML = '<em>Error: ' + e.message + '</em>';
        }
    }
    </script>"""))


@app.get("/ai/visualize", response_class=HTMLResponse)
async def ai_visualize_page():
    return HTMLResponse(_render(title="AI SVG Visualizer — CBSE Class X", content="""
    <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> <a href="/ai">AI Studio</a> <span class="sep">›</span> Visualizer</div>
    <div class="section">
        <h2>👁️ AI SVG Visualizer</h2>
        <p class="subtitle">Generate SVG diagrams for any concept</p>
        <div class="book-section" style="padding:1.5rem;margin-top:1rem;">
            <label style="font-weight:500;display:block;margin-bottom:0.5rem;">Concept</label>
            <input type="text" id="vis-concept" value="Photosynthesis" style="width:100%;padding:0.7rem;border:1px solid var(--border);border-radius:8px;margin-bottom:1rem;">
            <button onclick="doVisualize()" class="btn-primary" style="padding:0.8rem 2rem;background:var(--primary);color:#fff;border:none;border-radius:8px;font-size:1rem;font-weight:600;cursor:pointer;">Generate SVG</button>
            <div id="vis-output" style="margin-top:1rem;"></div>
        </div>
    </div>
    <script>
    async function doVisualize() {
        const c = document.getElementById('vis-concept').value;
        const out = document.getElementById('vis-output');
        out.innerHTML = '<em>Generating SVG...</em>';
        try {
            const resp = await fetch('/api/ai/visualize?concept='+encodeURIComponent(c));
            const data = await resp.json();
            out.innerHTML = data.svg ? '<div style="background:#fff;border-radius:8px;padding:1rem;">' + data.svg + '</div>' : '<em>No SVG generated</em>';
        } catch(e) {
            out.innerHTML = '<em>Error: ' + e.message + '</em>';
        }
    }
    </script>"""))


@app.get("/ai/pedagogical", response_class=HTMLResponse)
async def ai_pedagogical_page():
    return HTMLResponse(_render(title="NotebookLM Pedagogical Guide — CBSE Class X", content="""
    <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> <a href="/ai">AI Studio</a> <span class="sep">›</span> Pedagogical Guide</div>
    <div class="section">
        <h2>📖 AI Pedagogical Guide</h2>
        <p class="subtitle">Detailed study guides with learning objectives, prerequisites, and practice questions</p>
        <div class="book-section" style="padding:1.5rem;margin-top:1rem;">
            <label style="font-weight:500;display:block;margin-bottom:0.5rem;">Subject</label>
            <input type="text" id="ped-subject" value="Science" style="width:100%;padding:0.7rem;border:1px solid var(--border);border-radius:8px;margin-bottom:1rem;">
            <label style="font-weight:500;display:block;margin-bottom:0.5rem;">Topic</label>
            <input type="text" id="ped-topic" value="Photosynthesis" style="width:100%;padding:0.7rem;border:1px solid var(--border);border-radius:8px;margin-bottom:1rem;">
            <button onclick="doPedagogical()" class="btn-primary" style="padding:0.8rem 2rem;background:var(--primary);color:#fff;border:none;border-radius:8px;font-size:1rem;font-weight:600;cursor:pointer;">Generate Guide</button>
            <div id="ped-output" style="margin-top:1rem;padding:1rem;border:1px solid var(--border);border-radius:8px;min-height:80px;"></div>
        </div>
    </div>
    <script>
    async function doPedagogical() {
        const s = document.getElementById('ped-subject').value;
        const t = document.getElementById('ped-topic').value;
        const out = document.getElementById('ped-output');
        out.innerHTML = '<em>Generating pedagogical guide...</em>';
        try {
            const resp = await fetch('/api/ai/notebooklm?subject='+encodeURIComponent(s)+'&chapter=General&topic='+encodeURIComponent(t));
            const data = await resp.json();
            out.innerHTML = '<div style="line-height:1.7;white-space:pre-wrap;font-family:monospace;font-size:0.85rem;">' + (data.markdown || '<em>No guide generated</em>') + '</div>';
        } catch(e) {
            out.innerHTML = '<em>Error: ' + e.message + '</em>';
        }
    }
    </script>"""))


@app.get("/sw.js", response_class=Response)
async def service_worker():
    sw_js = """self.addEventListener('install', function(e) { self.skipWaiting(); });
self.addEventListener('activate', function(e) { e.waitUntil(clients.claim()); });
self.addEventListener('fetch', function(e) {
    if (e.request.method === 'GET') {
        e.respondWith(
            caches.open('cbse-v1').then(function(cache) {
                return cache.match(e.request).then(function(response) {
                    return response || fetch(e.request).then(function(resp) {
                        if (resp.status === 200) cache.put(e.request, resp.clone());
                        return resp;
                    });
                });
            }).catch(function() { return fetch(e.request); })
        );
    }
});"""
    return Response(content=sw_js, media_type="application/javascript")


# ═══════════════════════════════════════════════════════════════════════════
# CONTENT ROUTES (notes, revision, quiz, mindmap, interactives)
# ═══════════════════════════════════════════════════════════════════════════


@app.get("/notes/{chapter_id}", response_class=HTMLResponse)
async def notes_page(chapter_id: str):
    conn = DB
    chapter = conn.query_one("SELECT * FROM chapters WHERE id = ?", (chapter_id,)) if conn and conn.table_exists("chapters") else None
    if not chapter:
        return HTMLResponse(_render(title="Notes — Not Found", content='<div class="section"><h2>Notes Not Found</h2><p><a href="/">Go Home</a></p></div>'), status_code=404)
    topics = conn.query("SELECT * FROM topics WHERE chapter_id = ? ORDER BY num, title", (chapter_id,))
    items = "".join(f'<li><strong>{t["title"]}</strong>: {t.get("content","")[:200]}...</li>' for t in topics)
    return HTMLResponse(_render(title=f"Notes: {chapter['title']}", content=f"""
    <div class="breadcrumb">{_build_breadcrumb([("Home", "/"), (f"Ch {chapter['num']}: {chapter['title']}", f"/chapter/{chapter_id}"), ("Notes", None)])}</div>
    <div class="section"><h2>📝 Revision Notes: {chapter['title']}</h2><ul style="line-height:1.8;">{items}</ul></div>"""))


@app.get("/revision/{chapter_id}", response_class=HTMLResponse)
async def revision_page(chapter_id: str):
    conn = DB
    chapter = conn.query_one("SELECT * FROM chapters WHERE id = ?", (chapter_id,)) if conn and conn.table_exists("chapters") else None
    if not chapter:
        return HTMLResponse(_render(title="Revision — Not Found", content='<div class="section"><h2>Revision Not Found</h2><p><a href="/">Go Home</a></p></div>'), status_code=404)
    topics = conn.query("SELECT title, content FROM topics WHERE chapter_id = ? ORDER BY num, title", (chapter_id,))
    points = "".join(f'<li>✔ {t["title"]}: {t.get("content","")[:150]}</li>' for t in topics)
    return HTMLResponse(_render(title=f"Revision: {chapter['title']}", content=f"""
    <div class="breadcrumb">{_build_breadcrumb([("Home", "/"), (f"Ch {chapter['num']}: {chapter['title']}", f"/chapter/{chapter_id}"), ("Revision", None)])}</div>
    <div class="section"><h2>🔄 Quick Revision: {chapter['title']}</h2><ul style="line-height:1.8;">{points}</ul></div>"""))


@app.get("/quiz/{chapter_id}", response_class=HTMLResponse)
async def quiz_page(chapter_id: str):
    conn = DB
    chapter = conn.query_one("SELECT * FROM chapters WHERE id = ?", (chapter_id,)) if conn and conn.table_exists("chapters") else None
    if not chapter:
        return HTMLResponse(_render(title="Quiz — Not Found", content='<div class="section"><h2>Quiz Not Found</h2><p><a href="/">Go Home</a></p></div>'), status_code=404)
    problems = conn.query("SELECT * FROM problems WHERE chapter_id = ? LIMIT 20", (chapter_id,)) if conn.table_exists("problems") else []
    cards = ""
    for p in problems:
        qtext = p.get("problem_text", "")[:200]
        atext = p.get("solution_text", "")[:150]
        cards += f'<div class="book-section" style="margin-bottom:0.5rem;"><h4 style="margin:0;">Q: {qtext}</h4><p style="color:#2ecc71;font-size:0.85rem;margin:0.3rem 0 0;">Answer: {atext}</p></div>'
    if not cards:
        cards = '<p style="color:#666;">No practice problems for this chapter yet.</p>'
    return HTMLResponse(_render(title=f"Quiz: {chapter['title']}", content=f"""
    <div class="breadcrumb">{_build_breadcrumb([("Home", "/"), (f"Ch {chapter['num']}: {chapter['title']}", f"/chapter/{chapter_id}"), ("Quiz", None)])}</div>
    <div class="section"><h2>📝 Practice Quiz: {chapter['title']}</h2><p style="color:#666;margin-bottom:1rem;">Test your knowledge with these practice problems.</p>{cards}</div>"""))


@app.get("/mindmap/{topic_id}", response_class=HTMLResponse)
async def mindmap_page(topic_id: str):
    conn = DB
    topic = conn.query_one("SELECT * FROM topics WHERE id = ?", (topic_id,)) if conn and conn.table_exists("topics") else None
    if not topic:
        return HTMLResponse(_render(title="Mind Map — Not Found", content='<div class="section"><h2>Mind Map Not Found</h2><p><a href="/">Go Home</a></p></div>'), status_code=404)
    chunks = conn.query("SELECT * FROM chunks WHERE topic_id = ? ORDER BY seq", (topic_id,))
    nodes = [topic.get("title", "Topic")]
    for c in chunks:
        nodes.append(c.get("title", "") or c.get("content", "")[:40])
    mindmap_svg = _pomelli_mindmap_svg(nodes)
    return HTMLResponse(_render(title=f"Mind Map: {topic['title']}", content=f"""
    <div class="breadcrumb">{_build_breadcrumb([("Home", "/"), (topic['title'], f"/topic/{topic_id}"), ("Mind Map", None)])}</div>
    <div class="section"><h2>🧠 Mind Map: {topic['title']}</h2>{mindmap_svg}</div>"""))


@app.get("/interactives/cards/{topic_id}", response_class=HTMLResponse)
async def interactives_cards_page(topic_id: str):
    conn = DB
    topic = conn.query_one("SELECT * FROM topics WHERE id = ?", (topic_id,)) if conn and conn.table_exists("topics") else None
    if not topic:
        return HTMLResponse(_render(title="Flash Cards — Not Found", content='<div class="section"><h2>Flash Cards Not Found</h2><p><a href="/">Go Home</a></p></div>'), status_code=404)
    chunks = conn.query("SELECT * FROM chunks WHERE topic_id = ? ORDER BY seq", (topic_id,))
    cards_html = ""
    for c in chunks:
        title = c.get("title", "") or c.get("content", "")[:40]
        content = c.get("content", "")
        cards_html += f'<div class="book-section" style="cursor:pointer;margin-bottom:0.5rem;" onclick="this.querySelector(\'.card-content\').style.display=this.querySelector(\'.card-content\').style.display===\'none\'?\'block\':\'none\'"><h4 style="margin:0;">📇 {title}</h4><div class="card-content" style="display:none;margin-top:0.5rem;padding:0.8rem;background:#f8f9ff;border-radius:6px;">{content}</div></div>'
    if not cards_html:
        cards_html = '<p style="color:#666;">No flash cards for this topic yet.</p>'
    return HTMLResponse(_render(title=f"Flash Cards: {topic['title']}", content=f"""
    <div class="breadcrumb">{_build_breadcrumb([("Home", "/"), (topic['title'], f"/topic/{topic_id}"), ("Flash Cards", None)])}</div>
    <div class="section"><h2>🃏 Flash Cards: {topic['title']}</h2><p style="color:#666;margin-bottom:1rem;">Click a card to flip it.</p>{cards_html}</div>
    <script>document.querySelectorAll('.book-section h4').forEach(function(el,i){{el.textContent = '📇 Card '+(i+1)+': '+el.textContent.replace('📇 ','');}});</script>"""))


@app.get("/interactives/matching/{entity_id}", response_class=HTMLResponse)
async def interactives_matching_page(entity_id: str):
    conn = DB
    if not conn or not conn.table_exists("chapters"):
        return HTMLResponse(_render(title="Matching — Not Found", content='<div class="section"><h2>Matching Game Not Found</h2><p><a href="/">Go Home</a></p></div>'), status_code=404)
    # Accept either chapter_id or topic_id
    chapter = conn.query_one("SELECT * FROM chapters WHERE id = ?", (entity_id,))
    if not chapter:
        topic = conn.query_one("SELECT * FROM topics WHERE id = ?", (entity_id,))
        if topic:
            chapter = conn.query_one("SELECT * FROM chapters WHERE id = ?", (topic["chapter_id"],))
    if not chapter:
        return HTMLResponse(_render(title="Matching — Not Found", content='<div class="section"><h2>Matching Game Not Found</h2><p><a href="/">Go Home</a></p></div>'), status_code=404)
    chapter_id = chapter["id"]
    topics = conn.query("SELECT id, title, content FROM topics WHERE chapter_id = ? ORDER BY RANDOM() LIMIT 12", (chapter_id,))
    if len(topics) < 4:
        topics = conn.query("SELECT id, title, content FROM topics WHERE chapter_id = ? LIMIT 12", (chapter_id,))
    left = "".join(f'<div class="match-item" data-id="{t["id"]}" style="padding:0.5rem 0.8rem;background:#e8f4f8;border-radius:6px;cursor:pointer;margin:0.2rem;text-align:center;font-size:0.85rem;font-weight:500;">{t["title"]}</div>' for t in topics)
    right = "".join(f'<div class="match-item" data-id="{t["id"]}" style="padding:0.5rem 0.8rem;background:#fef9c3;border-radius:6px;cursor:pointer;margin:0.2rem;text-align:center;font-size:0.85rem;">{t.get("content","")[:80]}</div>' for t in topics)
    return HTMLResponse(_render(title=f"Matching: {chapter['title']}", content=f"""
    <div class="breadcrumb">{_build_breadcrumb([("Home", "/"), (f"Ch {chapter['num']}: {chapter['title']}", f"/chapter/{chapter_id}"), ("Matching Game", None)])}</div>
    <div class="section"><h2>🔗 Matching Game: {chapter['title']}</h2><p style="color:#666;margin-bottom:1rem;">Match topics with their descriptions.</p>
    <div style="display:flex;gap:2rem;flex-wrap:wrap;">
        <div style="flex:1;min-width:200px;"><h4 style="font-size:0.9rem;">Topics</h4><div id="match-left">{left}</div></div>
        <div style="flex:1;min-width:200px;"><h4 style="font-size:0.9rem;">Descriptions</h4><div id="match-right">{right}</div></div>
    </div>
    <p id="match-status" style="margin-top:1rem;font-weight:600;"></p></div>
    <script>
    (function(){{
        var sel = null;
        function checkMatch() {{
            var matched = 0; var total = document.querySelectorAll('#match-left .match-item').length;
            document.querySelectorAll('#match-left .match-item').forEach(function(l,i){{
                var r = document.querySelector('#match-right .match-item[data-id="'+l.dataset.id+'"]');
                if(l.style.opacity==='0.4' && r.style.opacity==='0.4') matched++;
            }});
            document.getElementById('match-status').textContent = matched + ' / ' + total + ' matched';
            if(matched===total) document.getElementById('match-status').textContent = '🎉 All matched! Perfect!';
        }}
        document.querySelectorAll('#match-left .match-item').forEach(function(el){{
            el.addEventListener('click',function(){{
                if(this.style.opacity==='0.4') return;
                if(sel){{sel.style.outline='none';}}
                sel=this; this.style.outline='3px solid #4a90d9';
            }});
        }});
        document.querySelectorAll('#match-right .match-item').forEach(function(el){{
            el.addEventListener('click',function(){{
                if(!sel || this.style.opacity==='0.4') return;
                if(sel.dataset.id===this.dataset.id){{
                    sel.style.opacity='0.4'; this.style.opacity='0.4';
                    sel.style.outline='none'; sel=null;
                    checkMatch();
                }} else {{
                    this.style.background='#fee2e2';
                    setTimeout(function(){{el.style.background='#fef9c3';}},500);
                }}
            }});
        }});
    }})();
    </script>"""))


def _pomelli_mindmap_svg(nodes):
    """Generate an SVG mind map visualization using PomelliAI-style rendering."""
    if not nodes:
        return '<p style="color:#666;">No nodes for mind map.</p>'
    center = nodes[0]
    children = nodes[1:]
    if len(children) > 10:
        children = children[:10]
    svg_w, svg_h = 700, max(300, len(children) * 50 + 100)
    cx, cy = 100, svg_h // 2
    items = ""
    colors = ["#4a90d9", "#2ecc71", "#9b59b6", "#e74c3c", "#f39c12", "#1abc9c", "#e67e22", "#3498db", "#2c3e50", "#8e44ad"]
    angle_step = min(60, 320 // max(1, len(children)))
    start_angle = 180 - (len(children) - 1) * angle_step / 2
    for i, node in enumerate(children):
        angle = (start_angle + i * angle_step) * 3.14159 / 180
        r = 220
        nx = cx + r * 0.8
        ny = 40 + i * (svg_h - 80) // max(1, len(children))
        color = colors[i % len(colors)]
        node_text = node[:50].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
        items += f'<line x1="{cx+15}" y1="{cy}" x2="{nx}" y2="{ny}" stroke="{color}" stroke-width="1.5" opacity="0.5"/><circle cx="{nx}" cy="{ny}" r="6" fill="{color}" opacity="0.8"/><text x="{nx+12}" y="{ny+4}" font-size="12" fill="#333">{node_text}</text>'
    escaped_center = center[:40].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    svg = f'<svg viewBox="0 0 {svg_w} {svg_h}" style="width:100%;max-width:{svg_w}px;height:auto;" xmlns="http://www.w3.org/2000/svg"><rect width="{svg_w}" height="{svg_h}" fill="#f8f9fa" rx="12"/><circle cx="{cx}" cy="{cy}" r="30" fill="#4a90d9" opacity="0.15"/><circle cx="{cx}" cy="{cy}" r="20" fill="#4a90d9" opacity="0.25"/><text x="{cx}" y="{cy+4}" text-anchor="middle" font-size="11" font-weight="600" fill="#1a1a2e">{escaped_center}</text>{items}</svg>'
    return svg


@app.get("/api/search")
@rate_limit(60)
async def api_search(request: Request, q: str = Query(""), board: Optional[str] = None, limit: int = Query(15, le=50)):
    if not q:
        return {"results": []}
    try:
        idx = get_index()
        results = idx.search(q, board=board, limit=limit)
    except Exception:
        results = []
    return {"results": results}


@app.get("/api/gamification")
async def api_gamification(user: dict = Depends(get_current_user)):
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


SYLLABUS_CACHE_FILE = os.path.join(os.path.dirname(__file__), "syllabus_index.json")
_syllabus_cache = None
_syllabus_cache_mtime = 0

def rebuild_syllabus_cache():
    conn = get_db()
    # 1. Compute subjects list
    subjects = conn.query("""
        SELECT s.id, s.name, s.board_id,
            (SELECT COUNT(*) FROM chapters c WHERE c.subject_id = s.id) as chapter_count,
            (SELECT COUNT(*) FROM topics t JOIN chapters c ON t.chapter_id = c.id WHERE c.subject_id = s.id) as topic_count,
            (SELECT COUNT(*) FROM chunks WHERE chapter_id IN (SELECT id FROM chapters WHERE subject_id = s.id)) as chunk_count,
            (SELECT COUNT(*) FROM problems p JOIN topics t ON p.topic_id = t.id JOIN chapters c ON t.chapter_id = c.id WHERE c.subject_id = s.id) as problem_count
        FROM subjects s ORDER BY s.board_id, s.name
    """)
    subjects_list = []
    for s in subjects:
        s_dict = dict(s)
        pct = min(100, int(s_dict["chunk_count"] / max(1, s_dict["topic_count"] * 3) * 100)) if s_dict["topic_count"] else 0
        s_dict["coverage"] = pct
        subjects_list.append(s_dict)
    
    # 2. Compute chapters per subject
    subject_chapters = {}
    for s in subjects_list:
        sub_id = s["id"]
        chapters = conn.query("""
            SELECT c.id, c.num, c.title, c.subject_id,
                (SELECT COUNT(*) FROM topics t WHERE t.chapter_id = c.id) as topic_count,
                (SELECT COUNT(*) FROM chunks WHERE chapter_id = c.id) as chunk_count,
                (SELECT COUNT(*) FROM problems p JOIN topics t ON p.topic_id = t.id WHERE t.chapter_id = c.id) as problem_count
            FROM chapters c WHERE c.subject_id = ? ORDER BY c.num
        """, (sub_id,))
        
        chapters_list = []
        for ch in chapters:
            ch_dict = dict(ch)
            pct = min(100, int(ch_dict["chunk_count"] / max(1, ch_dict["topic_count"] * 3) * 100)) if ch_dict["topic_count"] else 0
            ch_dict["coverage"] = pct
            ch_dict["subject_name"] = s["name"]
            chapters_list.append(ch_dict)
        subject_chapters[sub_id] = chapters_list

    cache_data = {
        "subjects": subjects_list,
        "subject_chapters": subject_chapters,
        "timestamp": time.time()
    }
    
    try:
        with open(SYLLABUS_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2)
    except Exception as e:
        log.warning("Failed to write syllabus cache file: %s", e)
        
    return cache_data

def get_syllabus_cache(force_rebuild=False):
    global _syllabus_cache, _syllabus_cache_mtime
    
    if not force_rebuild:
        if os.path.exists(SYLLABUS_CACHE_FILE):
            try:
                mtime = os.path.getmtime(SYLLABUS_CACHE_FILE)
                if _syllabus_cache is not None and mtime == _syllabus_cache_mtime:
                    return _syllabus_cache
                # Reload file
                with open(SYLLABUS_CACHE_FILE, "r", encoding="utf-8") as f:
                    _syllabus_cache = json.load(f)
                    _syllabus_cache_mtime = mtime
                    return _syllabus_cache
            except Exception as e:
                log.warning("Failed to read syllabus cache file: %s", e)
        else:
            _syllabus_cache = None
            _syllabus_cache_mtime = 0
            
    # Rebuild
    _syllabus_cache = rebuild_syllabus_cache()
    try:
        _syllabus_cache_mtime = os.path.getmtime(SYLLABUS_CACHE_FILE)
    except Exception:
        _syllabus_cache_mtime = 0
    return _syllabus_cache

@app.get("/api/syllabus")
@rate_limit(120)
async def api_syllabus(request: Request, subject_id: Optional[str] = Query(None)):
    cache = get_syllabus_cache()
    if subject_id:
        chapters = cache.get("subject_chapters", {}).get(subject_id)
        if chapters is None:
            cache = get_syllabus_cache(force_rebuild=True)
            chapters = cache.get("subject_chapters", {}).get(subject_id, [])
        return JSONResponse(content=chapters)
    else:
        return JSONResponse(content=cache.get("subjects", []))


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

    # Route rewriting for backward compatibility / validation
    if raw_path == "/learn-hub":
        raw_path = "/learn"
    elif raw_path == "/analytics":
        raw_path = "/parent-report"
    elif raw_path == "/game/quiz":
        raw_path = "/tutor"
    elif raw_path == "/game/flashcard":
        raw_path = "/tutor"
    elif raw_path == "/study-plan":
        raw_path = "/"
    else:
        # Rewrite /cbse/{subject}/chapter/{chapter_id} -> /chapter/{chapter_id}
        m_ch = re.match(r"^/cbse/[^/]+/chapter/([^/]+)", raw_path)
        if m_ch:
            raw_path = f"/chapter/{m_ch.group(1)}"
        else:
            # Rewrite /cbse/{subject} -> /board/cbse/{subject}
            m_sb = re.match(r"^/cbse/([^/]+)$", raw_path)
            if m_sb:
                raw_path = f"/board/cbse/{m_sb.group(1)}"

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

    loop = asyncio.get_event_loop()
    try:
        if request.method == "GET":
            await loop.run_in_executor(None, handler.do_GET)
        else:
            await loop.run_in_executor(None, handler.do_POST)
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
