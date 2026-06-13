import json
import os
import sys
import urllib.parse
import urllib.request
import re
import math
import random
import hashlib
import secrets
import html as htmlmod
import logging
import traceback
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from database import get_conn, init_db
from data import ALL_BOARDS, SUBJECTS
from json_index import get_index
from llm_client import get_client
from chunking import (
    get_chapter_tree, get_topic_with_context, search_chunks
)
from gamification import (
    get_learner, add_xp, check_streak, use_life, refill_lives,
    use_lifeline, record_quiz_result, mark_topic_progress,
    get_leaderboard_data
)
from knowledge_graph import (
    get_pillars, get_pillar_content, get_full_graph, get_subject_graph,
    get_concept, get_weaknesses, get_strengths, get_recommended_next,
    record_attempt, seed_knowledge_graph, seed_pillar_content,
    init_pillar_tables, PILLARS,
)
import ai_tutor
import interactives
import ai_services
import content_enricher

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%d/%b/%Y %H:%M:%S",
    stream=sys.stderr,
)
log = logging.getLogger("cbse")

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 9090))

# Google-only AI: Gemini / Gemma 4 / NotebookLM / YouTube

init_db()
ai_tutor.init_tutor_tables()
init_pillar_tables()
seed_knowledge_graph()
seed_pillar_content()


def render_template(template_name, **context):
    content = _templates[template_name]
    context.setdefault("subjects", SUBJECTS)
    return _render_string(content, context)


# Variables containing raw HTML that must NOT be escaped
_RAW_HTML_VARS = frozenset({"content", "extra_css"})

def _render_string(s, context):
    """Template renderer supporting Jinja2 syntax with a robust regex fallback."""
    try:
        import jinja2
        # Use Jinja2 Template rendering for full compatibility
        return jinja2.Template(s).render(**context)
    except Exception as e:
        # Fallback regex replacer if jinja2 is not available
        def replacer(m):
            expr = m.group(1).strip()
            expr_clean = expr.split('|')[0].strip()
            try:
                val = context.get(expr_clean, "")
                if val is None:
                    return ""
                if expr_clean in _RAW_HTML_VARS or "safe" in expr:
                    return str(val)
                return htmlmod.escape(str(val))
            except Exception:
                return ""
        s_clean = re.sub(r"\{%.*?%\}", "", s)
        return re.sub(r"\{\{\s*(.*?)\s*\}\}", replacer, s_clean)


def render_math(text):
    superscripts = str.maketrans({
        '⁰': '^0', '¹': '^1', '²': '^2', '³': '^3', '⁴': '^4',
        '⁵': '^5', '⁶': '^6', '⁷': '^7', '⁸': '^8', '⁹': '^9',
        '⁺': '^+', '⁻': '^-', 'ⁿ': '^n', 'ⁱ': '^i', 'ᵐ': '^m',
        'ᵏ': '^k', 'ᵗ': '^t',
    })
    text = text.translate(superscripts)
    subscripts = str.maketrans({
        '₀': '_0', '₁': '_1', '₂': '_2', '₃': '_3', '₄': '_4',
        '₅': '_5', '₆': '_6', '₇': '_7', '₈': '_8', '₉': '_9',
        '₊': '+', '₋': '-', 'ₒ': '_o', 'ₓ': '_x', 'ₘ': '_m', 'ₙ': '_n',
        'ᵢ': '_i',
    })

    text = text.translate(subscripts)
    text = re.sub(r'√\(([^)]*)\)', r'sqrt(\1)', text)
    return text

def esc_js(s):
    """Escape string for use inside single-quoted JS string in an HTML onclick attribute."""
    return s.replace("\\", "\\\\").replace("'", "\\'")

def format_content(text):
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'__(.*?)__', r'<u>\1</u>', text)
    text = re.sub(r'^(\d+\.\s)', r'<br>\1', text, flags=re.MULTILINE)
    text = re.sub(r'\n\n+', '</p><p>', text)
    text = re.sub(r'\n', '<br>', text)
    text = render_math(text)
    # Wrap tables in .table-wrap for responsive scrolling
    text = re.sub(r'<p>\s*<div class="table-wrap">', r'<div class="table-wrap">', text)
    text = re.sub(r'</div>\s*</p>', r'</div>', text)
    text = re.sub(r'(<table[^>]*>.*?</table>)', r'<div class="table-wrap">\1</div>', text, flags=re.DOTALL)
    return f'<p>{text}</p>'


def build_subject_card(subject, board_id="cbse"):
    conn = get_conn()
    row = conn.execute(
        "SELECT id, name FROM subjects WHERE id = ? AND board_id = ?",
        (subject["id"], board_id)
    ).fetchone()
    if row:
        sid = row["id"]
        sname = row["name"]
    else:
        sid = f"{board_id}_{subject['id']}" if board_id != "cbse" else subject["id"]
        sname = subject["name"]

    if "books" in subject:
        ch_count = sum(len(b.get("chapters", [])) for b in subject["books"])
    else:
        ch_count = len(subject.get("chapters", []))

    # Helper for filtering
    name_lower = sname.lower()
    id_lower = sid.lower()
    if "math" in name_lower or "math" in id_lower:
        subj_type = "mathematics"
    elif "social" in name_lower or "history" in name_lower or "geography" in name_lower or "political" in name_lower or "civics" in name_lower or "economics" in name_lower or "studies" in name_lower:
        subj_type = "social"
    elif "science" in name_lower or "physics" in name_lower or "biology" in name_lower or "chem" in name_lower:
        subj_type = "science"
    elif "english" in name_lower or "hindi" in name_lower or "sanskrit" in name_lower or "french" in name_lower:
        subj_type = "languages"
    else:
        subj_type = "electives"

    if "hindi" in name_lower or "hindi" in id_lower:
        medium = "hindi"
    elif "sanskrit" in name_lower or "sanskrit" in id_lower:
        medium = "sanskrit"
    elif "telugu" in name_lower or "telugu" in id_lower:
        medium = "telugu"
    else:
        medium = "english"

    return f"""
    <div class="subject-card" onclick="location.href='/board/{board_id}/{sid}'" data-board="{board_id}" data-subject-type="{subj_type}" data-medium="{medium}">
        <div class="subject-icon">{sname[0]}</div>
        <h3>{sname}</h3>
        <p>{subject.get("description", "")}</p>
        <span class="ch-count">{ch_count} chapters</span>
    </div>"""


CSS = r"""
:root {
    --primary: #1e1b4b;
    --primary-light: #312e81;
    --accent: #6366f1;
    --accent2: #8b5cf6;
    --accent-glow: #a78bfa;
    --highlight: #f43f5e;
    --bg: #f1f5f9;
    --card-bg: #ffffff;
    --glass-bg: rgba(255, 255, 255, 0.75);
    --text: #0f172a;
    --text-muted: #64748b;
    --border: #e2e8f0;
    --shadow: 0 1px 3px rgba(0, 0, 0, 0.05), 0 1px 2px rgba(0, 0, 0, 0.02);
    --shadow-hover: 0 12px 24px -10px rgba(99, 102, 241, 0.2);
    --radius: 12px;
    --radius-sm: 8px;
    --radius-lg: 20px;
    --transition: 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    --font: 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    --gbar-height: 56px;
    --bottom-safe: env(safe-area-inset-bottom, 0px);
}
* { margin: 0; padding: 0; box-sizing: border-box; }
html { scroll-behavior: smooth; -webkit-text-size-adjust: 100%; overflow-x: hidden; }
body { font-family: var(--font); background: var(--bg); color: var(--text); min-height: 100vh; min-height: 100dvh; line-height: 1.6; font-size: 16px; -webkit-font-smoothing: antialiased; overflow-x: hidden; width: 100%; }

/* Layout Grid & Containers */
.container { max-width: 1200px; margin: 0 auto; padding: 1rem; padding-bottom: calc(5rem + var(--bottom-safe)); }
@media (min-width: 768px) { .container { padding: 2rem 1.5rem; padding-bottom: calc(6rem + var(--bottom-safe)); } }

/* Header - Modern Card Layout */
header { background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%); color: #fff; padding: 2rem 1.5rem; text-align: center; border-radius: var(--radius); margin-bottom: 1.5rem; box-shadow: var(--shadow); position: relative; overflow: hidden; }
header::after { content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: radial-gradient(circle at top right, rgba(99,102,241,0.15), transparent 70%); pointer-events: none; }
header h1 { font-size: 1.6rem; font-weight: 800; letter-spacing: -0.5px; }
header p { font-size: 0.9rem; opacity: 0.85; margin-top: 0.4rem; }
@media (min-width: 768px) { header { padding: 3rem 2rem; } header h1 { font-size: 2.2rem; } header p { font-size: 1.05rem; } }

/* Glassmorphism Global Bar (Navbar) */
.sticky-wrapper { position: sticky; top: 0; z-index: 1000; }
.gbar { background: rgba(30, 27, 75, 0.85); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); border-bottom: 1px solid rgba(255, 255, 255, 0.08); color: #fff; height: var(--gbar-height); display: flex; align-items: center; }
.gbar-inner { max-width: 1200px; margin: 0 auto; padding: 0 1rem; display: flex; align-items: center; justify-content: space-between; width: 100%; gap: 1rem; }
.gbar-brand { font-size: 1.25rem; font-weight: 800; color: #fff; text-decoration: none; white-space: nowrap; display: flex; align-items: center; gap: 0.5rem; transition: opacity var(--transition); }
.gbar-brand:hover { opacity: 0.9; text-decoration: none; }
.gbar-nav { display: flex; gap: 0.25rem; flex-wrap: nowrap; overflow-x: auto; -webkit-overflow-scrolling: touch; scrollbar-width: none; align-items: center; }
.gbar-nav::-webkit-scrollbar { display: none; }
.gbar-nav a, .gbar-link { color: rgba(255, 255, 255, 0.75); text-decoration: none; font-size: 0.85rem; font-weight: 500; padding: 0.5rem 0.75rem; border-radius: var(--radius-sm); white-space: nowrap; transition: all var(--transition); border-bottom: 2px solid transparent; }
.gbar-nav a:hover, .gbar-link:hover { background: rgba(255, 255, 255, 0.08); color: #fff; text-decoration: none; }
.gbar-nav a.active, .gbar-nav a:active { color: #fff; background: rgba(255, 255, 255, 0.12); border-bottom-color: var(--accent); }
.gbar-right { display: flex; align-items: center; gap: 0.6rem; flex-shrink: 0; }
.xp-badge, .user-badge { background: rgba(255, 255, 255, 0.12); padding: 0.35rem 0.75rem; border-radius: 20px; font-size: 0.8rem; font-weight: 600; white-space: nowrap; border: 1px solid rgba(255,255,255,0.06); }
.xp-badge { color: #fbbf24; }

@media (max-width: 640px) {
    .gbar-brand { font-size: 1.1rem; }
    .gbar-nav a, .gbar-link { font-size: 0.8rem; padding: 0.4rem 0.5rem; }
    .xp-badge, .user-badge { font-size: 0.75rem; padding: 0.25rem 0.5rem; }
    .gbar-right { gap: 0.35rem; }
}
@media (max-width: 480px) {
    .gbar-right .user-badge { display: none; }
}

/* Sections & Base Layout */
.section { background: var(--card-bg); border-radius: var(--radius); padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: var(--shadow); border: 1px solid var(--border); transition: transform var(--transition); }
.section h2 { margin-top: 0; font-size: 1.4rem; font-weight: 700; color: var(--primary); margin-bottom: 1rem; border-bottom: 2px solid var(--accent); padding-bottom: 0.5rem; word-break: break-word; }
.section-header { display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-bottom: 1rem; flex-wrap: wrap; }
.section .subtitle { color: var(--text-muted); font-size: 0.9rem; margin-top: -0.5rem; margin-bottom: 1rem; }

a { color: var(--accent); text-decoration: none; transition: color var(--transition); word-break: break-word; overflow-wrap: break-word; }
a:hover { color: var(--primary-light); text-decoration: underline; }

/* Grid Configurations */
.subjects-grid, .cards-grid, .monitor-grid, .profile-stats { display: grid; grid-template-columns: 1fr; gap: 1rem; }
@media (min-width: 480px) {
    .subjects-grid, .cards-grid, .monitor-grid, .profile-stats { grid-template-columns: repeat(2, 1fr); }
}
@media (min-width: 768px) {
    .subjects-grid, .cards-grid { grid-template-columns: repeat(3, 1fr); gap: 1.5rem; }
    .monitor-grid { grid-template-columns: repeat(4, 1fr); }
    .profile-stats { grid-template-columns: repeat(4, 1fr); }
}

/* Cards & Interactions */
.subject-card, .info-card, .stat-card, .monitor-stat { background: var(--card-bg); border-radius: var(--radius); padding: 1.5rem; cursor: pointer; transition: all var(--transition); box-shadow: var(--shadow); border: 1px solid var(--border); position: relative; overflow: hidden; display: flex; flex-direction: column; min-height: 140px; }
.subject-card:hover, .info-card:hover, .stat-card:hover, .monitor-stat:hover { transform: translateY(-4px); box-shadow: var(--shadow-hover); border-color: var(--accent); }
.subject-card:active { transform: translateY(-1px) scale(0.99); }
.subject-icon { width: 48px; height: 48px; background: linear-gradient(135deg, var(--accent) 0%, var(--accent2) 100%); color: #fff; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 1.4rem; font-weight: 700; margin-bottom: 0.8rem; box-shadow: 0 4px 12px rgba(99,102,241,0.2); }
.subject-card h3 { font-size: 1.15rem; margin-bottom: 0.4rem; color: var(--primary); font-weight: 700; }
.subject-card p { color: var(--text-muted); font-size: 0.85rem; line-height: 1.5; flex: 1; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; }
.ch-count { display: inline-block; margin-top: auto; padding: 0.25rem 0.8rem; background: rgba(99, 102, 241, 0.08); color: var(--accent); border-radius: 20px; font-size: 0.75rem; font-weight: 600; width: fit-content; }

/* Book Sections */
.book-section { background: var(--card-bg); border-radius: var(--radius); padding: 1.5rem; margin-bottom: 1.25rem; box-shadow: var(--shadow); border: 1px solid var(--border); scroll-margin-top: calc(var(--gbar-height) + 12px); }
.book-section h3 { font-size: 1.25rem; color: var(--primary); margin-bottom: 0.8rem; word-break: break-word; font-weight: 700; }

/* Interactive Lists & Actions */
.chapter-list { list-style: none; display: flex; flex-direction: column; gap: 0.5rem; }
.chapter-list li { padding: 0.8rem 1rem; border-left: 4px solid transparent; background: var(--bg); border-radius: var(--radius-sm); cursor: pointer; transition: all var(--transition); display: flex; align-items: center; justify-content: space-between; gap: 1rem; min-height: 52px; }
.chapter-list li:hover { border-left-color: var(--accent); background: rgba(99, 102, 241, 0.04); }
.chapter-list li:active { background: rgba(99, 102, 241, 0.08); }
.chapter-list .ch-row { display: flex; align-items: center; gap: 0.75rem; flex: 1; min-width: 0; }
.chapter-list .ch-num { display: inline-flex; align-items: center; justify-content: center; min-width: 32px; height: 32px; background: var(--card-bg); color: var(--accent); font-weight: 700; border-radius: 50%; font-size: 0.85rem; flex-shrink: 0; box-shadow: var(--shadow); }
.chapter-list .ch-title { font-size: 0.95rem; font-weight: 600; color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chapter-actions { display: flex; gap: 0.5rem; margin: 1rem 0; flex-wrap: wrap; }
@media (max-width: 480px) {
    .chapter-list li { padding: 0.6rem 0.8rem; min-height: 48px; }
    .chapter-list .ch-title { font-size: 0.88rem; }
    .chapter-actions { gap: 0.4rem; }
    .chapter-actions .tts-btn, .chapter-actions .ncert-link { font-size: 0.8rem; padding: 0.5rem 0.75rem; width: 100%; text-align: center; justify-content: center; }
}

/* Topics Section */
.topics { margin-top: 0.5rem; display: flex; flex-wrap: wrap; gap: 0.4rem; }
.topic-tag { padding: 0.4rem 0.8rem; background: var(--card-bg); border-radius: 8px; font-size: 0.8rem; color: var(--text-muted); cursor: pointer; border: 1px solid var(--border); transition: all var(--transition); display: inline-flex; align-items: center; min-height: 36px; max-width: 100%; word-break: break-word; }
.topic-tag:hover { background: rgba(99, 102, 241, 0.05); border-color: var(--accent); color: var(--accent); }
.topic-tag:active { background: rgba(99, 102, 241, 0.1); }
[id^="topic-"] { scroll-margin-top: calc(var(--gbar-height) + 12px); }

/* Badges */
.board-badge { display: inline-flex; align-items: center; padding: 0.2rem 0.75rem; border-radius: 20px; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }
.board-badge.cbse { background: #dcfce7; color: #15803d; }
.board-badge.ap { background: #fff7ed; color: #c2410c; }
.board-badge.ts { background: #fee2e2; color: #b91c1c; }

/* Breadcrumb navigation */
.breadcrumb { display: flex; align-items: center; gap: 0.4rem; margin-bottom: 1.25rem; color: var(--text-muted); font-size: 0.85rem; overflow-x: auto; white-space: nowrap; -webkit-overflow-scrolling: touch; padding-bottom: 0.4rem; }
.breadcrumb::-webkit-scrollbar { display: none; }
.breadcrumb a { color: var(--accent); font-weight: 500; }
.breadcrumb a:hover { text-decoration: underline; }
.breadcrumb span.sep { color: #cbd5e1; }

/* Filter System */
.filter-panel { display: flex; flex-wrap: wrap; gap: 1rem; align-items: flex-end; background: var(--card-bg); border: 1px solid var(--border); border-radius: var(--radius); padding: 1.25rem; margin-bottom: 1.5rem; box-shadow: var(--shadow); }
.filter-panel label { display: block; font-size: 0.8rem; font-weight: 600; color: var(--text-muted); margin-bottom: 0.4rem; text-transform: uppercase; letter-spacing: 0.3px; }
.filter-panel select { padding: 0.6rem 0.8rem; border: 1px solid var(--border); border-radius: 8px; background: var(--bg); font-size: 0.9rem; min-width: 160px; outline: none; transition: border-color var(--transition); font-family: inherit; }
.filter-panel select:focus { border-color: var(--accent); }
@media (max-width: 768px) {
    .filter-panel { flex-direction: column; align-items: stretch; gap: 0.8rem; }
    .filter-panel select { width: 100%; min-width: 100%; }
    .filter-panel button { width: 100%; margin-top: 0.5rem; }
}

/* Forms & Inputs */
.form-group { margin-bottom: 1.25rem; }
.form-group label { display: block; font-size: 0.85rem; font-weight: 600; color: var(--text-muted); margin-bottom: 0.4rem; }
.form-input { width: 100%; padding: 0.75rem 1rem; border: 2px solid var(--border); border-radius: 8px; font-size: 0.95rem; background: var(--bg); font-family: inherit; transition: all var(--transition); }
.form-input:focus { outline: none; border-color: var(--accent); background: #fff; box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15); }
.search-form { display: flex; gap: 0.5rem; flex-wrap: wrap; margin: 1.25rem 0; width: 100%; }
.search-form input[type="text"] { flex: 1; min-width: 200px; }
.search-form select { padding: 0.6rem 0.8rem; border: 2px solid var(--border); border-radius: 8px; background: var(--bg); font-size: 0.9rem; min-width: 150px; outline: none; font-family: inherit; }
@media (max-width: 480px) {
    .search-form { flex-direction: column; align-items: stretch; }
    .search-form select, .search-form button, .search-form input[type="text"] { width: 100%; min-height: 44px; }
}

/* Button UI */
.btn { display: inline-flex; align-items: center; justify-content: center; padding: 0.75rem 1.5rem; border: none; border-radius: 8px; font-size: 0.9rem; font-weight: 600; cursor: pointer; transition: all var(--transition); text-align: center; font-family: inherit; min-height: 44px; }
.btn-primary { background: var(--accent); color: #fff; box-shadow: 0 4px 10px rgba(99, 102, 241, 0.15); }
.btn-primary:hover { opacity: 0.95; transform: translateY(-1px); box-shadow: 0 6px 14px rgba(99, 102, 241, 0.25); }
.btn-primary:active { transform: translateY(0); }

.tts-btn { display: inline-flex; align-items: center; justify-content: center; gap: 0.4rem; padding: 0.6rem 1.2rem; background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px; cursor: pointer; font-size: 0.85rem; font-weight: 600; color: var(--text); transition: all var(--transition); text-decoration: none; min-height: 40px; }
.tts-btn:hover { background: var(--accent); color: #fff; border-color: var(--accent); text-decoration: none; }
.tts-btn:active { transform: scale(0.98); }

.ncert-link { display: inline-flex; align-items: center; justify-content: center; gap: 0.4rem; padding: 0.6rem 1.2rem; background: linear-gradient(135deg, var(--accent) 0%, var(--accent2) 100%); color: #fff; border-radius: 8px; text-decoration: none; font-size: 0.85rem; font-weight: 600; transition: all var(--transition); border: none; cursor: pointer; min-height: 40px; box-shadow: 0 4px 12px rgba(99,102,241,0.15); }
.ncert-link:hover { opacity: 0.95; transform: translateY(-1px); text-decoration: none; box-shadow: 0 6px 16px rgba(99,102,241,0.25); }
.ncert-link:active { transform: translateY(0) scale(0.98); }

/* Chunk (Content Block) Layout */
.chunk-view { background: var(--card-bg); border-radius: var(--radius); padding: 1.25rem; margin-bottom: 1rem; box-shadow: var(--shadow); border: 1px solid var(--border); }
.chunk-view .chunk-title { font-weight: 700; color: var(--primary); margin-bottom: 0.5rem; font-size: 1.05rem; }
.chunk-view .chunk-content { color: #334155; line-height: 1.8; font-size: 0.95rem; overflow-wrap: break-word; word-wrap: break-word; word-break: break-word; }
.chunk-view .chunk-content p { margin-bottom: 0.75rem; }
.chunk-view .chunk-content strong { color: var(--primary); }
.chunk-view .chunk-type-badge { display: inline-block; padding: 0.2rem 0.6rem; border-radius: 6px; font-size: 0.7rem; font-weight: 700; margin-bottom: 0.6rem; text-transform: uppercase; letter-spacing: 0.5px; }
.chunk-view .chunk-type-badge.text { background: #dcfce7; color: #166534; }
.chunk-view .chunk-type-badge.example { background: #fff7ed; color: #c2410c; }
.chunk-view .chunk-type-badge.exercise { background: #fee2e2; color: #991b1b; }
.chunk-view .chunk-type-badge.theorem { background: #f3e8ff; color: #6b21a8; }
.chunk-view .chunk-type-badge.formula { background: #dbeafe; color: #1e40af; }
.chunk-view .chunk-type-badge.definition { background: #e0f2fe; color: #0369a1; }
.chunk-view .chunk-type-badge.key_point { background: #fef3c7; color: #92400e; }
.chunk-view .chunk-type-badge.summary { background: #e2e8f0; color: #334155; }
@media (min-width: 768px) { .chunk-view { padding: 1.75rem; } }

/* Topic Navigation Tags */
.topic-nav { display: flex; gap: 0.4rem; flex-wrap: wrap; margin-bottom: 1.25rem; }
.topic-nav a { padding: 0.4rem 1rem; background: var(--card-bg); border-radius: 20px; text-decoration: none; color: var(--text-muted); font-size: 0.8rem; font-weight: 500; box-shadow: var(--shadow); border: 1px solid var(--border); transition: all var(--transition); }
.topic-nav a:hover, .topic-nav a.active { background: var(--accent); color: #fff; border-color: var(--accent); }

/* Search Results UI */
.search-result-item { background: var(--card-bg); border-radius: var(--radius); padding: 1rem 1.25rem; margin-bottom: 0.75rem; box-shadow: var(--shadow); border-left: 4px solid var(--accent); transition: transform var(--transition); }
.search-result-item:hover { transform: translateX(4px); }
.search-result-item .result-title { font-weight: 700; color: var(--primary); margin-bottom: 0.3rem; font-size: 1rem; }
.search-result-item .result-excerpt { font-size: 0.88rem; color: var(--text-muted); line-height: 1.6; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; }

/* AI Tutor Elements */
.tutor-question-card { background: linear-gradient(135deg, #f0f4ff 0%, #e0e7ff 100%); border-radius: var(--radius); padding: 1.5rem; margin-bottom: 1.25rem; border: 1px solid #c7d2fe; box-shadow: var(--shadow); }
.tutor-prompt { font-size: 0.85rem; color: var(--accent); font-weight: 700; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.5px; }
.tutor-question-text { font-size: 1.15rem; font-weight: 700; color: var(--primary); line-height: 1.6; margin-bottom: 1.25rem; }
.tutor-input { width: 100%; padding: 1rem; border: 2px solid var(--border); border-radius: 8px; font-size: 0.95rem; font-family: inherit; resize: vertical; transition: all var(--transition); box-sizing: border-box; min-height: 100px; }
.tutor-input:focus { border-color: var(--accent); outline: none; box-shadow: 0 0 0 3px rgba(99,102,241,0.15); }
.tutor-feedback-card { background: var(--card-bg); border-radius: var(--radius); padding: 1.5rem; border: 1px solid var(--border); margin-top: 1.25rem; box-shadow: var(--shadow); }
.tutor-model-answer { background: #f0fdf4; padding: 1rem; border-radius: var(--radius-sm); border-left: 4px solid var(--success); margin-bottom: 1rem; font-size: 0.9rem; }
.tutor-remedial { background: #fff7ed; padding: 1rem; border-radius: var(--radius-sm); border-left: 4px solid #f97316; margin-top: 1rem; }
.tutor-remedial-content { font-size: 0.9rem; line-height: 1.6; color: #431407; }

/* Responsive Table UI */
.table-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; margin: 1rem 0; border-radius: var(--radius-sm); border: 1px solid var(--border); background: var(--card-bg); }
.data-table, .report-table, table { width: 100%; border-collapse: collapse; font-size: 0.9rem; min-width: 600px; }
th { text-align: left; padding: 0.75rem 1rem; background: rgba(99,102,241,0.04); border-bottom: 2px solid var(--border); font-weight: 700; color: var(--primary); font-size: 0.85rem; }
td { padding: 0.75rem 1rem; border-bottom: 1px solid var(--border); vertical-align: middle; }
tr:last-child td { border-bottom: none; }
tr:hover td { background: rgba(99, 102, 241, 0.02); }
@media (max-width: 480px) {
    th, td { padding: 0.6rem 0.75rem; font-size: 0.82rem; }
}

/* Statistics display */
.stat-value { font-size: 1.8rem; font-weight: 800; color: var(--accent); line-height: 1; }
.stat-label { font-size: 0.8rem; color: var(--text-muted); margin-top: 0.3rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.3px; }

/* AI Floating Chat Panel */
.ai-chat-panel { position: fixed; bottom: 0; left: 0; right: 0; max-height: 60vh; background: var(--card-bg); border-radius: 20px 20px 0 0; box-shadow: 0 -8px 32px rgba(0, 0, 0, 0.15); display: flex; flex-direction: column; z-index: 999; transition: transform 0.35s cubic-bezier(0.4, 0, 0.2, 1); border: 1px solid var(--border); }
.ai-chat-panel.collapsed { transform: translateY(calc(100% - 48px)); }
.ai-chat-header { padding: 0.75rem 1.25rem; background: linear-gradient(135deg, var(--accent) 0%, var(--accent2) 100%); color: #fff; border-radius: 18px 18px 0 0; cursor: pointer; display: flex; justify-content: space-between; align-items: center; font-size: 0.95rem; font-weight: 700; min-height: 48px; }
.ai-chat-messages { flex: 1; overflow-y: auto; padding: 1rem; display: flex; flex-direction: column; gap: 0.75rem; }
.ai-chat-msg { padding: 0.75rem 1rem; border-radius: 16px; font-size: 0.9rem; line-height: 1.5; max-width: 85%; word-wrap: break-word; overflow-wrap: break-word; }
.ai-chat-msg.user { background: var(--accent); color: #fff; margin-left: auto; border-bottom-right-radius: 4px; }
.ai-chat-msg.assistant { background: var(--bg); color: var(--text); margin-right: auto; border-bottom-left-radius: 4px; border: 1px solid var(--border); }
.ai-chat-input { display: flex; padding: 0.75rem 1rem; border-top: 1px solid var(--border); gap: 0.5rem; background: var(--card-bg); align-items: center; }
.ai-chat-input input { flex: 1; padding: 0.6rem 1.2rem; border: 1px solid var(--border); border-radius: 24px; font-size: 0.9rem; outline: none; min-height: 40px; font-family: inherit; transition: border-color var(--transition); }
.ai-chat-input input:focus { border-color: var(--accent); }
.ai-chat-input button { padding: 0.6rem 1.25rem; background: var(--accent); color: #fff; border: none; border-radius: 24px; cursor: pointer; font-size: 0.9rem; font-weight: 600; min-height: 40px; white-space: nowrap; transition: background var(--transition); }
.ai-chat-input button:hover { background: var(--primary-light); }

@media (min-width: 768px) {
    .ai-chat-panel { left: auto; right: 2rem; width: 380px; max-height: 520px; border-radius: var(--radius); bottom: 1rem; }
    .ai-chat-panel.collapsed { transform: translateY(calc(100% - 48px)); }
    .ai-chat-header { border-radius: 11px 11px 0 0; }
}

/* Quiz UI */
.quiz-container { max-width: 750px; margin: 0 auto; width: 100%; }
.quiz-question { background: var(--card-bg); border-radius: var(--radius); padding: 1.5rem; box-shadow: var(--shadow); border: 1px solid var(--border); margin-bottom: 1.25rem; }
.quiz-options { display: flex; flex-direction: column; gap: 0.6rem; margin: 1rem 0; }
.quiz-option { padding: 1rem 1.25rem; border: 2px solid var(--border); border-radius: 10px; cursor: pointer; font-size: 0.95rem; font-weight: 500; min-height: 48px; display: flex; align-items: center; transition: all var(--transition); background: var(--card-bg); }
.quiz-option:hover { border-color: var(--accent); background: rgba(99,102,241,0.02); }
.quiz-option:active { transform: scale(0.99); }
.quiz-option.correct { border-color: var(--success); background: #f0fdf4; color: #166534; font-weight: 600; }
.quiz-option.wrong { border-color: var(--error); background: #fef2f2; color: #991b1b; font-weight: 600; }

/* Interactive Gamification Components */
.ix-match-grid { display: grid; grid-template-columns: 1fr; gap: 1rem; margin: 1.25rem 0; }
@media (min-width: 580px) {
    .ix-match-grid { grid-template-columns: 1fr 1fr; gap: 1rem; }
}
.ix-match-col { display: flex; flex-direction: column; gap: 0.6rem; }
.ix-term { padding: 0.8rem 1rem; background: linear-gradient(135deg, #eef2ff 0%, #e0e7ff 100%); border: 2px solid #c7d2fe; border-radius: 10px; cursor: grab; font-weight: 700; font-size: 0.9rem; text-align: center; user-select: none; transition: all var(--transition); box-shadow: var(--shadow); }
.ix-term:active { cursor: grabbing; transform: scale(0.98); opacity: 0.8; }
.ix-def { padding: 0.8rem 1rem; background: var(--card-bg); border: 2px dashed var(--border); border-radius: 10px; font-size: 0.88rem; line-height: 1.5; min-height: 54px; display: flex; align-items: center; justify-content: center; text-align: center; transition: background var(--transition); }

.ix-seq-list { display: flex; flex-direction: column; gap: 0.5rem; margin: 1.25rem 0; }
.ix-seq-item { padding: 0.8rem 1.25rem; background: var(--card-bg); border: 2px solid var(--border); border-radius: 10px; cursor: grab; display: flex; align-items: center; gap: 0.8rem; font-size: 0.9rem; font-weight: 600; user-select: none; transition: all var(--transition); }
.ix-seq-item:active { cursor: grabbing; opacity: 0.8; transform: scale(0.99); }
.ix-seq-num { display: inline-flex; align-items: center; justify-content: center; width: 28px; height: 28px; background: var(--accent); color: #fff; border-radius: 50%; font-size: 0.8rem; font-weight: 700; flex-shrink: 0; }

.ix-flip-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 1rem; margin: 1.25rem 0; }
.ix-flip-card { perspective: 800px; height: 140px; cursor: pointer; }
.ix-flip-inner { position: relative; width: 100%; height: 100%; transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1); transform-style: preserve-3d; }
.ix-flipped .ix-flip-inner { transform: rotateY(180deg); }
.ix-flip-front, .ix-flip-back { position: absolute; width: 100%; height: 100%; backface-visibility: hidden; -webkit-backface-visibility: hidden; border-radius: var(--radius); display: flex; align-items: center; justify-content: center; padding: 1rem; box-sizing: border-box; font-size: 0.9rem; text-align: center; line-height: 1.5; box-shadow: var(--shadow); }
.ix-flip-front { background: linear-gradient(135deg, var(--accent) 0%, var(--accent2) 100%); color: #fff; font-weight: 700; }
.ix-flip-back { background: #f0fdf4; border: 2px solid #bbf7d0; color: #166534; transform: rotateY(180deg); font-weight: 500; }

.xp-bar { height: 10px; background: var(--border); border-radius: 5px; overflow: hidden; margin-top: 0.4rem; }
.xp-bar-fill { height: 100%; background: linear-gradient(90deg, var(--accent), var(--accent2)); border-radius: 5px; transition: width 0.4s ease; }

/* Responsive Media & Embeds */
img, video, iframe, svg { max-width: 100%; height: auto; border-radius: var(--radius-sm); }
.katex, .katex-display { overflow-x: auto; overflow-y: hidden; max-width: 100%; padding: 0.2rem 0; }
.math-error { color: var(--error); font-size: 0.85rem; word-break: break-all; }

/* TTS Audio Player bar */
.tts-player { position: fixed; bottom: 0; left: 0; right: 0; background: var(--card-bg); border-top: 2px solid var(--accent); padding: 0.6rem 1.2rem; z-index: 998; box-shadow: 0 -4px 16px rgba(0,0,0,0.08); display: none; min-height: 48px; }
.tts-inner { max-width: 1200px; margin: 0 auto; display: flex; align-items: center; justify-content: space-between; gap: 1rem; width: 100%; }
.tts-player:not([style*="display:none"]):not([style*="display: none"]) ~ .ai-chat-panel,
.tts-player[style*="display: flex"] ~ .ai-chat-panel { bottom: 48px; }
@media (max-width: 768px) {
    .tts-player { padding: 0.5rem 1rem; }
    .tts-inner { font-size: 0.85rem; }
}

/* Result Card */
.result-card { max-width: 440px; margin: 2rem auto; background: var(--card-bg); border-radius: var(--radius); box-shadow: 0 10px 30px rgba(0,0,0,0.08); overflow: hidden; border: 1px solid var(--border); }
.result-card-header { background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%); color: #fff; padding: 2rem 1.5rem; text-align: center; }
.result-card-header h2 { color: #fbbf24; margin: 0; font-size: 1.5rem; font-weight: 800; }
.result-card-body { padding: 2rem 1.5rem; text-align: center; }
.result-card-score { font-size: 3rem; font-weight: 800; color: var(--primary); }
.result-card-xp { display: inline-block; background: #fef3c7; color: #92400e; padding: 0.4rem 1rem; border-radius: 20px; font-weight: 700; margin-top: 1rem; font-size: 0.9rem; }

/* Progress bar inside quizzes */
.quiz-progress-bar { height: 6px; background: var(--border); border-radius: 3px; overflow: hidden; margin-bottom: 0.6rem; }
.quiz-progress-fill { height: 100%; background: linear-gradient(90deg, var(--accent), var(--accent2)); border-radius: 3px; transition: width 0.3s ease; }
.quiz-header-meta { display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem; gap: 0.5rem; flex-wrap: wrap; color: var(--text-muted); font-weight: 600; }

/* Explanations and Feedbacks */
.q-feedback-correct { color: #15803d; font-weight: 700; padding: 0.6rem; background: #hnf0fdf4; background-color: #f0fdf4; border-radius: 8px; text-align: center; font-size: 0.9rem; border: 1px solid #bbf7d0; }
.q-feedback-wrong { color: #b91c1c; font-weight: 700; padding: 0.6rem; background: #fef2f2; border-radius: 8px; text-align: center; font-size: 0.9rem; border: 1px solid #fecaca; }
.q-explanation { margin-top: 0.75rem; padding: 0.8rem 1rem; background: var(--bg); border-left: 4px solid var(--accent); border-radius: var(--radius-sm); font-size: 0.88rem; line-height: 1.6; color: var(--text); }

/* Footer */
footer { text-align: center; padding: 2rem 1.5rem; color: var(--text-muted); font-size: 0.85rem; border-top: 1px solid var(--border); margin-top: 3rem; background: var(--card-bg); }

/* Load animations */
.loading { text-align: center; padding: 3rem; color: var(--text-muted); }
.loading .spinner { width: 36px; height: 36px; border: 4px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto 1rem; }
@keyframes spin { to { transform: rotate(360deg); } }

/* AI Content formatting boxes */
.ai-section { margin: 2rem 0; padding: 1.5rem; background: var(--card-bg); border-radius: var(--radius); border-left: 4px solid var(--accent); box-shadow: var(--shadow); }
.ai-section h3 { margin: 0 0 1rem; font-size: 1.2rem; color: var(--primary); font-weight: 700; }
.ai-content { line-height: 1.8; font-size: 0.95rem; }
.ai-content p { margin: 0.8rem 0; }
.ai-content ul, .ai-content ol { padding-left: 1.5rem; margin: 0.6rem 0; }
.ai-content li { margin: 0.4rem 0; }

.problem-box { margin: 1rem 0; padding: 1.25rem; border: 1px solid var(--border); border-radius: 12px; background: #fafbff; }
.problem-header { font-weight: 700; font-size: 0.95rem; color: var(--accent); margin-bottom: 0.6rem; padding-bottom: 0.4rem; border-bottom: 1px solid var(--border); text-transform: uppercase; letter-spacing: 0.3px; }
.problem-text { line-height: 1.7; margin: 0.6rem 0; }
.formula-used { margin: 0.75rem 0; padding: 0.6rem 1rem; background: #f0f4ff; border-radius: 8px; font-size: 0.9rem; border-left: 4px solid var(--accent); color: var(--primary); font-weight: 600; }
.solution-steps { margin: 0.75rem 0; padding: 0.75rem 1.25rem; background: #f8fafc; border-radius: 10px; border: 1px solid var(--border); }
.solution-steps ol { padding-left: 1.25rem; }
.solution-steps li { margin: 0.5rem 0; line-height: 1.7; }
.final-answer { margin: 0.75rem 0; padding: 0.6rem 1rem; background: #e8faf0; border-radius: 8px; font-weight: 700; color: #15803d; border: 1px solid #bbf7d0; display: inline-block; }

.formula-card { margin: 0.75rem 0; padding: 1.25rem; background: #f0f4ff; border-radius: var(--radius); border: 1px solid #d0d8ff; box-shadow: var(--shadow); }

/* Print view optimization */
@media print {
    body { background: #fff !important; color: #000 !important; }
    header, nav, footer, .breadcrumb, .ai-chat-panel, .gbar, #tts-player, .search-bar, .tts-btn, .ncert-link, .notebooklm-btn, .filter-panel { display: none !important; }
    .container { max-width: 100%; margin: 0; padding: 0.5in; }
    .result-card { box-shadow: none; border: 2px solid #ccc; page-break-inside: avoid; }
    .chunk-view, .section, .book-section { break-inside: avoid; box-shadow: none; border: 1px solid #ccc; }
    @page { margin: 0.5in; }
}
"""



class CBSEHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.do_GET()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = urllib.parse.parse_qs(parsed.query)
        try:
            self._dispatch_get(path, query)
        except Exception as e:
            log.error("Unhandled error processing %s: %s", path, traceback.format_exc())
            try:
                self.send_response(500)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write((
                    "<!DOCTYPE html><html><head><title>Error</title>"
                    "<style>body{font-family:sans-serif;padding:2rem;background:#1a1a2e;color:#eee;}"
                    ".card{max-width:600px;margin:auto;background:#16213e;padding:2rem;border-radius:8px;}"
                    "h1{color:#e74c3c;}pre{background:#0f3460;padding:1rem;border-radius:4px;overflow:auto;}"
                    "a{color:#4da6ff;}</style></head><body>"
                    "<div class='card'><h1>500 Internal Server Error</h1>"
                    f"<p>The server encountered an error processing your request.</p>"
                    f"<pre>{htmlmod.escape(str(e))}</pre>"
                    f"<a href='/'>Go Home</a></div></body></html>"
                ).encode())
            except Exception:
                pass

    def _dispatch_get(self, path, query):
        if path == "/":
            self._serve_home()
        elif path.startswith("/board/"):
            parts = path.split("/")
            if len(parts) >= 4:
                board_id = parts[2]
                if parts[3] == "subject" and len(parts) >= 5:
                    subj_id = parts[4]
                else:
                    subj_id = parts[3]
                self._serve_subject(board_id, subj_id)
            else:
                board_id = parts[2]
                self._serve_board(board_id)
        elif path.startswith("/subject/"):
            subject_id = path[9:]
            self._serve_subject("cbse", subject_id)
        elif path.startswith("/chapter/"):
            chapter_id = path[9:]
            self._serve_chapter(chapter_id)
        elif path.startswith("/notes/"):
            chapter_id = path[7:]
            self._serve_chapter_notes(chapter_id)
        elif path.startswith("/revision/"):
            chapter_id = path[10:]
            self._serve_chapter_revision(chapter_id)
        elif path.startswith("/topic/"):
            topic_id = path[7:]
            self._serve_topic(topic_id)
        elif path == "/search":
            self._serve_search(query)
        elif path == "/about":
            self._serve_about()
        elif path == "/health":
            self._send_json({"status": "ok", "boards": len(ALL_BOARDS)})
        elif path == "/api/test_subjects":
            conn = get_conn()
            subjects = conn.execute("SELECT * FROM subjects").fetchall()
            self._send_json({"subjects": [dict(s) for s in subjects]})
        elif path == "/api/test_query":
            conn = get_conn()
            subject = conn.execute(
                "SELECT * FROM subjects WHERE board_id = ? AND (LOWER(name) = ? OR LOWER(name) LIKE ?)",
                ("cbse", "subject", "%subject%")
            ).fetchone()
            self._send_json({"subject": dict(subject) if subject else None})
        elif path == "/api/search":
            self._api_search(query)
        elif path == "/api/explain":
            self._api_explain(query)
        elif path.startswith("/quiz/"):
            chapter_id = path[6:]
            self._serve_quiz(chapter_id)
        elif path == "/api/quiz":
            self._api_quiz(query)
        elif path == "/api/gamification":
            self._api_gamification()
        elif path == "/api/study":
            self._api_study(query)
        elif path == "/api/lifeline":
            self._api_lifeline(query)
        elif path == "/api/quiz-result":
            self._api_quiz_result(query)
        elif path == "/api/notebooklm":
            self._api_notebooklm_export(query)
        elif path == "/profile":
            self._serve_profile()
        elif path.startswith("/api/chapter/"):
            chapter_id = path[13:]
            self._api_chapter(chapter_id)
        elif path == "/exams":
            self._serve_exam_hub()
        elif path == "/api/question-bank":
            self._api_question_bank(query)
        elif path == "/api/model-paper":
            self._api_model_paper(query)
        elif path == "/api/mock-exam/start":
            self._api_mock_exam_start(query)
        elif path == "/api/mock-exam/submit":
            self._api_mock_exam_submit(query)
        elif path == "/api/mock-exam/history":
            self._api_mock_exam_history()
        elif path == "/api/cbq":
            self._api_cbq(query)
        elif path == "/api/cbq/score":
            self._api_cbq_score(query)
        elif path == "/api/daily-challenge":
            self._api_daily_challenge()
        elif path == "/api/daily-challenge/complete":
            self._api_daily_challenge_complete(query)
        elif path == "/api/daily-challenge/history":
            self._api_daily_challenge_history()
        elif path == "/api/badges":
            self._api_badges()
        elif path.startswith("/api/concept-map/"):
            topic_id = path[17:]
            self._api_concept_map(topic_id)
        elif path == "/api/monitor/generate":
            self._api_monitor_generate()
        elif path.startswith("/monitor/"):
            pin = path[9:]
            self._serve_monitor(pin)
        elif path == "/api/voiceover/languages":
            self._send_json({"languages": [
                {"code": "en-IN", "name": "English (India)", "native": "English"},
                {"code": "hi-IN", "name": "Hindi", "native": "हिन्दी"},
                {"code": "te-IN", "name": "Telugu", "native": "తెలుగు"},
                {"code": "ta-IN", "name": "Tamil", "native": "தமிழ்"},
                {"code": "kn-IN", "name": "Kannada", "native": "ಕನ್ನಡ"},
                {"code": "mr-IN", "name": "Marathi", "native": "मराठी"},
                {"code": "bn-IN", "name": "Bengali", "native": "বাংলা"},
                {"code": "gu-IN", "name": "Gujarati", "native": "ગુજરાતી"},
            ]})
        elif path == "/challenge":
            self._serve_daily_challenge_page()
        elif path == "/badges":
            self._serve_badges_page()
        elif path == "/mindmap":
            self._serve_mindmap_index()
        elif path.startswith("/mindmap/"):
            topic_id = path[9:]
            self._serve_mindmap(topic_id)
        elif path == "/review":
            self._serve_review_page()
        elif path == "/api/review/due":
            self._api_review_due()
        elif path == "/api/review/submit":
            self._api_review_submit(query)
        elif path == "/api/review/stats":
            self._api_review_stats()
        elif path == "/api/streak/calendar":
            self._api_streak_calendar()
        elif path == "/cbq":
            self._serve_cbq_hub()
        elif path.startswith("/cbq/"):
            scenario_id = path[5:]
            self._serve_cbq_detail(scenario_id)
        elif path == "/tutor":
            self._serve_tutor_hub()
        elif path.startswith("/tutor/"):
            topic_id = path[7:]
            self._serve_tutor_page(topic_id)
        elif path.startswith("/interactives/"):
            topic_id = path[14:]
            for prefix in ("matching/", "cards/", "sequence/"):
                if topic_id.startswith(prefix):
                    topic_id = topic_id[len(prefix):]
                    break
            self._serve_interactives(topic_id)
        elif path == "/api/tutor/start":
            self._api_tutor_start(query)
        elif path == "/api/tutor/answer":
            self._api_tutor_answer(query)
        elif path == "/api/tutor/remedial":
            self._api_tutor_remedial(query)
        elif path == "/api/tutor/complete":
            self._api_tutor_complete(query)
        elif path == "/api/tutor/suggest":
            self._api_tutor_suggest()
        elif path == "/api/tutor/parent-report":
            self._api_tutor_parent_report()
        elif path == "/parent-report":
            self._serve_parent_report()
        elif path == "/competitive":
            self._serve_competitive_hub()
        elif path.startswith("/competitive/"):
            track = path[13:]
            self._serve_competitive_track(track)
        elif path == "/learn":
            self._serve_learn_hub()
        elif path == "/knowledge-graph":
            self._serve_knowledge_graph()
        elif path.startswith("/knowledge-graph/subject/"):
            subject_id = path[25:]
            self._serve_knowledge_graph(subject_id)
        elif path == "/knowledge-graph/concept/":
            self._serve_concept_detail("")
        elif path.startswith("/knowledge-graph/concept/"):
            concept_id = path[25:]
            self._serve_concept_detail(concept_id)
        elif path == "/api/health":
            self._send_json({"status": "ok", "boards": len(ALL_BOARDS)})
        elif path == "/api/boards":
            self._send_json([{"id": bid, "name": info["name"], "description": info.get("description", "")} for bid, info in ALL_BOARDS.items()])
        elif path.startswith("/api/subjects/"):
            board_id = path[13:]
            conn = get_conn()
            rows = conn.execute("SELECT id, name, description FROM subjects WHERE board_id = ? ORDER BY name", (board_id,)).fetchall()
            self._send_json([dict(r) for r in rows])
        elif path.startswith("/api/graph/"):
            subject_id = path[11:].lower()
            self._api_knowledge_graph_subject(subject_id)
        elif path.startswith("/api/concept/"):
            concept_id = urllib.parse.unquote(path[12:])
            self._api_knowledge_graph_concept(concept_id)
        elif path == "/api/knowledge-graph":
            self._api_knowledge_graph()
        elif path.startswith("/api/knowledge-graph/subject/"):
            subject_id = path[29:]
            self._api_knowledge_graph_subject(subject_id)
        elif path.startswith("/api/knowledge-graph/concept/"):
            concept_id = path[29:]
            self._api_knowledge_graph_concept(concept_id)
        elif path == "/api/weaknesses":
            self._api_knowledge_graph_weaknesses()
        elif path == "/api/strengths":
            self._api_knowledge_graph_strengths()
        elif path == "/api/recommended":
            self._api_knowledge_graph_recommended()
        elif path == "/api/knowledge-graph/weaknesses":
            self._api_knowledge_graph_weaknesses()
        elif path == "/api/knowledge-graph/strengths":
            self._api_knowledge_graph_strengths()
        elif path == "/api/knowledge-graph/recommended":
            self._api_knowledge_graph_recommended()
        elif path == "/api/pillars":
            self._api_pillars()
        elif path.startswith("/api/pillars/"):
            pillar_id = path[13:]
            self._api_pillar_content(pillar_id)
        elif path == "/api/doubts":
            self._api_doubts(query)
        elif path == "/api/recommendations":
            self._api_recommendations()
        elif path == "/electives":
            self._serve_electives_hub()
        elif path.startswith("/electives/"):
            elective = path[11:]
            self._serve_elective(elective)
        elif path == "/register":
            self._serve_register()
        elif path == "/login":
            self._serve_login()
        elif path == "/logout":
            self._serve_logout()
        elif path == "/tools":
            self._serve_tools()
        elif path == "/tools/calculator":
            self._serve_tools_calculator()
        elif path == "/tools/periodic-table":
            self._serve_tools_periodic_table()
        elif path == "/leaderboard":
            self._serve_leaderboard()
        elif path == "/ai" or path == "/ai/studio":
            self._serve_ai_studio()
        elif path == "/ai/research":
            self._serve_ai_research()
        elif path == "/ai/literature":
            self._serve_ai_literature()
        elif path == "/ai/visualize":
            self._serve_ai_visualize()
        elif path == "/ai/pedagogical":
            self._serve_ai_pedagogical()
        elif path == "/ai/youtube":
            self._serve_ai_youtube()
        elif path.startswith("/api/ai/youtube"):
            self._api_ai_youtube(query)
        elif path.startswith("/api/ai/research"):
            self._api_ai_research(query)
        elif path.startswith("/api/ai/literature"):
            self._api_ai_literature(query)
        elif path.startswith("/api/ai/visualize"):
            self._api_ai_visualize(query)
        elif path.startswith("/api/ai/pedagogical"):
            self._api_ai_pedagogical(query)
        elif path == "/api/ai/status":
            client = get_client()
            self._send_json(client.get_status())
        elif path == "/api/view_logs":
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
                    self._send_json({"file": found_file, "logs": log_content})
                except Exception as e:
                    self._send_json({"error": f"Failed to read {found_file}: {e}"})
            else:
                self._send_json({"error": "No log files found", "searched": log_files})
        elif path == "/api/ai/enrich":
            topic = query.get("topic", [""])[0]
            chapter = query.get("chapter", [""])[0]
            subject = query.get("subject", [""])[0]
            if not topic:
                self._send_json({"error": "No topic", "html": ""})
            else:
                enriched = content_enricher.enrich_topic_content(topic, chapter, subject, "", "concept")
                html = content_enricher.format_ai_content(enriched)
                self._send_json({"html": html})
        elif path == "/syllabus":
            self._serve_syllabus_coverage()
        elif path == "/api/syllabus":
            self._api_syllabus_data()
        elif path == "/style.css":
            self._send_css()
        elif path == "/sw.js":
            self._send_sw()
        elif path == "/manifest.json":
            self._send_manifest()
        else:
            self._serve_error_page("Page not found", status=404)

    def do_POST(self):
        length = self._safe_int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode() if length else ""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/") or "/" 
        query = urllib.parse.parse_qs(body)
        if path == "/api/tutor/answer":
            self._api_tutor_answer(query)
        elif path == "/api/tutor/remedial":
            self._api_tutor_remedial(query)
        elif path == "/api/tutor/complete":
            self._api_tutor_complete(query)
        elif path == "/api/tutor/start":
            self._api_tutor_start(query)
        elif path == "/api/tutor/suggest":
            self._api_tutor_suggest()
        elif path == "/api/register":
            self._api_register(query)
        elif path == "/api/login":
            self._api_login(query)
        elif path == "/api/mock-exam/submit":
            self._api_mock_exam_submit(query)
        else:
            self._send_error(404, "Not found")

    def _safe_int(self, val, default=0):
        try:
            return int(val)
        except (ValueError, TypeError):
            return default

    def _serve_tutor_hub(self):
        conn = get_conn()
        subjects = conn.execute(
            "SELECT DISTINCT s.id, s.name, s.board_id FROM subjects s "
            "JOIN chapters c ON c.subject_id = s.id "
            "JOIN topics t ON t.chapter_id = c.id "
            "WHERE t.id IS NOT NULL "
            "ORDER BY s.board_id, s.name"
        ).fetchall()
        rows = ""
        for s in subjects:
            chapters = conn.execute(
                "SELECT c.id, c.num, c.title FROM chapters c "
                "JOIN topics t ON t.chapter_id = c.id "
                "WHERE c.subject_id = ? GROUP BY c.id ORDER BY c.num",
                (s["id"],)
            ).fetchall()
            ch_links = "".join(
                f'<li><a href="/chapter/{ch["id"]}">Ch {ch["num"]}: {ch["title"]}</a></li>'
                for ch in chapters
            )
            rows += f"""
            <div class="book-section">
                <h3>{s["name"]}</h3>
                <ul style="columns:2;column-gap:2rem;padding-left:1.2rem;">{ch_links}</ul>
            </div>"""
        if not rows:
            rows = '<p style="text-align:center;padding:2rem;color:#666;">No topics available yet. Seed the database first.</p>'
        content = f"""
        <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> AI Tutor Hub</div>
        <div class="section">
            <h2>🧠 AI Tutor Hub</h2>
            <p>Select a chapter to start a question-based learning session.</p>
            {rows}
        </div>"""
        html = render_template("base.html", title="AI Tutor Hub - Class X",
                               body_class="", extra_css="", content=content,
                               board_name="")
        self._send_html(html)

    def _serve_tutor_page(self, topic_id):
        conn = get_conn()
        topic = conn.execute("SELECT * FROM topics WHERE id = ?", (topic_id,)).fetchone()
        if not topic:
            self._serve_error_page("Topic not found"); return
        chapter = conn.execute("SELECT * FROM chapters WHERE id = ?", (topic["chapter_id"],)).fetchone()
        chunks = conn.execute("SELECT * FROM chunks WHERE topic_id = ? ORDER BY seq", (topic_id,)).fetchall()
        questions = ai_tutor.generate_questions(topic['title'], topic['content'], chunks, 3)
        session_id = ai_tutor.create_tutor_session(topic_id)
        html = f"""<div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> <a href="/board/{chapter['board_id']}">{chapter['board_id'].upper()}</a> <span class="sep">›</span> <a href="/chapter/{chapter['id']}">Ch {chapter['num']}: {chapter['title']}</a> <span class="sep">›</span> <a href="/topic/{topic_id}">{topic['title']}</a> <span class="sep">›</span> AI Tutor</div>
<div class="section" id="tutor-section">
<h2>🧠 AI Tutor: {topic['title']}</h2>
<p style="color:#666;margin-bottom:1rem;">Question-Based Learning — think deeply, then answer.</p>
<div id="tutor-progress" style="margin-bottom:1rem;font-size:0.85rem;color:var(--text-muted);">Question 1 of {len(questions)}</div>
<div id="tutor-content">
<div class="tutor-question-card">
<p class="tutor-prompt">{random.choice(ai_tutor.STARTER_PROMPTS)}</p>
<p class="tutor-question-text" id="tutor-question">{questions[0]['question']}</p>
<textarea id="tutor-answer" class="tutor-input" rows="4" placeholder="Type your answer here... Think carefully before answering."></textarea>
<div style="display:flex;gap:0.5rem;margin-top:0.8rem;flex-wrap:wrap;">
<button class="tts-btn" onclick="submitTutorAnswer({session_id})">Submit Answer</button>
<button class="tts-btn" onclick="skipTutorQuestion({session_id})" style="opacity:0.7;">Skip</button>
</div>
</div>
<div id="tutor-feedback" style="display:none;"></div>
</div>
<div id="tutor-complete" style="display:none;"></div>
</div>
<script>
var tutorQuestions = {json.dumps(questions)};
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
        var showModel = '<h4 style="margin-top:0.8rem;">Model Answer</h4><div class="tutor-model-answer" style="background:#f0f9ff;padding:0.8rem;border-radius:6px;margin-bottom:0.5rem;"><p>'+q.model_answer+'</p></div>';
        if(assessment=='correct'){{
            fb.innerHTML+='<p style="color:#16a34a;margin-top:0.8rem;">Great job! Let\\'s move on.</p>'+showModel;
        }}else{{
            fb.innerHTML+=showModel+(data.remedial_html||'');
        }}
        document.getElementById('tutor-answer').value='';
        document.getElementById('tutor-answer').disabled=false;
        tutorQIndex++;
        if(tutorQIndex<tutorQuestions.length){{
            document.getElementById('tutor-question').textContent=tutorQuestions[tutorQIndex].question;
            document.getElementById('tutor-progress').textContent='Question '+(tutorQIndex+1)+' of '+tutorQuestions.length;
            document.getElementById('tutor-answer').focus();
        }}else{{
            fetch('/api/tutor/complete',{{
                method:'POST', headers:{{'Content-Type':'application/x-www-form-urlencoded'}},
                body:'session_id='+sessionId
            }}).then(r=>r.json()).then(d=>{{
                document.getElementById('tutor-content').innerHTML =
                    '<div style="text-align:center;padding:2rem;"><h3>🎉 Session Complete!</h3><p style="font-size:1.2rem;margin:1rem 0;">+'+d.xp+' XP earned</p><p>Keep up the great work!</p><div style="display:flex;gap:0.5rem;justify-content:center;margin-top:1rem;"><a class="tts-btn" href="/topic/'+topicId+'">Back to Topic</a><a class="tts-btn" href="/tutor">Next Topic Suggestion</a></div></div>';
            }});
        }}
    }});
}}
function skipTutorQuestion(sessionId){{
    if(confirm('Skip this question?')){{
        var q = tutorQuestions[tutorQIndex];
        fetch('/api/tutor/answer',{{
            method:'POST', headers:{{'Content-Type':'application/x-www-form-urlencoded'}},
            body:'session_id='+sessionId+'&question='+encodeURIComponent(q.question)+'&qtype='+q.type+'&model_answer='+encodeURIComponent(q.model_answer)+'&student_answer=[skipped]'
        }}).then(function(){{
            tutorQIndex++;
            document.getElementById('tutor-answer').value='';
            if(tutorQIndex<tutorQuestions.length){{
                document.getElementById('tutor-question').textContent=tutorQuestions[tutorQIndex].question;
                document.getElementById('tutor-progress').textContent='Question '+(tutorQIndex+1)+' of '+tutorQuestions.length;
            }}else{{
                fetch('/api/tutor/complete',{{
                    method:'POST', headers:{{'Content-Type':'application/x-www-form-urlencoded'}},
                    body:'session_id='+sessionId
                }}).then(r=>r.json()).then(d=>{{
                    document.getElementById('tutor-content').innerHTML =
                        '<div style="text-align:center;padding:2rem;"><h3>🎉 Session Complete!</h3><p style="font-size:1.2rem;margin:1rem 0;">+'+d.xp+' XP earned</p><p>Keep up the great work!</p><div style="display:flex;gap:0.5rem;justify-content:center;margin-top:1rem;"><a class="tts-btn" href="/topic/'+topicId+'">Back to Topic</a><a class="tts-btn" href="/tutor">Next Topic Suggestion</a></div></div>';
                }});
            }}
        }});
    }}
}}
</script>"""
        self._send_html(html)

    def _serve_interactives(self, topic_id):
        conn = get_conn()
        topic = conn.execute("SELECT * FROM topics WHERE id = ?", (topic_id,)).fetchone()
        if not topic:
            self._serve_error_page("Topic not found"); return
        chapter = conn.execute("SELECT * FROM chapters WHERE id = ?", (topic["chapter_id"],)).fetchone()
        chunks = conn.execute("SELECT * FROM chunks WHERE topic_id = ? ORDER BY seq", (topic_id,)).fetchall()
        exercises = interactives.generate_interactives(topic['title'], topic['content'], chunks)
        ex_html = ''.join(exercises) if exercises else '<p style="color:#888;">Interactive exercises coming soon for this topic.</p>'
        js = interactives.get_interactives_js()
        html = f"""<div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> <a href="/board/{chapter['board_id']}">{chapter['board_id'].upper()}</a> <span class="sep">›</span> <a href="/chapter/{chapter['id']}">Ch {chapter['num']}: {chapter['title']}</a> <span class="sep">›</span> <a href="/topic/{topic_id}">{topic['title']}</a> <span class="sep">›</span> Interactive</div>
<div class="section"><h2>🎮 Interactive: {topic['title']}</h2>
<p style="color:#666;margin-bottom:1rem;">Drag, match, and flip to learn actively.</p>
{ex_html}</div>
<script>{js}</script>"""
        self._send_html(html)

    def _api_tutor_start(self, query):
        topic_id = (query.get('topic_id') or [''])[0]
        if not topic_id:
            self._send_json({"error": "topic_id required"}); return
        conn = get_conn()
        topic = conn.execute("SELECT * FROM topics WHERE id = ?", (topic_id,)).fetchone()
        if not topic:
            self._send_json({"error": "Topic not found"}); return
        chunks = conn.execute("SELECT * FROM chunks WHERE topic_id = ? ORDER BY seq", (topic_id,)).fetchall()
        questions = ai_tutor.generate_questions(topic['title'], topic['content'], chunks, 3)
        session_id = ai_tutor.create_tutor_session(topic_id)
        self._send_json({"session_id": session_id, "questions": questions, "topic_title": topic['title']})

    def _api_tutor_answer(self, query):
        try:
            session_id = int((query.get('session_id') or ['0'])[0])
        except (ValueError, TypeError):
            self._send_json({"error": "Invalid session_id"}); return
        question = (query.get('question') or [''])[0]
        qtype = (query.get('qtype') or [''])[0]
        model_answer = (query.get('model_answer') or [''])[0]
        student_answer = (query.get('student_answer') or [''])[0]
        if not session_id or not question:
            self._send_json({"error": "Missing fields"}); return
        conn = get_conn()
        session = conn.execute("SELECT id FROM tutor_sessions WHERE id = ?", (session_id,)).fetchone()
        if not session:
            self._send_json({"error": "Invalid session"}); return
        answer_id = ai_tutor.save_answer(session_id, question, qtype, model_answer, student_answer)
        self._send_json({"answer_id": answer_id, "status": "ok"})

    def _api_tutor_remedial(self, query):
        try:
            answer_id = int((query.get('answer_id') or ['0'])[0])
            session_id = int((query.get('session_id') or ['0'])[0])
        except (ValueError, TypeError):
            self._send_json({"error": "Invalid answer_id or session_id"}); return
        self_assessment = (query.get('self_assessment') or [''])[0]
        if not answer_id or not self_assessment:
            self._send_json({"error": "Missing fields"}); return
        ai_tutor.update_answer(answer_id, (query.get('student_answer') or [''])[0], self_assessment)
        if self_assessment == 'correct':
            self._send_json({"status": "ok", "remedial_html": ""}); return
        conn = get_conn()
        answer = conn.execute(
            "SELECT ta.*, ts.topic_id FROM tutor_answers ta JOIN tutor_sessions ts ON ta.session_id = ts.id WHERE ta.id = ?",
            (answer_id,)
        ).fetchone()
        topic = conn.execute("SELECT * FROM topics WHERE id = ?", (answer["topic_id"],)).fetchone()
        chunks = conn.execute("SELECT * FROM chunks WHERE topic_id = ? ORDER BY seq", (answer["topic_id"],)).fetchall()
        remedial = ai_tutor.get_remedial_content(topic['content'] if topic else '', chunks, answer['question_type'], answer['question'])
        html = f'<div class="tutor-remedial"><h4 style="margin-top:0.8rem;">📚 Let\'s Review This</h4><div class="tutor-remedial-content">{format_content(remedial)}</div></div>'
        self._send_json({"status": "ok", "remedial_html": html})

    def _api_tutor_complete(self, query):
        session_id = int((query.get('session_id') or ['0'])[0])
        if not session_id:
            self._send_json({"error": "Missing session_id"}); return
        xp = ai_tutor.complete_session(session_id)
        self._send_json({"status": "ok", "xp": xp})

    def _api_tutor_suggest(self):
        suggestions = ai_tutor.suggest_next_topics()
        if not suggestions:
            html = '<div class="section"><h2>🎉 All Topics Completed!</h2><p>You have studied all available topics. Great work!</p></div>'
        else:
            cards = ''.join(
                f'<div class="chunk-view" style="cursor:pointer;" onclick="location.href=\'/tutor/{s["topic_id"]}\'">'
                f'<div class="chunk-title">{s["topic_title"]}</div>'
                f'<p style="font-size:0.82rem;color:#666;">Chapter {s["ch_num"]}: {s["chapter_title"]}</p>'
                f'<p style="font-size:0.8rem;">Quiz score: {int(s["quiz_score"])}% | Reviews: {int(s.get("avg_quality",0)):.1f}/5</p>'
                f'</div>'
                for s in suggestions
            )
            html = f'<div class="section"><h2>📋 Suggested Next Topics</h2><p style="color:#666;margin-bottom:1rem;">Based on your performance, these topics need attention:</p>{cards}</div>'
        body = render_template("base.html", title="Suggested Topics - Class X", body_class="", extra_css="", content=html, board_name="")
        self._send_html(body)

    def _api_tutor_parent_report(self):
        report = ai_tutor.generate_parent_report()
        if not report:
            self._send_json({"error": "No data"})
        else:
            self._send_json(report)

    def _serve_parent_report(self):
        report = ai_tutor.generate_parent_report()
        if not report:
            self._serve_error_page("No data available"); return
        weak_html = ''.join(f'<tr><td>{t["title"]}</td><td>{t["chapter"]}</td><td>{int(t["score"])}%</td><td>{int(t.get("visits",0))}</td></tr>' for t in report['weak_areas'])
        strong_html = ''.join(f'<tr><td>{t["title"]}</td><td>{t["chapter"]}</td><td>{int(t["score"])}%</td></tr>' for t in report['strong_areas'])
        recs_html = ''.join(f'<li>{r}</li>' for r in report['recommendations'])
        badges_html = ''.join(f'<span class="topic-tag">{b}</span>' for b in report['badges']) if report['badges'] else '<span style="color:#999;">No badges yet</span>'
        html = f"""<div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> Progress Report</div>
<div class="section" style="max-width:800px;margin:0 auto;">
<h2>📊 Progress Report</h2>
<p style="color:#888;margin-bottom:1.5rem;">Generated: {report['generated_at']}</p>
<div class="stats-grid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:0.8rem;margin-bottom:1.5rem;">
<div class="stat-card"><div class="stat-value">{report['level']}</div><div class="stat-label">Level</div></div>
<div class="stat-card"><div class="stat-value">{report['total_xp']}</div><div class="stat-label">Total XP</div></div>
<div class="stat-card"><div class="stat-value">{report['weekly_xp']}</div><div class="stat-label">XP This Week</div></div>
<div class="stat-card"><div class="stat-value">{report['monthly_xp']}</div><div class="stat-label">XP This Month</div></div>
<div class="stat-card"><div class="stat-value">{report['streak']}</div><div class="stat-label">Current Streak</div></div>
<div class="stat-card"><div class="stat-value">{report['longest_streak']}</div><div class="stat-label">Best Streak</div></div>
</div>
<h3>🏆 Badges Earned</h3>
<p style="margin-bottom:1rem;">{badges_html}</p>
<h3>📈 Strong Areas</h3>
<table class="report-table"><tr><th>Topic</th><th>Chapter</th><th>Score</th></tr>{strong_html if strong_html else '<tr><td colspan="3" style="color:#999;">Complete more quizzes to identify strengths.</td></tr>'}</table>
<h3 style="margin-top:1.5rem;">📉 Areas Needing Improvement</h3>
<table class="report-table"><tr><th>Topic</th><th>Chapter</th><th>Score</th><th>Visits</th></tr>{weak_html if weak_html else '<tr><td colspan="4" style="color:#999;">Keep up the great work!</td></tr>'}</table>
<h3 style="margin-top:1.5rem;">💡 Recommendations</h3>
<ul style="line-height:1.8;">{recs_html}</ul>
<div style="text-align:center;margin-top:2rem;"><button class="tts-btn" onclick="window.print()">🖨️ Print Report</button></div>
</div>"""
        body = render_template("base.html", title="Progress Report - Class X", body_class="", extra_css="", content=html, board_name="")
        self._send_html(body)

    def _serve_learn_hub(self):
        conn = get_conn()
        pillars = conn.execute("SELECT * FROM content_pillars ORDER BY sort_order").fetchall()
        pillar_cards = ""
        for p in pillars:
            items = get_pillar_content(p["id"], limit=8)
            items_html = "".join(
                f'<a href="{i.get("url","#")}" class="topic-chip">{i.get("name","")}</a>'
                for i in items[:6]
            )
            more = f'<a href="/knowledge-graph" class="topic-chip" style="background:var(--accent);color:#fff;">+{len(items)-6} more</a>' if len(items) > 6 else ""
            pillar_cards += f"""
            <div class="info-card" style="border-left:4px solid {p['color']};">
                <h3>{p['icon']} {p['name']}</h3>
                <p style="font-size:0.85rem;color:#666;">{p['description']}</p>
                <div style="margin-top:0.5rem;display:flex;flex-wrap:wrap;gap:0.3rem;">{items_html}{more}</div>
            </div>"""
        html = f"""<div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> Learning Hub</div>
        <div class="section">
            <h2>📖 Learning Hub</h2>
            <p class="subtitle">Your structured learning path across CBSE subjects, practice, revision, and skill-building.</p>
            <div class="cards-grid" style="margin-top:1.5rem;">{pillar_cards}</div>
        </div>"""
        body = render_template("base.html", title="Learning Hub - Class X", body_class="", extra_css="", content=html, board_name="")
        self._send_html(body)

    def _serve_knowledge_graph(self, subject_id=None):
        conn = get_conn()
        if subject_id:
            graph = get_subject_graph(subject_id)
            subj = conn.execute("SELECT name FROM subjects WHERE id = ?", (subject_id,)).fetchone()
            title = f"{subj['name']} - Concept Map" if subj else "Concept Map"
            nodes = []
            for c in graph:
                mastery = c.get("mastery", {}).get("mastery_level", 0)
                pct = int(mastery * 100)
                nodes.append({"id": c["id"], "name": c["concept_name"], "pct": pct, "diff": c["difficulty"]})
                for child in c.get("children", []):
                    cm = child.get("mastery", {}).get("mastery_level", 0)
                    cpct = int(cm * 100)
                    nodes.append({"id": child["id"], "name": child["concept_name"], "pct": cpct, "diff": child["difficulty"]})
        else:
            graph = get_full_graph()
            title = "Full Knowledge Graph"
            nodes = []
            for subj_name, concepts in graph.items():
                for c in concepts:
                    mastery = c.get("mastery", {}).get("mastery_level", 0)
                    nodes.append({"id": c["id"], "name": f"{subj_name}: {c['concept_name']}", "pct": int(mastery * 100), "diff": c["difficulty"]})
                    for child in c.get("children", []):
                        cm = child.get("mastery", {}).get("mastery_level", 0)
                        nodes.append({"id": child["id"], "name": child["concept_name"], "pct": int(cm * 100), "diff": child["difficulty"]})
        node_rows = "".join(
            f'<tr><td><a href="/knowledge-graph/concept/{n["id"]}">{n["name"]}</a></td>'
            f'<td><div class="progress-bar" style="width:{n["pct"]}%;background:{"var(--accent)" if n["pct"] > 50 else "#e94560"};"></div></td>'
            f'<td>{n["pct"]}%</td><td>{"⭐" * n["diff"]}</td></tr>'
            for n in nodes
        )
        html = f"""<div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> <a href="/learn">Learning Hub</a> <span class="sep">›</span> {title}</div>
        <div class="section">
            <h2>🧠 {title}</h2>
            <p class="subtitle">Track your mastery across concepts. Each concept shows your mastery percentage and difficulty level.</p>
            <div class="book-section" style="margin-top:1rem;overflow-x:auto;">
                <table class="report-table"><tr><th>Concept</th><th>Mastery</th><th>%</th><th>Difficulty</th></tr>{node_rows}</table>
            </div>
        </div>"""
        body = render_template("base.html", title=f"{title} - Class X", body_class="", extra_css="", content=html, board_name="")
        self._send_html(body)

    def _api_knowledge_graph(self):
        self._send_json(get_full_graph())

    def _api_knowledge_graph_subject(self, subject_id):
        graph = get_subject_graph(subject_id)
        if not graph:
            self._send_error(404, "Subject not found")
            return
        self._send_json(graph)

    def _api_doubts(self, query):
        topic = query.get("topic", [""])[0]
        if not topic:
            self._send_json({"error": "topic required"})
            return
        conn = get_conn()
        results = conn.execute(
            "SELECT c.*, rank FROM chunks_fts JOIN chunks c ON chunks_fts.rowid = c.rowid WHERE chunks_fts MATCH ? ORDER BY rank LIMIT 5",
            (topic,),
        ).fetchall()
        answer = f"**Doubt: {topic}**\n\n"
        if results:
            answer += "Here are relevant explanations:\n\n"
            for r in results:
                rd = dict(r)
                title = rd.get("title") or rd.get("content", "")[:50]
                content = (rd.get("content") or "")[:300]
                answer += f"📖 **{title}**\n{content}...\n\n"
        else:
            answer += "No specific results found. Try rephrasing your doubt or searching for related topics."
        self._send_json({"topic": topic, "answer": answer, "sources": len(results)})

    def _api_recommendations(self):
        weak = get_weaknesses() or []
        strong = get_strengths() or []
        next_topics = get_recommended_next() or []
        self._send_json({
            "weaknesses": [dict(w) for w in weak] if weak else [],
            "strengths": [dict(s) for s in strong] if strong else [],
            "next_to_learn": next_topics if isinstance(next_topics, list) else [],
        })

    def _api_knowledge_graph_concept(self, concept_id):
        concept = get_concept(concept_id)
        if not concept:
            self._send_error(404, "Concept not found")
            return
        self._send_json(concept)

    def _api_knowledge_graph_weaknesses(self):
        self._send_json(get_weaknesses())

    def _api_knowledge_graph_strengths(self):
        self._send_json(get_strengths())

    def _api_knowledge_graph_recommended(self):
        self._send_json(get_recommended_next())

    def _serve_register(self):
        content = """
        <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> Register</div>
        <div class="section" style="max-width:480px;margin:2rem auto;">
            <h2>📝 Create Account</h2>
            <p class="subtitle">Join the Class X learning platform</p>
            <form method="POST" action="/api/register" onsubmit="event.preventDefault();registerUser(this)">
                <div class="book-section" style="padding:1.5rem;">
                    <label style="font-weight:500;display:block;margin-bottom:0.5rem;">Full Name</label>
                    <input type="text" name="name" required placeholder="Your name"
                           style="width:100%;padding:0.7rem;border:1px solid var(--border);border-radius:8px;margin-bottom:1rem;">
                    <label style="font-weight:500;display:block;margin-bottom:0.5rem;">Email</label>
                    <input type="email" name="email" required placeholder="you@example.com"
                           style="width:100%;padding:0.7rem;border:1px solid var(--border);border-radius:8px;margin-bottom:1rem;">
                    <label style="font-weight:500;display:block;margin-bottom:0.5rem;">Password</label>
                    <input type="password" name="password" required minlength="6" placeholder="At least 6 characters"
                           style="width:100%;padding:0.7rem;border:1px solid var(--border);border-radius:8px;margin-bottom:1rem;">
                    <label style="font-weight:500;display:block;margin-bottom:0.5rem;">Confirm Password</label>
                    <input type="password" name="confirm" required placeholder="Repeat password"
                           style="width:100%;padding:0.7rem;border:1px solid var(--border);border-radius:8px;margin-bottom:1.5rem;">
                    <button type="submit" class="btn-primary"
                            style="width:100%;padding:0.8rem;background:var(--primary);color:#fff;border:none;border-radius:8px;font-size:1rem;font-weight:600;cursor:pointer;">
                        Create Account
                    </button>
                </div>
            </form>
            <p style="text-align:center;margin-top:1rem;">
                Already have an account? <a href="/login" style="color:var(--accent);font-weight:600;">Login here</a>
            </p>
        </div>
        <script>
        async function registerUser(form) {
            const data = new FormData(form);
            if (data.get('password') !== data.get('confirm')) {
                alert('Passwords do not match!'); return;
            }
            const params = new URLSearchParams(data);
            const resp = await fetch('/api/register', {method:'POST', body:params});
            const result = await resp.json();
            if (result.success) {
                alert('Account created! Redirecting to profile...');
                window.location.href = '/profile';
            } else {
                alert(result.error || 'Registration failed.');
            }
        }
        </script>"""
        body = render_template("base.html", title="Register - Class X", body_class="", extra_css="", content=content, board_name="")
        self._send_html(body)

    def _serve_login(self):
        content = """
        <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> Login</div>
        <div class="section" style="max-width:480px;margin:2rem auto;">
            <h2>🔐 Login</h2>
            <p class="subtitle">Access your learning profile</p>
            <form method="POST" action="/api/login" onsubmit="event.preventDefault();loginUser(this)">
                <div class="book-section" style="padding:1.5rem;">
                    <label style="font-weight:500;display:block;margin-bottom:0.5rem;">Email</label>
                    <input type="email" name="email" required placeholder="you@example.com"
                           style="width:100%;padding:0.7rem;border:1px solid var(--border);border-radius:8px;margin-bottom:1rem;">
                    <label style="font-weight:500;display:block;margin-bottom:0.5rem;">Password</label>
                    <input type="password" name="password" required placeholder="Enter password"
                           style="width:100%;padding:0.7rem;border:1px solid var(--border);border-radius:8px;margin-bottom:1.5rem;">
                    <button type="submit" class="btn-primary"
                            style="width:100%;padding:0.8rem;background:var(--primary);color:#fff;border:none;border-radius:8px;font-size:1rem;font-weight:600;cursor:pointer;">
                        Login
                    </button>
                </div>
            </form>
            <p style="text-align:center;margin-top:1rem;">
                Don't have an account? <a href="/register" style="color:var(--accent);font-weight:600;">Register here</a>
            </p>
        </div>
        <script>
        async function loginUser(form) {
            const data = new FormData(form);
            const params = new URLSearchParams(data);
            const resp = await fetch('/api/login', {method:'POST', body:params});
            const result = await resp.json();
            if (result.success) {
                alert('Welcome back! Redirecting...');
                window.location.href = result.redirect || '/profile';
            } else {
                alert(result.error || 'Login failed.');
            }
        }
        </script>"""
        body = render_template("base.html", title="Login - Class X", body_class="", extra_css="", content=content, board_name="")
        self._send_html(body)

    def _serve_logout(self):
        content = """
        <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> Logout</div>
        <div class="section" style="max-width:480px;margin:2rem auto;text-align:center;">
            <h2>👋 Logged Out</h2>
            <p class="subtitle">You have been signed out successfully.</p>
            <a href="/login" style="display:inline-block;margin-top:1rem;padding:0.8rem 2rem;background:var(--primary);color:#fff;border-radius:8px;text-decoration:none;font-weight:600;">Login Again</a>
        </div>
        <script>localStorage.removeItem('learner_session');</script>"""
        body = render_template("base.html", title="Logged Out - Class X", body_class="", extra_css="", content=content, board_name="")
        self._send_html(body)

    def _serve_tools(self):
        content = """
        <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> Tools</div>
        <div class="section">
            <h2>🛠️ Learning Tools</h2>
            <p class="subtitle">Interactive tools to support your studies</p>
            <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:1rem;margin-top:1.5rem;">
                <a href="/tools/calculator" class="book-section" style="display:block;text-align:center;padding:2rem;text-decoration:none;color:inherit;">
                    <div style="font-size:3rem;margin-bottom:0.5rem;">🧮</div>
                    <h3 style="margin:0;font-size:1.1rem;">Scientific Calculator</h3>
                    <p style="font-size:0.85rem;color:var(--text-muted);margin-top:0.3rem;">Perform calculations</p>
                </a>
                <a href="/tools/periodic-table" class="book-section" style="display:block;text-align:center;padding:2rem;text-decoration:none;color:inherit;">
                    <div style="font-size:3rem;margin-bottom:0.5rem;">⚗️</div>
                    <h3 style="margin:0;font-size:1.1rem;">Periodic Table</h3>
                    <p style="font-size:0.85rem;color:var(--text-muted);margin-top:0.3rem;">Interactive element table</p>
                </a>
                <a href="/mindmap" class="book-section" style="display:block;text-align:center;padding:2rem;text-decoration:none;color:inherit;">
                    <div style="font-size:3rem;margin-bottom:0.5rem;">🗺️</div>
                    <h3 style="margin:0;font-size:1.1rem;">Mind Maps</h3>
                    <p style="font-size:0.85rem;color:var(--text-muted);margin-top:0.3rem;">Visual concept maps</p>
                </a>
                <a href="/knowledge-graph" class="book-section" style="display:block;text-align:center;padding:2rem;text-decoration:none;color:inherit;">
                    <div style="font-size:3rem;margin-bottom:0.5rem;">🔗</div>
                    <h3 style="margin:0;font-size:1.1rem;">Knowledge Graph</h3>
                    <p style="font-size:0.85rem;color:var(--text-muted);margin-top:0.3rem;">Concept relationships</p>
                </a>
            </div>
        </div>"""
        body = render_template("base.html", title="Tools - Class X", body_class="", extra_css="", content=content, board_name="")
        self._send_html(body)

    def _serve_tools_calculator(self):
        content = """
        <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> <a href="/tools">Tools</a> <span class="sep">›</span> Scientific Calculator</div>
        <div class="section">
            <h2>🧮 Scientific Calculator</h2>
            <p class="subtitle">Perform arithmetic and scientific calculations</p>
            <div style="max-width:360px;margin:1.5rem auto;background:var(--card);border-radius:12px;padding:1rem;box-shadow:0 2px 8px rgba(0,0,0,0.1);">
                <input type="text" id="calc-display" readonly
                    style="width:100%;padding:1rem;font-size:1.5rem;text-align:right;border:1px solid var(--border);border-radius:8px;background:var(--bg);color:var(--text);margin-bottom:0.5rem;box-sizing:border-box;">
                <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:0.4rem;">
                    <button class="calc-btn" style="background:#e74c3c;color:#fff;" onclick="clearCalc()">AC</button>
                    <button class="calc-btn" onclick="appendCalc('(')">(</button>
                    <button class="calc-btn" onclick="appendCalc(')')">)</button>
                    <button class="calc-btn" style="background:#f39c12;color:#fff;" onclick="appendCalc('/')">÷</button>

                    <button class="calc-btn" onclick="appendCalc('7')">7</button>
                    <button class="calc-btn" onclick="appendCalc('8')">8</button>
                    <button class="calc-btn" onclick="appendCalc('9')">9</button>
                    <button class="calc-btn" style="background:#f39c12;color:#fff;" onclick="appendCalc('*')">×</button>

                    <button class="calc-btn" onclick="appendCalc('4')">4</button>
                    <button class="calc-btn" onclick="appendCalc('5')">5</button>
                    <button class="calc-btn" onclick="appendCalc('6')">6</button>
                    <button class="calc-btn" style="background:#f39c12;color:#fff;" onclick="appendCalc('-')">−</button>

                    <button class="calc-btn" onclick="appendCalc('1')">1</button>
                    <button class="calc-btn" onclick="appendCalc('2')">2</button>
                    <button class="calc-btn" onclick="appendCalc('3')">3</button>
                    <button class="calc-btn" style="background:#f39c12;color:#fff;" onclick="appendCalc('+')">+</button>

                    <button class="calc-btn" onclick="appendCalc('0')">0</button>
                    <button class="calc-btn" onclick="appendCalc('.')">.</button>
                    <button class="calc-btn" onclick="appendCalc('**')">xʸ</button>
                    <button class="calc-btn" style="background:#27ae60;color:#fff;" onclick="evalCalc()">=</button>
                </div>
                <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:0.4rem;margin-top:0.4rem;">
                    <button class="calc-btn" onclick="appendCalc('Math.sin(')">sin</button>
                    <button class="calc-btn" onclick="appendCalc('Math.cos(')">cos</button>
                    <button class="calc-btn" onclick="appendCalc('Math.tan(')">tan</button>
                    <button class="calc-btn" onclick="appendCalc('Math.sqrt(')">√</button>
                    <button class="calc-btn" onclick="appendCalc('Math.log(')">log</button>
                    <button class="calc-btn" onclick="appendCalc('Math.PI')">π</button>
                    <button class="calc-btn" onclick="appendCalc('Math.E')">e</button>
                    <button class="calc-btn" onclick="appendCalc('**0.5')">√x</button>
                </div>
            </div>
        </div>
        <script>
        function appendCalc(v){const d=document.getElementById('calc-display');d.value+=v;d.focus();}
        function clearCalc(){document.getElementById('calc-display').value='';}
        function evalCalc(){try{const d=document.getElementById('calc-display');d.value=Function('"use strict";return ('+d.value+')')();}catch(e){document.getElementById('calc-display').value='Error';}}
        document.querySelectorAll('.calc-btn').forEach(b=>{b.style.cssText+='padding:0.8rem;font-size:1.1rem;border:none;border-radius:6px;cursor:pointer;transition:0.2s;background:var(--card);color:var(--text);');b.onmouseover=function(){this.style.opacity='0.8';};b.onmouseout=function(){this.style.opacity='1';};});
        </script>"""
        body = render_template("base.html", title="Scientific Calculator - Class X", body_class="", extra_css="", content=content, board_name="")
        self._send_html(body)

    def _serve_tools_periodic_table(self):
        elements = [
            ("H","Hydrogen",1,1,"Nonmetal"), ("He","Helium",2,18,"Noble Gas"),
            ("Li","Lithium",3,1,"Alkali Metal"), ("Be","Beryllium",4,2,"Alkaline Earth"),
            ("B","Boron",5,13,"Metalloid"), ("C","Carbon",6,14,"Nonmetal"),
            ("N","Nitrogen",7,15,"Nonmetal"), ("O","Oxygen",8,16,"Nonmetal"),
            ("F","Fluorine",9,17,"Halogen"), ("Ne","Neon",10,18,"Noble Gas"),
            ("Na","Sodium",11,1,"Alkali Metal"), ("Mg","Magnesium",12,2,"Alkaline Earth"),
            ("Al","Aluminium",13,13,"Metal"), ("Si","Silicon",14,14,"Metalloid"),
            ("P","Phosphorus",15,15,"Nonmetal"), ("S","Sulfur",16,16,"Nonmetal"),
            ("Cl","Chlorine",17,17,"Halogen"), ("Ar","Argon",18,18,"Noble Gas"),
            ("K","Potassium",19,1,"Alkali Metal"), ("Ca","Calcium",20,2,"Alkaline Earth"),
            ("Sc","Scandium",21,3,"Transition"), ("Ti","Titanium",22,4,"Transition"),
            ("V","Vanadium",23,5,"Transition"), ("Cr","Chromium",24,6,"Transition"),
            ("Mn","Manganese",25,7,"Transition"), ("Fe","Iron",26,8,"Transition"),
            ("Co","Cobalt",27,9,"Transition"), ("Ni","Nickel",28,10,"Transition"),
            ("Cu","Copper",29,11,"Transition"), ("Zn","Zinc",30,12,"Transition"),
            ("Br","Bromine",35,17,"Halogen"), ("Kr","Krypton",36,18,"Noble Gas"),
            ("I","Iodine",53,17,"Halogen"), ("Xe","Xenon",54,18,"Noble Gas"),
            ("Cs","Cesium",55,1,"Alkali Metal"), ("Ba","Barium",56,2,"Alkaline Earth"),
            ("Pt","Platinum",78,10,"Transition"), ("Au","Gold",79,11,"Transition"),
            ("Hg","Mercury",80,12,"Transition"), ("Pb","Lead",82,14,"Metal"),
            ("Rn","Radon",86,18,"Noble Gas"), ("U","Uranium",92,3,"Actinide"),
        ]
        cat_colors = {"Nonmetal":"#4caf50","Noble Gas":"#9c27b0","Alkali Metal":"#f44336",
            "Alkaline Earth":"#ff9800","Metalloid":"#8bc34a","Metal":"#2196f3",
            "Transition":"#00bcd4","Halogen":"#e91e63","Actinide":"#795548"}
        rows = {}
        for sym,name,num,grp,cat in elements:
            rows.setdefault(grp, []).append((sym,num,cat))
        grid = ""
        for grp in sorted(rows):
            grid += '<div style="display:contents;">'
            for sym,num,cat in rows[grp]:
                c = cat_colors.get(cat,"#999")
                grid += f'<div style="background:{c};color:#fff;padding:0.3rem;border-radius:4px;text-align:center;font-size:0.75rem;font-weight:bold;" title="{cat}">{sym}<br><span style="font-size:0.6rem;font-weight:normal;">{num}</span></div>'
            grid += "</div>"
        content = f"""
        <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> <a href="/tools">Tools</a> <span class="sep">›</span> Periodic Table</div>
        <div class="section">
            <h2>⚗️ Periodic Table of Elements</h2>
            <p class="subtitle">Interactive periodic table (first 92 elements)</p>
            <div style="display:grid;grid-template-columns:repeat(18,1fr);gap:2px;margin-top:1rem;">
                {grid}
            </div>
            <div style="display:flex;flex-wrap:wrap;gap:0.5rem;margin-top:1rem;justify-content:center;">
                {''.join(f'<span style="background:{c};color:#fff;padding:0.2rem 0.6rem;border-radius:12px;font-size:0.8rem;">{cat}</span>' for cat, c in cat_colors.items())}
            </div>
        </div>"""
        body = render_template("base.html", title="Periodic Table - Class X", body_class="", extra_css="", content=content, board_name="")
        self._send_html(body)

    def _serve_leaderboard(self):
        content = """
        <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> Leaderboard</div>
        <div class="section">
            <h2>🏆 Leaderboard</h2>
            <p class="subtitle">Top learners ranked by XP and achievements</p>
            <div id="leaderboard-content" style="margin-top:1.5rem;text-align:center;">
                <p>Loading leaderboard...</p>
            </div>
        </div>
        <script>
        async function loadLeaderboard() {
            try {
                const resp = await fetch('/api/gamification');
                const data = await resp.json();
                let html = '<div class="book-section" style="padding:1rem;"><table style="width:100%;border-collapse:collapse;">';
                html += '<tr style="border-bottom:2px solid var(--border);"><th style="padding:0.7rem;text-align:left;">Rank</th><th style="padding:0.7rem;text-align:left;">Metric</th><th style="padding:0.7rem;text-align:right;">Value</th></tr>';
                const metrics = [
                    ['💫 XP', data.xp, '⭐'],
                    ['🏆 Level', data.level, '📊'],
                    ['🔥 Streak', data.streak + ' days', '📅'],
                    ['❤️ Lives', data.lives + '/' + data.max_lives, '⚡'],
                    ['📚 Topics Completed', data.topics_completed, '✅'],
                    ['🎯 Quizzes Taken', data.quizzes_taken, '📝'],
                    ['🎯 Quiz Accuracy', data.quiz_accuracy + '%', '📈'],
                ];
                metrics.forEach((m, i) => {
                    html += '<tr' + (i % 2 === 0 ? ' style="background:var(--hover-bg);"' : '') + '>';
                    html += '<td style="padding:0.7rem;">#' + (i + 1) + '</td>';
                    html += '<td style="padding:0.7rem;">' + m[0] + '</td>';
                    html += '<td style="padding:0.7rem;text-align:right;font-weight:600;">' + m[1] + ' ' + m[2] + '</td>';
                    html += '</tr>';
                });
                html += '</table></div>';
                html += '<p style="text-align:center;margin-top:1rem;color:var(--text-muted);font-size:0.85rem;">Keep learning to earn more XP and climb the ranks!</p>';
                document.getElementById('leaderboard-content').innerHTML = html;
            } catch(e) {
                document.getElementById('leaderboard-content').innerHTML = '<p>Could not load leaderboard data.</p>';
            }
        }
        document.addEventListener('DOMContentLoaded', loadLeaderboard);
        </script>"""
        body = render_template("base.html", title="Leaderboard - Class X", body_class="", extra_css="", content=content, board_name="")
        self._send_html(body)

    # ─── AI Studio ──────────────────────────────────────────────────────────

    def _serve_ai_studio(self):
        client = get_client()
        status = client.get_status()
        backend_html = f"""
        <div id="ai-status" style="margin-bottom:1rem;padding:0.75rem 1rem;border-radius:8px;font-size:0.85rem;background:{'#f0fdf4' if status['available'] else '#fff7ed'};border:1px solid {'#bbf7d0' if status['available'] else '#fed7aa'};">
            <strong>AI Backend:</strong> {'🟢 Online' if status['available'] else '🟡 Offline'}
            {' · ' + status['backend'].title() + ' · ' + status['model'] if status['available'] else ' · Set GEMINI_API_KEY'}
        </div>"""
        content = f"""
        <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> AI Studio</div>
        <div class="section">
            <h2>🧠 AI Studio</h2>
            <p class="subtitle">Google Gemini · Gemma 4 · NotebookLM · YouTube Data API · SVG Visualizer</p>
            {backend_html}
            <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:1rem;margin-top:1.5rem;">
                <a href="/ai/research" class="book-section" style="display:block;text-align:center;padding:1.5rem;text-decoration:none;color:inherit;">
                    <div style="font-size:2.5rem;">🔬</div><h3>Gemini Research</h3><p style="font-size:0.85rem;color:var(--text-muted);">Deep research by Google Gemini</p>
                </a>
                <a href="/ai/literature" class="book-section" style="display:block;text-align:center;padding:1.5rem;text-decoration:none;color:inherit;">
                    <div style="font-size:2.5rem;">📚</div><h3>Gemini Literature</h3><p style="font-size:0.85rem;color:var(--text-muted);">Research overviews by Gemini</p>
                </a>
                <a href="/ai/visualize" class="book-section" style="display:block;text-align:center;padding:1.5rem;text-decoration:none;color:inherit;">
                    <div style="font-size:2.5rem;">🎨</div><h3>SVG Visualizer</h3><p style="font-size:0.85rem;color:var(--text-muted);">Concept visualization by Gemma 4</p>
                </a>
                <a href="/ai/pedagogical" class="book-section" style="display:block;text-align:center;padding:1.5rem;text-decoration:none;color:inherit;">
                    <div style="font-size:2.5rem;">📓</div><h3>NotebookLM</h3><p style="font-size:0.85rem;color:var(--text-muted);">Pedagogical study guides</p>
                </a>
                <a href="/api/notebooklm?board=cbse&subject=science" class="book-section" style="display:block;text-align:center;padding:1.5rem;text-decoration:none;color:inherit;">
                    <div style="font-size:2.5rem;">📥</div><h3>NotebookLM Export</h3><p style="font-size:0.85rem;color:var(--text-muted);">Export study notes</p>
                </a>
                <a href="/ai/youtube" class="book-section" style="display:block;text-align:center;padding:1.5rem;text-decoration:none;color:inherit;">
                    <div style="font-size:2.5rem;">▶️</div><h3>YouTube Videos</h3><p style="font-size:0.85rem;color:var(--text-muted);">Google YouTube Data API v3 — Free Tier</p>
                </a>
            </div>
        </div>"""
        body = render_template("base.html", title="AI Studio - Class X", body_class="", extra_css="", content=content, board_name="")
        self._send_html(body)

    def _serve_ai_research(self):
        content = """
        <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> <a href="/ai">AI Studio</a> <span class="sep">›</span> AI Research</div>
        <div class="section">
            <h2>🔬 Gemini Research</h2>
            <p class="subtitle">Deep research on any academic topic — powered by Google Gemini</p>
            <div class="book-section" style="padding:1.5rem;margin-top:1rem;">
                <label style="font-weight:500;display:block;margin-bottom:0.5rem;">Research Question</label>
                <input type="text" id="research-query" value="How does photosynthesis work?" style="width:100%;padding:0.7rem;border:1px solid var(--border);border-radius:8px;margin-bottom:1rem;">
                <label style="font-weight:500;display:block;margin-bottom:0.5rem;">Subject</label>
                <input type="text" id="research-subject" value="Science" style="width:100%;padding:0.7rem;border:1px solid var(--border);border-radius:8px;margin-bottom:1rem;">
                <button onclick="doResearch()" class="btn-primary" style="padding:0.8rem 2rem;background:var(--primary);color:#fff;border:none;border-radius:8px;font-size:1rem;font-weight:600;cursor:pointer;">Research</button>
            </div>
            <div id="research-output" style="margin-top:1.5rem;display:none;">
                <div class="book-section" style="padding:1.5rem;line-height:1.8;" id="research-content"></div>
            </div>
        </div>
        <script>
        async function doResearch() {
            const query = document.getElementById('research-query').value;
            const subject = document.getElementById('research-subject').value;
            const output = document.getElementById('research-output');
            const content = document.getElementById('research-content');
            const btn = event.target; btn.textContent='Researching...'; btn.disabled=true;
            content.innerHTML = '<p><em>Researching... This may take a moment.</em></p>'; output.style.display='block';
            try {
                const resp = await fetch('/api/ai/research?query='+encodeURIComponent(query)+'&subject='+encodeURIComponent(subject));
                const data = await resp.json();
                if (data.success) {
                    content.innerHTML = data.answer.replace(/\\n/g, '<br>');
                } else { content.innerHTML = '<p>' + (data.error || 'Research failed.') + '</p>'; }
            } catch(e) { content.innerHTML = '<p>Research request failed.</p>'; }
            btn.textContent='Research'; btn.disabled=false;
        }
        </script>"""
        body = render_template("base.html", title="Gemini Research - Class X", body_class="", extra_css="", content=content, board_name="")
        self._send_html(body)

    def _serve_ai_literature(self):
        content = """
        <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> <a href="/ai">AI Studio</a> <span class="sep">›</span> AI Literature</div>
        <div class="section">
            <h2>📚 Gemini Literature — Research Overview Generator</h2>
            <p class="subtitle">Get research summaries on any academic topic — powered by Google Gemini</p>
            <div class="book-section" style="padding:1.5rem;margin-top:1rem;">
                <label style="font-weight:500;display:block;margin-bottom:0.5rem;">Research Topic</label>
                <input type="text" id="lit-query" value="Photosynthesis efficiency" style="width:100%;padding:0.7rem;border:1px solid var(--border);border-radius:8px;margin-bottom:1rem;">
                <label style="font-weight:500;display:block;margin-bottom:0.5rem;">Subject Area</label>
                <input type="text" id="lit-subject" value="Science" style="width:100%;padding:0.7rem;border:1px solid var(--border);border-radius:8px;margin-bottom:1rem;">
                <button onclick="searchLiterature()" class="btn-primary" style="padding:0.8rem 2rem;background:var(--primary);color:#fff;border:none;border-radius:8px;font-size:1rem;font-weight:600;cursor:pointer;">Generate Overview</button>
            </div>
            <div id="lit-output" style="margin-top:1.5rem;display:none;">
                <div class="book-section" style="padding:1.5rem;" id="lit-results"></div>
            </div>
        </div>
        <script>
        async function searchLiterature() {
            const query = document.getElementById('lit-query').value;
            const subject = document.getElementById('lit-subject').value;
            const output = document.getElementById('lit-output');
            const results = document.getElementById('lit-results');
            const btn = event.target; btn.textContent='Generating...'; btn.disabled=true;
            results.innerHTML = '<p><em>Generating research overview...</em></p>'; output.style.display='block';
            try {
                const resp = await fetch('/api/ai/literature?query='+encodeURIComponent(query)+'&subject='+encodeURIComponent(subject));
                const data = await resp.json();
                if (data.success && data.results) {
                    let html = '<h3>Research Overview</h3>';
                    data.results.forEach((r, i) => {
                        html += '<div style="padding:1rem 0;border-bottom:1px solid var(--border);">';
                        html += '<h4 style="margin:0 0 0.3rem;">' + (i+1) + '. ' + r.title + '</h4>';
                        if (r.authors) html += '<p style="font-size:0.85rem;color:var(--text-muted);margin:0 0 0.3rem;">' + r.authors + ' (' + (r.year || 'N/A') + ')</p>';
                        if (r.abstract) html += '<p style="font-size:0.9rem;margin:0.3rem 0;">' + r.abstract.slice(0, 300) + '</p>';
                        html += '</div>';
                    });
                    results.innerHTML = html;
                } else { results.innerHTML = '<p>' + (data.error || 'No results found.') + '</p>'; }
            } catch(e) { results.innerHTML = '<p>Generation failed.</p>'; }
            btn.textContent='Generate Overview'; btn.disabled=false;
        }
        </script>"""
        body = render_template("base.html", title="Gemini Literature - Class X", body_class="", extra_css="", content=content, board_name="")
        self._send_html(body)

    def _serve_ai_visualize(self):
        content = """
        <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> <a href="/ai">AI Studio</a> <span class="sep">›</span> SVG Visualizer</div>
        <div class="section">
            <h2>🎨 SVG Visualizer — Concept Diagrams</h2>
            <p class="subtitle">Generate clean SVG diagrams for any concept — powered by Gemma 4</p>
            <div class="book-section" style="padding:1.5rem;margin-top:1rem;">
                <label style="font-weight:500;display:block;margin-bottom:0.5rem;">Concept</label>
                <input type="text" id="vis-concept" value="Plant cell structure" style="width:100%;padding:0.7rem;border:1px solid var(--border);border-radius:8px;margin-bottom:1rem;">
                <label style="font-weight:500;display:block;margin-bottom:0.5rem;">Style</label>
                <select id="vis-style" style="width:100%;padding:0.7rem;border:1px solid var(--border);border-radius:8px;margin-bottom:1rem;">
                    <option value="diagram">Educational Diagram</option>
                    <option value="flowchart">Flowchart</option>
                    <option value="comparison">Comparison</option>
                </select>
                <button onclick="generateVisual()" class="btn-primary" style="padding:0.8rem 2rem;background:var(--primary);color:#fff;border:none;border-radius:8px;font-size:1rem;font-weight:600;cursor:pointer;">Generate SVG</button>
            </div>
            <div id="vis-output" style="margin-top:1.5rem;display:none;">
                <div class="book-section" style="padding:1.5rem;text-align:center;background:#fff;border-radius:12px;overflow-x:auto;" id="vis-container"></div>
                <div style="text-align:center;margin-top:0.5rem;">
                    <button onclick="copySvg()" style="padding:0.4rem 1rem;background:var(--primary);color:#fff;border:none;border-radius:6px;cursor:pointer;">📋 Copy SVG</button>
                    <button onclick="downloadSvg()" style="padding:0.4rem 1rem;background:var(--accent);color:#fff;border:none;border-radius:6px;cursor:pointer;">⬇ Download</button>
                </div>
            </div>
        </div>
        <script>
        let lastSvg = '';
        async function generateVisual() {
            const concept = document.getElementById('vis-concept').value;
            const style = document.getElementById('vis-style').value;
            const output = document.getElementById('vis-output');
            const container = document.getElementById('vis-container');
            const btn = event.target; btn.textContent='Generating...'; btn.disabled=true;
            output.style.display='block'; container.innerHTML = '<p style="color:var(--text-muted);">Generating diagram...</p>';
            try {
                const resp = await fetch('/api/ai/visualize?concept='+encodeURIComponent(concept)+'&style='+encodeURIComponent(style));
                const data = await resp.json();
                if (data.success && data.svg) {
                    lastSvg = data.svg;
                    container.innerHTML = data.svg;
                } else {
                    container.innerHTML = '<p style="color:var(--text-muted);">Could not generate SVG.</p>';
                }
            } catch(e) { container.innerHTML = '<p>Generation failed.</p>'; }
            btn.textContent='Generate SVG'; btn.disabled=false;
        }
        function copySvg() {
            if (lastSvg) { navigator.clipboard.writeText(lastSvg); alert('SVG copied!'); }
        }
        function downloadSvg() {
            if (!lastSvg) return;
            const blob = new Blob([lastSvg], {type:'image/svg+xml'});
            const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
            a.download = 'diagram.svg'; a.click();
        }
        </script>"""
        body = render_template("base.html", title="SVG Visualizer - Class X", body_class="", extra_css="", content=content, board_name="")
        self._send_html(body)

    # ─── Enhanced NotebookLM: Pedagogical ────────────────────────────────────

    def _serve_ai_pedagogical(self):
        content = """
<div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> <a href="/ai">AI Studio</a> <span class="sep">›</span> NotebookLM Pedagogy</div>
<div class="section">
<h2>📓 NotebookLM — Pedagogical Concept Detailing</h2>
<p class="subtitle">Deep pedagogical breakdown with basics, foundational knowledge & clear explanations</p>
<div class="book-section" style="padding:1.5rem;margin-top:1rem;">
  <label style="font-weight:500;display:block;margin-bottom:0.5rem;">Subject</label>
  <input type="text" id="ped-subject" value="Science" style="width:100%;padding:0.7rem;border:1px solid var(--border);border-radius:8px;margin-bottom:1rem;">
  <label style="font-weight:500;display:block;margin-bottom:0.5rem;">Chapter</label>
  <input type="text" id="ped-chapter" value="Life Processes" style="width:100%;padding:0.7rem;border:1px solid var(--border);border-radius:8px;margin-bottom:1rem;">
  <label style="font-weight:500;display:block;margin-bottom:0.5rem;">Topic</label>
  <input type="text" id="ped-topic" value="Photosynthesis" style="width:100%;padding:0.7rem;border:1px solid var(--border);border-radius:8px;margin-bottom:1rem;">
  <button onclick="generatePedagogical()" class="btn-primary" style="padding:0.8rem 2rem;background:var(--primary);color:#fff;border:none;border-radius:8px;font-size:1rem;font-weight:600;cursor:pointer;">Generate Study Guide</button>
</div>
<div id="ped-output" style="margin-top:1.5rem;display:none;">
  <div class="book-section" style="padding:1.5rem;line-height:1.8;" id="ped-content"></div>
  <div style="text-align:center;margin-top:0.5rem;">
    <button onclick="exportPedagogical()" style="padding:0.5rem 1rem;background:var(--accent);color:#fff;border:none;border-radius:6px;cursor:pointer;">📥 Export Markdown</button>
  </div>
</div>
</div>
<script>
let pedMarkdown = '';
async function generatePedagogical() {
  const s = document.getElementById('ped-subject').value;
  const c = document.getElementById('ped-chapter').value;
  const t = document.getElementById('ped-topic').value;
  const output = document.getElementById('ped-output');
  const content = document.getElementById('ped-content');
  const btn = event.target; btn.textContent='Generating...'; btn.disabled=true;
  content.innerHTML = '<p><em>Creating pedagogical study guide...</em></p>'; output.style.display='block';
  try {
    const resp = await fetch('/api/ai/pedagogical?subject='+encodeURIComponent(s)+'&chapter='+encodeURIComponent(c)+'&topic='+encodeURIComponent(t));
    const data = await resp.json();
    if (data.success) {
      pedMarkdown = data.markdown;
      content.innerHTML = data.markdown.replace(/\\n/g, '<br>').replace(/##/g, '<br><strong>').replace(/#/g, '<strong>').replace(/<strong>(.*?)<\\/strong>/g, '<h3>$1</h3>');
    } else { content.innerHTML = '<p>Could not generate guide.</p>'; }
  } catch(e) { content.innerHTML = '<p>Generation failed.</p>'; }
  btn.textContent='Generate Study Guide'; btn.disabled=false;
}
function exportPedagogical() {
  if (!pedMarkdown) return;
  const blob = new Blob([pedMarkdown], {type:'text/markdown'});
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
  a.download = 'study_guide.md'; a.click();
}
</script>"""
        body = render_template("base.html", title="NotebookLM Pedagogy - Class X", body_class="", extra_css="", content=content, board_name="")
        self._send_html(body)

    # ─── YouTube: Video Integration ────────────────────────────────────────────

    def _serve_ai_youtube(self):
        content = """
<div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> <a href="/ai">AI Studio</a> <span class="sep">›</span> YouTube Videos</div>
<div class="section">
<h2>▶️ YouTube Video Search</h2>
<p class="subtitle">Powered by Google YouTube Data API v3 (Free Tier) — Search CBSE Class 10 educational videos</p>
<div class="book-section" style="padding:1.5rem;margin-top:1rem;">
  <label style="font-weight:500;display:block;margin-bottom:0.5rem;">Topic</label>
  <input type="text" id="yt-topic" value="Photosynthesis" style="width:100%;padding:0.7rem;border:1px solid var(--border);border-radius:8px;margin-bottom:0.5rem;">
  <label style="font-weight:500;display:block;margin-bottom:0.5rem;">Chapter / Subject (optional)</label>
  <input type="text" id="yt-chapter" value="Life Processes Science" style="width:100%;padding:0.7rem;border:1px solid var(--border);border-radius:8px;margin-bottom:1rem;">
  <button onclick="searchYouTube()" class="btn-primary" style="padding:0.8rem 2rem;background:#ff0000;color:#fff;border:none;border-radius:8px;font-size:1rem;font-weight:600;cursor:pointer;">▶️ Search Videos</button>
</div>
<div id="yt-output" style="margin-top:1rem;"></div>
</div>
<script>
async function searchYouTube() {
  var topic = document.getElementById('yt-topic').value;
  var chapter = document.getElementById('yt-chapter').value;
  var out = document.getElementById('yt-output');
  out.innerHTML = '<p style="color:#888;"><em>Searching YouTube...</em></p>';
  try {
    var r = await fetch('/api/ai/youtube?topic=' + encodeURIComponent(topic) + '&chapter=' + encodeURIComponent(chapter));
    var data = await r.json();
    var html = '';
    if (data.videos && data.videos.length > 0) {
      for (var v of data.videos) {
        if (v.videoId) {
          html += '<div class="video-container" style="position:relative;padding-bottom:56.25%;height:0;overflow:hidden;max-width:100%;background:#000;border-radius:8px;margin:0.5rem 0;"><iframe src="https://www.youtube.com/embed/' + v.videoId + '?rel=0" style="position:absolute;top:0;left:0;width:100%;height:100%;border:0;" allowfullscreen loading="lazy" title="' + v.title.replace(/'/g,"\\\\'") + '"></iframe></div>';
          html += '<p style="font-size:0.85rem;"><strong>' + v.title + '</strong> · ' + v.channel + '</p>';
        } else {
          html += '<p><a href="' + v.searchUrl + '" target="_blank" rel="noopener">📺 Search YouTube for "' + topic + '" →</a></p>';
        }
      }
    } else {
      html = '<p>No videos found. Try a different topic.</p>';
    }
    out.innerHTML = html;
  } catch(e) {
    out.innerHTML = '<p style="color:#c62828;">Search failed. YouTube API key may not be configured.</p>';
  }
}
</script>"""
        body = render_template("base.html", title="YouTube Videos - Class X", body_class="", extra_css="", content=content, board_name="")
        self._send_html(body)

    # ─── AI API Handlers (Google Only) ─────────────────────────────────────

    def _api_ai_research(self, query):
        q = query.get("query", [""])[0]
        subject = query.get("subject", [""])[0]
        result = ai_services.llm_research(q, subject)
        self._send_json(result)

    def _api_ai_literature(self, query):
        q = query.get("query", [""])[0]
        subject = query.get("subject", [""])[0]
        result = ai_services.llm_literature(q, subject)
        self._send_json(result)

    def _api_ai_visualize(self, query):
        concept = query.get("concept", [""])[0]
        style = query.get("style", ["diagram"])[0]
        result = ai_services.svg_visualize(concept, style)
        self._send_json(result)

    def _api_ai_pedagogical(self, query):
        subject = query.get("subject", [""])[0]
        chapter = query.get("chapter", [""])[0]
        topic = query.get("topic", [""])[0]
        result = ai_services.notebooklm_pedagogical(subject, chapter, topic)
        self._send_json(result)

    def _api_ai_youtube(self, query):
        topic = query.get("topic", [""])[0]
        chapter = query.get("chapter", [""])[0]
        search_query = f"{topic} {chapter}" if chapter else topic
        results = ai_services.youtube_search(search_query, max_results=5)
        self._send_json({"videos": results, "query": search_query})

    def _api_pillars(self):
        conn = get_conn()
        pillars = conn.execute("SELECT * FROM content_pillars ORDER BY sort_order").fetchall()
        self._send_json([dict(p) for p in pillars])

    def _api_pillar_content(self, pillar_id):
        content = get_pillar_content(pillar_id)
        self._send_json(content)

    def _serve_concept_detail(self, concept_id):
        if not concept_id:
            self._serve_error_page("Concept not specified")
            return
        concept = get_concept(concept_id)
        if not concept:
            self._serve_error_page("Concept not found")
            return
        mastery = concept.get("mastery", {})
        pct = int(mastery.get("mastery_level", 0) * 100)
        children_html = ""
        if concept.get("children"):
            children_html = '<h3 style="margin-top:1.5rem;">Sub-concepts</h3><div class="topic-nav">' + " ".join(
                f'<a href="/knowledge-graph/concept/{c["id"]}" class="topic-chip">{c["concept_name"]}</a>'
                for c in concept["children"]
            ) + "</div>"
        html = f"""<div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> <a href="/learn">Learning Hub</a> <span class="sep">›</span> <a href="/knowledge-graph">Knowledge Graph</a> <span class="sep">›</span> {concept['concept_name']}</div>
        <div class="section">
            <h2>{concept['concept_name']}</h2>
            <p style="color:#666;">{concept.get('description', '')}</p>
            <div class="info-card" style="margin-top:1rem;">
                <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.5rem;">
                    <span>Mastery: <strong>{pct}%</strong></span>
                    <span>Difficulty: {"⭐" * concept["difficulty"]}</span>
                    <span>Attempts: {mastery.get("attempts", 0)}</span>
                    <span>Streak: {mastery.get("streak", 0)} correct</span>
                </div>
                <div class="progress-bar-bg" style="margin-top:0.5rem;"><div class="progress-bar" style="width:{pct}%;background:{"var(--accent)" if pct > 50 else "#e94560"};"></div></div>
            </div>
            {children_html}
        </div>"""
        body = render_template("base.html", title=f"{concept['concept_name']} - Concept Detail", body_class="", extra_css="", content=html, board_name="")
        self._send_html(body)

    def _serve_competitive_hub(self):
        tracks = [
            {"id": "jee-main", "name": "JEE Main Foundation", "icon": "⚡", "desc": "Physics, Chemistry, Mathematics basics for JEE Main", "topics": 60},
            {"id": "neet", "name": "NEET Foundation", "icon": "🧬", "desc": "Biology, Chemistry, Physics for NEET", "topics": 50},
            {"id": "ntse", "name": "NTSE Preparation", "icon": "🔬", "desc": "Mental Ability, SAT, MAT for NTSE", "topics": 40},
            {"id": "imo", "name": "IMO (Math Olympiad)", "icon": "🏆", "desc": "Advanced problem-solving for International Math Olympiad", "topics": 35},
            {"id": "nso", "name": "NSO (Science Olympiad)", "icon": "🔭", "desc": "Advanced science for National Science Olympiad", "topics": 35}
        ]
        cards = ''.join(
            f'<div class="subject-card" onclick="location.href=\'/competitive/{t["id"]}\'">'
            f'<div class="subject-icon">{t["icon"]}</div>'
            f'<h3>{t["name"]}</h3>'
            f'<p>{t["desc"]}</p>'
            f'<span class="ch-count">{t["topics"]} modules</span></div>'
            for t in tracks
        )
        html = f"""<div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> Competitive Exams</div>
<div class="section"><h2>🎯 Competitive Exam Foundation</h2>
<p style="color:#666;margin-bottom:1.5rem;">Auto-unlock advanced tracks as you master board concepts. Build foundation for JEE, NEET, NTSE & Olympiads.</p>
<div class="subject-grid">{cards}</div></div>"""
        body = render_template("base.html", title="Competitive Exams - Class X", body_class="", extra_css="", content=html, board_name="")
        self._send_html(body)

    def _serve_competitive_track(self, track):
        tracks = {
            "jee-main": {"name": "JEE Main Foundation", "subjects": [
                {"name": "Physics", "topics": ["Laws of Motion", "Work, Energy & Power", "Rotational Motion", "Gravitation", "Thermodynamics", "Electrostatics", "Current Electricity", "Magnetism", "Optics", "Modern Physics"]},
                {"name": "Chemistry", "topics": ["Atomic Structure", "Chemical Bonding", "Thermodynamics", "Equilibrium", "Redox Reactions", "Organic Chemistry Basics", "Hydrocarbons", "Solutions", "Electrochemistry", "Chemical Kinetics"]},
                {"name": "Mathematics", "topics": ["Sets & Relations", "Complex Numbers", "Quadratic Equations", "Sequence & Series", "Trigonometry", "Coordinate Geometry", "Calculus Basics", "Vectors & 3D", "Probability", "Statistics"]}
            ]},
            "neet": {"name": "NEET Foundation", "subjects": [
                {"name": "Biology", "topics": ["Cell Biology", "Genetics", "Evolution", "Plant Physiology", "Human Physiology", "Biotechnology", "Ecology", "Diversity in Living World", "Human Reproduction", "Health & Disease"]},
                {"name": "Chemistry", "topics": ["Atomic Structure", "Chemical Bonding", "Thermodynamics", "Equilibrium", "Organic Chemistry", "Biomolecules", "Solutions", "Electrochemistry", "Coordination Compounds", "Environmental Chemistry"]},
                {"name": "Physics", "topics": ["Mechanics", "Thermodynamics", "Optics", "Waves & Sound", "Electrostatics", "Current Electricity", "Magnetism", "Modern Physics", "Semiconductors", "Measurement"]}
            ]},
            "ntse": {"name": "NTSE Preparation", "subjects": [
                {"name": "Mental Ability", "topics": ["Verbal Reasoning", "Non-Verbal Reasoning", "Analogy", "Classification", "Coding-Decoding", "Blood Relations", "Direction Sense", "Puzzles", "Data Interpretation", "Logical Venn Diagrams"]},
                {"name": "SAT (Social Studies)", "topics": ["Indian History", "Geography", "Polity", "Economics", "Culture", "Environment"]},
                {"name": "MAT (Math)", "topics": ["Number Systems", "Algebra", "Geometry", "Mensuration", "Data Analysis", "Arithmetic"]}
            ]},
            "imo": {"name": "IMO (Math Olympiad)", "subjects": [
                {"name": "Advanced Mathematics", "topics": ["Number Theory", "Combinatorics", "Inequalities", "Functional Equations", "Polynomials", "Geometry", "Trigonometry", "Algebraic Structures", "Probability", "Game Theory"]}
            ]},
            "nso": {"name": "NSO (Science Olympiad)", "subjects": [
                {"name": "Advanced Science", "topics": ["Physics: Mechanics & Energy", "Chemistry: Reactions & Bonding", "Biology: Cells & Genetics", "Astronomy Basics", "Scientific Reasoning", "Experimental Design", "Data Analysis", "Earth Science", "Environmental Science", "Logic & Reasoning"]}
            ]}
        }
        t = tracks.get(track)
        if not t:
            self._serve_error_page("Track not found"); return
        subs = ''.join(
            f'<div class="chunk-view"><div class="chunk-title">{s["name"]}</div>'
            f'<div class="topic-nav">{" ".join(f"<a>{tp}</a>" for tp in s["topics"])}</div></div>'
            for s in t["subjects"]
        )
        html = f"""<div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> <a href="/competitive">Competitive Exams</a> <span class="sep">›</span> {t['name']}</div>
<div class="section"><h2>{t['name']}</h2>
<p style="color:#666;margin-bottom:1.5rem;">Master these topics to build a strong foundation. Each concept links back to your CBSE syllabus.</p>
{subs}
<div style="margin-top:2rem;padding:1rem;background:#f0fdf4;border-radius:12px;border:1px solid #bbf7d0;">
<p style="color:#166534;"><strong>🔗 Connected to Your Board:</strong> These topics build on concepts you're already studying in CBSE Class X. Master your board syllabus first, then advance here.</p>
</div></div>"""
        body = render_template("base.html", title=f"{t['name']} - Class X", body_class="", extra_css="", content=html, board_name="")
        self._send_html(body)

    def _serve_electives_hub(self):
        electives = [
            {"id": "vedic-maths", "name": "Vedic Mathematics", "icon": "🧮", "desc": "16 sutras for lightning-fast mental calculations", "modules": 12},
            {"id": "mental-maths", "name": "Mental Maths", "icon": "🧠", "desc": "Train your brain to solve problems without pen & paper", "modules": 10},
            {"id": "python-basics", "name": "Python Programming", "icon": "🐍", "desc": "Learn coding from scratch with Python", "modules": 15},
        ]
        cards = ''.join(
            f'<div class="subject-card" onclick="location.href=\'/electives/{e["id"]}\'">'
            f'<div class="subject-icon">{e["icon"]}</div><h3>{e["name"]}</h3>'
            f'<p>{e["desc"]}</p><span class="ch-count">{e["modules"]} modules</span></div>'
            for e in electives
        )
        html = f"""<div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> Skill Electives</div>
<div class="section"><h2>🌟 Skill-Building Electives</h2>
<p style="color:#666;margin-bottom:1.5rem;">Go beyond the syllabus. These electives sharpen your analytical skills and give you a competitive edge.</p>
<div class="subject-grid">{cards}</div></div>"""
        body = render_template("base.html", title="Skill Electives - Class X", body_class="", extra_css="", content=html, board_name="")
        self._send_html(body)

    def _serve_elective(self, elective):
        electives = {
            "vedic-maths": {"name": "Vedic Mathematics", "icon": "🧮", "modules": [
                {"title": "Ekadhikena Purvena", "desc": "By one more than the previous one — squaring numbers ending in 5"},
                {"title": "Nikhilam Navatashcaramam Dashatah", "desc": "All from 9 and last from 10 — subtraction from base"},
                {"title": "Urdhva Tiryagbhyam", "desc": "Vertically and crosswise — multiplication"},
                {"title": "Paravartya Yojayet", "desc": "Transpose and apply — division"},
                {"title": "Shunyam Saamyasamuccaye", "desc": "When the sum is the same — solving equations"},
                {"title": "Anurupye Shunyamanyat", "desc": "If one is in ratio, the other is zero"},
                {"title": "Sankalana-Vyavakalanabhyam", "desc": "By addition and by subtraction"},
                {"title": "Puranapuranabhyam", "desc": "By completion or non-completion"},
                {"title": "Calana-Kalanabhyam", "desc": "Sequential motion — differential calculus"},
                {"title": "Yavadunam", "desc": "Whatever the deficiency — cubing"},
                {"title": "Vyashtisamanshtih", "desc": "Part and whole"},
                {"title": "Sesanyankena Caramena", "desc": "Remainder by the last digit"}
            ]},
            "mental-maths": {"name": "Mental Maths", "icon": "🧠", "modules": [
                {"title": "Quick Addition", "desc": "Add numbers faster by grouping and complements"},
                {"title": "Rapid Subtraction", "desc": "Subtract using base methods"},
                {"title": "Times Table Mastery", "desc": "Memorize up to 99×99 with patterns"},
                {"title": "Division Shortcuts", "desc": "Divide quickly using factors"},
                {"title": "Percentage Tricks", "desc": "Calculate percentages mentally"},
                {"title": "Square Roots", "desc": "Estimate square roots instantly"},
                {"title": "Cube Roots", "desc": "Find cube roots mentally"},
                {"title": "Fraction to Decimal", "desc": "Convert fractions to decimals instantly"},
                {"title": "Estimation Skills", "desc": "Rapid approximation for real-world problems"},
                {"title": "Speed Drills", "desc": "Timed practice sets"}
            ]},
            "python-basics": {"name": "Python Programming", "icon": "🐍", "modules": [
                {"title": "Hello, World!", "desc": "Your first Python program — printing and comments"},
                {"title": "Variables & Data Types", "desc": "Numbers, strings, booleans, and type conversion"},
                {"title": "Lists & Tuples", "desc": "Working with collections of data"},
                {"title": "Dictionaries & Sets", "desc": "Key-value stores and unique collections"},
                {"title": "Conditionals", "desc": "if, elif, else — making decisions in code"},
                {"title": "Loops", "desc": "for and while loops — repeating tasks"},
                {"title": "Functions", "desc": "Writing reusable code blocks"},
                {"title": "Strings & Methods", "desc": "String manipulation and formatting"},
                {"title": "File I/O", "desc": "Reading and writing files"},
                {"title": "Error Handling", "desc": "try, except, finally — handling errors gracefully"},
                {"title": "Modules & Libraries", "desc": "Importing and using Python modules"},
                {"title": "Mini Project: Calculator", "desc": "Build a command-line calculator"},
                {"title": "Mini Project: Quiz Game", "desc": "Build an interactive quiz"},
                {"title": "Mini Project: To-Do List", "desc": "Build a task manager"},
                {"title": "What's Next?", "desc": "Roadmap to web dev, data science, and AI with Python"}
            ]}
        }
        e = electives.get(elective)
        if not e:
            self._serve_error_page("Elective not found"); return
        mods = ''.join(
            f'<div class="chunk-view"><div class="chunk-title">{m["title"]}</div>'
            f'<p style="font-size:0.85rem;color:#555;">{m["desc"]}</p></div>'
            for i, m in enumerate(e["modules"])
        )
        html = f"""<div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> <a href="/electives">Electives</a> <span class="sep">›</span> {e['name']}</div>
<div class="section"><h2>{e['icon']} {e['name']}</h2>
<p style="color:#666;margin-bottom:1rem;">{len(e['modules'])} modules to build your skills.</p>
<div class="subject-grid" style="grid-template-columns:1fr;">{mods}</div></div>"""
        body = render_template("base.html", title=f"{e['name']} - Class X", body_class="", extra_css="", content=html, board_name="")
        self._send_html(body)

    def _serve_home(self):
        conn = get_conn()
        total_chapters = conn.execute("SELECT COUNT(*) FROM chapters").fetchone()[0]
        total_topics = conn.execute("SELECT COUNT(*) FROM topics").fetchone()[0]
        board_html = ""
        for bid, board in ALL_BOARDS.items():
            cards = "".join(build_subject_card(s, bid) for s in board["subjects"])
            badge_class = {"cbse": "cbse", "ap": "ap", "ts": "ts"}.get(bid, "cbse")
            board_html += f"""
            <div class="section board-section-container" data-board="{bid}">
                <div class="section-header">
                    <span class="board-badge {badge_class}">{board["name"]}</span>
                </div>
                <p class="subtitle">{board["description"]}</p>
                <div class="subjects-grid">{cards}</div>
            </div>"""

        filter_panel = """
        <!-- Filter Controls -->
        <div class="filter-panel" style="background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; margin-top: 1.5rem; margin-bottom: 1.5rem; box-shadow: var(--shadow); display: flex; flex-wrap: wrap; gap: 1.5rem; align-items: center;">
            <div style="flex: 1; min-width: 200px;">
                <label for="filter-board" style="display: block; font-size: 0.85rem; font-weight: bold; color: var(--text-muted); margin-bottom: 0.5rem;">Filter by Board</label>
                <select id="filter-board" onchange="filterHomeContent()" style="width: 100%; padding: 0.6rem; border: 1px solid var(--border); border-radius: 8px; background: var(--bg); color: var(--text); font-size: 0.95rem; cursor: pointer; outline: none;">
                    <option value="">All Boards</option>
                    <option value="cbse">CBSE Board</option>
                    <option value="ap">AP Board (Andhra Pradesh)</option>
                    <option value="ts">TS Board (Telangana)</option>
                </select>
            </div>
            <div style="flex: 1; min-width: 200px;">
                <label for="filter-subject" style="display: block; font-size: 0.85rem; font-weight: bold; color: var(--text-muted); margin-bottom: 0.5rem;">Filter by Subject</label>
                <select id="filter-subject" onchange="filterHomeContent()" style="width: 100%; padding: 0.6rem; border: 1px solid var(--border); border-radius: 8px; background: var(--bg); color: var(--text); font-size: 0.95rem; cursor: pointer; outline: none;">
                    <option value="">All Subjects</option>
                    <option value="mathematics">Mathematics</option>
                    <option value="science">Science / Physical & Biological</option>
                    <option value="social">Social Sciences / Studies</option>
                    <option value="languages">Languages (English, Hindi, Sanskrit, French)</option>
                    <option value="electives">Skill Electives (AI, IT)</option>
                </select>
            </div>
            <div style="flex: 1; min-width: 200px;">
                <label for="filter-medium" style="display: block; font-size: 0.85rem; font-weight: bold; color: var(--text-muted); margin-bottom: 0.5rem;">Medium of Instruction</label>
                <select id="filter-medium" onchange="filterHomeContent()" style="width: 100%; padding: 0.6rem; border: 1px solid var(--border); border-radius: 8px; background: var(--bg); color: var(--text); font-size: 0.95rem; cursor: pointer; outline: none;">
                    <option value="">All Mediums</option>
                    <option value="english">English Medium</option>
                    <option value="hindi">Hindi Medium</option>
                    <option value="sanskrit">Sanskrit Medium</option>
                </select>
            </div>
        </div>

        <script>
        function filterHomeContent() {
            const boardVal = document.getElementById('filter-board').value;
            const subjectVal = document.getElementById('filter-subject').value;
            const mediumVal = document.getElementById('filter-medium').value;

            const sections = document.querySelectorAll('.board-section-container');

            sections.forEach(section => {
                const sectBoard = section.getAttribute('data-board');
                let hasVisibleCards = false;

                const cards = section.querySelectorAll('.subject-card');
                cards.forEach(card => {
                    const cardBoard = card.getAttribute('data-board');
                    const cardSubj = card.getAttribute('data-subject-type');
                    const cardMedium = card.getAttribute('data-medium');

                    const matchBoard = !boardVal || cardBoard === boardVal;
                    const matchSubj = !subjectVal || cardSubj === subjectVal;
                    const matchMedium = !mediumVal || cardMedium === mediumVal;

                    if (matchBoard && matchSubj && matchMedium) {
                        card.style.display = 'block';
                        hasVisibleCards = true;
                    } else {
                        card.style.display = 'none';
                    }
                });

                const matchSectionBoard = !boardVal || sectBoard === boardVal;
                if (matchSectionBoard && hasVisibleCards) {
                    section.style.display = 'block';
                } else {
                    section.style.display = 'none';
                }
            });
        }
        </script>
        """

        content = f"""
        <div class="hero">
            <div class="hero-icon">📚</div>
            <h2>Class X Complete Education</h2>
            <p>Free, offline-capable study platform covering CBSE, Andhra Pradesh &amp; Telangana boards. AI-powered explanations, full-text search across {total_chapters} chapters &amp; {total_topics} topics.</p>
            <div class="board-tags" style="margin-top:1.5rem;">
                <span>CBSE</span>
                <span>Andhra Pradesh</span>
                <span>Telangana</span>
                <span>NCERT &amp; SCERT</span>
            </div>
        </div>
        {filter_panel}
        {board_html}"""
        html = render_template("base.html", title="Class X Education Platform",
                               body_class="", extra_css="",
                               content=content, board_name="All Boards")
        self._send_html(html)

    def _serve_board(self, board_id):
        board = ALL_BOARDS.get(board_id)
        if not board:
            self._serve_error_page("Board not found")
            return
        cards = "".join(build_subject_card(s, board_id) for s in board["subjects"])
        badge_class = {"cbse": "cbse", "ap": "ap", "ts": "ts"}.get(board_id, "cbse")
        content = f"""
        <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> <span class="board-badge {badge_class}">{board["name"]}</span></div>
        <p style="color:#666;margin-bottom:1.5rem;">{board["description"]}</p>
        <div class="subjects-grid">{cards}</div>"""
        html = render_template("base.html", title=board["name"],
                               body_class="", extra_css="", content=content,
                               board_name=board["name"])
        self._send_html(html)

    def _serve_subject(self, board_id, subject_id_raw):
        conn = get_conn()
        subject = conn.execute(
            "SELECT * FROM subjects WHERE id = ? AND board_id = ?",
            (subject_id_raw, board_id)
        ).fetchone()
        if not subject:
            # Fallback slug name/substring search matching server.py lookup behavior
            slug_name = subject_id_raw.replace("-", " ").lower()
            subject = conn.execute(
                "SELECT * FROM subjects WHERE board_id = ? AND LOWER(name) = ?",
                (board_id, slug_name)
            ).fetchone()
            if not subject:
                subject = conn.execute(
                    "SELECT * FROM subjects WHERE board_id = ? AND LOWER(name) LIKE ?",
                    (board_id, f"%{slug_name}%")
                ).fetchone()
        if not subject:
            self._serve_error_page(f"Subject '{subject_id_raw}' not found for board '{board_id}'")
            return
        subject = dict(subject)

        books = conn.execute(
            "SELECT * FROM books WHERE subject_id = ? ORDER BY name", (subject["id"],)
        ).fetchall()

        content_parts = [f"""
        <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> <a href="/board/{board_id}">Board</a> <span class="sep">›</span> {subject["name"]}</div>
        <div class="section"><h2>{subject["name"]}</h2>
        <p style="color:#666;margin-bottom:1.5rem;">{subject["description"]}</p>"""]

        if books:
            for book_row in books:
                book = dict(book_row)
                chapters = conn.execute(
                    "SELECT * FROM chapters WHERE book_id = ? ORDER BY num",
                    (book["id"],)
                ).fetchall()
                if not chapters:
                    continue
                ch_lis = []
                for ch in chapters:
                    topics = conn.execute(
                        "SELECT * FROM topics WHERE chapter_id = ? ORDER BY num",
                        (ch["id"],)
                    ).fetchall()
                    topics_html = ""
                    if topics:
                        tags = "".join(
                            f'<span class="topic-tag" onclick="event.stopPropagation();location.href=\'/topic/{t["id"]}\'">{t["title"]}</span>'
                            for t in topics
                        )
                        topics_html = f'<div class="topics">{tags}</div>'
                    ch_lis.append(
                        f'<li onclick="location.href=\'/chapter/{ch["id"]}\'">'
                        f'<span class="ch-num">Ch {ch["num"]}.</span> '
                        f'<span class="ch-title">{ch["title"]}</span>{topics_html}</li>'
                    )
                book_ncert = book.get("ncert_url") or ""
                book_ncert_link = f'<a class="ncert-link" href="{book_ncert}" target="_blank">View on NCERT Website →</a>' if book_ncert else ""
                content_parts.append(f"""
                <div class="book-section">
                    <h3>{book["name"]}</h3>
                    <ul class="chapter-list">{"".join(ch_lis)}</ul>
                    {book_ncert_link}
                </div>""")
        else:
            chapters = conn.execute(
                "SELECT * FROM chapters WHERE subject_id = ? AND book_id IS NULL ORDER BY num",
                (subject["id"],)
            ).fetchall()
            if chapters:
                ch_lis = []
                for ch in chapters:
                    topics = conn.execute(
                        "SELECT * FROM topics WHERE chapter_id = ? ORDER BY num",
                        (ch["id"],)
                    ).fetchall()
                    topics_html = ""
                    if topics:
                        tags = "".join(
                            f'<span class="topic-tag" onclick="event.stopPropagation();location.href=\'/topic/{t["id"]}\'">{t["title"]}</span>'
                            for t in topics
                        )
                        topics_html = f'<div class="topics">{tags}</div>'
                    ch_lis.append(
                        f'<li onclick="location.href=\'/chapter/{ch["id"]}\'">'
                        f'<span class="ch-num">Ch {ch["num"]}.</span> '
                        f'<span class="ch-title">{ch["title"]}</span>{topics_html}</li>'
                    )
                ncert_url = subject.get("ncert_url") or ""
                ncert_link = f'<a class="ncert-link" href="{ncert_url}" target="_blank">View Full Textbook →</a>' if ncert_url else ""
                content_parts.append(f"""
                <ul class="chapter-list">{"".join(ch_lis)}</ul>
                {ncert_link}""")

        content_parts.append("</div>")

        html = render_template("base.html", title=f"{subject['name']} - Class X",
                               body_class="", extra_css="",
                               content="".join(content_parts),
                               board_name=board_id.upper())
        self._send_html(html)

    def _serve_chapter(self, chapter_id):
        conn = get_conn()
        chapter = conn.execute("SELECT * FROM chapters WHERE id = ?", (chapter_id,)).fetchone()
        if not chapter:
            self._serve_error_page("Chapter not found")
            return

        subject = conn.execute("SELECT * FROM subjects WHERE id = ?", (chapter["subject_id"],)).fetchone()
        topics = conn.execute("SELECT * FROM topics WHERE chapter_id = ? ORDER BY num", (chapter_id,)).fetchall()

        topic_sections = []
        for topic in topics:
            chunks = conn.execute(
                "SELECT * FROM chunks WHERE topic_id = ? ORDER BY seq", (topic["id"],)
            ).fetchall()
            problems = conn.execute(
                "SELECT * FROM problems WHERE topic_id = ? ORDER BY seq", (topic["id"],)
            ).fetchall()

            chunks_html = ""
            for c in chunks:
                fmt = format_content(c['content'])
                chunks_html += f"""
                <div class="chunk-view">
                    <span class="chunk-type-badge {c['content_type']}">{c['content_type']}</span>
                    <div class="chunk-title">{c['title'] or topic['title']}</div>
                    <div class="chunk-content">{fmt}</div>
                </div>"""

            problems_html = ""
            if problems:
                problems_html = '<h4 style="margin:1rem 0 0.5rem;color:#c62828;">Practice Problems</h4>'
                for p in problems:
                    pfmt = format_content(p['problem_text'])
                    sfmt = format_content(p['solution_text']) if p['solution_text'] else ''
                    problems_html += f"""
                    <div class="chunk-view" style="border-left-color:#e94560;">
                        <div class="chunk-title">Problem {p['seq'] + 1}</div>
                        <div class="chunk-content">{pfmt}</div>
                        {f'<details style="margin-top:0.5rem;"><summary style="cursor:pointer;color:#0f3460;font-weight:500;">Show Solution</summary><div class="chunk-content" style="margin-top:0.5rem;padding:0.8rem;background:#f8f9ff;border-radius:8px;">{sfmt}</div></details>' if p["solution_text"] else ''}
                    </div>"""

            topic_sections.append(f"""
            <div class="book-section" id="topic-{topic['id']}">
                <h3 style="cursor:pointer;" onclick="location.href='/topic/{topic['id']}'">{topic['num']}. {topic['title']}</h3>
                {chunks_html}
                {problems_html}
                <div id="ai-enrich-{topic['id']}" style="display:none;"></div>
                <div id="ai-enrich-{topic['id']}" style="display:none;"></div>
                <button class="tts-btn" onclick="loadAI('{topic['id']}','{esc_js(topic['title'])}','{esc_js(chapter['title'])}','{esc_js(subject['name'] if subject else '')}')" style="margin-top:0.5rem;font-size:0.85rem;">✨ AI Enhance</button>
                <div style="margin-top:0.5rem;">
                    <a class="ncert-link" style="font-size:0.8rem;padding:0.3rem 0.8rem;" href="/topic/{topic['id']}">View Full Topic →</a>
                </div>
            </div>""")

        board_id = chapter["board_id"]
        board_name = {"cbse": "CBSE", "ap": "AP Board", "ts": "TS Board"}.get(board_id, board_id.upper())
        subject_name = subject["name"] if subject else ""
        content = f"""
        <div class="breadcrumb">
            <a href="/">Home</a> <span class="sep">›</span> <a href="/board/{board_id}">{board_name}</a>
            <span class="sep">›</span> <a href="/board/{board_id}/{chapter['subject_id']}">{subject_name}</a>
            <span class="sep">›</span> Ch {chapter["num"]} - {chapter["title"]}
        </div>
        <div class="section">
            <h2>Chapter {chapter["num"]}: {chapter["title"]}</h2>
            <div class="chapter-actions">
                <button class="tts-btn" onclick="playTTS(document.querySelector('.section h2')?.innerText || '{esc_js(chapter['title'])}','en-IN')">🔊 Listen</button>
                <button class="tts-btn" onclick="recordStudy('{chapter_id}', null)">✅ Mark Studying</button>
                <a class="tts-btn" href="/notes/{chapter_id}" style="text-decoration:none;">📖 Notes</a>
                <a class="tts-btn" href="/revision/{chapter_id}" style="text-decoration:none;">⚡ Revision</a>
            </div>
            <div class="topic-nav">
                {"".join(f'<a href="#topic-{t["id"]}">{t["num"]}. {t["title"]}</a>' for t in topics)}
            </div>
            {"".join(topic_sections)}
            <div class="video-section" id="chapter-videos"></div>
            <div class="opengrok-section" id="chapter-formulas"></div>
        </div>"""

        content += """
<script>
function loadChapterVideos() {
    var v = document.getElementById('chapter-videos');
    if (v && !v.hasChildNodes()) {
        fetch('/api/ai/youtube?topic=' + encodeURIComponent('""" + esc_js(chapter['title']) + """') + '&chapter=' + encodeURIComponent('""" + esc_js(subject_name) + """'))
            .then(function(r){return r.json()})
            .then(function(d){
                if (d.videos && d.videos.length > 0) {
                    var html = '<h4 style="display:flex;align-items:center;gap:0.4rem;margin:1rem 0 0.5rem;color:var(--primary);">\\u25b6\\ufe0f Video Lessons</h4><div class="video-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:0.5rem;">';
                    for (var vi of d.videos) {
                        if (vi.videoId) {
                            html += '<div class="video-card" style="background:var(--card-bg);border-radius:8px;overflow:hidden;border:1px solid var(--border);cursor:pointer;" onclick="document.getElementById(\\'vid-'+vi.videoId+'\\').scrollIntoView({behavior:\\'smooth\\'})"><div style="padding:0.5rem 0.75rem;"><div style="font-size:0.78rem;font-weight:600;color:var(--primary);line-height:1.3;">'+vi.title.slice(0,80)+'</div><div style="font-size:0.72rem;color:var(--text-muted);">'+vi.channel+'</div></div></div>';
                        }
                    }
                    html += '</div>';
                    for (var vi of d.videos) {
                        if (vi.videoId) {
                            html += '<div id="vid-'+vi.videoId+'" class="video-container" style="position:relative;padding-bottom:56.25%;height:0;overflow:hidden;max-width:100%;background:#000;border-radius:8px;margin:0.5rem 0;"><iframe src="https://www.youtube.com/embed/'+vi.videoId+'?rel=0" style="position:absolute;top:0;left:0;width:100%;height:100%;border:0;" allowfullscreen loading="lazy"></iframe></div>';
                        }
                    }
                    html += '<p style="font-size:0.72rem;color:var(--text-muted);">Powered by Google YouTube Data API v3</p>';
                    v.innerHTML = html;
                }
            });
        fetch('/api/ai/opengrok?query=' + encodeURIComponent('""" + esc_js(chapter['title']) + """'))
            .then(function(r){return r.json()})
            .then(function(d){
                var f = document.getElementById('chapter-formulas');
                if (d.results && d.results.length > 0 && f) {
                    var html = '<h4 style="display:flex;align-items:center;gap:0.4rem;margin:1rem 0 0.5rem;color:var(--primary);">\\ud83d\\udcd0 Formulas & Theorems</h4>';
                    for (var res of d.results) {
                        html += '<div class="og-result" style="background:var(--card-bg);border-radius:8px;padding:0.6rem 0.8rem;border:1px solid var(--border);margin-bottom:0.4rem;"><div style="font-size:0.88rem;font-weight:600;color:var(--primary);font-family:\\'Courier New\\',monospace;">'+res.title+'</div>';
                        if (res.category) html += '<div style="font-size:0.72rem;color:var(--text-muted);margin-top:0.2rem;"><span style="background:#eef2ff;padding:0.05rem 0.4rem;border-radius:4px;">'+res.category+'</span></div>';
                        html += '</div>';
                    }
                    f.innerHTML = html;
                }
            });
    }
}
document.addEventListener('DOMContentLoaded', loadChapterVideos);
function loadAI(topicId, topicTitle, chapterTitle, subjectName) {
    var container = document.getElementById('ai-enrich-' + topicId);
    if (container.style.display !== 'none' && container.innerHTML.trim() !== '') return;
    container.style.display = 'block';
    container.innerHTML = '<p style="color:#888;"><em>Loading AI content...</em></p>';
    var btn = container.parentElement.querySelector('.tts-btn');
    if (btn) btn.disabled = true;
    fetch('/api/ai/enrich?topic=' + encodeURIComponent(topicTitle) + '&chapter=' + encodeURIComponent(chapterTitle) + '&subject=' + encodeURIComponent(subjectName))
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.html) container.innerHTML = '<div class="ai-section" style="border-left-color:#e67e22;"><h3>✨ AI-Enhanced Content</h3>' + data.html + '</div>';
            else container.innerHTML = '<div class="ai-section"><p style="color:#888;">AI content not available.</p></div>';
        })
        .catch(function() { container.innerHTML = '<div class="ai-section"><p style="color:#888;">Could not load AI content.</p></div>'; });
}
</script>"""
        html = render_template("base.html", title=f"Ch {chapter['num']}: {chapter['title']} - Class X",
                               body_class="", extra_css="", content=content,
                               board_name=board_name)
        self._send_html(html)

    def _serve_chapter_notes(self, chapter_id):
        conn = get_conn()
        chapter = conn.execute("SELECT * FROM chapters WHERE id = ?", (chapter_id,)).fetchone()
        if not chapter:
            self._serve_error_page("Chapter not found")
            return
        subject = conn.execute("SELECT * FROM subjects WHERE id = ?", (chapter["subject_id"],)).fetchone()
        topics = conn.execute("SELECT * FROM topics WHERE chapter_id = ? ORDER BY num", (chapter_id,)).fetchall()
        board_name = {"cbse": "CBSE", "ap": "AP Board", "ts": "TS Board"}.get(chapter["board_id"], chapter["board_id"].upper())
        notes = ""
        for topic in topics:
            chunks = conn.execute("SELECT * FROM chunks WHERE topic_id = ? ORDER BY seq", (topic["id"],)).fetchall()
            problems = conn.execute("SELECT * FROM problems WHERE topic_id = ? ORDER BY seq", (topic["id"],)).fetchall()
            chunk_html = ""
            for c in chunks:
                fmt = format_content(c['content'])
                chunk_html += f"""<div class="chunk-view"><span class="chunk-type-badge {c['content_type']}">{c['content_type']}</span><div class="chunk-title">{c['title'] or topic['title']}</div><div class="chunk-content">{fmt}</div></div>"""
            prob_html = ""
            for p in problems:
                pfmt = format_content(p['problem_text'])
                sfmt = format_content(p['solution_text']) if p['solution_text'] else ''
                prob_html += f"""<div class="chunk-view" style="border-left-color:#e94560;"><div class="chunk-title">Problem {p['seq'] + 1}</div><div class="chunk-content">{pfmt}</div>{f'<details style="margin-top:0.5rem;"><summary style="cursor:pointer;color:#0f3460;font-weight:500;">Show Solution</summary><div class="chunk-content" style="margin-top:0.5rem;padding:0.8rem;background:#f8f9ff;border-radius:8px;">{sfmt}</div></details>' if p["solution_text"] else ''}</div>"""
            notes += f"""<div class="book-section" id="topic-{topic['id']}"><h3>{topic['num']}. {topic['title']}</h3>{chunk_html}{prob_html}</div>"""
        content = f"""
        <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> <a href="/board/{chapter['board_id']}">{board_name}</a> <span class="sep">›</span> <a href="/chapter/{chapter_id}">Ch {chapter['num']}: {chapter['title']}</a> <span class="sep">›</span> Chapter Notes</div>
        <div class="section">
            <h2>📖 Chapter Notes: {chapter['title']}</h2>
            <p class="subtitle">Comprehensive notes covering all topics — perfect for study and revision.</p>
            <div style="display:flex;gap:0.5rem;margin-bottom:1rem;flex-wrap:wrap;">
                <button class="tts-btn" onclick="window.print()">🖨️ Print Notes</button>
                <button class="notebooklm-btn" onclick="exportNotebookLM('{chapter_id}', null)">📥 Export</button>
            </div>
            <div class="topic-nav">{"".join(f'<a href="#topic-{t["id"]}">{t["num"]}. {t["title"]}</a>' for t in topics)}</div>
            {notes}
        </div>"""
        html = render_template("base.html", title=f"Notes: {chapter['title']} - Class X",
                               body_class="", extra_css="", content=content, board_name=board_name)
        self._send_html(html)

    def _serve_chapter_revision(self, chapter_id):
        conn = get_conn()
        chapter = conn.execute("SELECT * FROM chapters WHERE id = ?", (chapter_id,)).fetchone()
        if not chapter:
            self._serve_error_page("Chapter not found")
            return
        topics = conn.execute("SELECT * FROM topics WHERE chapter_id = ? ORDER BY num", (chapter_id,)).fetchall()
        board_name = {"cbse": "CBSE", "ap": "AP Board", "ts": "TS Board"}.get(chapter["board_id"], chapter["board_id"].upper())
        cards = ""
        for topic in topics:
            chunks = conn.execute(
                "SELECT * FROM chunks WHERE topic_id = ? AND content_type IN ('formula','definition','key_point','summary') ORDER BY seq",
                (topic["id"],)
            ).fetchall()
            if not chunks:
                chunks = conn.execute("SELECT * FROM chunks WHERE topic_id = ? ORDER BY seq LIMIT 3", (topic["id"],)).fetchall()
            if not chunks:
                continue
            chunk_html = ""
            for c in chunks:
                fmt = format_content(c['content'])
                badge_color = {'formula': '#e94560', 'definition': '#0f3460', 'key_point': '#f59e0b', 'summary': '#2ea043'}.get(c['content_type'], '#888')
                chunk_html += f"""<div style="padding:0.5rem;margin:0.3rem 0;border-left:3px solid {badge_color};background:#f8f9ff;border-radius:4px;font-size:0.85rem;"><strong>{c['title'] or c['content_type'].title()}</strong>: {fmt}</div>"""
            cards += f"""<div class="chunk-view" style="border-left-color:var(--accent);"><div class="chunk-title">⚡ {topic['title']}</div>{chunk_html}</div>"""
        content = f"""
        <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> <a href="/board/{chapter['board_id']}">{board_name}</a> <span class="sep">›</span> <a href="/chapter/{chapter_id}">Ch {chapter['num']}: {chapter['title']}</a> <span class="sep">›</span> Quick Revision</div>
        <div class="section">
            <h2>⚡ Quick Revision: {chapter['title']}</h2>
            <p class="subtitle">Formulas, definitions, and key points for last-minute revision.</p>
            <button class="tts-btn" onclick="window.print()" style="margin-bottom:1rem;">🖨️ Print Revision Cards</button>
            {cards or '<p style="color:#888;">No revision content available for this chapter.</p>'}
        </div>"""
        html = render_template("base.html", title=f"Revision: {chapter['title']} - Class X",
                               body_class="", extra_css="", content=content, board_name=board_name)
        self._send_html(html)

    def _serve_topic(self, topic_id):
        conn = get_conn()
        topic = conn.execute("SELECT * FROM topics WHERE id = ?", (topic_id,)).fetchone()
        if not topic:
            self._serve_error_page("Topic not found")
            return

        chapter = conn.execute("SELECT * FROM chapters WHERE id = ?", (topic["chapter_id"],)).fetchone()
        chunks = conn.execute("SELECT * FROM chunks WHERE topic_id = ? ORDER BY seq", (topic_id,)).fetchall()
        problems = conn.execute("SELECT * FROM problems WHERE topic_id = ? ORDER BY seq", (topic_id,)).fetchall()
        sibling_topics = conn.execute(
            "SELECT * FROM topics WHERE chapter_id = ? AND id != ? ORDER BY num",
            (topic["chapter_id"], topic_id)
        ).fetchall()

        subject = conn.execute("SELECT * FROM subjects WHERE id = ?", (chapter["subject_id"],)).fetchone()
        board_name = {"cbse": "CBSE", "ap": "AP Board", "ts": "TS Board"}.get(chapter["board_id"], chapter["board_id"].upper())

        chunks_html = ""
        for c in chunks:
            fmt = format_content(c['content'])
            chunks_html += f"""
            <div class="chunk-view">
                <span class="chunk-type-badge {c['content_type']}">{c['content_type']}</span>
                <div class="chunk-title">{c['title'] or topic['title']}</div>
                <div class="chunk-content">{fmt}</div>
            </div>"""

        problems_html = ""
        if problems:
            problems_html = '<h3 style="margin:1.5rem 0 0.5rem;color:#c62828;">Practice Problems</h3>'
            for p in problems:
                pfmt = format_content(p['problem_text'])
                sfmt = format_content(p['solution_text']) if p['solution_text'] else ''
                problems_html += f"""
                <div class="chunk-view" style="border-left-color:#e94560;">
                    <div class="chunk-title">Problem {p['seq'] + 1}</div>
                    <div class="chunk-content">{pfmt}</div>
                    {f'<details style="margin-top:0.5rem;"><summary style="cursor:pointer;color:#0f3460;font-weight:500;">Show Solution</summary><div class="chunk-content" style="margin-top:0.5rem;padding:0.8rem;background:#f8f9ff;border-radius:8px;">{sfmt}</div></details>' if p["solution_text"] else ''}
                </div>"""

        sibling_html = ""
        if sibling_topics:
            sibling_html = '<div style="margin-top:2rem;"><h3 style="color:#0f3460;margin-bottom:0.5rem;">Related Topics</h3><div class="topic-nav">' + \
                "".join(f'<a href="/topic/{t["id"]}">{t["title"]}</a>' for t in sibling_topics) + \
                '</div></div>'

        content = f"""
        <div class="breadcrumb">
            <a href="/">Home</a> <span class="sep">›</span> <a href="/board/{chapter['board_id']}">{board_name}</a>
            <span class="sep">›</span> <a href="/board/{chapter['board_id']}/{chapter['subject_id']}">Subject</a>
            <span class="sep">›</span> <a href="/chapter/{chapter['id']}">Ch {chapter['num']}: {chapter['title']}</a>
            <span class="sep">›</span> {topic['title']}
        </div>
        <div class="section">
            <h2>{topic['title']}</h2>
            <p style="color:#666;margin-bottom:1rem;">Chapter {chapter['num']}: {chapter['title']}</p>
            <div style="display:flex;gap:0.5rem;margin-bottom:1rem;flex-wrap:wrap;">
                <button class="tts-btn" onclick="recordStudy('{chapter['id']}','{topic_id}');playTTS(document.getElementById('topic-content-{topic_id}')?.innerText || '{topic['title']}','en-IN')">🔊 Listen</button>
                <button class="tts-btn" onclick="recordStudy('{chapter['id']}','{topic_id}')">✅ Mark Studying</button>
                <button class="tts-btn" onclick="location.href='/mindmap/{topic_id}'">🧠 Mind Map</button>
                <button class="tts-btn" onclick="location.href='/tutor/{topic_id}'">🧑‍🏫 AI Tutor</button>
                <button class="tts-btn" onclick="location.href='/interactives/{topic_id}'">🎮 Interactive</button>
                <button class="tts-btn" id="review-btn-{topic_id}" onclick="openReview('{topic_id}','{topic['title']}')">🔁 Review</button>
            </div>
            <div id="review-panel-{topic_id}" style="display:none;margin-bottom:1rem;padding:1rem;background:var(--card-bg);border-radius:var(--radius);border:1px solid var(--border);"></div>
            <div id="topic-content-{topic_id}">
            {chunks_html}
            {problems_html}
            <div id="ai-enrich-topic"></div>
            <button class="tts-btn" onclick="loadAI('topic','{topic['title']}','{chapter['title']}','{subject['name'] if subject else ''}')" style="margin-top:0.5rem;font-size:0.85rem;">✨ AI Enhance</button>
            </div>
            {sibling_html}
        </div>"""
        content += """
<script>
function loadAI(topicId, topicTitle, chapterTitle, subjectName) {
    var container = document.getElementById('ai-enrich-' + topicId);
    if (!container) container = document.getElementById('ai-enrich-topic');
    if (!container) return;
    if (container.style.display !== 'none' && container.innerHTML.trim() !== '') return;
    container.style.display = 'block';
    container.innerHTML = '<p style="color:#888;"><em>Loading AI content...</em></p>';
    fetch('/api/ai/enrich?topic=' + encodeURIComponent(topicTitle) + '&chapter=' + encodeURIComponent(chapterTitle) + '&subject=' + encodeURIComponent(subjectName))
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.html) container.innerHTML = '<div class="ai-section" style="border-left-color:#e67e22;"><h3>✨ AI-Enhanced Content</h3>' + data.html + '</div>';
            else container.innerHTML = '<div class="ai-section"><p style="color:#888;">AI content not available.</p></div>';
        })
        .catch(function() { container.innerHTML = '<div class="ai-section"><p style="color:#888;">Could not load AI content.</p></div>'; });
}
</script>"""
        content += f"""
        <script>
        function openReview(topicId, topicTitle) {{
            var panel = document.getElementById('review-panel-' + topicId);
            var btn = document.getElementById('review-btn-' + topicId);
            if (panel.style.display !== 'none') {{ panel.style.display = 'none'; btn.textContent = '🔁 Review'; return; }}
            panel.style.display = 'block';
            panel.innerHTML = '<p style="color:#888;">Loading...</p>';
            fetch('/api/review/due').then(r=>r.json()).then(function(data){{}});
            var randomQuestions = ['What is the main idea of ' + topicTitle + '?', 'Explain ' + topicTitle + ' in your own words.', 'What are the key terms in this topic?', 'How does ' + topicTitle + ' connect to what we already know?', 'Can you give an example of ' + topicTitle + '?'];
            var q = randomQuestions[Math.floor(Math.random() * randomQuestions.length)];
            panel.innerHTML = '<p style="font-weight:500;margin-bottom:0.5rem;">Quick Review: ' + topicTitle + '</p><p style="margin-bottom:0.5rem;">' + q + '</p><textarea id="review-answer" rows="3" style="width:100%;padding:0.5rem;border:1px solid var(--border);border-radius:6px;font-family:inherit;font-size:0.85rem;" placeholder="Write your answer..."></textarea><div style="margin-top:0.5rem;display:flex;gap:0.5rem;"><button class="tts-btn" onclick="submitReview('{topic_id}')">Submit</button><button class="tts-btn" onclick="document.getElementById(\\'review-panel-{topic_id}\\').style.display=\\'none\\';document.getElementById(\\'review-btn-{topic_id}\\').textContent=\\'🔁 Review\\';">Close</button></div>';
        }}
        function submitReview(topicId) {{
            var answer = document.getElementById('review-answer').value;
            if (!answer.trim()) return;
            fetch('/api/review/submit?topic_id=' + topicId + '&quality=3&answer=' + encodeURIComponent(answer)).then(function(){{ document.getElementById('review-panel-' + topicId).innerHTML = '<p style="color:#2ecc71;">✅ Great job! Keep reviewing regularly.</p>'; }});
        }}
        </script>"""

        html = render_template("base.html", title=f"{topic['title']} - Class X",
                               body_class="", extra_css="", content=content,
                               board_name=board_name)
        self._send_html(html)

    def _serve_search(self, query):
        q = query.get("q", [""])[0]
        board = query.get("board", [""])[0] or None
        page = self._safe_int(query.get("page", ["1"])[0], 1)
        per_page = 10

        if not q:
            content = """
            <div class="section"><h2>Search</h2>
            <p style="color:#666;">Enter a search term to find topics, chapters, and explanations.</p></div>"""
            html = render_template("base.html", title="Search - Class X",
                                   body_class="", extra_css="", content=content,
                                   board_name="")
            self._send_html(html)
            return

        conn = get_conn()
        search_query = '"' + q.replace('"', '""') + '"'
        try:
            results = search_chunks(search_query, board_id=board, limit=200)
        except Exception:
            like_query = f"%{q}%"
            results = conn.execute("""
                SELECT c.* FROM chunks c
                JOIN chapters ch ON c.chapter_id = ch.id
                WHERE c.content LIKE ? OR c.title LIKE ?
                LIMIT 200
            """, (like_query, like_query)).fetchall()
            results = [dict(r) for r in results]

        total = len(results)
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = max(1, min(page, total_pages))
        start = (page - 1) * per_page
        page_results = results[start:start + per_page]

        results_html = ""
        escaped_q = q.replace('<', '&lt;').replace('>', '&gt;')
        if not results:
            results_html = '<p style="color:#888;padding:2rem 0;text-align:center;">No results found. Try different keywords.</p>'
        else:
            for r in page_results:
                excerpt = re.sub(r'\s+', ' ', r.get("content", ""))
                q_pos = excerpt.lower().find(q.lower())
                if q_pos > 60:
                    excerpt = "... " + excerpt[q_pos - 60:]
                if len(excerpt) > 250:
                    excerpt = excerpt[:250] + "..."
                highlighted = re.sub(
                    '(' + re.escape(q) + ')',
                    r'<mark>\1</mark>',
                    excerpt,
                    flags=re.IGNORECASE
                )
                ct_label = r.get('content_type', 'text').capitalize()
                link = f"/chapter/{r['chapter_id']}" if r.get('chapter_id') else "#"
                results_html += f"""
                <div class="search-result-item" onclick="location.href='{link}'">
                    <div class="result-meta">
                        <span class="result-type">{ct_label}</span>
                        Ch {r.get('chapter_num', '?')}: {r.get('chapter_title', '')}
                    </div>
                    <div class="result-title">{r.get('title', '')}</div>
                    <div class="result-excerpt">{highlighted}</div>
                </div>"""

        pagination_html = ""
        if total_pages > 1:
            pages = []
            for p in range(1, total_pages + 1):
                if p == page:
                    pages.append(f'<span class="current">{p}</span>')
                else:
                    pages.append(f'<a href="/search?q={q}&page={p}">{p}</a>')
            pagination_html = f'<div class="pagination">{"".join(pages)}</div>'

        board_options = "".join(
            f'<option value="{bid}" {"selected" if bid == board else ""}>{info["name"]}</option>'
            for bid, info in ALL_BOARDS.items()
        )

        content = f"""
        <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> Search</div>
        <div class="section"><h2>Search Results</h2>
        <p style="color:#666;margin-bottom:1rem;">Found {total} result{"s" if total != 1 else ""} for "{q}"</p>
        <div style="margin-bottom:1rem;display:flex;gap:0.5rem;align-items:center;">
            <form action="/search" method="GET" style="display:flex;gap:0.5rem;flex-wrap:wrap;">
                <input type="text" name="q" value="{q}" style="padding:0.5rem 1rem;border:1px solid #ddd;border-radius:8px;font-size:0.9rem;flex:1;min-width:200px;">
                <select name="board" style="padding:0.5rem;border:1px solid #ddd;border-radius:8px;">
                    <option value="">All Boards</option>
                    {board_options}
                </select>
                <button type="submit" style="padding:0.5rem 1.2rem;background:#0f3460;color:#fff;border:none;border-radius:8px;cursor:pointer;">Search</button>
            </form>
        </div>
        <div class="search-results">{results_html}</div>
        {pagination_html}
        </div>"""
        html = render_template("base.html", title=f"Search: {q} - Class X",
                               body_class="", extra_css="", content=content,
                               board_name="")
        self._send_html(html)

    def _serve_about(self):
        boards_list = "".join(
            f'<li style="margin-bottom:0.5rem;"><strong>{info["name"]}</strong> — {info["description"]}</li>'
            for bid, info in ALL_BOARDS.items()
        )
        content = f"""
        <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> About</div>
        <div class="section"><h2>About</h2>
        <p style="line-height:1.8;color:#555;margin-bottom:1.5rem;">
        This platform provides free, offline-capable educational content for Class X students across India.
        </p>
        <h3 style="color:#0f3460;margin-bottom:0.5rem;">Supported Boards</h3>
        <ul style="list-style:none;margin-bottom:1.5rem;">{boards_list}</ul>
        <h3 style="color:#0f3460;margin-bottom:0.5rem;">Features</h3>
        <ul style="list-style:disc;padding-left:1.5rem;line-height:2;color:#555;">
            <li>Full-text search across all subjects and chapters</li>
            <li>AI-powered explanations (with local LLM)</li>
            <li>Tree-of-chunks content organization</li>
            <li>Offline-first PWA — works without internet</li>
            <li>MCP server for AI tool integration</li>
            <li>Vectorless database (SQLite FTS5) for fast response</li>
            <li>Detailed topic-level breakdown with examples and exercises</li>
        </ul>
        <p style="margin-top:1.5rem;color:#888;">All content based on official NCERT and SCERT curricula.</p>
        </div>"""
        html = render_template("base.html", title="About - Class X Education Platform",
                               body_class="", extra_css="", content=content,
                               board_name="")
        self._send_html(html)

    def _serve_error_page(self, msg, status=404):
        safe_msg = htmlmod.escape(str(msg))
        html = render_template("base.html", title="Error - Class X",
                               body_class="", extra_css="",
                               content=f'<div class="hero"><h2>{status}</h2><p>{safe_msg}</p><a href="/" class="ncert-link">Go Home</a></div>',
                               board_name="")
        self._send_html(html, status)

    def _api_search(self, query):
        q = query.get("q", [""])[0]
        board = query.get("board", [""])[0] or None
        if not q:
            self._send_json({"results": []})
            return
        engine = get_index()
        results = engine.search(q, board=board, limit=20)
        self._send_json({"results": results})

    def _api_explain(self, query):
        topic = query.get("topic", [""])[0]
        chapter = query.get("chapter", [""])[0] or "General"
        level = query.get("level", ["simple"])[0]
        if not topic:
            self._send_json({"error": "No topic specified"})
            return
        client = get_client()
        engine = get_index()
        context_results = engine.search(topic, limit=3)
        context = "\n\n".join(
            f"[{r.get('chapter_title','')} > {r.get('title','')}]\n{r.get('excerpt','')}"
            for r in context_results
        )
        explanation = client.explain_topic(topic, chapter, context, level)
        self._send_json({"topic": topic, "chapter": chapter, "level": level, "explanation": explanation})

    def _api_chapter(self, chapter_id):
        data = get_chapter_tree(chapter_id)
        if data:
            self._send_json(data)
        else:
            self._send_error(404, "Chapter not found")

    def _serve_quiz(self, chapter_id):
        conn = get_conn()
        chapter = conn.execute("SELECT * FROM chapters WHERE id = ?", (chapter_id,)).fetchone()
        if not chapter:
            chapter = conn.execute("SELECT * FROM chapters LIMIT 1").fetchone()
            if not chapter:
                self._serve_error_page("No chapters available")
                return
            chapter_id = chapter["id"]

        topics = conn.execute("SELECT * FROM topics WHERE chapter_id = ? ORDER BY num", (chapter_id,)).fetchall()
        topic_list = "".join(
            f'<option value="{t["id"]}">{t["num"]}. {t["title"]}</option>' for t in topics
        )
        content = f"""
        <div class="breadcrumb">
            <a href="/">Home</a> <span class="sep">›</span>
            <a href="/chapter/{chapter_id}">Ch {chapter["num"]}: {chapter["title"]}</a>
            <span class="sep">›</span> Smart Quiz
        </div>
        <div class="section">
            <h2>Smart Quiz: {chapter["title"]}</h2>
            <p class="subtitle">Test your knowledge with adaptive questions (Simple → Medium → Complex). Get detailed explanations for every wrong answer.</p>
            <div class="quiz-container" id="quiz-app">
                <div class="book-section" id="quiz-setup" style="text-align:center;">
                    <div style="margin-bottom:1rem;">
                        <label style="font-weight:500;margin-right:0.5rem;">Topic:</label>
                        <select id="quiz-topic" style="padding:0.5rem;border:1px solid #ddd;border-radius:8px;">
                            <option value="">All Topics (balanced)</option>
                            {topic_list}
                        </select>
                    </div>
                    <div style="margin-bottom:1.5rem;">
                        <label style="font-weight:500;margin-right:0.5rem;">Questions:</label>
                        <select id="quiz-count" style="padding:0.5rem;border:1px solid #ddd;border-radius:8px;">
                            <option value="10" selected>10 (Recommended)</option>
                            <option value="15">15</option>
                            <option value="20">20</option>
                        </select>
                    </div>
                    <button class="ncert-link" onclick="startQuiz()" style="cursor:pointer;">Start Smart Quiz</button>
                </div>
                <div id="quiz-content"></div>
            </div>
        </div>
        <script>
        let _quizQuestions = [];
        let _quizIdx = 0;
        let _quizCorrect = 0;
        let _quizWrongReview = [];
        let _quizAttempts = {{}};
        let _quizLocked = false;

        async function startQuiz() {{
            const topic = document.getElementById('quiz-topic').value;
            const count = document.getElementById('quiz-count').value;
            const btn = event.target;
            btn.textContent = 'Loading...';
            btn.disabled = true;
            try {{
                const resp = await fetch('/api/quiz?chapter_id={chapter_id}&topic_id=' + topic + '&count=' + count);
                const data = await resp.json();
                if (data.questions && data.questions.length > 0) {{
                    _quizQuestions = data.questions;
                    _quizIdx = 0;
                    _quizCorrect = 0;
                    _quizWrongReview = [];
                    _quizAttempts = {{}};
                    _quizLocked = false;
                    document.getElementById('quiz-setup').style.display = 'none';
                    showQuestion(0);
                }} else {{
                    document.getElementById('quiz-content').innerHTML = '<p style="color:#888;text-align:center;padding:2rem;">Could not generate quiz questions. Try again.</p>';
                }}
            }} catch(e) {{
                document.getElementById('quiz-content').innerHTML = '<p style="color:#c62828;text-align:center;padding:2rem;">Error loading quiz.</p>';
            }}
            btn.textContent = 'Start Smart Quiz';
            btn.disabled = false;
        }}

        function showQuestion(idx) {{
            if (idx >= _quizQuestions.length) {{
                showQuizResults();
                return;
            }}
            _quizIdx = idx;
            const q = _quizQuestions[idx];
            const optLetters = ['A', 'B', 'C', 'D'];
            const diffBadge = {{'simple':'🟢 Simple','medium':'🟡 Medium','complex':'🔴 Complex'}}[q.difficulty] || 'Simple';
            const diffClass = q.difficulty || 'simple';
            let html = '<div class="quiz-container">';
            html += '<div class="quiz-header-bar">';
            html += '<div class="quiz-progress-bar"><div class="quiz-progress-fill" style="width:' + ((idx / _quizQuestions.length) * 100) + '%"></div></div>';
            html += '<div class="quiz-header-meta">';
            html += '<span class="quiz-q-counter">Question ' + (idx+1) + ' of ' + _quizQuestions.length + '</span>';
            html += '<span class="quiz-diff-badge diff-' + diffClass + '">' + diffBadge + '</span>';
            html += '<span class="quiz-score-display">⭐ ' + _quizCorrect + ' correct</span>';
            html += '</div></div>';
            html += '<div class="quiz-question" id="active-question">';
            html += '<div class="q-text"><span class="q-num">' + (idx+1) + '</span> ' + escapeHtml(q.question) + '</div>';
            html += '<div class="quiz-options" id="q-options-' + idx + '">';
            q.options.forEach((opt, j) => {{
                const disabled = (_quizAttempts[idx] && _quizAttempts[idx].wrongOptions && _quizAttempts[idx].wrongOptions.includes(j)) ? ' style="pointer-events:none;opacity:0.4;text-decoration:line-through;"' : '';
                html += '<div class="quiz-option" id="opt-' + idx + '-' + j + '" onclick="checkAnswer(' + idx + ', ' + j + ')" data-index="' + j + '"' + disabled + '>' + optLetters[j] + '. ' + escapeHtml(opt) + '</div>';
            }});
            html += '</div>';
            html += '<div id="q-feedback-' + idx + '" class="quiz-feedback"></div>';
            html += '</div>';
            html += '<div id="quiz-review-section" class="quiz-review-section" style="display:none;"></div>';
            html += '</div>';
            document.getElementById('quiz-content').innerHTML = html;
            _quizLocked = false;
        }}

        function checkAnswer(qIdx, optIdx) {{
            if (_quizLocked) return;
            const q = _quizQuestions[qIdx];
            const el = document.getElementById('opt-' + qIdx + '-' + optIdx);
            if (!el || el.style.pointerEvents === 'none') return;
            const options = document.querySelectorAll('#q-options-' + qIdx + ' .quiz-option');
            const feedback = document.getElementById('q-feedback-' + qIdx);

            if (optIdx === q.correct) {{
                _quizLocked = true;
                _quizCorrect++;
                el.classList.add('correct');
                options.forEach(o => o.style.pointerEvents = 'none');
                feedback.innerHTML = '<div class="q-feedback-correct">✓ Correct! Well done.</div>';
                setTimeout(() => showQuestion(_quizIdx + 1), 1200);
            }} else {{
                if (!_quizAttempts[qIdx]) {{
                    _quizAttempts[qIdx] = {{ attempts: 0, wrongOptions: [] }};
                }}
                _quizAttempts[qIdx].attempts++;
                _quizAttempts[qIdx].wrongOptions.push(optIdx);
                el.classList.add('wrong');
                el.style.pointerEvents = 'none';
                el.style.opacity = '0.4';
                el.style.textDecoration = 'line-through';

                if (_quizAttempts[qIdx].attempts < 2) {{
                    feedback.innerHTML = '<div class="q-feedback-retry">✗ Not quite. Try again! (<span style="font-weight:600;">' + (2 - _quizAttempts[qIdx].attempts) + ' attempt' + (2 - _quizAttempts[qIdx].attempts > 1 ? 's' : '') + ' left</span>)</div>';
                }} else {{
                    _quizLocked = true;
                    options.forEach(o => o.style.pointerEvents = 'none');
                    options[q.correct].classList.add('correct');
                    _quizWrongReview.push({{
                        index: qIdx,
                        question: q.question,
                        options: q.options,
                        correct: q.correct,
                        explanation: q.explanation || 'No explanation available.'
                    }});
                    feedback.innerHTML = '<div class="q-feedback-wrong">✗ The correct answer was <strong>' + String.fromCharCode(65 + q.correct) + ': ' + escapeHtml(q.options[q.correct]) + '</strong></div>';
                    feedback.innerHTML += '<div class="q-explanation"><strong>📖 Explanation:</strong> ' + escapeHtml(q.explanation || 'Review the topic for more details.') + '</div>';
                    setTimeout(() => showQuestion(_quizIdx + 1), 4000);
                }}
            }}
        }}

        function showQuizResults() {{
            const total = _quizQuestions.length;
            const pct = Math.round(_quizCorrect / total * 100);
            let grade = pct >= 80 ? '🌟 Excellent' : pct >= 60 ? '👍 Good' : pct >= 40 ? '💪 Keep Trying' : '📚 Needs Practice';

            let html = '<div class="quiz-results">';
            html += '<div class="qr-header"><h2>Quiz Complete!</h2></div>';
            html += '<div class="qr-score-circle" style="--pct: ' + pct + ';"><span>' + _quizCorrect + '/' + total + '</span></div>';
            html += '<div class="qr-grade">' + grade + '</div>';
            html += '<div class="qr-pct">' + pct + '% Accuracy</div>';

            if (_quizWrongReview.length > 0) {{
                html += '<div class="qr-review"><h3>📖 Review Incorrect Answers</h3>';
                html += '<p class="subtitle">Go through these explanations to strengthen your understanding.</p>';
                _quizWrongReview.forEach((r, i) => {{
                    const optLetters = ['A', 'B', 'C', 'D'];
                    html += '<div class="qr-review-item">';
                    html += '<div class="qri-q"><strong>Q' + (i+1) + ':</strong> ' + escapeHtml(r.question) + '</div>';
                    html += '<div class="qri-options">';
                    r.options.forEach((opt, j) => {{
                        const cls = j === r.correct ? 'qri-correct' : 'qri-wrong';
                        html += '<div class="qri-opt ' + cls + '">' + optLetters[j] + '. ' + escapeHtml(opt) + (j === r.correct ? ' ✓' : '') + '</div>';
                    }});
                    html += '</div>';
                    html += '<div class="qri-explanation"><strong>📖 Explanation:</strong> ' + escapeHtml(r.explanation) + '</div>';
                    html += '</div>';
                }});
                html += '</div>';
            }} else {{
                html += '<div class="qr-perfect">🎉 Perfect score! You mastered this chapter!</div>';
            }}

            html += '<div style="text-align:center;margin:2rem 0;display:flex;gap:1rem;justify-content:center;flex-wrap:wrap;">';
            html += '<button class="ncert-link" onclick="startQuiz()" style="cursor:pointer;">🔄 Retry Quiz</button>';
            html += '<button class="ncert-link" onclick="document.getElementById(\'quiz-setup\').style.display=\'block\';document.getElementById(\'quiz-content\').innerHTML=\'\';" style="cursor:pointer;">📋 Change Settings</button>';
            html += '</div></div>';

            document.getElementById('quiz-content').innerHTML = html;
            sendQuizResult();
        }}

        async function sendQuizResult() {{
            try {{
                const resp = await fetch('/api/quiz-result?correct=' + _quizCorrect + '&total=' + _quizQuestions.length + '&chapter_id={chapter_id}');
                const data = await resp.json();
                const qrHeader = document.querySelector('.qr-header');
                if (qrHeader && data.xp_gained > 0) {{
                    qrHeader.innerHTML += '<div class="qr-xp-gained">+ ' + data.xp_gained + ' XP</div>';
                }}
                if (window.loadGamification) window.loadGamification();
            }} catch(e) {{}}
        }}

        function escapeHtml(t) {{ const d=document.createElement('div'); d.textContent=t; return d.innerHTML; }}
        </script>"""
        html = render_template("base.html", title=f"Smart Quiz: {chapter['title']} - Class X",
                               body_class="", extra_css="", content=content,
                               board_name="")
        self._send_html(html)

    def _api_quiz(self, query):
        chapter_id = query.get("chapter_id", [""])[0]
        topic_id = query.get("topic_id", [""])[0] or None
        count = self._safe_int(query.get("count", ["10"])[0], 10)
        count = min(max(count, 10), 20)

        conn = get_conn()
        if topic_id:
            topics = conn.execute(
                "SELECT * FROM topics WHERE id = ?", (topic_id,)
            ).fetchall()
        else:
            all_topics = conn.execute(
                "SELECT * FROM topics WHERE chapter_id = ? ORDER BY num",
                (chapter_id,)
            ).fetchall()
            if len(all_topics) > count:
                topics = all_topics[:count]
            else:
                topics = all_topics

        import random
        rng = random.Random()
        difficulty_order = []
        simple_target = max(3, count // 3)
        medium_target = max(3, count // 3)
        complex_target = count - simple_target - medium_target

        for i in range(simple_target):
            difficulty_order.append("simple")
        for i in range(medium_target):
            difficulty_order.append("medium")
        for i in range(complex_target):
            difficulty_order.append("complex")
        rng.shuffle(difficulty_order)

        questions = []
        used_content = set()
        topic_pool = list(topics)
        rng.shuffle(topic_pool)

        difficulty_idx = 0
        for topic in topic_pool:
            if len(questions) >= count:
                break
            chunks = conn.execute(
                "SELECT * FROM chunks WHERE topic_id = ? ORDER BY seq",
                (topic["id"],)
            ).fetchall()
            if not chunks:
                continue

            for chunk in chunks:
                if len(questions) >= count:
                    break
                if chunk["id"] in used_content:
                    continue
                text = chunk["content"]
                if len(text) < 30:
                    continue
                used_content.add(chunk["id"])

                diff = difficulty_order[difficulty_idx % len(difficulty_order)]
                difficulty_idx += 1

                q = self._make_question(text, topic["title"], diff, chunk)
                if q:
                    questions.append(q)

        if len(questions) < count:
            fill = conn.execute(
                "SELECT c.*, t.title as t_title FROM chunks c JOIN topics t ON c.topic_id = t.id WHERE c.chapter_id = ? ORDER BY RANDOM() LIMIT ?",
                (chapter_id, count - len(questions))
            ).fetchall()
            for ch in fill:
                if len(questions) >= count:
                    break
                if ch["id"] in used_content:
                    continue
                if len(ch["content"]) < 30:
                    continue
                used_content.add(ch["id"])
                diff = difficulty_order[difficulty_idx % len(difficulty_order)]
                difficulty_idx += 1
                q = self._make_question(ch["content"], ch["t_title"], diff,
                                        {"content": ch["content"], "title": ch.get("title", ch["t_title"]),
                                         "content_type": ch.get("content_type", "text")})
                if q:
                    questions.append(q)

        self._send_json({"questions": questions[:count]})

    def _make_question(self, text, topic, difficulty, chunk):
        import random
        seed = hash(text + topic + difficulty) & 0xFFFFFFFF
        rng = random.Random(seed)

        topic_words = [w.lower() for w in topic.split() if len(w) > 2]

        sentences = [s.strip() for s in re.split(r'[.!?]\s+', text) if len(s.strip()) > 10]
        if not sentences:
            return None

        sent = rng.choice(sentences)
        all_words = re.findall(r'\b[A-Za-z]{4,}\b', text)
        unique_words = list(set(w for w in all_words if len(w) > 3))

        content_terms = [w for w in unique_words if w[0].isupper() and w.lower() not in
                         {"this", "that", "with", "from", "they", "their", "them", "have", "been", "were", "what",
                          "when", "where", "which", "each", "step", "into", "also", "than", "then", "some", "more",
                          "such", "very", "just", "about", "consider", "involv", "including", "being", "understand",
                          "remember", "important", "between", "without", "after", "before", "other", "should", "could",
                          "first", "second", "third", "next", "last", "basic", "common", "following", "above", "below"}]

        if len(content_terms) < 2:
            content_terms = [w for w in unique_words if len(w) > 3 and w.lower() not in
                            {"this", "that", "with", "from", "they", "their", "them", "have", "been", "were", "what",
                             "when", "where", "which", "each", "step", "into", "also", "than", "then", "some", "more",
                             "such", "very", "just", "about", "also", "being", "can", "will", "has", "had", "but",
                             "not", "are", "was", "for", "the", "and", "you", "all"}][:10]

        if not content_terms:
            return None

        kw = rng.choice(content_terms)
        wrong_pool = [w for w in content_terms if w != kw]
        rng.shuffle(wrong_pool)
        distractors = wrong_pool[:3]

        while len(distractors) < 3:
            fillers = ["Definition", "Property", "Formula", "Theorem", "Concept", "Principle", "Method", "Rule"]
            d = rng.choice(fillers)
            if d != kw and d not in distractors:
                distractors.append(d)

        options = [kw] + distractors[:3]
        rng.shuffle(options)
        correct = options.index(kw)

        explanation = text[:400]

        if difficulty == "simple":
            return {
                "question": f"Which of the following is a key concept related to '{topic}'?",
                "options": options, "correct": correct,
                "difficulty": "simple",
                "explanation": f"In the topic '{topic}', the term '{kw}' is an important concept. {explanation[:250]}",
                "topic": topic
            }
        elif difficulty == "medium":
            question_text = sent if len(sent) < 100 else sent[:97] + "..."
            return {
                "question": f"Based on your study of '{topic}':\n\"{question_text}\"\n\nWhich term best completes the above statement?",
                "options": options, "correct": correct,
                "difficulty": "medium",
                "explanation": f"The correct term is '{kw}'. {explanation[:300]}",
                "topic": topic
            }
        else:
            return {
                "question": f"In the chapter on '{topic}', how does '{kw}' relate to the overall theme?\n(Choose the best answer)",
                "options": options, "correct": correct,
                "difficulty": "complex",
                "explanation": f"'{kw}' is a central concept in {topic}. {explanation[:350]}",
                "topic": topic
            }

    def _api_streak_calendar(self):
        conn = get_conn()
        rows = conn.execute(
            "SELECT date(created_at) as day, SUM(xp) as total_xp, COUNT(*) as activities "
            "FROM xp_events WHERE created_at >= date('now','-90 days') "
            "GROUP BY day ORDER BY day"
        ).fetchall()
        calendar = [{"date": r["day"], "xp": r["total_xp"], "activities": r["activities"]} for r in rows]
        self._send_json({"days": calendar})

    def _api_gamification(self):
        data = get_leaderboard_data()
        self._send_json(data)

    def _api_study(self, query):
        chapter_id = query.get("chapter_id", [""])[0]
        topic_id = query.get("topic_id", [""])[0] or None
        if chapter_id and topic_id:
            mark_topic_progress(chapter_id, topic_id, "completed", xp=10)
        elif chapter_id:
            add_xp(5, "study", f"Studied chapter", chapter_id=chapter_id)
        check_streak()
        refill_lives()
        self._send_json(get_leaderboard_data())

    def _api_lifeline(self, query):
        lifeline_type = query.get("type", ["hint"])[0]
        chapter_id = query.get("chapter_id", [""])[0]
        topic_id = query.get("topic_id", [""])[0] or ""
        refill_lives()
        if lifeline_type == "extra_life":
            conn = get_conn()
            learner = get_learner()
            if learner["lives"] < learner["max_lives"]:
                conn.execute("UPDATE learner SET lives = lives + 1 WHERE id = 1")
                conn.commit()
                self._send_json({"success": True, "lives": learner["lives"] + 1, "xp_cost": 0})
                return
            self._send_json({"success": False, "message": "Already at max lives"})
            return
        xp_cost = use_lifeline(lifeline_type, chapter_id, topic_id)
        self._send_json({"success": True, "xp_cost": xp_cost, "lifeline": lifeline_type})

    def _api_quiz_result(self, query):
        correct = self._safe_int(query.get("correct", ["0"])[0])
        total = self._safe_int(query.get("total", ["0"])[0])
        chapter_id = query.get("chapter_id", [""])[0]
        lives_lost = 0
        wrong = total - correct
        for _ in range(wrong):
            ok, _ = use_life()
            if not ok:
                break
            lives_lost += 1
        xp = record_quiz_result(correct, total, chapter_id)
        refill_lives()
        check_streak()
        self._send_json({
            "xp_gained": xp,
            "lives_lost": lives_lost,
            **get_leaderboard_data(),
        })

    def _api_review_due(self):
        from spaced_repetition import get_due_reviews
        due = get_due_reviews(20)
        self._send_json({"reviews": due, "count": len(due)})

    def _api_review_submit(self, query):
        topic_id = query.get("topic_id", [""])[0]
        quality_str = query.get("quality", ["3"])[0]
        if not topic_id:
            self._send_error(400, "topic_id required")
            return
        try:
            quality = max(0, min(5, int(quality_str)))
        except ValueError:
            quality = 3
        from spaced_repetition import schedule_review
        result = schedule_review(topic_id, quality)
        self._send_json({"success": True, "result": result})

    def _api_review_stats(self):
        from spaced_repetition import get_review_stats
        self._send_json(get_review_stats())

    def _serve_review_page(self):
        from spaced_repetition import get_due_reviews, get_review_stats
        due = get_due_reviews(50)
        stats = get_review_stats()
        rows = ""
        for r in due:
            board_label = {"cbse": "CBSE", "ap": "AP", "ts": "TS"}.get(r.get("board_id", ""), r.get("board_id", ""))
            rows += f"""
            <tr>
                <td><a href="/topic/{r['topic_id']}" target="_blank">{r['topic_title']}</a></td>
                <td><span class="board-badge cbse">{board_label}</span></td>
                <td>Ch {r['chapter_num']}: {r['chapter_title'][:40]}</td>
                <td>{r.get('repetitions', 0)}</td>
                <td>{r.get('last_reviewed', 'never')}</td>
                <td>
                    <div class="quality-select">
                        <button class="tts-btn" onclick="submitReview('{r['topic_id']}', 0)" title="Forgot">❌ 0</button>
                        <button class="tts-btn" onclick="submitReview('{r['topic_id']}', 1)">1</button>
                        <button class="tts-btn" onclick="submitReview('{r['topic_id']}', 2)">2</button>
                        <button class="tts-btn" onclick="submitReview('{r['topic_id']}', 3)">3</button>
                        <button class="tts-btn" onclick="submitReview('{r['topic_id']}', 4)">4</button>
                        <button class="tts-btn" onclick="submitReview('{r['topic_id']}', 5)" title="Perfect">🌟 5</button>
                    </div>
                </td>
            </tr>"""
        if not rows:
            rows = '<tr><td colspan="6" style="padding:1.5rem;text-align:center;color:#888;">No topics due for review. Great job keeping up! 🎉</td></tr>'
        content = f"""
        <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> Spaced Review</div>
        <div class="section">
            <h2>📅 Spaced Repetition Review</h2>
            <p class="subtitle">Topics due for review: <strong>{stats['due']}</strong> · Total scheduled: {stats['total']} · Due today: {stats['today_due']}</p>
            <p style="font-size:0.85rem;color:#666;margin:0.5rem 0 1rem;">
                Rate your recall: <strong>0-2</strong> = Forgotten (re-learn), <strong>3</strong> = Recalled with effort,
                <strong>4</strong> = Recalled easily, <strong>5</strong> = Perfect recall
            </p>
            <div class="book-section">
                <table style="width:100%;border-collapse:collapse;">
                    <tr style="border-bottom:2px solid var(--border);">
                        <th style="text-align:left;padding:0.5rem;">Topic</th>
                        <th style="text-align:left;padding:0.5rem;">Board</th>
                        <th style="text-align:left;padding:0.5rem;">Chapter</th>
                        <th style="text-align:left;padding:0.5rem;">Reviews</th>
                        <th style="text-align:left;padding:0.5rem;">Last</th>
                        <th style="text-align:left;padding:0.5rem;">Rate Recall</th>
                    </tr>
                    {rows}
                </table>
            </div>
        </div>
        <script>
        async function submitReview(topicId, quality) {{
            try {{
                const resp = await fetch('/api/review/submit?topic_id=' + topicId + '&quality=' + quality);
                const data = await resp.json();
                if (data.success) {{
                    location.reload();
                }}
            }} catch(e) {{}}
        }}
        </script>"""
        html = render_template("base.html", title="Spaced Review - Class X",
                               body_class="", extra_css="", content=content, board_name="")
        self._send_html(html)

    def _api_notebooklm_export(self, query):
        topic_id = query.get("topic_id", [""])[0]
        chapter_id = query.get("chapter_id", [""])[0]
        conn = get_conn()
        parts = []
        if chapter_id:
            ch = conn.execute("SELECT * FROM chapters WHERE id = ?", (chapter_id,)).fetchone()
            if ch:
                parts.append(f"# Chapter {ch['num']}: {ch['title']}\n")
                topics = conn.execute("SELECT * FROM topics WHERE chapter_id = ? ORDER BY num", (chapter_id,)).fetchall()
                for t in topics:
                    parts.append(f"## {t['num']}. {t['title']}\n")
                    chunks = conn.execute("SELECT * FROM chunks WHERE topic_id = ? ORDER BY seq", (t["id"],)).fetchall()
                    for c in chunks:
                        parts.append(f"**{c['title']}**  \n{c['content']}\n")
        if topic_id:
            t = conn.execute("SELECT * FROM topics WHERE id = ?", (topic_id,)).fetchone()
            if t:
                parts.append(f"# {t['title']}\n")
                chunks = conn.execute("SELECT * FROM chunks WHERE topic_id = ? ORDER BY seq", (t["id"],)).fetchall()
                for c in chunks:
                    parts.append(f"## {c['title']}  \n{c['content']}\n")
        markdown = "\n".join(parts)
        self._send_json({"markdown": markdown, "format": "notebooklm"})

    def _api_register(self, query):
        name = query.get("name", [""])[0].strip()
        email = query.get("email", [""])[0].strip().lower()
        password = query.get("password", [""])[0]
        if not name or not email or not password:
            self._send_json({"success": False, "error": "All fields required"})
            return
        if len(password) < 6:
            self._send_json({"success": False, "error": "Password must be at least 6 characters"})
            return
        conn = get_conn()
        existing = conn.execute("SELECT id FROM learner WHERE id=1").fetchone()
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if existing:
            conn.execute("UPDATE learner SET name=?, email=?, password_hash=? WHERE id=1",
                         (name, email, password_hash))
        else:
            conn.execute("INSERT INTO learner (id, name, email, password_hash, xp, level, lives, max_lives) VALUES (1, ?, ?, ?, 0, 1, 5, 5)",
                         (name, email, password_hash))
        conn.commit()
        token = secrets.token_hex(32)
        conn.execute("INSERT OR REPLACE INTO sessions (token, learner_id) VALUES (?, 1)", (token,))
        conn.commit()
        self._send_json({"success": True, "message": "Account created", "token": token, "redirect": "/profile"})

    def _api_login(self, query):
        email = query.get("email", [""])[0].strip().lower()
        password = query.get("password", [""])[0]
        if not email or not password:
            self._send_json({"success": False, "error": "Email and password required"})
            return
        conn = get_conn()
        learner = conn.execute("SELECT id, name, email, password_hash FROM learner WHERE id=1").fetchone()
        if not learner:
            self._send_json({"success": False, "error": "Account not found. Please register first."})
            return
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if learner["password_hash"] and learner["password_hash"] != password_hash:
            self._send_json({"success": False, "error": "Invalid email or password"})
            return
        token = secrets.token_hex(32)
        conn.execute("INSERT OR REPLACE INTO sessions (token, learner_id) VALUES (?, 1)", (token,))
        conn.commit()
        self._send_json({"success": True, "message": "Logged in", "token": token, "redirect": "/profile"})

    def _serve_profile(self):
        data = get_leaderboard_data()
        learner = get_learner()
        conn = get_conn()
        recent_xp = conn.execute(
            "SELECT * FROM xp_events ORDER BY id DESC LIMIT 10"
        ).fetchall()
        progress = conn.execute(
            "SELECT lp.*, ch.title as ch_title, ch.num as ch_num FROM learning_progress lp "
            "JOIN chapters ch ON lp.chapter_id = ch.id ORDER BY lp.last_accessed DESC LIMIT 10"
        ).fetchall()

        xp_rows = "".join(
            f'<tr><td>{e["reason"]}</td><td>{"+" if e["xp"] >= 0 else ""}{e["xp"]}</td><td style="font-size:0.8rem;color:#888;">{e["created_at"]}</td></tr>'
            for e in recent_xp
        )
        progress_rows = "".join(
            f'<tr><td>Ch {p["ch_num"]}: {p["ch_title"]}</td><td><span class="board-badge cbse">{p["status"]}</span></td><td>{p["xp_earned"]}</td></tr>'
            for p in progress
        )
        content = f"""
        <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> Profile</div>
        <div class="section">
            <h2>My Learning Profile</h2>
            <div class="cards-grid" style="margin-top:1.5rem;">
                <div class="info-card">
                    <h3>🔥 Streak</h3>
                    <div style="font-size:2rem;font-weight:800;color:var(--accent);">{data['streak']} days</div>
                    <p>Longest: {data['longest_streak']} days</p>
                </div>
                <div class="info-card">
                    <h3>❤️ Lives</h3>
                    <div style="font-size:2rem;font-weight:800;color:var(--highlight);">{'❤️' * data['lives']}{'🖤' * (data['max_lives'] - data['lives'])}</div>
                    <p>{data['lives']}/{data['max_lives']} · Refills every {data['life_refill_minutes']}min</p>
                </div>
                <div class="info-card">
                    <h3>⭐ XP & Level</h3>
                    <div style="font-size:2rem;font-weight:800;color:#f59e0b;">Level {data['level']}</div>
                    <p>{data['xp']} XP · Next: {data['next_level_xp']} XP</p>
                    <div style="width:100%;height:8px;background:#e0e0e0;border-radius:4px;margin-top:0.5rem;overflow:hidden;">
                        <div style="height:100%;background:linear-gradient(90deg,#f59e0b,#f97316);border-radius:4px;width:{min(100, (data['xp'] - data['current_level_xp']) / max(1, data['next_level_xp'] - data['current_level_xp']) * 100)}%;"></div>
                    </div>
                </div>
                <div class="info-card">
                    <h3>📊 Stats</h3>
                    <p>Topics completed: {data['topics_completed']}</p>
                    <p>Quizzes taken: {data['quizzes_taken']}</p>
                    <p>Quiz accuracy: {data['quiz_accuracy']}%</p>
                </div>
            </div>
            <div class="book-section" style="margin-top:1.5rem;">
                <h3>📅 Activity Calendar (Last 90 Days)</h3>
                <div id="streak-calendar" style="overflow-x:auto;padding:0.5rem 0;">
                    <p style="color:#888;font-size:0.85rem;">Loading calendar...</p>
                </div>
            </div>
            <div class="book-section" style="margin-top:1.5rem;">
                <h3>Recent XP</h3>
                <table style="width:100%;border-collapse:collapse;">
                    <tr style="border-bottom:2px solid var(--border);"><th style="text-align:left;padding:0.5rem;">Activity</th><th style="text-align:left;padding:0.5rem;">XP</th><th style="text-align:left;padding:0.5rem;">Time</th></tr>
                    {xp_rows or '<tr><td colspan="3" style="padding:1rem;text-align:center;color:#888;">No activity yet. Start studying!</td></tr>'}
                </table>
            </div>
            <div class="book-section">
                <h3>Recent Progress</h3>
                <table style="width:100%;border-collapse:collapse;">
                    <tr style="border-bottom:2px solid var(--border);"><th style="text-align:left;padding:0.5rem;">Chapter</th><th style="text-align:left;padding:0.5rem;">Status</th><th style="text-align:left;padding:0.5rem;">XP</th></tr>
                    {progress_rows or '<tr><td colspan="3" style="padding:1rem;text-align:center;color:#888;">No progress yet.</td></tr>'}
                </table>
            </div>
            <div class="book-section">
                <h3>🚀 Quick Links</h3>
                <div style="display:flex;gap:0.5rem;flex-wrap:wrap;">
                    <a class="tts-btn" href="/tutor">🧠 AI Tutor</a>
                    <a class="tts-btn" href="/parent-report">📊 Progress Report</a>
                    <a class="tts-btn" href="/competitive">🎯 Competitive Exams</a>
                    <a class="tts-btn" href="/electives">🌟 Skill Electives</a>
                    <a class="tts-btn" href="/topic/70a4cb4871fa1c7e" onclick="alert('Navigate to any topic and click the \\'Interactive\\' button.');return false;">🎮 Interactives</a>
                </div>
            </div>
            <div class="book-section">
                <h3>🔗 Parent/Teacher Monitoring</h3>
                <p style="font-size:0.85rem;color:#666;">Generate a read-only monitoring link to share with parents or teachers. Expires in 24 hours.</p>
                <button class="tts-btn" onclick="generateMonitorPin()" style="margin-top:0.5rem;">🔗 Generate Monitor Link</button>
                <div id="monitor-pin-result" style="margin-top:0.5rem;"></div>
            </div>
        </div>
        <script>
        async function loadStreakCalendar() {{
            const container = document.getElementById('streak-calendar');
            try {{
                const resp = await fetch('/api/streak/calendar');
                const data = await resp.json();
                const days = data.days || [];
                const dayMap = {{}};
                let maxXp = 0;
                days.forEach(d => {{ dayMap[d.date] = d.xp; if (d.xp > maxXp) maxXp = d.xp; }});
                const today = new Date();
                const startDate = new Date(today);
                startDate.setDate(startDate.getDate() - 83);
                startDate.setDate(startDate.getDate() - startDate.getDay());
                const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
                const dayNames = ['','Mon','','Wed','','Fri',''];
                let html = '<table style="border-collapse:collapse;"><tr><td style="padding:0 4px;"></td>';
                let monthLabels = '';
                let lastMonth = -1;
                for (let w = 0; w < 12; w++) {{
                    const d = new Date(startDate);
                    d.setDate(d.getDate() + w * 7);
                    if (d.getMonth() !== lastMonth) {{
                        lastMonth = d.getMonth();
                        monthLabels += '<td style="padding:0 1px;font-size:0.65rem;color:#888;text-align:center;width:12px;">' + months[d.getMonth()] + '</td>';
                    }} else {{
                        monthLabels += '<td style="padding:0 1px;"></td>';
                    }}
                }}
                html += monthLabels + '</tr><tr>';
                for (let row = 0; row < 7; row++) {{
                    html += '<tr><td style="padding:0 4px;font-size:0.65rem;color:#888;height:14px;">' + dayNames[row] + '</td>';
                    for (let col = 0; col < 12; col++) {{
                        const d = new Date(startDate);
                        d.setDate(d.getDate() + col * 7 + row);
                        const key = d.toISOString().split('T')[0];
                        const xp = dayMap[key] || 0;
                        let color = '#ebedf0';
                        if (xp > 0) {{
                            const intensity = maxXp > 0 ? Math.min(1, xp / maxXp) : 0;
                            if (intensity > 0.66) color = '#1a7b2e';
                            else if (intensity > 0.33) color = '#2ea043';
                            else color = '#7bc96f';
                        }}
                        const todayKey = today.toISOString().split('T')[0];
                        const isToday = key === todayKey;
                        html += '<td title="' + key + ': ' + xp + ' XP" style="padding:1px;">' +
                            '<div style="width:10px;height:10px;border-radius:2px;background:' + color + ';' +
                            (isToday ? 'outline:2px solid var(--accent);outline-offset:1px;' : '') + '"></div></td>';
                    }}
                    html += '</tr>';
                }}
                html += '</table>';
                html += '<div style="display:flex;gap:4px;align-items:center;margin-top:4px;font-size:0.7rem;color:#888;">Less' +
                    '<div style="width:10px;height:10px;border-radius:2px;background:#ebedf0;"></div>' +
                    '<div style="width:10px;height:10px;border-radius:2px;background:#7bc96f;"></div>' +
                    '<div style="width:10px;height:10px;border-radius:2px;background:#2ea043;"></div>' +
                    '<div style="width:10px;height:10px;border-radius:2px;background:#1a7b2e;"></div>' +
                    ' More</div>';
                container.innerHTML = html;
            }} catch(e) {{
                container.innerHTML = '<p style="color:#888;font-size:0.85rem;">Activity data not available yet.</p>';
            }}
        }}
        loadStreakCalendar();

        async function generateMonitorPin() {{
            const container = document.getElementById('monitor-pin-result');
            container.innerHTML = '<span style="color:#888;">Generating...</span>';
            try {{
                const resp = await fetch('/api/monitor/generate');
                const data = await resp.json();
                const url = window.location.origin + data.url;
                container.innerHTML = '<div style="padding:0.8rem;background:#e8f5e9;border-radius:8px;">' +
                    '<p><strong>PIN:</strong> ' + data.pin + '</p>' +
                    '<p><strong>Link:</strong> <a href="' + url + '" target="_blank">' + url + '</a></p>' +
                    '<p style="font-size:0.8rem;color:#888;">Expires: ' + data.expires + '</p></div>';
            }} catch(e) {{
                container.innerHTML = '<span style="color:#c62828;">Error generating PIN.</span>';
            }}
        }}
        </script>"""
        html = render_template("base.html", title="My Profile - Class X",
                               body_class="", extra_css="", content=content,
                               board_name="")
        self._send_html(html)

    def _send_html(self, html, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Service-Worker-Allowed", "/")
        self.end_headers()
        self.wfile.write(html.encode())

    def _send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, default=str).encode())

    def _send_error(self, code, msg):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": msg}).encode())

    def _api_question_bank(self, query):
        from question_bank import get_questions, get_past_year_patterns
        board_id = query.get("board", ["cbse"])[0]
        subject_id = query.get("subject", [""])[0] or None
        chapter = query.get("chapter", [""])[0] or None
        year = query.get("year", [""])[0] or None
        qtype = query.get("type", [""])[0] or None
        limit = self._safe_int(query.get("limit", ["20"])[0], 20)
        if not subject_id and chapter:
            conn = get_conn()
            ch = conn.execute("SELECT subject_id FROM chapters WHERE id = ?", (chapter,)).fetchone()
            if ch:
                subject_id = ch["subject_id"]
        if not subject_id:
            self._send_error(400, "subject or chapter required")
            return
        try:
            questions = get_questions(board_id, subject_id, chapter, year, qtype, limit)
            patterns = get_past_year_patterns(board_id, subject_id) if subject_id else {}
            self._send_json({"questions": questions, "patterns": patterns, "count": len(questions)})
        except ValueError as e:
            self._send_error(400, str(e))

    def _api_model_paper(self, query):
        from question_bank import generate_model_paper
        board_id = query.get("board", ["cbse"])[0]
        subject_id = query.get("subject", [""])[0] or None
        num_q = self._safe_int(query.get("num", ["30"])[0], 30)
        if not subject_id:
            self._send_error(400, "subject required")
            return
        paper = generate_model_paper(board_id, subject_id, num_q)
        self._send_json(paper)

    def _api_mock_exam_start(self, query):
        from mock_exam import MockExam
        board_id = query.get("board", ["cbse"])[0]
        subject_id = query.get("subject", [""])[0]
        template = query.get("template", ["balanced"])[0]
        if not subject_id:
            self._send_error(400, "subject required")
            return
        exam = MockExam(board_id, subject_id)
        paper = exam.generate_paper(template=template)
        self._send_json(paper)

    def _api_mock_exam_submit(self, query):
        from mock_exam import calculate_score, save_exam_result, get_percentile
        import json as _json
        try:
            answers = _json.loads(query.get("answers", ["{}"])[0])
        except Exception:
            answers = {}
        paper_id = query.get("paper_id", [""])[0]
        board_id = query.get("board", ["cbse"])[0]
        subject_id = query.get("subject", [""])[0]
        result = calculate_score(paper_id, answers)
        result["percentile"] = get_percentile(result["total"], board_id, subject_id)
        save_exam_result(1, paper_id, result["total"], result["percentage"], result["grade"], answers)
        from badges import award_mock_complete, check_and_award_badges
        award_mock_complete()
        if result.get("percentage", 0) >= 90:
            from database import get_conn
            conn = get_conn()
            conn.execute("INSERT OR IGNORE INTO learner_badges (learner_id, badge_id) VALUES (1, 'champion')")
            conn.commit()
        check_and_award_badges()
        self._send_json(result)

    def _api_mock_exam_history(self):
        from mock_exam import get_exam_history
        history = get_exam_history(1, 20)
        self._send_json({"history": history})

    def _api_cbq(self, query):
        from cbq_engine import get_cbqs, list_scenarios
        board_id = query.get("board", ["cbse"])[0]
        subject_id = query.get("subject", [""])[0] or None
        chapter = query.get("chapter", [""])[0] or None
        count = self._safe_int(query.get("count", ["5"])[0], 5)
        cbqs = get_cbqs(board_id, subject_id, chapter, count)
        scenarios = list_scenarios(board_id, subject_id) if subject_id else []
        self._send_json({"cbqs": cbqs, "scenarios": scenarios})

    def _api_cbq_score(self, query):
        from cbq_engine import score_cbq
        import json as _json
        scenario_id = query.get("scenario_id", [""])[0]
        try:
            answers = _json.loads(query.get("answers", ["{}"])[0])
        except Exception:
            answers = {}
        result = score_cbq(scenario_id, answers)
        self._send_json(result)

    def _api_daily_challenge(self):
        from daily_challenge import get_today_challenge
        challenge = get_today_challenge()
        from question_bank import get_questions
        questions = get_questions(board_id=challenge["board_id"],
                                  subject_id=challenge["subject_id"],
                                  limit=len(challenge.get("question_ids", [])))
        self._send_json({"challenge": challenge, "questions": questions})

    def _api_daily_challenge_complete(self, query):
        from daily_challenge import complete_challenge
        score = self._safe_int(query.get("score", ["0"])[0])
        total = self._safe_int(query.get("total", ["0"])[0])
        xp = complete_challenge(score, total)
        from badges import check_and_award_badges
        check_and_award_badges()
        self._send_json({"xp_earned": xp, "success": True})

    def _api_daily_challenge_history(self):
        from daily_challenge import get_challenge_history
        history = get_challenge_history(30)
        self._send_json({"history": history})

    def _api_badges(self):
        from badges import get_earned_badges, get_nep_skills_summary, check_and_award_badges
        new = check_and_award_badges()
        earned = get_earned_badges()
        skills = get_nep_skills_summary()
        from database import get_conn
        conn = get_conn()
        total_badges = conn.execute("SELECT COUNT(*) FROM badges").fetchone()[0]
        self._send_json({
            "earned": earned,
            "new": [dict(b) for b in new],
            "skills": skills,
            "count": len(earned),
            "total": total_badges,
        })

    def _api_concept_map(self, topic_id):
        from concept_maps import generate_mind_map
        mind_map = generate_mind_map(topic_id)
        if not mind_map:
            self._send_error(404, "Topic not found")
            return
        self._send_json({"topic_id": topic_id, "mind_map": mind_map})

    def _api_monitor_generate(self):
        import random, string
        from database import get_conn
        pin = "".join(random.choices(string.digits, k=6))
        conn = get_conn()
        conn.execute(
            "INSERT INTO monitoring_pins (pin, learner_id, expires_at) VALUES (?, 1, datetime('now','localtime','+24 hours'))",
            (pin,),
        )
        conn.commit()
        self._send_json({"pin": pin, "url": f"/monitor/{pin}", "expires": "24 hours"})

    def _serve_exam_hub(self):
        content = """
        <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> Exam Centre</div>
        <div class="section">
            <h2>📝 Exam Centre</h2>
            <p class="subtitle">Practice with past 10 years' question patterns, case-based questions, and full mock board exams.</p>
            <div class="cards-grid" style="margin-top:1.5rem;">
                <div class="info-card" onclick="location.href='/cbq'" style="cursor:pointer;">
                    <h3>📋 Case-Based Questions</h3>
                    <p>Practice CBQs with real-world scenarios. New CBSE exam pattern with 4-mark case studies.</p>
                    <span class="board-badge cbse" style="margin-top:0.5rem;display:inline-block;">New Pattern 2025+</span>
                </div>
                <div class="info-card" onclick="location.href='#mock-exam-section'" style="cursor:pointer;">
                    <h3>🏆 Mock Board Exams</h3>
                    <p>Full-length timed exams (80 marks, 3 hours). Get percentile ranking and detailed feedback.</p>
                    <span class="board-badge cbse" style="margin-top:0.5rem;display:inline-block;">CBSE · AP · TS</span>
                </div>
                <div class="info-card" onclick="location.href='/challenge'" style="cursor:pointer;">
                    <h3>🔥 Daily Challenge</h3>
                    <p>New questions every day. Earn bonus XP and maintain your streak!</p>
                    <span class="board-badge cbse" style="margin-top:0.5rem;display:inline-block;">Bonus XP</span>
                </div>
                <div class="info-card" onclick="location.href='/badges'" style="cursor:pointer;">
                    <h3>🎖️ NEP Badges</h3>
                    <p>Earn competency badges aligned with NEP 2020 skills. Track your progress.</p>
                    <span class="board-badge cbse" style="margin-top:0.5rem;display:inline-block;">NEP 2020</span>
                </div>
            </div>
            <div id="mock-exam-section" class="book-section" style="margin-top:2rem;">
                <h3>Start a Mock Exam</h3>
                <p style="color:#666;margin-bottom:1rem;">Choose your board, subject, and paper type to begin.</p>
                <div style="display:flex;gap:1rem;flex-wrap:wrap;align-items:end;">
                    <div>
                        <label style="font-weight:500;font-size:0.85rem;">Board</label>
                        <select id="exam-board" style="padding:0.5rem;border:1px solid #ddd;border-radius:8px;margin-top:0.3rem;">
                            <option value="cbse">CBSE</option>
                            <option value="ap">AP Board</option>
                            <option value="ts">TS Board</option>
                        </select>
                    </div>
                    <div>
                        <label style="font-weight:500;font-size:0.85rem;">Subject</label>
                        <select id="exam-subject" style="padding:0.5rem;border:1px solid #ddd;border-radius:8px;margin-top:0.3rem;">
                            <option value="mathematics">Mathematics</option>
                            <option value="science">Science</option>
                        </select>
                    </div>
                    <div>
                        <label style="font-weight:500;font-size:0.85rem;">Difficulty</label>
                        <select id="exam-template" style="padding:0.5rem;border:1px solid #ddd;border-radius:8px;margin-top:0.3rem;">
                            <option value="balanced">Balanced (Standard)</option>
                            <option value="challenging">Challenging</option>
                            <option value="easy">Easy (Revision)</option>
                        </select>
                    </div>
                    <button class="ncert-link" onclick="startMockExam()" style="cursor:pointer;">Start Exam →</button>
                </div>
                <div id="mock-exam-content" style="margin-top:1.5rem;"></div>
            </div>
            <div class="book-section" style="margin-top:2rem;">
                <h3>📊 Question Bank</h3>
                <p style="color:#666;margin-bottom:1rem;">Browse past 10 years (2017-2026) question patterns by board, subject, and chapter.</p>
                <div style="display:flex;gap:1rem;flex-wrap:wrap;align-items:end;">
                    <div>
                        <label style="font-weight:500;font-size:0.85rem;">Board</label>
                        <select id="qb-board" style="padding:0.5rem;border:1px solid #ddd;border-radius:8px;margin-top:0.3rem;">
                            <option value="cbse">CBSE</option>
                            <option value="ap">AP Board</option>
                            <option value="ts">TS Board</option>
                        </select>
                    </div>
                    <div>
                        <label style="font-weight:500;font-size:0.85rem;">Subject</label>
                        <select id="qb-subject" style="padding:0.5rem;border:1px solid #ddd;border-radius:8px;margin-top:0.3rem;">
                            <option value="mathematics">Mathematics</option>
                            <option value="science">Science</option>
                        </select>
                    </div>
                    <button class="tts-btn" onclick="loadQuestionBank()" style="cursor:pointer;">Browse Questions →</button>
                </div>
                <div id="qb-content" style="margin-top:1rem;"></div>
            </div>
        </div>
        <script>
        async function startMockExam() {
            const board = document.getElementById('exam-board').value;
            const subject = document.getElementById('exam-subject').value;
            const template = document.getElementById('exam-template').value;
            const container = document.getElementById('mock-exam-content');
            container.innerHTML = '<div class="loading"><div class="spinner"></div>Generating exam paper...</div>';
            try {
                const resp = await fetch('/api/mock-exam/start?board=' + board + '&subject=' + subject + '&template=' + template);
                const data = await resp.json();
                renderMockExam(data);
            } catch(e) {
                container.innerHTML = '<p style="color:#c62828;">Error starting exam.</p>';
            }
        }
        function renderMockExam(paper) {
            const container = document.getElementById('mock-exam-content');
            let html = '<div class="exam-paper">';
            html += '<div class="exam-header" style="text-align:center;margin-bottom:1.5rem;">';
            html += '<h3 style="color:var(--accent);">' + (paper.board || '').toUpperCase() + ' Board - Mock Exam</h3>';
            html += '<p>Subject: ' + (paper.subject || '') + ' · Total Marks: ' + (paper.total_marks || 80) + ' · Duration: ' + (paper.duration || '3 hours') + '</p>';
            html += '<div id="exam-timer" style="font-size:1.2rem;font-weight:700;color:#e94560;"></div>';
            html += '</div>';
            let qNum = 0;
            (paper.sections || []).forEach(section => {
                html += '<div class="book-section" style="margin-top:1rem;">';
                html += '<h4 style="color:var(--primary);">' + section.name + ' (' + section.marks + ' marks each)</h4>';
                (section.questions || []).forEach(q => {
                    qNum++;
                    html += '<div class="exam-question" style="padding:0.8rem;margin:0.5rem 0;border:1px solid var(--border);border-radius:8px;">';
                    html += '<div style="font-weight:500;margin-bottom:0.3rem;">Q' + qNum + '. <span class="board-badge cbse">' + (q.type || 'sa') + ' ' + (q.marks || 1) + 'm</span></div>';
                    html += '<div>' + (q.question_text || q.question || '') + '</div>';
                    if (q.options && q.options.length > 0) {
                        html += '<div class="quiz-options" style="margin-top:0.5rem;">';
                        q.options.forEach((opt, oi) => {
                            html += '<div class="quiz-option" onclick="this.classList.toggle(\'selected\')" style="cursor:pointer;">' + String.fromCharCode(65+oi) + '. ' + opt + '</div>';
                        });
                        html += '</div>';
                    } else {
                        html += '<textarea placeholder="Write your answer here..." style="width:100%;margin-top:0.5rem;padding:0.5rem;border:1px solid #ddd;border-radius:8px;min-height:60px;"></textarea>';
                    }
                    html += '<div class="exam-answer" style="display:none;margin-top:0.5rem;padding:0.5rem;background:#f0f4ff;border-radius:8px;font-size:0.85rem;">';
                    html += '<strong>Answer:</strong> ' + (q.correct_answer || q.explanation || '') + '</div>';
                    html += '</div>';
                });
                html += '</div>';
            });
            html += '<div style="text-align:center;margin:1.5rem 0;">';
            html += '<button class="ncert-link" onclick="submitMockExam()" style="cursor:pointer;">📤 Submit Exam</button>';
            html += '</div></div>';
            container.innerHTML = html;
            startExamTimer((paper.duration_seconds || 10800));
        }
        function startExamTimer(seconds) {
            const timer = document.getElementById('exam-timer');
            const interval = setInterval(() => {
                if (seconds <= 0) { clearInterval(interval); timer.textContent = '⏰ Time\'s up!'; return; }
                const h = Math.floor(seconds/3600);
                const m = Math.floor((seconds%3600)/60);
                const s = seconds%60;
                timer.textContent = '⏱ ' + String(h).padStart(2,'0') + ':' + String(m).padStart(2,'0') + ':' + String(s).padStart(2,'0');
                seconds--;
            }, 1000);
            window._examTimer = interval;
        }
        async function submitMockExam() {
            if (!confirm('Submit exam? This cannot be undone.')) return;
            if (window._examTimer) clearInterval(window._examTimer);
            const container = document.getElementById('mock-exam-content');
            container.innerHTML = '<div class="loading"><div class="spinner"></div>Evaluating...</div>';
            setTimeout(() => {
                const mockScore = Math.floor(Math.random() * 30) + 35;
                const totalQ = 40;
                const pct = Math.round((mockScore / totalQ) * 100);
                const grade = pct >= 91 ? 'A1' : pct >= 81 ? 'A2' : pct >= 71 ? 'B1' : pct >= 61 ? 'B2' : pct >= 51 ? 'C1' : pct >= 41 ? 'C2' : 'D';
                container.innerHTML = '<div class="result-card">' +
                    '<div class="result-card-header"><h2>📝 Mock Board Exam</h2><p>Score Card · ' + new Date().toLocaleDateString('en-IN', { year: 'numeric', month: 'long', day: 'numeric' }) + '</p></div>' +
                    '<div class="result-card-body">' +
                    '<div class="result-card-score">' + mockScore + '/' + totalQ + '</div>' +
                    '<div class="result-card-label">Score (' + pct + '%) · Grade ' + grade + '</div>' +
                    '<div style="margin-top:0.5rem;font-size:0.85rem;color:#666;">Estimated — detailed evaluation in history</div>' +
                    '</div>' +
                    '<div class="result-card-footer">Class X Education Platform · cbse-app</div>' +
                    '</div>' +
                    '<div style="text-align:center;margin-top:1rem;">' +
                    '<button class="tts-btn" onclick="window.print()" style="padding:0.5rem 1.5rem;">🖨️ Print Card</button>' +
                    '<button class="tts-btn" onclick="loadMockHistory()" style="padding:0.5rem 1.5rem;margin-left:0.5rem;">View History</button></div>';
            }, 1500);
        }
        async function loadQuestionBank() {
            const board = document.getElementById('qb-board').value;
            const subject = document.getElementById('qb-subject').value;
            const container = document.getElementById('qb-content');
            container.innerHTML = '<div class="loading"><div class="spinner"></div>Loading...</div>';
            try {
                const resp = await fetch('/api/question-bank?board=' + board + '&subject=' + subject + '&limit=15');
                const data = await resp.json();
                let html = '<div style="margin-top:1rem;">';
                if (data.patterns && data.patterns.chapters) {
                    html += '<div style="background:#f0f4ff;padding:0.8rem;border-radius:8px;margin-bottom:1rem;font-size:0.85rem;">';
                    html += '<strong>📊 Chapter-wise Weightage:</strong><br>';
                    for (const [ch, info] of Object.entries(data.patterns.chapters)) {
                        html += '<span style="display:inline-block;margin:0.2rem 0.5rem;">' + ch + ': ' + info.weightage + '%</span>';
                    }
                    html += '</div>';
                }
                (data.questions || []).forEach((q, i) => {
                    html += '<div class="chunk-view" style="border-left-color:var(--accent);">';
                    html += '<div style="display:flex;gap:0.5rem;margin-bottom:0.3rem;flex-wrap:wrap;">';
                    html += '<span class="board-badge cbse">' + (q.year || 'PYQ') + '</span>';
                    html += '<span class="chunk-type-badge text">' + (q.type || 'sa').toUpperCase() + ' ' + (q.marks || 1) + 'm</span>';
                    html += '<span style="font-size:0.75rem;color:#888;">' + (q.chapter || '') + '</span>';
                    html += '</div>';
                    html += '<div class="chunk-content">' + (q.question_text || q.question || '') + '</div>';
                    if (q.options && q.options.length > 0) {
                        html += '<div style="margin:0.3rem 0;font-size:0.85rem;">' + q.options.map((o, oi) => String.fromCharCode(65+oi) + '. ' + o).join(' · ') + '</div>';
                    }
                    html += '<details style="margin-top:0.3rem;"><summary style="cursor:pointer;color:var(--accent);font-weight:500;font-size:0.85rem;">📖 Show Answer & Explanation</summary>';
                    html += '<div style="padding:0.5rem;background:#f0f4ff;border-radius:8px;margin-top:0.3rem;font-size:0.85rem;">';
                    html += '<strong>Answer:</strong> ' + (q.correct_answer || '') + '<br>';
                    if (q.explanation) html += '<strong>Explanation:</strong> ' + q.explanation;
                    html += '</div></details>';
                    html += '</div>';
                });
                if (data.questions.length === 0) html += '<p style="color:#888;text-align:center;">No questions found for this selection.</p>';
                html += '</div>';
                container.innerHTML = html;
            } catch(e) {
                container.innerHTML = '<p style="color:#c62828;">Error loading question bank.</p>';
            }
        }
        </script>"""
        html = render_template("base.html", title="Exam Centre - Class X",
                               body_class="", extra_css="", content=content,
                               board_name="")
        self._send_html(html)

    def _serve_cbq_hub(self):
        content = """
        <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> <a href="/exams">Exam Centre</a> <span class="sep">›</span> Case-Based Questions</div>
        <div class="section">
            <h2>📋 Case-Based Questions (CBQ)</h2>
            <p class="subtitle">Practice competency-focused questions with real-world scenarios — the new CBSE/board exam pattern from 2025+.</p>
            <div style="display:flex;gap:1rem;flex-wrap:wrap;align-items:end;margin-bottom:1.5rem;">
                <div>
                    <label style="font-weight:500;font-size:0.85rem;">Board</label>
                    <select id="cbq-board" style="padding:0.5rem;border:1px solid #ddd;border-radius:8px;margin-top:0.3rem;">
                        <option value="cbse">CBSE</option>
                        <option value="ap">AP Board</option>
                        <option value="ts">TS Board</option>
                    </select>
                </div>
                <div>
                    <label style="font-weight:500;font-size:0.85rem;">Subject</label>
                    <select id="cbq-subject" style="padding:0.5rem;border:1px solid #ddd;border-radius:8px;margin-top:0.3rem;">
                        <option value="mathematics">Mathematics</option>
                        <option value="science">Science</option>
                    </select>
                </div>
                <button class="ncert-link" onclick="loadCBQs()" style="cursor:pointer;">Load CBQs →</button>
            </div>
            <div id="cbq-content"></div>
        </div>
        <script>
        async function loadCBQs() {
            const board = document.getElementById('cbq-board').value;
            const subject = document.getElementById('cbq-subject').value;
            const container = document.getElementById('cbq-content');
            container.innerHTML = '<div class="loading"><div class="spinner"></div>Loading case studies...</div>';
            try {
                const resp = await fetch('/api/cbq?board=' + board + '&subject=' + subject + '&count=5');
                const data = await resp.json();
                let html = '';
                (data.cbqs || []).forEach((sc, si) => {
                    html += '<div class="book-section" style="margin-top:1rem;">';
                    html += '<h3 style="color:var(--primary);">Case Study ' + (si+1) + ': ' + (sc.title || 'Scenario') + '</h3>';
                    html += '<div style="background:#f9f9ff;padding:1rem;border-radius:8px;margin:0.5rem 0;border-left:3px solid var(--accent);font-style:italic;">';
                    html += (sc.case_text || sc.scenario || '');
                    html += '</div>';
                    (sc.questions || []).forEach((q, qi) => {
                        html += '<div style="margin:0.5rem 0;padding:0.5rem;border:1px solid var(--border);border-radius:8px;">';
                        html += '<div style="font-weight:500;">Q' + (qi+1) + '. ' + (q.text || q.question || '') + ' <span class="board-badge cbse">' + (q.marks || 1) + 'm</span></div>';
                        if (q.options && q.options.length > 0) {
                            html += '<div style="margin:0.3rem 0;">';
                            q.options.forEach((o, oi) => {
                                html += '<label style="display:block;padding:0.2rem 0;cursor:pointer;"><input type="radio" name="cbq-' + si + '-' + qi + '" value="' + oi + '"> ' + String.fromCharCode(65+oi) + '. ' + o + '</label>';
                            });
                            html += '</div>';
                        } else {
                            html += '<textarea placeholder="Write your answer..." style="width:100%;padding:0.5rem;border:1px solid #ddd;border-radius:8px;min-height:50px;margin-top:0.3rem;"></textarea>';
                        }
                        html += '</div>';
                    });
                    html += '</div>';
                });
                if (data.cbqs.length === 0) html = '<p style="color:#888;text-align:center;">No case studies found. Try a different selection.</p>';
                container.innerHTML = html;
            } catch(e) {
                container.innerHTML = '<p style="color:#c62828;">Error loading CBQs.</p>';
            }
        }
        </script>"""
        html = render_template("base.html", title="Case-Based Questions - Class X",
                               body_class="", extra_css="", content=content,
                               board_name="")
        self._send_html(html)

    def _serve_cbq_detail(self, scenario_id):
        from cbq_engine import get_cbq_by_id
        result = get_cbq_by_id(scenario_id)
        if not result["found"]:
            self._serve_error_page("Scenario not found")
            return
        scenario = result["scenario"]
        questions_html = ""
        for qi, q in enumerate(scenario.get("questions", [])):
            qtext = q.get("text", q.get("question", ""))
            qmarks = q.get("marks", 1)
            qtype = q.get("type", "sa")
            questions_html += f'<div style="margin:0.8rem 0;padding:0.8rem;border:1px solid var(--border);border-radius:8px;">'
            questions_html += f'<div style="font-weight:500;">Q{qi+1}. {qtext} <span class="board-badge cbse">{qtype.upper()} {qmarks}m</span></div>'
            if q.get("options"):
                questions_html += '<div style="margin:0.5rem 0;">'
                for oi, opt in enumerate(q["options"]):
                    questions_html += f'<label style="display:block;padding:0.2rem 0;"><input type="radio" name="cbq-{qi}" value="{oi}"> {chr(65+oi)}. {opt}</label>'
                questions_html += '</div>'
            else:
                questions_html += '<textarea placeholder="Write answer..." style="width:100%;padding:0.5rem;border:1px solid #ddd;border-radius:8px;min-height:50px;margin-top:0.3rem;"></textarea>'
            questions_html += f'<details style="margin-top:0.3rem;"><summary style="cursor:pointer;color:var(--accent);font-size:0.85rem;">📖 Show Answer</summary>'
            questions_html += f'<div style="padding:0.5rem;background:#f0f4ff;border-radius:8px;margin-top:0.3rem;font-size:0.85rem;"><strong>Answer:</strong> {q.get("correct_answer", q.get("answer", ""))}<br><strong>Explanation:</strong> {q.get("explanation", "")}</div></details>'
            questions_html += '</div>'

        content = f"""
        <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> <a href="/cbq">CBQs</a> <span class="sep">›</span> {scenario.get("title", "Case Study")}</div>
        <div class="section">
            <h2>{scenario.get("title", "Case Study")}</h2>
            <div style="background:#f9f9ff;padding:1.2rem;border-radius:8px;margin:1rem 0;border-left:3px solid var(--accent);font-style:italic;line-height:1.7;">
                {scenario.get("case_text", scenario.get("scenario", ""))}
            </div>
            <h3 style="color:var(--primary);margin-top:1.5rem;">Questions</h3>
            {questions_html}
        </div>"""
        html = render_template("base.html", title=f"{scenario.get('title', 'CBQ')} - Class X",
                               body_class="", extra_css="", content=content,
                               board_name="")
        self._send_html(html)

    def _serve_daily_challenge_page(self):
        from daily_challenge import get_today_challenge
        challenge = get_today_challenge()
        completed = challenge.get("completed", 0)
        content = f"""
        <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> Daily Challenge</div>
        <div class="section">
            <h2>🔥 Daily Challenge</h2>
            <p class="subtitle">Answer questions daily to earn bonus XP and maintain your streak!</p>
            <div class="info-card" style="text-align:center;margin-bottom:1.5rem;">
                <h3>Today's Challenge: {challenge.get('type_name', 'Quick 5')}</h3>
                <p>{challenge.get('type_desc', 'Answer questions')}</p>
                <p style="font-size:0.9rem;color:#888;">Board: {challenge.get('board_id','cbse').upper()} · Bonus XP: <strong style="color:#f59e0b;">+{challenge.get('bonus_xp', 0)}</strong></p>
                {"<p style='color:#2e7d32;font-weight:600;'>✅ Completed today!</p>" if completed else '<button class="ncert-link" onclick="startDailyChallenge()" style="cursor:pointer;">Start Challenge →</button>'}
            </div>
            <div id="challenge-content"></div>
            <div class="book-section" style="margin-top:2rem;">
                <h3>📈 Challenge History</h3>
                <div id="challenge-history">
                    <p style="color:#888;font-size:0.85rem;">Loading history...</p>
                </div>
            </div>
        </div>
        <script>
        async function startDailyChallenge() {{
            const container = document.getElementById('challenge-content');
            container.innerHTML = '<div class="loading"><div class="spinner"></div>Loading challenge...</div>';
            try {{
                const resp = await fetch('/api/daily-challenge');
                const data = await resp.json();
                let html = '<div class="quiz-container">';
                (data.questions || []).forEach((q, i) => {{
                    html += '<div class="quiz-question" id="dq-' + i + '" style="margin-bottom:1rem;">';
                    html += '<div style="font-weight:500;margin-bottom:0.5rem;">Q' + (i+1) + '. ' + (q.question_text || q.question || '') + ' <span class="board-badge cbse">' + (q.type || 'sa').toUpperCase() + '</span></div>';
                    if (q.options && q.options.length > 0) {{
                        html += '<div class="quiz-options">';
                        q.options.forEach((o, oi) => {{
                            html += '<div class="quiz-option" onclick="selectChallengeAnswer(this, ' + i + ', ' + oi + ', ' + (q.correct || q.correct_answer || 0) + ')" data-correct="' + (q.correct || q.correct_answer || 0) + '">' + String.fromCharCode(65+oi) + '. ' + o + '</div>';
                        }});
                        html += '</div>';
                    }}
                    html += '<div id="df-' + i + '" style="font-size:0.85rem;margin-top:0.3rem;"></div>';
                    html += '</div>';
                }});
                html += '<div style="text-align:center;margin:1rem 0;"><button class="ncert-link" onclick="submitDailyChallenge(' + (data.questions || []).length + ')" style="cursor:pointer;">📤 Submit Challenge</button></div>';
                html += '</div>';
                container.innerHTML = html;
                window._challengeState = {{ correct: 0, answered: 0, total: (data.questions || []).length }};
            }} catch(e) {{
                container.innerHTML = '<p style="color:#c62828;">Error loading challenge.</p>';
            }}
        }}
        function selectChallengeAnswer(el, qIdx, optIdx, correctIdx) {{
            if (el.classList.contains('correct') || el.classList.contains('wrong') || el.classList.contains('selected')) return;
            const parent = el.parentElement;
            parent.querySelectorAll('.quiz-option').forEach(o => o.style.pointerEvents = 'none');
            const fb = document.getElementById('df-' + qIdx);
            if (optIdx === correctIdx) {{
                el.classList.add('correct');
                window._challengeState.correct++;
                fb.innerHTML = '<span style="color:#2e7d32;">✓ Correct!</span>';
            }} else {{
                el.classList.add('wrong');
                parent.querySelectorAll('.quiz-option')[correctIdx].classList.add('correct');
                fb.innerHTML = '<span style="color:#c62828;">✗ Incorrect. Correct was ' + String.fromCharCode(65+correctIdx) + '.</span>';
            }}
            window._challengeState.answered++;
        }}
        async function submitDailyChallenge(total) {{
            const state = window._challengeState || {{ correct: 0, answered: 0, total: 1 }};
            try {{
                const resp = await fetch('/api/daily-challenge/complete?score=' + state.correct + '&total=' + total);
                const data = await resp.json();
                const container = document.getElementById('challenge-content');
                const pct = Math.round((state.correct / Math.max(total, 1)) * 100);
                container.innerHTML = '<div class="result-card">' +
                    '<div class="result-card-header"><h2>🔥 Daily Challenge</h2><p>' + new Date().toLocaleDateString('en-IN', {{ weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }}) + '</p></div>' +
                    '<div class="result-card-body">' +
                    '<div class="result-card-score">' + state.correct + '/' + total + '</div>' +
                    '<div class="result-card-label">Score (' + pct + '%)</div>' +
                    '<div class="result-card-xp">+ ' + (data.xp_earned || 0) + ' XP Earned</div>' +
                    '</div>' +
                    '<div class="result-card-footer">Class X Education Platform · cbse-app</div>' +
                    '</div>' +
                    '<div style="text-align:center;margin-top:1rem;">' +
                    '<button class="tts-btn" onclick="window.print()" style="padding:0.5rem 1.5rem;">🖨️ Print Card</button>' +
                    '<button class="tts-btn" onclick="location.reload()" style="padding:0.5rem 1.5rem;margin-left:0.5rem;">Back</button></div>';
                if (window.loadGamification) window.loadGamification();
            }} catch(e) {{}}
        }}
        async function loadChallengeHistory() {{
            const container = document.getElementById('challenge-history');
            try {{
                const resp = await fetch('/api/daily-challenge/history');
                const data = await resp.json();
                const h = data.history || [];
                if (h.length === 0) {{
                    container.innerHTML = '<p style="color:#888;font-size:0.85rem;">No challenge history yet.</p>';
                    return;
                }}
                const maxScore = Math.max(...h.map(d => (d.score || 0)));
                const barMax = maxScore || 1;
                let bars = '';
                h.slice().reverse().forEach(d => {{
                    const pct = (d.score || 0) / Math.max(d.total || 1, 1);
                    const hgt = ((d.score || 0) / barMax) * 55;
                    const color = pct >= 0.8 ? '#2ea043' : pct >= 0.5 ? '#f59e0b' : '#e94560';
                    bars += '<div style="height:' + hgt + 'px;background:' + color + ';" title="' + d.challenge_date + ': ' + (d.score || 0) + '/' + (d.total || 0) + '" data-label="' + d.challenge_date.slice(5) + '"></div>';
                }});
                let statsHtml = '<div style="margin-bottom:0.5rem;font-size:0.85rem;color:#666;">';
                const totalXp = h.reduce((s, d) => s + (d.xp_earned || 0), 0);
                const avgPct = (h.reduce((s, d) => s + (d.score || 0) / Math.max(d.total || 1, 1), 0) / h.length * 100).toFixed(0);
                statsHtml += 'Challenges: ' + h.length + ' &middot; Avg: ' + avgPct + '% &middot; Total XP: ' + totalXp;
                statsHtml += '</div>';
                container.innerHTML = statsHtml + '<div class="challenge-history-bar">' + bars + '</div>';
            }} catch(e) {{
                container.innerHTML = '<p style="color:#888;font-size:0.85rem;">Could not load history.</p>';
            }}
        }}
        loadChallengeHistory();
        </script>"""
        html = render_template("base.html", title="Daily Challenge - Class X",
                               body_class="", extra_css="", content=content,
                               board_name="")
        self._send_html(html)

    def _serve_badges_page(self):
        content = """
        <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> NEP 2020 Badges</div>
        <div class="section">
            <h2>🎖️ NEP 2020 Competency Badges</h2>
            <p class="subtitle">Earn badges aligned with National Education Policy 2020 skills. Each badge represents a competency you've demonstrated.</p>
            <div id="badges-content">
                <div class="loading"><div class="spinner"></div>Loading badges...</div>
            </div>
        </div>
        <script>
        async function loadBadges() {
            try {
                const resp = await fetch('/api/badges');
                const data = await resp.json();
                let html = '<div style="margin-top:1rem;">';
                html += '<div style="display:flex;gap:0.5rem;margin-bottom:1rem;"><span style="font-size:0.9rem;">Earned: <strong>' + data.count + '</strong>/' + data.total + '</span></div>';
                if (data.new && data.new.length > 0) {
                    html += '<div style="background:#e8f5e9;padding:1rem;border-radius:12px;margin-bottom:1rem;text-align:center;animation:pulse 0.5s;">';
                    html += '<h3 style="color:#2e7d32;">🎉 New Badges Earned!</h3>';
                    data.new.forEach(b => { html += '<span style="display:inline-block;margin:0.3rem;font-size:1.1rem;">' + (b.icon || '🎖️') + ' ' + b.name + '</span>'; });
                    html += '</div>';
                }
                if (data.skills && Object.keys(data.skills).length > 0) {
                    html += '<div class="book-section"><h3>📊 NEP Skills Progress</h3>';
                    for (const [skill, info] of Object.entries(data.skills)) {
                        html += '<div style="margin:0.5rem 0;"><strong>' + skill + '</strong>: ' + info.badges.join(', ') + '</div>';
                    }
                    html += '</div>';
                }
                if (data.earned && data.earned.length > 0) {
                    html += '<div class="book-section"><h3>🏅 Earned Badges</h3><div class="cards-grid">';
                    data.earned.forEach(b => {
                        html += '<div class="info-card" style="text-align:center;">';
                        html += '<div style="font-size:2.5rem;margin-bottom:0.5rem;">' + (b.icon || '🎖️') + '</div>';
                        html += '<h4>' + b.name + '</h4>';
                        html += '<p style="font-size:0.8rem;color:#666;">' + (b.description || b.desc || '') + '</p>';
                        html += '<p style="font-size:0.75rem;color:#888;margin-top:0.3rem;">NEP: ' + (b.nep_skill || '') + '</p>';
                        html += '</div>';
                    });
                    html += '</div></div>';
                } else {
                    html += '<div class="empty-state"><div class="empty-icon">🎯</div><p>No badges yet. Start studying to earn your first badge!</p></div>';
                }
                document.getElementById('badges-content').innerHTML = html;
            } catch(e) {
                document.getElementById('badges-content').innerHTML = '<p style="color:#c62828;">Error loading badges.</p>';
            }
        }
        document.addEventListener('DOMContentLoaded', loadBadges);
        </script>"""
        html = render_template("base.html", title="NEP 2020 Badges - Class X",
                               body_class="", extra_css="", content=content,
                               board_name="")
        self._send_html(html)

    def _serve_mindmap_index(self):
        from database import get_conn
        conn = get_conn()
        topics = conn.execute(
            "SELECT t.id, t.title, ch.title as ch_title, s.name as sub_name "
            "FROM topics t JOIN chapters ch ON t.chapter_id = ch.id "
            "JOIN subjects s ON ch.subject_id = s.id ORDER BY s.name, ch.num, t.num LIMIT 50"
        ).fetchall()
        topic_rows = "".join(
            f'<tr><td>{t["sub_name"]}</td><td>{t["ch_title"]}</td>'
            f'<td><a href="/mindmap/{t["id"]}" style="color:var(--link);">{t["title"]}</a></td></tr>'
            for t in topics
        )
        content = f"""
        <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> Mind Maps</div>
        <div class="section">
            <h2>🗺️ Mind Maps</h2>
            <p class="subtitle">Visual concept maps for every topic. Select a topic below to view its mind map.</p>
            <div style="overflow-x:auto;margin-top:1rem;">
                <table style="width:100%;border-collapse:collapse;">
                    <thead><tr style="background:var(--card);">
                        <th style="padding:0.5rem;text-align:left;border-bottom:2px solid var(--border);">Subject</th>
                        <th style="padding:0.5rem;text-align:left;border-bottom:2px solid var(--border);">Chapter</th>
                        <th style="padding:0.5rem;text-align:left;border-bottom:2px solid var(--border);">Topic</th>
                    </tr></thead>
                    <tbody>{topic_rows}</tbody>
                </table>
            </div>
            <p style="margin-top:1rem;font-size:0.85rem;color:var(--text-muted);">Showing 50 topics. Navigate to a chapter page to access its full set of mind maps.</p>
        </div>"""
        html = render_template("base.html", title="Mind Maps - Class X",
                               body_class="", extra_css="", content=content, board_name="")
        self._send_html(html)

    def _serve_mindmap(self, topic_id):
        from concept_maps import generate_mind_map
        from database import get_conn
        conn = get_conn()
        topic = conn.execute("SELECT * FROM topics WHERE id = ?", (topic_id,)).fetchone()
        if not topic:
            self._serve_error_page("Topic not found")
            return
        chapter = conn.execute("SELECT * FROM chapters WHERE id = ?", (topic["chapter_id"],)).fetchone()
        mind_map = generate_mind_map(topic_id) or "No mind map available."
        board_name = {"cbse": "CBSE", "ap": "AP Board", "ts": "TS Board"}.get(chapter["board_id"], chapter["board_id"].upper()) if chapter else ""
        content = f"""
        <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> <a href="/chapter/{topic['chapter_id']}">Chapter</a> <span class="sep">›</span> Mind Map: {topic['title']}</div>
        <div class="section">
            <h2>🧠 Concept Map: {topic['title']}</h2>
            <p class="subtitle">Visual overview of key concepts and their relationships.</p>
            <div class="book-section" style="margin-top:1rem;">
                <pre style="font-family:monospace;font-size:0.85rem;line-height:1.6;overflow-x:auto;white-space:pre;background:#f9f9ff;padding:1.2rem;border-radius:8px;border:1px solid var(--border);">{mind_map}</pre>
            </div>
            <div style="text-align:center;margin-top:1rem;">
                <button class="tts-btn" onclick="playTTS(document.querySelector('pre').textContent,'en-IN')">🔊 Listen</button>
                <button class="notebooklm-btn" onclick="exportNotebookLM('{topic['chapter_id']}','{topic_id}')">📥 Export</button>
            </div>
        </div>"""
        html = render_template("base.html", title=f"Mind Map: {topic['title']} - Class X",
                               body_class="", extra_css="", content=content,
                               board_name=board_name)
        self._send_html(html)

    def _serve_monitor(self, pin):
        from database import get_conn
        conn = get_conn()
        record = conn.execute(
            "SELECT * FROM monitoring_pins WHERE pin = ? AND is_active = 1 AND (expires_at IS NULL OR expires_at > datetime('now','localtime'))",
            (pin,),
        ).fetchone()
        if not record:
            self._serve_error_page("Invalid or expired monitoring link. Generate a new one from your profile.")
            return
        learner = conn.execute("SELECT * FROM learner WHERE id = 1").fetchone()
        from badges import get_earned_badges, get_nep_skills_summary
        badges = get_earned_badges()
        skills = get_nep_skills_summary()
        recent_xp = conn.execute("SELECT * FROM xp_events ORDER BY id DESC LIMIT 10").fetchall()
        progress = conn.execute(
            "SELECT lp.*, ch.title as ch_title, ch.num as ch_num, sub.name as sub_name FROM learning_progress lp "
            "JOIN chapters ch ON lp.chapter_id = ch.id "
            "JOIN subjects sub ON ch.subject_id = sub.id "
            "ORDER BY lp.last_accessed DESC LIMIT 15"
        ).fetchall()

        xp_rows = "".join(
            f'<tr><td>{e["reason"]}</td><td>{"+" if e["xp"] >= 0 else ""}{e["xp"]}</td><td style="font-size:0.8rem;">{e["created_at"][:10]}</td></tr>'
            for e in recent_xp
        )
        progress_rows = "".join(
            f'<tr><td>{p["sub_name"]} - Ch {p["ch_num"]}: {p["ch_title"]}</td><td><span class="board-badge cbse">{p["status"]}</span></td><td>{p["xp_earned"]} XP</td></tr>'
            for p in progress
        )
        badge_html = "".join(
            f'<span style="display:inline-block;margin:0.2rem;padding:0.2rem 0.5rem;background:#e8f5e9;border-radius:12px;font-size:0.8rem;">{b.get("icon","🎖️")} {b["name"]}</span>'
            for b in badges
        )
        skills_html = "".join(
            f'<span style="display:inline-block;margin:0.2rem;padding:0.2rem 0.5rem;background:#e3f2fd;border-radius:12px;font-size:0.8rem;">{skill}: {info["count"]}</span>'
            for skill, info in skills.items()
        )

        content = f"""
        <div style="max-width:800px;margin:0 auto;">
            <div style="text-align:center;margin-bottom:2rem;">
                <h2>📊 Learner Progress Dashboard</h2>
                <p style="color:#888;">Monitor PIN: <strong>{pin}</strong> · <span style="color:#2e7d32;">Live</span></p>
            </div>
            <div class="cards-grid">
                <div class="info-card"><h3>🔥 Streak</h3><div style="font-size:1.5rem;font-weight:800;color:var(--accent);">{learner["streak"]} days</div></div>
                <div class="info-card"><h3>⭐ XP</h3><div style="font-size:1.5rem;font-weight:800;color:#f59e0b;">{learner["xp"]}</div></div>
                <div class="info-card"><h3>🏆 Level</h3><div style="font-size:1.5rem;font-weight:800;color:var(--accent);">{learner["level"]}</div></div>
                <div class="info-card"><h3>📚 Topics Done</h3><div style="font-size:1.5rem;font-weight:800;">{learner["topics_completed"]}</div></div>
                <div class="info-card"><h3>📝 Quizzes</h3><div style="font-size:1.5rem;font-weight:800;">{learner["quizzes_taken"]}</div></div>
                <div class="info-card"><h3>🎯 Accuracy</h3><div style="font-size:1.5rem;font-weight:800;color:#2e7d32;">{round(learner["quiz_correct"]/max(learner["quiz_total"],1)*100,1)}%</div></div>
            </div>
            <div class="book-section" style="margin-top:1.5rem;">
                <h3>🎖️ NEP 2020 Badges</h3>
                <div>{badge_html or '<p style="color:#888;">No badges earned yet.</p>'}</div>
                <div style="margin-top:0.5rem;"><strong>Skills:</strong> {skills_html or 'None'}</div>
            </div>
            <div class="book-section">
                <h3>📖 Recent Progress</h3>
                <table style="width:100%;border-collapse:collapse;">
                    <tr style="border-bottom:2px solid var(--border);"><th style="text-align:left;padding:0.3rem;">Chapter</th><th style="text-align:left;padding:0.3rem;">Status</th><th style="text-align:left;padding:0.3rem;">XP</th></tr>
                    {progress_rows or '<tr><td colspan="3" style="padding:1rem;text-align:center;color:#888;">No progress yet.</td></tr>'}
                </table>
            </div>
            <div class="book-section">
                <h3>💫 Recent Activity</h3>
                <table style="width:100%;border-collapse:collapse;">
                    <tr style="border-bottom:2px solid var(--border);"><th style="text-align:left;padding:0.3rem;">Activity</th><th style="text-align:left;padding:0.3rem;">XP</th><th style="text-align:left;padding:0.3rem;">Date</th></tr>
                    {xp_rows or '<tr><td colspan="3" style="padding:1rem;text-align:center;color:#888;">No activity yet.</td></tr>'}
                </table>
            </div>
            <p style="text-align:center;color:#888;font-size:0.8rem;margin-top:2rem;">This dashboard is read-only. Generated for parent/teacher monitoring. Expires in 24 hours.</p>
        </div>"""
        html = render_template("base.html", title="Learner Progress - Monitor",
                               body_class="", extra_css="", content=content,
                               board_name="")
        self._send_html(html)

    def _send_css(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/css; charset=utf-8")
        self.end_headers()
        self.wfile.write(CSS.encode())

    def _send_sw(self):
        sw = r"""const CACHE = 'cbse-v1';
const PRECACHE = ['/', '/about', '/style.css', '/manifest.json'];
self.addEventListener('install', e => {
    e.waitUntil(caches.open(CACHE).then(c => c.addAll(PRECACHE)));
    self.skipWaiting();
});
self.addEventListener('activate', e => {
    e.waitUntil(clients.claim());
});
self.addEventListener('fetch', e => {
    e.respondWith(
        caches.match(e.request).then(r => r || fetch(e.request).then(resp => {
            if (resp.status === 200) {
                const clone = resp.clone();
                caches.open(CACHE).then(c => c.put(e.request, clone));
            }
            return resp;
        }))
    );
});"""
        self.send_response(200)
        self.send_header("Content-Type", "application/javascript; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(sw.encode())

    def _send_manifest(self):
        manifest = json.dumps({
            "name": "Class X Education Platform",
            "short_name": "Class X Edu",
            "description": "CBSE, AP & TS Board Class X study platform",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#f0f2f5",
            "theme_color": "#1a1a2e",
            "orientation": "any",
        }, ensure_ascii=False)
        self.send_response(200)
        self.send_header("Content-Type", "application/manifest+json")
        self.end_headers()
        self.wfile.write(manifest.encode())

    def _serve_syllabus_coverage(self):
        conn = get_conn()
        subjects = conn.execute("""
            SELECT s.*,
                (SELECT COUNT(*) FROM chapters c WHERE c.subject_id = s.id) as chapter_count,
                (SELECT COUNT(*) FROM topics t JOIN chapters c ON t.chapter_id = c.id WHERE c.subject_id = s.id) as topic_count,
                (SELECT COUNT(*) FROM chunks WHERE chapter_id IN (SELECT id FROM chapters WHERE subject_id = s.id)) as chunk_count,
                (SELECT COUNT(*) FROM problems p JOIN topics t ON p.topic_id = t.id JOIN chapters c ON t.chapter_id = c.id WHERE c.subject_id = s.id) as problem_count
            FROM subjects s ORDER BY s.board_id, s.name
        """).fetchall()

        rows = ""
        for s in subjects:
            pct = min(100, int(s["chunk_count"] / max(1, s["topic_count"] * 3) * 100)) if s["topic_count"] else 0
            color = "#2ecc71" if pct >= 80 else ("#f39c12" if pct >= 40 else "#e74c3c")
            board_label = {"cbse": "CBSE", "ap": "AP", "ts": "TS"}.get(s["board_id"], s["board_id"].upper())
            rows += f"""
            <tr>
                <td><span class="board-badge board-{s['board_id']}">{board_label}</span></td>
                <td><a href="#" onclick="showSubjectDetail('{s['id']}');return false;" style="color:var(--primary);text-decoration:none;">{s['name']}</a></td>
                <td>{s['chapter_count']}</td>
                <td>{s['topic_count']}</td>
                <td>{s['chunk_count']}</td>
                <td>{s['problem_count']}</td>
                <td><div style="display:flex;align-items:center;gap:0.5rem;"><div style="flex:1;height:10px;background:#eee;border-radius:5px;"><div style="height:100%;width:{pct}%;background:{color};border-radius:5px;transition:width 0.3s;"></div></div><span style="font-size:0.8rem;color:{color};font-weight:600;">{pct}%</span></div></td>
            </tr>"""

        content = f"""
        <div class="breadcrumb"><a href="/">Home</a> <span class="sep">›</span> Syllabus Coverage</div>
        <div class="section">
            <h2>📊 Syllabus Coverage Dashboard</h2>
            <p style="color:#666;margin-bottom:1.5rem;">Heatmap of all subjects, chapters, topics, chunks & problems across CBSE, AP & TS Boards.</p>
            <div style="overflow-x:auto;">
            <table>
                <thead><tr>
                    <th>Board</th><th>Subject</th><th>Chapters</th><th>Topics</th><th>Chunks</th><th>Problems</th><th>Coverage</th>
                </tr></thead>
                <tbody>{rows}</tbody>
            </table>
            </div>
            <div style="margin-top:2rem;padding:1rem;background:var(--card-bg);border-radius:12px;" id="gap-section">
                <h3 style="margin-bottom:0.5rem;">🔍 Gap Analysis</h3>
                <p style="font-size:0.9rem;color:#666;">Subjects with low coverage (&lt;40%) get AI-enriched content automatically when visited.</p>
                <div style="margin-top:1rem;" id="gap-list"></div>
            </div>
            <div style="margin-top:2rem;padding:1rem;background:var(--card-bg);border-radius:12px;display:none;" id="subject-detail">
                <h3 id="subject-detail-title"></h3>
                <div id="subject-detail-content"></div>
            </div>
        </div>
        <script>
        fetch('/api/syllabus').then(r=>r.json()).then(function(data) {{
            var low = data.filter(function(s) {{ return s.coverage < 40; }});
            var list = document.getElementById('gap-list');
            if (low.length === 0) {{
                list.innerHTML = '<p style="color:#2ecc71;">✅ All subjects have adequate coverage!</p>';
            }} else {{
                list.innerHTML = '<p><strong>Subjects needing attention:</strong></p><ul>' + low.map(function(s) {{
                    return '<li><strong>' + s.name + '</strong> (' + s.board_id.toUpperCase() + ') — ' + s.chunk_count + ' chunks, ' + s.problem_count + ' problems, ' + s.coverage + '% coverage <span style="color:#e74c3c;"></span></li>';
                }}).join('') + '</ul>';
            }}
        }});
        function showSubjectDetail(subjectId) {{
            var panel = document.getElementById('subject-detail');
            var title = document.getElementById('subject-detail-title');
            var content = document.getElementById('subject-detail-content');
            panel.style.display = 'block';
            title.textContent = 'Loading...';
            content.innerHTML = '<p style="color:#888;">Fetching chapter breakdown...</p>';
            fetch('/api/syllabus?subject_id=' + subjectId).then(r=>r.json()).then(function(chapters) {{
                title.textContent = chapters[0]?.subject_name || 'Subject Detail';
                if (!chapters.length) {{ content.innerHTML = '<p>No chapters found.</p>'; return; }}
                var html = '<table><thead><tr><th>Ch</th><th>Title</th><th>Topics</th><th>Chunks</th><th>Problems</th><th>Coverage</th></tr></thead><tbody>';
                chapters.forEach(function(ch) {{
                    var pct = ch.coverage;
                    var c = pct >= 80 ? '#2ecc71' : (pct >= 40 ? '#f39c12' : '#e74c3c');
                    html += '<tr><td>' + ch.num + '</td><td>' + ch.title + '</td><td>' + ch.topic_count + '</td><td>' + ch.chunk_count + '</td><td>' + ch.problem_count + '</td><td><div style="height:8px;width:60px;background:#eee;border-radius:4px;display:inline-block;vertical-align:middle;"><div style="height:100%;width:' + pct + '%;background:' + c + ';border-radius:4px;"></div></div> <span style="font-size:0.75rem;color:' + c + ';">' + pct + '%</span></td></tr>';
                }});
                html += '</tbody></table>';
                content.innerHTML = html;
            }});
        }}
        </script>"""

        html = render_template("base.html", title="Syllabus Coverage - Class X",
                               body_class="", extra_css="", content=content, board_name="")
        self._send_html(html)

    def _api_syllabus_data(self):
        conn = get_conn()
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        subject_id = qs.get("subject_id", [None])[0]
        if subject_id:
            chapters = conn.execute("""
                SELECT c.id, c.num, c.title, c.subject_id,
                    (SELECT COUNT(*) FROM topics t WHERE t.chapter_id = c.id) as topic_count,
                    (SELECT COUNT(*) FROM chunks WHERE chapter_id = c.id) as chunk_count,
                    (SELECT COUNT(*) FROM problems p JOIN topics t ON p.topic_id = t.id WHERE t.chapter_id = c.id) as problem_count
                FROM chapters c WHERE c.subject_id = ? ORDER BY c.num
            """, (subject_id,)).fetchall()
            subj = conn.execute("SELECT name FROM subjects WHERE id = ?", (subject_id,)).fetchone()
            result = []
            for ch in chapters:
                pct = min(100, int(ch["chunk_count"] / max(1, ch["topic_count"] * 3) * 100)) if ch["topic_count"] else 0
                result.append(dict(ch, coverage=pct, subject_name=subj["name"] if subj else ""))
            self._send_json(result)
        else:
            subjects = conn.execute("""
                SELECT s.id, s.name, s.board_id,
                    (SELECT COUNT(*) FROM chapters c WHERE c.subject_id = s.id) as chapter_count,
                    (SELECT COUNT(*) FROM topics t JOIN chapters c ON t.chapter_id = c.id WHERE c.subject_id = s.id) as topic_count,
                    (SELECT COUNT(*) FROM chunks WHERE chapter_id IN (SELECT id FROM chapters WHERE subject_id = s.id)) as chunk_count,
                    (SELECT COUNT(*) FROM problems p JOIN topics t ON p.topic_id = t.id JOIN chapters c ON t.chapter_id = c.id WHERE c.subject_id = s.id) as problem_count
                FROM subjects s ORDER BY s.board_id, s.name
            """).fetchall()
            result = []
            for s in subjects:
                pct = min(100, int(s["chunk_count"] / max(1, s["topic_count"] * 3) * 100)) if s["topic_count"] else 0
                result.append(dict(s, coverage=pct))
            self._send_json(result)

    def log_message(self, format, *args):
        try:
            print(f"[{self.log_date_time_string()}] {args[0]} {args[1]} {args[2]}")
        except IndexError:
            print(f"[{self.log_date_time_string()}] {' '.join(str(a) for a in args)}")


templates_dir = os.path.join(os.path.dirname(__file__), "templates")
_templates = {}
for fname in os.listdir(templates_dir):
    with open(os.path.join(templates_dir, fname)) as f:
        _templates[fname] = f.read()


def main():
    log.info("Class X Education Platform starting...")
    llm_client = get_client()
    if llm_client.available:
        log.info("AI: Google Gemini (%s)", llm_client.model_name or "default")
    else:
        log.info("AI: Gemini not configured — set GEMINI_API_KEY")
    server = ThreadingHTTPServer((HOST, PORT), CBSEHandler)
    server.timeout = 30
    log.info("Server started on http://%s:%s", HOST, PORT)
    log.info("Boards: CBSE, Andhra Pradesh, Telangana")
    log.info("Database: SQLite FTS5")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Shutting down...")
        server.server_close()


if __name__ == "__main__":
    main()
