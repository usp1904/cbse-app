"""AI Services Layer — zero API keys required.
Napkin AI, Gamma, Quillbot, LLM Research, LLM Literature,
SVG Visualize, Tome, NotebookLM, Gemma 4, Browser Music"""

import json
import os
import re
import html as html_mod
import urllib.parse

from llm_client import get_client


def _get_rag_context(query, board=None, subject=None, limit=5):
    try:
        from rag_engine import get_engine
        engine = get_engine()
        results = engine.hybrid_search(query, board=board, subject=subject, limit=limit)
        if not results:
            return ""
        context_parts = []
        for r in results:
            level_name = {3: "Chapter", 4: "Topic", 5: "Subtopic", 6: "Example"}.get(r.get("level"), "Content")
            header = f"[{level_name}: {r.get('chapter_title', '')} > {r.get('title', '')}]"
            context_parts.append(f"{header}\n{r.get('content', '')}")
        return "\n\n".join(context_parts)
    except Exception as e:
        print(f"RAG context error: {e}")
        return ""


def _llm(prompt, system=None, max_tokens=1024, temp=0.3):
    client = get_client()
    if client.available:
        return client.query(prompt, system, max_tokens, temp)
    return ""


# ─── Napkin AI: Concept → Diagram (zero API key) ──────────────────────────

def generate_local_diagram_fallback(concept, diagram_type, context_text):
    lines_list = [line.strip() for line in context_text.split('\n') if line.strip()]
    nodes = []
    current_header = None
    for line in lines_list:
        if line.startswith('[') and ']' in line:
            current_header = line.replace('[', '').split(']')[0].split(':')[-1].strip()
        elif current_header and len(line) > 15 and not line.startswith('Context:'):
            sentence = re.split(r'[.!?]', line)[0].strip()
            if len(sentence) > 50:
                sentence = sentence[:47] + "..."
            nodes.append((current_header, sentence))
            current_header = None
            if len(nodes) >= 4:
                break
    
    if not nodes:
        if "photosynthesis" in concept.lower():
            nodes = [
                ("Light Absorption", "Chlorophyll in leaves absorbs solar energy"),
                ("Water Splitting", "Water molecules split into Hydrogen and Oxygen"),
                ("Carbon Fixation", "Stomata absorb CO2 for glucose synthesis"),
                ("Energy Storage", "Glucose stored as starch for plant growth")
            ]
        elif "quadratic" in concept.lower():
            nodes = [
                ("Standard Form", "ax^2 + bx + c = 0"),
                ("Discriminant", "D = b^2 - 4ac determines nature of roots"),
                ("Quadratic Formula", "x = (-b ± √D) / 2a"),
                ("Roots", "Real & Equal, Real & Distinct, or Imaginary")
            ]
        else:
            nodes = [
                ("Introduction", f"Understand the core definitions of {concept}"),
                ("Key Features", f"Identify the primary properties of {concept}"),
                ("Applications", f"See how {concept} is used in practice"),
                ("Summary", f"Review the essential takeaways of {concept}")
            ]
            
    lines = []
    if diagram_type == "mindmap":
        lines.append("mindmap")
        lines.append(f"    root(({concept}))")
        for title, desc in nodes:
            safe_title = title.replace('(', '').replace(')', '').replace('[', '').replace(']', '')
            safe_desc = desc.replace('(', '').replace(')', '').replace('[', '').replace(']', '')
            lines.append(f"        {safe_title}")
            lines.append(f"            {safe_desc}")
    elif diagram_type == "concept-map":
        lines.append("graph TD")
        lines.append(f"    Core(({concept}))")
        for i, (title, desc) in enumerate(nodes):
            safe_title = title.replace('[', '').replace(']', '').replace('(', '').replace(')', '')
            safe_desc = desc.replace('[', '').replace(']', '').replace('(', '').replace(')', '')
            lines.append(f"    Node{i}[\"{safe_title}: {safe_desc}\"]")
            lines.append(f"    Core -- involves --> Node{i}")
            if i > 0:
                lines.append(f"    Node{i-1} -- leads to --> Node{i}")
    else: # flowchart
        lines.append("graph TD")
        lines.append(f"    Start(({concept}))")
        for i, (title, desc) in enumerate(nodes):
            safe_title = title.replace('[', '').replace(']', '').replace('(', '').replace(')', '')
            safe_desc = desc.replace('[', '').replace(']', '').replace('(', '').replace(')', '')
            lines.append(f"    Node{i}[\"{safe_title}: {safe_desc}\"]")
            if i == 0:
                lines.append(f"    Start --> Node{i}")
            else:
                lines.append(f"    Node{i-1} --> Node{i}")
            
    return "\n".join(lines)


def generate_local_explanation_fallback(concept, context_text):
    blocks = context_text.split('\n\n')
    formatted_sections = ""
    for block in blocks:
        lines = [l.strip() for l in block.split('\n') if l.strip()]
        if not lines:
            continue
        header = lines[0]
        content = "\n".join(lines[1:])
        
        if header.startswith('[') and ']' in header:
            clean_header = header.replace('[', '').replace(']', '')
            formatted_sections += f"""
            <div style="margin-bottom:1.2rem; padding:1rem; background:#f8fafc; border-radius:8px; border:1px solid #e2e8f0;">
                <h5 style="color:#0f172a; margin:0 0 0.5rem 0; font-size:1.05rem; font-weight:600;">{html_mod.escape(clean_header)}</h5>
                <p style="margin:0; font-size:0.95rem; color:#334155; line-height:1.6;">{html_mod.escape(content)}</p>
            </div>
            """
    
    if not formatted_sections:
        formatted_sections = f"<p>Detailed textbook sections on {html_mod.escape(concept)} are currently being indexed. Please study the main chapter sections for complete formulas and examples.</p>"

    formula_section = ""
    if "quadratic" in concept.lower():
        formula_section = """
        <div style="background:#eff6ff; border-left:4px solid #3b82f6; padding:1rem; border-radius:6px; margin:1rem 0;">
            <h5 style="color:#1d4ed8; margin:0 0 0.5rem 0; font-size:1rem; font-weight:700;">📐 Key Quadratic Formulas:</h5>
            <ul style="margin:0; padding-left:1.2rem; font-size:0.95rem; color:#1e40af; line-height:1.6;">
                <li>Standard Form: <strong>ax² + bx + c = 0</strong></li>
                <li>Roots formula: <strong>x = (-b ± √(b² - 4ac)) / 2a</strong></li>
                <li>Discriminant: <strong>D = b² - 4ac</strong> (If D > 0: Real & Distinct; If D = 0: Real & Equal; If D < 0: Complex/No Real Roots)</li>
            </ul>
        </div>
        """
    elif "photosynthesis" in concept.lower():
        formula_section = """
        <div style="background:#f0fdf4; border-left:4px solid #16a34a; padding:1rem; border-radius:6px; margin:1rem 0;">
            <h5 style="color:#15803d; margin:0 0 0.5rem 0; font-size:1rem; font-weight:700;">🧪 Photosynthesis Balanced Equation:</h5>
            <code style="font-size:1.05rem; color:#166534; font-weight:700; display:block; padding:0.5rem; background:#dcfce7; border-radius:4px;">6CO₂ + 6H₂O + Sunlight ──(Chlorophyll)──> C₆H₁₂O₆ + 6O₂</code>
        </div>
        """

    fallback_exp = f"""
    <div class="study-guide-fallback">
        <h4>Detailed Study Guide: {html_mod.escape(concept)}</h4>
        <p>Grounding context retrieved from verified NCERT textbook chunks:</p>
        
        {formatted_sections}
        
        {formula_section}

        <div style="background:#fef2f2; border-left:4px solid #ef4444; padding:1rem; border-radius:6px; margin:1.5rem 0 0.5rem 0;">
            <strong style="color:#991b1b; display:block; margin-bottom:0.3rem;">💡 Crucial Board Exam Tip (100% Pass Strategy):</strong>
            <span style="color:#7f1d1d; font-size:0.95rem; line-height:1.5;">
                Make sure you state the standard formulas/theorems first in any answer. Showing the logical steps and stating variables clearly receives full step-marking in the CBSE Class X evaluation.
            </span>
        </div>
    </div>
    """
    return fallback_exp


def generate_veo_animator(concept, context_text):
    prompt = f"""You are a Google Veo-3 video concept designer.
We want to generate a simulated high-fidelity animated video conceptualizing: "{concept}"
Based on this NCERT textbook context:
{context_text}

Design a 4-scene video script with actual embedded CSS/SVG visual animations.
Generate a self-contained HTML snippet (wrapped in a single div container) that acts as an interactive video animator:
1. It must have 4 sequential visual "video frames" represented as colorful SVG diagrams (use SVG shapes, paths, and CSS keyframe animations to simulate motion, like stomata opening, molecules moving, or graphs plotting).
2. Play, Pause, Next, and Prev controls.
3. A timeline progress bar.
4. Voiceover script text and a detailed visual layout description shown alongside the player.
5. Apply HSL colors, modern dark theme styling, and premium transitions.

Return ONLY the clean HTML/CSS/JS code block. Do NOT explain the code."""

    html_code = _llm(prompt, "You output ONLY valid self-contained HTML/CSS/JS.", 2048, 0.3)
    if not html_code or "AI Offline" in html_code or len(html_code) < 500:
        html_code = get_fallback_veo_animator(concept)
    return html_code


def get_fallback_veo_animator(concept):
    if "photosynthesis" in concept.lower():
        svg_anim = """
        <svg viewBox="0 0 600 350" width="100%" height="100%" style="background:#0a0f1d; border-radius:8px;">
            <defs>
                <linearGradient id="sun-glow" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stop-color="#fffb00" />
                    <stop offset="100%" stop-color="#ff5100" />
                </linearGradient>
            </defs>
            <path d="M 150,250 C 150,120 300,100 450,180 C 450,300 300,320 150,250 Z" fill="#2ecc71" opacity="0.8" />
            <path d="M 150,250 Q 300,200 450,180" stroke="#27ae60" stroke-width="3" fill="none" />
            <circle cx="80" cy="80" r="30" fill="url(#sun-glow)">
                <animate attributeName="r" values="30;35;30" dur="3s" repeatCount="indefinite" />
            </circle>
            <g stroke="#ffd700" stroke-width="3" stroke-dasharray="5 5">
                <line x1="120" y1="120" x2="220" y2="180">
                    <animate attributeName="stroke-dashoffset" values="50;0" dur="2s" repeatCount="indefinite" />
                </line>
            </g>
            <circle cx="120" cy="280" r="8" fill="#3498db">
                <animate attributeName="cx" values="120;250;280" dur="4s" repeatCount="indefinite" />
                <animate attributeName="cy" values="280;230;200" dur="4s" repeatCount="indefinite" />
            </circle>
            <text x="110" y="310" fill="#3498db" font-size="12" font-family="sans-serif">H2O (Water)</text>
            <circle cx="350" cy="80" r="8" fill="#e67e22">
                <animate attributeName="cx" values="350;300;280" dur="4s" repeatCount="indefinite" />
                <animate attributeName="cy" values="80;150;200" dur="4s" repeatCount="indefinite" />
            </circle>
            <text x="360" y="85" fill="#e67e22" font-size="12" font-family="sans-serif">CO2 (Carbon Dioxide)</text>
            <circle cx="280" cy="200" r="10" fill="#2ecc71">
                <animate attributeName="cx" values="280;380;420" dur="4s" repeatCount="indefinite" />
                <animate attributeName="cy" values="200;220;250" dur="4s" repeatCount="indefinite" />
            </circle>
            <text x="430" y="270" fill="#2ecc71" font-size="12" font-family="sans-serif">C6H12O6 (Glucose)</text>
        </svg>
        """
        scenes = [
            {"title": "Scene 1: Absorption of Sunlight", "desc": "Chlorophyll inside the leaf chloroplasts traps light energy from solar rays.", "vo": "First, the green pigment chlorophyll inside the leaf chloroplasts absorbs sunlight energy."},
            {"title": "Scene 2: Water splitting (Photolysis)", "desc": "Water absorbed by roots is split by light energy into Hydrogen ions and Oxygen gas.", "vo": "Next, water molecules absorbed by roots are split using light energy, releasing oxygen as a byproduct."},
            {"title": "Scene 3: Carbon dioxide reduction", "desc": "Stomata absorb CO2 from the air, which is reduced to synthesize carbohydrates.", "vo": "Then, stomata absorb carbon dioxide, which undergoes reduction using chemical energy to synthesize glucose."},
            {"title": "Scene 4: Storage of Glucose", "desc": "Glucose is synthesized and converted into starch for storage in plant tissues.", "vo": "Finally, the synthesized glucose is stored as starch, providing energy for plant growth and development."}
        ]
    else:
        svg_anim = """
        <svg viewBox="0 0 600 350" width="100%" height="100%" style="background:#0a0f1d; border-radius:8px;">
            <circle cx="300" cy="175" r="50" fill="#9b59b6" opacity="0.6">
                <animate attributeName="r" values="50;70;50" dur="3s" repeatCount="indefinite" />
            </circle>
            <circle cx="300" cy="175" r="15" fill="#fff" />
            <line x1="300" y1="175" x2="420" y2="175" stroke="#00f2fe" stroke-width="4">
                <animateTransform attributeName="transform" type="rotate" from="0 300 175" to="360 300 175" dur="5s" repeatCount="indefinite" />
            </line>
        </svg>
        """
        scenes = [
            {"title": "Scene 1: Defining the Core Concept", "desc": f"Introducing the primary components and foundations of {concept}.", "vo": f"Let's explore the core concept of {concept} step-by-step."},
            {"title": "Scene 2: Visualizing Key Formulas", "desc": "Examining the equations, theorems, and definitions that govern this topic.", "vo": "Understanding the key formulas and logic that form the basis of this lesson."},
            {"title": "Scene 3: Step-by-Step Mechanism", "desc": "Observing how elements interact in sequence according to textbook syllabus.", "vo": "Let's watch how the variables interact and change states during the process."},
            {"title": "Scene 4: Real-world Synthesis", "desc": "Reviewing practical examples and key questions for board exam success.", "vo": "Finally, apply this knowledge to solve problems and practice past board exam questions."}
        ]
    
    slides_html = ""
    dots_html = ""
    for i, s in enumerate(scenes):
        slides_html += f'''
        <div class="veo-slide" data-index="{i}" style="display:{'block' if i==0 else 'none'};">
            <h4 style="color:#00f2fe; margin:0 0 0.5rem 0;">{s['title']}</h4>
            <p style="color:#e2e2e9; font-size:0.95rem; margin:0 0 1rem 0; line-height:1.5;">{s['desc']}</p>
            <div style="background:#111; padding:0.8rem; border-radius:6px; border:1px solid #333; margin-top:0.5rem;">
                <span style="font-size:0.75rem; text-transform:uppercase; color:#888; font-weight:700; display:block; margin-bottom:0.2rem;">Voiceover Script</span>
                <p style="margin:0; font-size:0.9rem; color:#fff; font-style:italic;">"{s['vo']}"</p>
            </div>
            <button onclick="speakVeoScript('{s['vo'].replace("'", "\\'")}')" style="margin-top:0.8rem; padding:0.4rem 1rem; background:#4facfe; color:#1a1a2e; border:none; border-radius:4px; font-size:0.8rem; font-weight:700; cursor:pointer;">🔊 Play Voiceover</button>
        </div>'''
        dots_html += f'<span class="veo-dot" data-index="{i}" onclick="goVeo({i})" style="display:inline-block; width:10px; height:10px; border-radius:50%; background:#fff; margin:0 4px; cursor:pointer; opacity:{0.3 if i>0 else 1};"></span>'

    html = f"""
    <div class="veo-player-container" style="background:#151821; color:#fff; border-radius:12px; padding:1.5rem; width:100%; border:1px solid #2a2d3d;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem; border-bottom:1px solid #2a2d3d; padding-bottom:0.5rem;">
            <h3 style="color:#00f2fe; margin:0; display:flex; align-items:center; gap:0.5rem;">🎥 Google Veo-3 Concept Animator</h3>
            <span style="font-size:0.75rem; background:#4facfe22; color:#4facfe; padding:0.2rem 0.6rem; border-radius:12px; font-weight:600;">Veo-3 Engine</span>
        </div>
        <div style="display:grid; grid-template-columns:1fr; gap:1.5rem;">
            <div style="background:#000; border-radius:8px; overflow:hidden; border:1px solid #333; display:flex; justify-content:center; align-items:center; min-height:250px; position:relative;">
                {svg_anim}
            </div>
            <div style="background:#1a1d29; padding:1rem; border-radius:8px; border:1px solid #2a2d3d; text-align:left;">
                <div class="veo-slides">{slides_html}</div>
                <div style="display:flex; justify-content:space-between; align-items:center; margin-top:1.5rem; border-top:1px solid #2a2d3d; padding-top:0.8rem;">
                    <div style="display:flex; gap:0.5rem;">
                        <button onclick="prevVeo()" style="padding:0.4rem 0.8rem; background:#333; color:#fff; border:none; border-radius:4px; font-size:0.8rem; cursor:pointer;">◀ Prev</button>
                        <button onclick="nextVeo()" style="padding:0.4rem 0.8rem; background:#333; color:#fff; border:none; border-radius:4px; font-size:0.8rem; cursor:pointer;">Next ▶</button>
                    </div>
                    <div class="veo-dots-container" style="display:flex; align-items:center;">{dots_html}</div>
                </div>
            </div>
        </div>
        <script>
        let veoIndex = 0;
        let veoTotal = {len(scenes)};
        function showVeo(n) {{
            document.querySelectorAll('.veo-slide').forEach((s,i) => s.style.display = i===n ? 'block' : 'none');
            document.querySelectorAll('.veo-dot').forEach((d,i) => d.style.opacity = i===n ? '1' : '0.3');
            veoIndex = n;
        }}
        function goVeo(n) {{ showVeo(n); }}
        function nextVeo() {{ if(veoIndex < veoTotal-1) showVeo(veoIndex+1); }}
        function prevVeo() {{ if(veoIndex > 0) showVeo(veoIndex-1); }}
        function speakVeoScript(text) {{
            if (!('speechSynthesis' in window)) {{ alert('Text-to-speech not supported.'); return; }}
            window.speechSynthesis.cancel();
            let utter = new SpeechSynthesisUtterance(text);
            utter.lang = 'en-IN';
            utter.pitch = 1.0;
            utter.rate = 0.95;
            window.speechSynthesis.speak(utter);
        }}
        </script>
    </div>
    """
    return html


def napkin_diagram(concept, diagram_type="flowchart"):
    context = _get_rag_context(concept, limit=3)
    if diagram_type == "veo-animator":
        html = generate_veo_animator(concept, context)
        return {"success": True, "html": html, "type": diagram_type}

    desc = ""
    if diagram_type == "flowchart":
        desc = "step-by-step sequential process flowchart with arrows and start/end steps"
    elif diagram_type == "mindmap":
        desc = "hierarchical mind map branching radially from the main concept core"
    elif diagram_type == "concept-map":
        desc = "cross-connected web of relationships between sub-concepts with clear connecting verb labels on links"

    prompt = f"""Use the following verified NCERT/SCERT textbook context to build a learning module:
Context:
{context}

Create a learning module for: "{concept}"
Include:
1. A Mermaid.js {diagram_type} diagram that shows {desc}. Use color styles or classes if applicable to make it look visually stunning. If you generate a mindmap, use the standard Mermaid mindmap syntax:
mindmap
    root((Topic))
        Subtopic1
            Details1

2. A highly detailed educational explanation (HTML formatted with headings and paragraph tags) that acts as a self-study guide for a remote student. Address:
   - What the diagram represents step-by-step
   - Key formulas, equations, or theorems
   - Real-world application
   - Crucial Board Exam Tip (to ensure 100% pass)

Return the response in JSON format with keys:
- diagram (raw Mermaid.js code, do NOT wrap in ```mermaid or other formatting)
- explanation (HTML formatted explanation)
"""

    response = _llm(prompt, "You output ONLY JSON format.", 1536, 0.3)
    try:
        # Robust extract and parse JSON
        match = re.search(r"({.*})", response.strip(), re.DOTALL)
        if match:
            data = json.loads(match.group(1))
        else:
            data = json.loads(response.strip())
        return {
            "success": True, 
            "diagram": data["diagram"].strip(), 
            "explanation": data["explanation"].strip(), 
            "type": diagram_type
        }
    except Exception:
        fallback_diag = generate_local_diagram_fallback(concept, diagram_type, context)
        fallback_exp = generate_local_explanation_fallback(concept, context)
        return {"success": True, "diagram": fallback_diag, "explanation": fallback_exp, "type": diagram_type}


# ─── Gamma: Content → Presentation (zero API key) ────────────────────────

def gamma_presentation(subject, chapter, topics_data):
    context = _get_rag_context(f"{chapter} {subject}", limit=6)
    prompt = f"""Use the following verified NCERT/SCERT textbook context to create the presentation:
Context:
{context}

Create an HTML slide presentation for {subject} chapter "{chapter}".
Convert the topics and textbook context into slides with headings and bullet points.

Topics:
{json.dumps(topics_data, indent=2)[:3000]}

Return self-contained HTML with <section class="slide"> per slide.
Inline CSS for slide layout. First slide = title, last = summary. Use professional styling, clear margins, HSL colors, and dark mode-friendly themes."""
    html_output = _llm(prompt, "You create beautiful HTML slide decks.", 2048, 0.3)

    if "slide" not in html_output.lower():
        slides = '<section class="slide title-slide"><h1>' + html_mod.escape(subject) + '</h1><h2>' + html_mod.escape(chapter) + '</h2></section>'
        for t in topics_data[:8]:
            slides += '<section class="slide"><h2>' + html_mod.escape(t.get("title", "")) + '</h2>'
            chunks_list = [str(k) for k in (t.get("chunks", [])[:5])]
            slides += '<ul>' + ''.join('<li>' + html_mod.escape(c) + '</li>' for c in chunks_list) + '</ul></section>'
        slides += '<section class="slide summary-slide"><h1>Summary</h1><p>Review and practice.</p></section>'
        return {"success": True, "html": slides}
    return {"success": True, "html": html_output}


# ─── Quillbot: AI Paraphraser (replaces Elevenlabs, zero API key) ─────────

def quillbot_paraphrase(text, mode="simpler"):
    instructions = {
        "simpler": "Reword this to be simpler and easier for a Class X student. Use shorter sentences and everyday words.",
        "formal": "Reword this in a formal, academic style suitable for a textbook.",
        "bullets": "Convert this into concise bullet points highlighting key ideas.",
        "summarize": "Summarize this in 2-3 sentences covering only the most important points.",
        "expand": "Expand on this with more detail, examples, and explanations.",
    }
    instruction = instructions.get(mode, instructions["simpler"])
    prompt = f"""Original text:
{text}

{instruction}

Return only the rewritten text."""
    result = _llm(prompt, "You are a paraphrasing assistant that rewrites educational content.", 1024, 0.3)
    if not result or "AI Offline" in result:
        result = text
    return {"success": True, "original": text, "paraphrased": result, "mode": mode}


def quillbot_speak(text, lang="en-IN"):
    """Browser-based TTS (handled client-side). Returns text for JS SpeechSynthesis."""
    return {"success": True, "text": text, "lang": lang, "tts": "browser"}


def quillbot_speak_segments(text, lang="en-IN", voice="female"):
    """Split text into time-coded segments for voiceover-video sync."""
    sentences = re.split(r'(?<=[.?!])\s+', text.strip())
    segments = []
    total_dur = 0
    for s in sentences:
        if not s.strip():
            continue
        words = len(s.split())
        duration = max(2.0, words * 0.35)
        segments.append({
            "text": s.strip(),
            "start": round(total_dur, 1),
            "end": round(total_dur + duration, 1),
            "duration": round(duration, 1),
        })
        total_dur += duration
    return {
        "success": True,
        "text": text,
        "lang": lang,
        "voice": voice,
        "tts": "browser",
        "segments": segments,
        "total_duration": round(total_dur, 1),
        "sync_url": "/api/ai/youtube?topic=" + urllib.parse.quote(text[:60]),
    }


# ─── LLM Research Assistant (replaces Perplexity, zero API key) ───────────

def llm_research(query, subject=None):
    context = _get_rag_context(query, subject=subject, limit=5)
    context_prompt = f"""You are a research assistant for Class X {subject or 'CBSE'} students.
Using the verified textbook context below, research the topic thoroughly and provide a comprehensive answer:

Context:
{context}

Topic: {query}
Subject: {subject or 'General'}

Cover:
1. Core explanation (grounded in the textbook context)
2. Key concepts and principles
3. Real-world applications
4. Connections to other topics
5. Important terms to remember

Format your answer with clear sections, formulas, and bullet points where helpful."""
    answer = _llm(context_prompt, "You are a thorough research assistant.", 1536, 0.3)
    if not answer or "AI Offline" in answer:
        answer = f"**{query}**\n\nThis topic covers fundamental concepts in {subject or 'this subject'}. Study the NCERT textbook chapters and practice problems to build a strong foundation."
    return {"success": True, "answer": answer, "source": "llm"}


# ─── LLM Literature Review (replaces Consensus, zero API key) ────────────

def llm_literature(query, subject="science"):
    context = _get_rag_context(query, subject=subject, limit=5)
    prompt = f"""Use the following verified NCERT/SCERT textbook sections context:
Context:
{context}

Generate a comprehensive educational literature and section review on the query: "{query}" in {subject}.
Provide 3-5 summaries of relevant textbook sections, chapters, or syllabus entries.
For each entry, include: Title/Section header, Source (e.g., NCERT Class X Science), Chapter, and a detailed 2-3 sentence summary of findings, definitions, or core principles.

Format each exactly as:
**Title** by Source (Chapter)
Summary of findings..."""
    result = _llm(prompt, "You generate educational research and textbook reviews.", 1024, 0.3)
    papers = []
    if result and "AI Offline" not in result:
        blocks = re.split(r'\*\*(.*?)\*\*', result)
        for i in range(1, len(blocks), 2):
            title = blocks[i].strip()
            body = blocks[i + 1].strip() if i + 1 < len(blocks) else ""
            papers.append({"title": title, "authors": "NCERT/SCERT Board", "year": "2026", "abstract": body[:400], "url": ""})
    if not papers:
        papers = [{"title": f"Study of {query}", "authors": "NCERT Board", "year": "2026", "abstract": f"Verified syllabus content on {query} in {subject} education shows key concepts.", "url": ""}]
    return {"success": True, "results": papers}


# ─── SVG Visualizer (replaces Ideogram, zero API key) ────────────────────

def svg_visualize(concept, style="diagram"):
    context = _get_rag_context(concept, limit=3)
    prompt = f"""Use the following verified textbook context:
{context}

Generate SVG code for an educational diagram about "{concept}" in {style} style.
The SVG should be clean, colorful (use educational colors), and suitable for a Class X student.
Include labels, formulas (if any), and visual elements that explain the concept.
Return ONLY valid SVG code inside ```svg ... ``` markers. Use viewBox 0 0 800 500."""

    svg = _llm(prompt, "You generate clean SVG educational diagrams.", 1024, 0.2)
    svg_match = re.search(r"```svg\n?(.*?)```", svg, re.DOTALL)
    if svg_match:
        return {"success": True, "svg": svg_match.group(1).strip(), "concept": concept}

    fallback = f'''<svg viewBox="0 0 800 500" xmlns="http://www.w3.org/2000/svg">
  <rect width="800" height="500" fill="#f0f4f8" rx="12"/>
  <text x="400" y="60" text-anchor="middle" font-size="28" font-weight="bold" fill="#1a1a2e">{html_mod.escape(concept)}</text>
  <rect x="250" y="100" width="300" height="60" rx="10" fill="#4a90d9"/>
  <text x="400" y="138" text-anchor="middle" font-size="18" fill="white">Core Concept</text>
  <line x1="400" y1="160" x2="250" y2="220" stroke="#666" stroke-width="2"/>
  <line x1="400" y1="160" x2="550" y2="220" stroke="#666" stroke-width="2"/>
  <rect x="100" y="220" width="300" height="60" rx="10" fill="#50c878"/>
  <text x="250" y="258" text-anchor="middle" font-size="16" fill="white">Key Aspect 1</text>
  <rect x="400" y="220" width="300" height="60" rx="10" fill="#ff6b6b"/>
  <text x="550" y="258" text-anchor="middle" font-size="16" fill="white">Key Aspect 2</text>
  <text x="400" y="400" text-anchor="middle" font-size="14" fill="#666">An educational diagram explaining {html_mod.escape(concept)}</text>
</svg>'''
    return {"success": True, "svg": fallback, "concept": concept}


# ─── Tome: Storytelling & Analogy Engine (zero API key) ──────────────────

def tome_story(topic, chapter="", subject=""):
    context = _get_rag_context(f"{topic} {chapter}", subject=subject, limit=3)
    prompt = f"""Use the following verified NCERT/SCERT textbook context:
Context:
{context}

Create an engaging educational story explaining "{topic}" from {subject} chapter "{chapter}".

The story should:
1. Start with a relatable everyday scenario a Class X student would understand
2. Map analogical elements to the real concept
3. Explain key principles through the narrative, explicitly grounded in the textbook context
4. End with a "What this means" summary

Return the story in HTML with <p> tags. Keep it under 400 words."""
    story = _llm(prompt, "You are a master storyteller who explains through analogy.", 1024, 0.4)
    if not story or "AI Offline" in story:
        story = f"""<p>Imagine <strong>{topic}</strong> as something from your daily life...</p>
<p>Just like how a recipe has specific steps that must be followed in order,
{topic} works on the same principle — each step builds on the previous one.</p>
<p><strong>What this means:</strong> Master each stage to understand the complete picture.</p>"""
    return {"success": True, "story": story}


# ─── NotebookLM: Knowledge Management (zero API key) ─────────────────────

def notebooklm_export(subject, chapter, topics):
    md = f"# {subject}: {chapter}\n\n"
    for i, t in enumerate(topics, 1):
        md += f"## {i}. {t.get('title', '')}\n\n"
        for c in t.get("chunks", []):
            title = c.get("title", "") or c.get("content", "")[:50]
            md += f"### {title}\n{c.get('content', '')}\n\n"
        md += "---\n\n"
    md += "## Study Questions\n\n"
    md += "1. What are the key concepts covered?\n2. How do these relate?\n3. What real-world applications exist?\n4. Practice numerical problems\n5. Review diagrams\n\n"
    md += "> Import into NotebookLM for AI-powered analysis.\n"
    return {"success": True, "markdown": md, "title": f"{subject} - {chapter}"}


# ─── Browser Music Generator (replaces Udio/Suno, zero API key) ─────────

def browser_music_params(mood="calm study piano"):
    params = {
        "calm study piano": {"type": "sine", "frequency": 261.63, "lfo_freq": 0.5, "gain": 0.15, "label": "Calm Piano Study"},
        "lo-fi study beats": {"type": "triangle", "frequency": 220, "lfo_freq": 0.8, "gain": 0.12, "label": "Lo-fi Study Beats"},
        "nature sounds for focus": {"type": "sine", "frequency": 180, "lfo_freq": 0.3, "gain": 0.1, "label": "Nature Sounds"},
        "classical study music": {"type": "sine", "frequency": 392, "lfo_freq": 0.4, "gain": 0.13, "label": "Classical Study"},
        "ambient electronic": {"type": "sawtooth", "frequency": 130.81, "lfo_freq": 0.2, "gain": 0.08, "label": "Ambient Electronic"},
    }
    p = params.get(mood, params["calm study piano"])
    return {"success": True, "mood": mood, "params": p}


# ─── Gemma 4: LLM Backend ────────────────────────────────────────────────

def gemma4_query(prompt, system=None, max_tokens=1024, temp=0.3):
    client = get_client()
    if client.gemini_api_key:
        orig_model = client.gemini_model
        try:
            return client.query(prompt, system or "You are a helpful CBSE Class X tutor using Gemma/Gemini.", max_tokens, temp)
        finally:
            pass
    return _llm(prompt, system, max_tokens, temp)


# ─── Google Flash: Gemini Flash Backend (optional, needs GEMINI_API_KEY) ─

def google_flash_query(prompt, system=None, max_tokens=1024, temp=0.3):
    client = get_client()
    if client.gemini_api_key:
        return client.query(prompt, system, max_tokens, temp)
    return _llm(prompt, system, max_tokens, temp)


# ─── Pomelli: Math Animation Engine (zero API key) ───────────────────────

POMMELLI_TEMPLATES = {
    "graph-linear": {
        "title": "Linear Graph Plotter",
        "desc": "Plot y = mx + c and see how slope and intercept change",
    },
    "graph-quadratic": {
        "title": "Quadratic Graph Plotter",
        "desc": "Visualize y = ax² + bx + c with real-time parameter adjustment",
    },
    "graph-trig": {
        "title": "Trigonometric Functions",
        "desc": "Interactive sin, cos, tan curves with amplitude & frequency control",
    },
    "geometry-transform": {
        "title": "Geometric Transformations",
        "desc": "Translate, rotate, reflect and scale shapes on a coordinate plane",
    },
    "fractions": {
        "title": "Fraction Visualizer",
        "desc": "See fractions as shaded portions of circles and rectangles",
    },
    "pythagoras": {
        "title": "Pythagorean Theorem",
        "desc": "Interactive proof and visualization of a² + b² = c²",
    },
    "number-line": {
        "title": "Number Line Operations",
        "desc": "Visualize addition, subtraction, multiplication on a number line",
    },
    "probability": {
        "title": "Probability Simulator",
        "desc": "Run experiments with dice, coins, and spinners to see probability in action",
    },
    "statistics": {
        "title": "Statistics Visualizer",
        "desc": "Bar charts, histograms, and pie charts from your data",
    },
    "area-perimeter": {
        "title": "Area & Perimeter Explorer",
        "desc": "Drag to resize shapes and see area/perimeter update live",
    },
}


def pomelli_list_templates():
    return {"success": True, "templates": POMMELLI_TEMPLATES}


def pomelli_generate(template_id, params=None):
    t = POMMELLI_TEMPLATES.get(template_id)
    if not t:
        return {"success": False, "error": f"Unknown template: {template_id}"}
    if not params:
        params = {}

    if template_id == "graph-linear":
        return _pomelli_graph_linear(params)
    elif template_id == "graph-quadratic":
        return _pomelli_graph_quadratic(params)
    elif template_id == "graph-trig":
        return _pomelli_graph_trig(params)
    elif template_id == "geometry-transform":
        return _pomelli_geometry_transform(params)
    elif template_id == "fractions":
        return _pomelli_fractions(params)
    elif template_id == "pythagoras":
        return _pomelli_pythagoras(params)
    elif template_id == "number-line":
        return _pomelli_number_line(params)
    elif template_id == "probability":
        return _pomelli_probability(params)
    elif template_id == "statistics":
        return _pomelli_statistics(params)
    elif template_id == "area-perimeter":
        return _pomelli_area_perimeter(params)
    else:
        return _pomelli_graph_linear(params)


def _pomelli_graph_linear(params):
    m = params.get("slope", "2")
    c = params.get("intercept", "1")
    html = f'''<div class="pomelli-container" style="width:100%;max-width:700px;margin:0 auto;">
<canvas id="pomelli-canvas" width="650" height="450" style="width:100%;background:#fff;border-radius:12px;border:1px solid var(--border);"></canvas>
<div style="display:flex;gap:1rem;margin-top:1rem;flex-wrap:wrap;align-items:center;">
  <label>m (slope): <input type="range" id="p-slope" min="-5" max="5" step="0.5" value="{m}" oninput="drawLinearGraph()" style="width:100px;"></label>
  <span id="p-slope-val">{m}</span>
  <label>c (intercept): <input type="range" id="p-intercept" min="-10" max="10" step="0.5" value="{c}" oninput="drawLinearGraph()" style="width:100px;"></label>
  <span id="p-intercept-val">{c}</span>
</div>
<script>
function drawLinearGraph() {{
  const canvas = document.getElementById('pomelli-canvas');
  const ctx = canvas && canvas.getContext('2d');
  if (!canvas || !ctx) return;
  const w = canvas.width, h = canvas.height;
  const cx = w/2, cy = h/2, scale = 25;
  const m = parseFloat(document.getElementById('p-slope').value);
  const c = parseFloat(document.getElementById('p-intercept').value);
  document.getElementById('p-slope-val').textContent = m;
  document.getElementById('p-intercept-val').textContent = c;
  ctx.clearRect(0, 0, w, h);
  ctx.strokeStyle = '#ddd'; ctx.lineWidth = 0.5;
  for (let x = 0; x <= w; x += scale) {{ ctx.beginPath(); ctx.moveTo(x,0); ctx.lineTo(x,h); ctx.stroke(); }}
  for (let y = 0; y <= h; y += scale) {{ ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(w,y); ctx.stroke(); }}
  ctx.strokeStyle = '#333'; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(cx,0); ctx.lineTo(cx,h); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(0,cy); ctx.lineTo(w,cy); ctx.stroke();
  ctx.fillStyle = '#333'; ctx.font = '12px sans-serif';
  for (let i = -12; i <= 12; i++) {{ if (i===0) continue; ctx.fillText(i, cx + i*scale + 3, cy + 15); ctx.fillText(-i, cx + 3, cy + i*scale + 4); }}
  ctx.strokeStyle = '#4a90d9'; ctx.lineWidth = 3;
  ctx.beginPath();
  for (let px = 0; px <= w; px++) {{
    const x = (px - cx) / scale;
    const y = m * x + c;
    const py = cy - y * scale;
    if (px === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
  }}
  ctx.stroke();
  ctx.fillStyle = '#e74c3c'; ctx.beginPath(); ctx.arc(cx + c*scale, cy, 5, 0, Math.PI*2); ctx.fill();
  ctx.fillStyle = '#2ecc71'; ctx.beginPath(); ctx.arc(cx, cy + c*scale, 5, 0, Math.PI*2); ctx.fill();
  ctx.fillStyle = '#333'; ctx.font = '14px sans-serif'; ctx.fillText('y = ' + m + 'x + ' + c, 20, 30);
}} drawLinearGraph();
</script></div>'''
    return {"success": True, "html": html, "template": "graph-linear", "title": "Linear Graph: y = mx + c"}


def _pomelli_graph_quadratic(params):
    a = params.get("a", "1")
    b = params.get("b", "0")
    c = params.get("c", "-4")
    html = f'''<div class="pomelli-container" style="width:100%;max-width:700px;margin:0 auto;">
<canvas id="pomelli-canvas-q" width="650" height="450" style="width:100%;background:#fff;border-radius:12px;border:1px solid var(--border);"></canvas>
<div style="display:flex;gap:1rem;margin-top:1rem;flex-wrap:wrap;align-items:center;">
  <label>a: <input type="range" id="p-qa" min="-3" max="3" step="0.2" value="{a}" oninput="drawQuadGraph()" style="width:80px;"></label><span id="p-qa-val">{a}</span>
  <label>b: <input type="range" id="p-qb" min="-5" max="5" step="0.5" value="{b}" oninput="drawQuadGraph()" style="width:80px;"></label><span id="p-qb-val">{b}</span>
  <label>c: <input type="range" id="p-qc" min="-10" max="10" step="0.5" value="{c}" oninput="drawQuadGraph()" style="width:80px;"></label><span id="p-qc-val">{c}</span>
</div>
<script>
function drawQuadGraph() {{
  const canvas = document.getElementById('pomelli-canvas-q');
  const ctx = canvas && canvas.getContext('2d');
  if (!canvas || !ctx) return;
  const w=canvas.width, h=canvas.height;
  const cx=w/2, cy=h/2, scale=25;
  const a = parseFloat(document.getElementById('p-qa').value);
  const b = parseFloat(document.getElementById('p-qb').value);
  const c = parseFloat(document.getElementById('p-qc').value);
  ['p-qa-val','p-qb-val','p-qc-val'].forEach((id,i)=>document.getElementById(id).textContent=[a,b,c][i]);
  ctx.clearRect(0,0,w,h);
  ctx.strokeStyle='#ddd'; ctx.lineWidth=0.5;
  for(let x=0;x<=w;x+=scale){{ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke();}}
  for(let y=0;y<=h;y+=scale){{ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke();}}
  ctx.strokeStyle='#333'; ctx.lineWidth=2;
  ctx.beginPath();ctx.moveTo(cx,0);ctx.lineTo(cx,h);ctx.stroke();
  ctx.beginPath();ctx.moveTo(0,cy);ctx.lineTo(w,cy);ctx.stroke();
  ctx.strokeStyle='#e74c3c'; ctx.lineWidth=3; ctx.beginPath();
  for(let px=0;px<=w;px++){{const x=(px-cx)/scale;const y=a*x*x+b*x+c;const py=cy-y*scale;if(px===0)ctx.moveTo(px,py);else ctx.lineTo(px,py);}}
  ctx.stroke();
  const disc = b*b-4*a*c;
  if (disc >= 0) {{
    const r1 = (-b + Math.sqrt(disc))/(2*a); const r2 = (-b - Math.sqrt(disc))/(2*a);
    ctx.fillStyle='#2ecc71';
    ctx.beginPath();ctx.arc(cx+r1*scale,cy,6,0,Math.PI*2);ctx.fill();
    ctx.beginPath();ctx.arc(cx+r2*scale,cy,6,0,Math.PI*2);ctx.fill();
  }}
  ctx.fillStyle='#333'; ctx.font='14px sans-serif'; ctx.fillText('y = '+a+'x² + '+b+'x + '+c, 20, 30);
  const vx = -b/(2*a); const vy = a*vx*vx+b*vx+c;
  ctx.fillStyle='#9b59b6'; ctx.beginPath();ctx.arc(cx+vx*scale,cy-vy*scale,5,0,Math.PI*2);ctx.fill();
}} drawQuadGraph();
</script></div>'''
    return {"success": True, "html": html, "template": "graph-quadratic", "title": "Quadratic Graph: y = ax² + bx + c"}


def _pomelli_graph_trig(params):
    func = params.get("func", "sin")
    html = f'''<div class="pomelli-container" style="width:100%;max-width:700px;margin:0 auto;">
<canvas id="pomelli-canvas-t" width="650" height="450" style="width:100%;background:#fff;border-radius:12px;border:1px solid var(--border);"></canvas>
<div style="display:flex;gap:1rem;margin-top:1rem;flex-wrap:wrap;align-items:center;">
  <label>Function: <select id="p-trig" onchange="drawTrigGraph()">
    <option value="sin" {"selected" if func=="sin" else ""}>sin(x)</option>
    <option value="cos" {"selected" if func=="cos" else ""}>cos(x)</option>
    <option value="tan" {"selected" if func=="tan" else ""}>tan(x)</option>
  </select></label>
  <label>Amp: <input type="range" id="p-tamp" min="0.5" max="3" step="0.25" value="1" oninput="drawTrigGraph()" style="width:80px;"></label><span id="p-tamp-val">1</span>
  <label>Freq: <input type="range" id="p-tfreq" min="0.5" max="3" step="0.25" value="1" oninput="drawTrigGraph()" style="width:80px;"></label><span id="p-tfreq-val">1</span>
</div>
<script>
function drawTrigGraph() {{
  const canvas = document.getElementById('pomelli-canvas-t');
  const ctx = canvas.getContext('2d');
  if (!canvas || !ctx) return;
  const w=canvas.width, h=canvas.height;
  const cx=w/2, cy=h/2, scale=40; const pi=Math.PI;
  const f = document.getElementById('p-trig').value;
  const amp = parseFloat(document.getElementById('p-tamp').value);
  const freq = parseFloat(document.getElementById('p-tfreq').value);
  document.getElementById('p-tamp-val').textContent=amp;
  document.getElementById('p-tfreq-val').textContent=freq;
  ctx.clearRect(0,0,w,h);
  ctx.strokeStyle='#ddd'; ctx.lineWidth=0.5;
  for(let x=0;x<=w;x+=scale){{ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke();}}
  for(let y=0;y<=h;y+=scale){{ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke();}}
  ctx.strokeStyle='#333'; ctx.lineWidth=2;
  ctx.beginPath();ctx.moveTo(cx,0);ctx.lineTo(cx,h);ctx.stroke();
  ctx.beginPath();ctx.moveTo(0,cy);ctx.lineTo(w,cy);ctx.stroke();
  for(let i=-6;i<=6;i++){{ctx.fillStyle='#333';ctx.font='12px sans-serif';if(i!==0)ctx.fillText(i*pi/4+'π',cx+i*scale*pi/4+3,cy+15);}}
  ctx.strokeStyle='#4a90d9'; ctx.lineWidth=3; ctx.beginPath();
  for(let px=0;px<=w;px++){{
    const x = (px-cx)/scale; let y=0;
    if(f==='sin') y=amp*Math.sin(freq*x);
    else if(f==='cos') y=amp*Math.cos(freq*x);
    else y=amp*Math.tan(freq*x);
    if(Math.abs(y)>5){{ctx.stroke();ctx.beginPath();continue;}}
    const py=cy-y*scale; if(px===0)ctx.moveTo(px,py);else ctx.lineTo(px,py);
  }}
  ctx.stroke();
  ctx.fillStyle='#333'; ctx.font='14px sans-serif'; ctx.fillText('y = '+amp+''+f+'('+freq+'x)', 20, 30);
}} drawTrigGraph();
</script></div>'''
    return {"success": True, "html": html, "template": "graph-trig", "title": "Trigonometric Graphs"}


def _pomelli_geometry_transform(params):
    shape = params.get("shape", "triangle")
    html = f'''<div class="pomelli-container" style="width:100%;max-width:700px;margin:0 auto;">
<canvas id="pomelli-canvas-geo" width="650" height="450" style="width:100%;background:#fff;border-radius:12px;border:1px solid var(--border);"></canvas>
<div style="display:flex;gap:1rem;margin-top:1rem;flex-wrap:wrap;align-items:center;">
  <label>Shape: <select id="p-shape" onchange="drawGeo()">
    <option value="triangle">Triangle</option>
    <option value="square">Square</option>
    <option value="rectangle">Rectangle</option>
  </select></label>
  <label>Rotate: <input type="range" id="p-rotate" min="0" max="360" value="0" oninput="drawGeo()" style="width:100px;"></label><span id="p-rot-val">0°</span>
  <label>Translate X: <input type="range" id="p-tx" min="-100" max="100" value="0" oninput="drawGeo()" style="width:100px;"></label>
  <label>Scale: <input type="range" id="p-scale" min="0.5" max="2" step="0.1" value="1" oninput="drawGeo()" style="width:80px;"></label><span id="p-scl-val">1</span>
</div>
<script>
function drawGeo() {{
  const canvas = document.getElementById('pomelli-canvas-geo');
  const ctx = canvas.getContext('2d');
  if (!canvas || !ctx) return;
  const w=canvas.width, h=canvas.height;
  const cx=w/2, cy=h/2;
  const shape = document.getElementById('p-shape').value;
  const rot = parseFloat(document.getElementById('p-rotate').value)*Math.PI/180;
  const tx = parseFloat(document.getElementById('p-tx').value);
  const scale = parseFloat(document.getElementById('p-scale').value);
  document.getElementById('p-rot-val').textContent=rot*180/Math.PI+'°';
  document.getElementById('p-scl-val').textContent=scale;
  ctx.clearRect(0,0,w,h);
  ctx.strokeStyle='#ddd'; ctx.lineWidth=0.5;
  for(let x=0;x<=w;x+=30){{ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke();}}
  for(let y=0;y<=h;y+=30){{ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke();}}
  ctx.strokeStyle='#333'; ctx.lineWidth=1;
  ctx.beginPath();ctx.moveTo(cx,0);ctx.lineTo(cx,h);ctx.stroke();
  ctx.beginPath();ctx.moveTo(0,cy);ctx.lineTo(w,cy);ctx.stroke();
  let pts = [];
  if(shape==='triangle') pts=[[0,-60],[-52,30],[52,30]];
  else if(shape==='square') pts=[[-50,-50],[50,-50],[50,50],[-50,50]];
  else pts=[[-70,-40],[70,-40],[70,40],[-70,40]];
  pts = pts.map(p=>{{const x=p[0]*scale,y=p[1]*scale;const rx=x*Math.cos(rot)-y*Math.sin(rot);const ry=x*Math.sin(rot)+y*Math.cos(rot);return [rx+tx,ry];}});
  ctx.strokeStyle='#4a90d9'; ctx.lineWidth=3; ctx.beginPath();
  pts.forEach((p,i)=>{{if(i===0)ctx.moveTo(cx+p[0],cy+p[1]);else ctx.lineTo(cx+p[0],cy+p[1]);}});
  if(pts.length>2)ctx.closePath(); ctx.stroke();
  ctx.fillStyle='rgba(74,144,217,0.15)'; ctx.fill();
  ctx.fillStyle='#333'; ctx.font='14px sans-serif';
  ctx.fillText('Original (gray) → Transformed (blue)', 20, 30);
  const opt = pts.map(p=>[cx-p[0],cy-p[1]]);
  ctx.strokeStyle='#bbb'; ctx.lineWidth=1; ctx.setLineDash([5,5]);
  ctx.beginPath(); opt.forEach((p,i)=>{{if(i===0)ctx.moveTo(p[0],p[1]);else ctx.lineTo(p[0],p[1]);}});
  if(opt.length>2)ctx.closePath(); ctx.stroke(); ctx.setLineDash([]);
}} drawGeo();
</script></div>'''
    return {"success": True, "html": html, "template": "geometry-transform", "title": "Geometric Transformations"}


def _pomelli_fractions(params):
    num = params.get("numerator", "3")
    den = params.get("denominator", "4")
    html = f'''<div class="pomelli-container" style="width:100%;max-width:700px;margin:0 auto;">
<canvas id="pomelli-canvas-f" width="650" height="350" style="width:100%;background:#fff;border-radius:12px;border:1px solid var(--border);"></canvas>
<div style="display:flex;gap:1rem;margin-top:1rem;flex-wrap:wrap;align-items:center;">
  <label>Numerator: <input type="range" id="p-fnum" min="0" max="12" value="{num}" oninput="drawFraction()" style="width:100px;"></label><span id="p-fnum-val">{num}</span>
  <label>Denominator: <input type="range" id="p-fden" min="1" max="12" value="{den}" oninput="drawFraction()" style="width:100px;"></label><span id="p-fden-val">{den}</span>
</div>
<script>
function drawFraction() {{
  const canvas = document.getElementById('pomelli-canvas-f');
  const ctx = canvas.getContext('2d');
  if (!canvas || !ctx) return;
  const w=canvas.width, h=canvas.height;
  const n = parseInt(document.getElementById('p-fnum').value);
  const d = parseInt(document.getElementById('p-fden').value);
  document.getElementById('p-fnum-val').textContent=n;
  document.getElementById('p-fden-val').textContent=d;
  ctx.clearRect(0,0,w,h);
  const cx = w/2, cy = h/2 - 20, r = Math.min(w/3, h/2 - 40);
  ctx.strokeStyle='#333'; ctx.lineWidth=2;
  // Circle fraction
  ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI*2); ctx.stroke();
  const slice = 2*Math.PI/d;
  for(let i=0;i<d;i++){{
    ctx.beginPath(); ctx.moveTo(cx,cy); ctx.arc(cx,cy,r,i*slice,(i+1)*slice);
    ctx.closePath();
    if(i<n){{ctx.fillStyle='#4a90d9'; ctx.fill();}} else {{ctx.fillStyle='#e8f4f8'; ctx.fill();}}
    ctx.stroke();
  }}
  ctx.fillStyle='#333'; ctx.font='bold 24px sans-serif';
  ctx.fillText(n+'/'+d, cx-25, cy + r + 50);
  ctx.font='16px sans-serif'; ctx.fillText('= '+(n/d).toFixed(2), cx+40, cy + r + 50);
  if(d>0){{ctx.fillStyle='#666'; ctx.font='14px sans-serif'; ctx.fillText(Math.round(n/d*100)+'%', cx-20, cy);}}
}} drawFraction();
</script></div>'''
    return {"success": True, "html": html, "template": "fractions", "title": f"Fraction: {num}/{den}"}


def _pomelli_pythagoras(params):
    a = params.get("a", "3")
    b = params.get("b", "4")
    html = f'''<div class="pomelli-container" style="width:100%;max-width:700px;margin:0 auto;">
<canvas id="pomelli-canvas-p" width="650" height="450" style="width:100%;background:#fff;border-radius:12px;border:1px solid var(--border);"></canvas>
<div style="display:flex;gap:1rem;margin-top:1rem;flex-wrap:wrap;align-items:center;">
  <label>a: <input type="range" id="p-pa" min="1" max="10" step="0.5" value="{a}" oninput="drawPythagoras()" style="width:100px;"></label><span id="p-pa-val">{a}</span>
  <label>b: <input type="range" id="p-pb" min="1" max="10" step="0.5" value="{b}" oninput="drawPythagoras()" style="width:100px;"></label><span id="p-pb-val">{b}</span>
</div>
<script>
function drawPythagoras() {{
  const canvas = document.getElementById('pomelli-canvas-p');
  const ctx = canvas.getContext('2d');
  if (!canvas || !ctx) return;
  const w=canvas.width, h=canvas.height;
  const a = parseFloat(document.getElementById('p-pa').value);
  const b = parseFloat(document.getElementById('p-pb').value);
  const c = Math.sqrt(a*a + b*b);
  document.getElementById('p-pa-val').textContent=a;
  document.getElementById('p-pb-val').textContent=b;
  ctx.clearRect(0,0,w,h);
  const scale = Math.min(180/Math.max(a,b), 35);
  const ox = 60, oy = h - 60;
  // Draw triangle
  ctx.strokeStyle='#333'; ctx.lineWidth=3;
  ctx.beginPath(); ctx.moveTo(ox, oy); ctx.lineTo(ox + a*scale, oy); ctx.lineTo(ox, oy - b*scale); ctx.closePath(); ctx.stroke();
  ctx.fillStyle='rgba(74,144,217,0.15)'; ctx.fill();
  // Right angle marker
  ctx.strokeStyle='#e74c3c'; ctx.lineWidth=2;
  ctx.beginPath(); ctx.moveTo(ox+15, oy); ctx.lineTo(ox+15, oy-15); ctx.lineTo(ox, oy-15); ctx.stroke();
  // Labels
  ctx.fillStyle='#333'; ctx.font='bold 16px sans-serif';
  ctx.fillText('a = '+a, ox + a*scale/2 - 15, oy + 25);
  ctx.fillText('b = '+b, ox - 40, oy - b*scale/2);
  ctx.fillText('c = '+c.toFixed(2), ox + a*scale/2 + 10, oy - b*scale/2 - 5);
  // Squares on each side
  ctx.strokeStyle='rgba(74,144,217,0.3)'; ctx.lineWidth=1;
  a>0&&ctx.strokeRect(ox, oy, a*scale, -a*scale);
  b>0&&ctx.strokeRect(ox-a*scale, oy-b*scale, a*scale, b*scale);
  ctx.fillStyle='#333'; ctx.font='bold 20px sans-serif';
  ctx.fillText('a² + b² = c²', 20, 35);
  ctx.font='16px sans-serif'; ctx.fillStyle='#666';
  ctx.fillText(a+'² + '+b+'² = '+c.toFixed(2)+'²', 20, 60);
  ctx.fillText((a*a)+' + '+(b*b)+' = '+(c*c).toFixed(2), 20, 85);
}} drawPythagoras();
</script></div>'''
    return {"success": True, "html": html, "template": "pythagoras", "title": f"Pythagorean Theorem: a² + b² = c²"}


def _pomelli_number_line(params):
    op = params.get("operation", "add")
    a = params.get("a", "3")
    b = params.get("b", "5")
    html = f'''<div class="pomelli-container" style="width:100%;max-width:700px;margin:0 auto;">
<canvas id="pomelli-canvas-n" width="650" height="300" style="width:100%;background:#fff;border-radius:12px;border:1px solid var(--border);"></canvas>
<div style="display:flex;gap:1rem;margin-top:1rem;flex-wrap:wrap;align-items:center;">
  <label>Op: <select id="p-op" onchange="drawNumLine()">
    <option value="add" {"selected" if op=="add" else ""}>a + b</option>
    <option value="sub" {"selected" if op=="sub" else ""}>a - b</option>
    <option value="mul" {"selected" if op=="mul" else ""}>a × b</option>
  </select></label>
  <label>a: <input type="range" id="p-na" min="-10" max="10" value="{a}" oninput="drawNumLine()" style="width:100px;"></label><span id="p-na-val">{a}</span>
  <label>b: <input type="range" id="p-nb" min="-10" max="10" value="{b}" oninput="drawNumLine()" style="width:100px;"></label><span id="p-nb-val">{b}</span>
</div>
<script>
function drawNumLine() {{
  const canvas = document.getElementById('pomelli-canvas-n');
  const ctx = canvas.getContext('2d');
  if (!canvas || !ctx) return;
  const w=canvas.width, h=canvas.height;
  const op = document.getElementById('p-op').value;
  const a = parseInt(document.getElementById('p-na').value);
  const b = parseInt(document.getElementById('p-nb').value);
  document.getElementById('p-na-val').textContent=a;
  document.getElementById('p-nb-val').textContent=b;
  ctx.clearRect(0,0,w,h);
  const range = 20, ox = 50, len = w - 100, scale = len/range;
  const cy = h/2;
  ctx.strokeStyle='#333'; ctx.lineWidth=2;
  ctx.beginPath(); ctx.moveTo(ox, cy); ctx.lineTo(ox+len, cy); ctx.stroke();
  ctx.fillStyle='#333'; ctx.font='12px sans-serif';
  for(let i=-range/2;i<=range/2;i++){{
    const x = ox + (i+range/2)*scale;
    ctx.beginPath(); ctx.moveTo(x, cy-5); ctx.lineTo(x, cy+5); ctx.stroke();
    if(i%2===0) ctx.fillText(i, x-5, cy+20);
  }}
  const result = op==='add' ? a+b : op==='sub' ? a-b : a*b;
  const startPos = ox + (a+range/2)*scale;
  const endPos = ox + ((op==='add'?a+b:op==='sub'?a-b:a*b)+range/2)*scale;
  ctx.fillStyle='#4a90d9'; ctx.beginPath(); ctx.arc(startPos, cy, 8, 0, Math.PI*2); ctx.fill();
  ctx.fillStyle='#fff'; ctx.font='bold 10px sans-serif'; ctx.fillText(a, startPos-4, cy+4);
  ctx.fillStyle='#e74c3c'; ctx.beginPath(); ctx.arc(endPos, cy, 8, 0, Math.PI*2); ctx.fill();
  ctx.fillStyle='#fff'; ctx.font='bold 10px sans-serif'; ctx.fillText(result, endPos-6, cy+4);
  ctx.strokeStyle='rgba(231,76,60,0.5)'; ctx.lineWidth=2; ctx.setLineDash([5,5]);
  ctx.beginPath(); ctx.moveTo(startPos, cy-30); ctx.lineTo(endPos, cy-30); ctx.stroke();
  ctx.setLineDash([]);
  ctx.fillStyle='#333'; ctx.font='bold 20px sans-serif';
  ctx.fillText(a + ' ' + (op==='add'?'+':op==='sub'?'−':'×') + ' ' + b + ' = ' + result, 20, 40);
  // Step indicator
  if(op!=='mul'){{
    const step = op==='add'?b:-b; const dir = step>=0?1:-1;
    for(let i=0;i<Math.abs(b);i++){{
      const px = ox + (a + dir*i + range/2)*scale;
      ctx.fillStyle='rgba(46,204,113,0.5)';
      ctx.beginPath(); ctx.arc(px + dir*scale/2, cy-40, 3+i, 0, Math.PI*2); ctx.fill();
    }}
  }}
}} drawNumLine();
</script></div>'''
    return {"success": True, "html": html, "template": "number-line", "title": "Number Line Operations"}


def _pomelli_probability(params):
    html = '''<div class="pomelli-container" style="width:100%;max-width:700px;margin:0 auto;">
<canvas id="pomelli-canvas-prob" width="650" height="400" style="width:100%;background:#fff;border-radius:12px;border:1px solid var(--border);"></canvas>
<div style="display:flex;gap:1rem;margin-top:1rem;flex-wrap:wrap;align-items:center;">
  <button onclick="runProb()" style="padding:0.5rem 1.5rem;background:#4a90d9;color:#fff;border:none;border-radius:6px;cursor:pointer;">🎲 Roll Dice (1000x)</button>
  <button onclick="runCoin()" style="padding:0.5rem 1.5rem;background:#2ecc71;color:#fff;border:none;border-radius:6px;cursor:pointer;">🪙 Flip Coin (1000x)</button>
  <span id="prob-result" style="font-weight:600;"></span>
</div>
<script>
let probData = {};
async function runProb() {
  const canvas = document.getElementById('pomelli-canvas-prob');
  const ctx = canvas.getContext('2d');
  if (!canvas || !ctx) return;
  const w=canvas.width, h=canvas.height;
  const rolls = 1000; const counts = [0,0,0,0,0,0];
  for(let i=0;i<rolls;i++) counts[Math.floor(Math.random()*6)]++;
  ctx.clearRect(0,0,w,h);
  const barW = 60, gap = 30, startX = (w - 6*(barW+gap) + gap)/2;
  const maxCount = Math.max(...counts);
  ctx.fillStyle='#333'; ctx.font='bold 18px sans-serif'; ctx.fillText('Dice Roll Distribution ('+rolls+' rolls)', 20, 35);
  counts.forEach((c,i) => {
    const barH = (c/maxCount)*250;
    const x = startX + i*(barW+gap);
    const gradient = ctx.createLinearGradient(x, h-80-barH, x, h-80);
    gradient.addColorStop(0,'#4a90d9'); gradient.addColorStop(1,'#2ecc71');
    ctx.fillStyle = gradient;
    ctx.fillRect(x, h-80-barH, barW, barH);
    ctx.fillStyle='#333'; ctx.font='14px sans-serif'; ctx.textAlign='center';
    ctx.fillText(i+1, x+barW/2, h-55);
    ctx.fillText(c, x+barW/2, h-90-barH);
    ctx.fillText((c/rolls*100).toFixed(1)+'%', x+barW/2, h-70-barH);
  });
  document.getElementById('prob-result').textContent = 'Expected: 16.7% each';
}
async function runCoin() {
  const canvas = document.getElementById('pomelli-canvas-prob');
  const ctx = canvas.getContext('2d');
  if (!canvas || !ctx) return;
  const w=canvas.width, h=canvas.height;
  const flips = 1000;
  let heads = 0, tails = 0;
  for(let i=0;i<flips;i++) Math.random()<0.5 ? heads++ : tails++;
  ctx.clearRect(0,0,w,h);
  const barW = 150, gap = 50, startX = (w - 2*barW - gap)/2;
  ctx.fillStyle='#333'; ctx.font='bold 18px sans-serif';
  ctx.fillText('Coin Flip Distribution ('+flips+' flips)', 20, 35);
  [[heads,'Heads','#f1c40f'],[tails,'Tails','#3498db']].forEach(([c,label,color],i) => {
    const barH = (c/(flips/2))*200;
    const x = startX + i*(barW+gap);
    ctx.fillStyle = color;
    ctx.fillRect(x, h-80-barH, barW, barH);
    ctx.fillStyle='#333'; ctx.font='bold 16px sans-serif'; ctx.textAlign='center';
    ctx.fillText(label, x+barW/2, h-55);
    ctx.fillText(c, x+barW/2, h-90-barH);
    ctx.fillText((c/flips*100).toFixed(1)+'%', x+barW/2, h-70-barH);
  });
  document.getElementById('prob-result').textContent = 'Expected: 50% each';
}
</script></div>'''
    return {"success": True, "html": html, "template": "probability", "title": "Probability Simulator"}


def _pomelli_statistics(params):
    html = '''<div class="pomelli-container" style="width:100%;max-width:700px;margin:0 auto;">
<canvas id="pomelli-canvas-stats" width="650" height="400" style="width:100%;background:#fff;border-radius:12px;border:1px solid var(--border);"></canvas>
<div style="display:flex;gap:1rem;margin-top:1rem;flex-wrap:wrap;align-items:center;">
  <button onclick="genData()" style="padding:0.5rem 1.5rem;background:#4a90d9;color:#fff;border:none;border-radius:6px;cursor:pointer;">📊 Generate Random Data</button>
  <span id="stats-result" style="font-weight:600;"></span>
</div>
<script>
function genData() {
  const canvas = document.getElementById('pomelli-canvas-stats');
  const ctx = canvas.getContext('2d');
  if (!canvas || !ctx) return;
  const w=canvas.width, h=canvas.height;
  const data = Array.from({length:8},()=>Math.floor(Math.random()*50+10));
  const labels = ['A','B','C','D','E','F','G','H'];
  ctx.clearRect(0,0,w,h);
  const barW = 55, gap = 20, startX = (w - 8*(barW+gap) + gap)/2;
  const maxVal = Math.max(...data);
  const mean = data.reduce((a,b)=>a+b,0)/data.length;
  ctx.fillStyle='#333'; ctx.font='bold 18px sans-serif';
  ctx.fillText('Data Distribution   Mean: '+mean.toFixed(1), 20, 35);
  data.forEach((v,i) => {
    const barH = (v/maxVal)*220;
    const x = startX + i*(barW+gap);
    ctx.fillStyle = v >= mean ? '#4a90d9' : '#e74c3c';
    ctx.fillRect(x, h-80-barH, barW, barH);
    ctx.fillStyle='#333'; ctx.font='14px sans-serif'; ctx.textAlign='center';
    ctx.fillText(labels[i], x+barW/2, h-55);
    ctx.fillText(v, x+barW/2, h-90-barH);
  });
  // Mean line
  const meanY = h - 80 - (mean/maxVal)*220;
  ctx.strokeStyle='#e74c3c'; ctx.lineWidth=2; ctx.setLineDash([8,4]);
  ctx.beginPath(); ctx.moveTo(startX, meanY); ctx.lineTo(startX+8*(barW+gap)-gap, meanY); ctx.stroke();
  ctx.setLineDash([]);
  ctx.fillStyle='#e74c3c'; ctx.font='12px sans-serif'; ctx.fillText('Mean: '+mean.toFixed(1), startX, meanY-5);
  // Summary stats
  const sorted = [...data].sort((a,b)=>a-b);
  const median = sorted.length%2===0 ? (sorted[sorted.length/2-1]+sorted[sorted.length/2])/2 : sorted[Math.floor(sorted.length/2)];
  ctx.textAlign='left'; ctx.font='14px sans-serif'; ctx.fillStyle='#666';
  ctx.fillText('Median: '+median+'  |  Min: '+sorted[0]+'  |  Max: '+sorted[sorted.length-1]+'  |  Range: '+(sorted[sorted.length-1]-sorted[0]), 20, 70);
  document.getElementById('stats-result').textContent = 'Mean='+mean.toFixed(1)+' Median='+median;
} genData();
</script></div>'''
    return {"success": True, "html": html, "template": "statistics", "title": "Statistics Visualizer"}


def _pomelli_area_perimeter(params):
    html = '''<div class="pomelli-container" style="width:100%;max-width:700px;margin:0 auto;">
<canvas id="pomelli-canvas-ap" width="650" height="400" style="width:100%;background:#fff;border-radius:12px;border:1px solid var(--border);"></canvas>
<div style="display:flex;gap:1rem;margin-top:1rem;flex-wrap:wrap;align-items:center;">
  <label>Shape: <select id="ap-shape" onchange="drawAP()">
    <option value="rectangle">Rectangle</option>
    <option value="square">Square</option>
    <option value="circle">Circle</option>
    <option value="triangle">Triangle</option>
  </select></label>
  <label>Width/Radius: <input type="range" id="ap-w" min="30" max="180" value="120" oninput="drawAP()" style="width:100px;"></label>
  <label>Height: <input type="range" id="ap-h" min="30" max="180" value="80" oninput="drawAP()" style="width:100px;"></label>
</div>
<script>
function drawAP() {
  const canvas = document.getElementById('pomelli-canvas-ap');
  const ctx = canvas.getContext('2d');
  if (!canvas || !ctx) return;
  const w=canvas.width, h=canvas.height;
  const shape = document.getElementById('ap-shape').value;
  const wd = parseInt(document.getElementById('ap-w').value);
  const ht = parseInt(document.getElementById('ap-h').value);
  ctx.clearRect(0,0,w,h);
  const cx = w/2, cy = h/2 - 20;
  ctx.strokeStyle='#333'; ctx.lineWidth=3;
  if (shape==='rectangle') {
    ctx.fillStyle='rgba(74,144,217,0.2)'; ctx.fillRect(cx-wd/2, cy-ht/2, wd, ht);
    ctx.strokeRect(cx-wd/2, cy-ht/2, wd, ht);
    ctx.fillStyle='#333'; ctx.font='bold 20px sans-serif';
    ctx.fillText('Area = '+wd+' × '+ht+' = '+(wd*ht)+' sq units', 20, 35);
    ctx.fillText('Perimeter = 2×('+wd+'+'+ht+') = '+(2*(wd+ht))+' units', 20, 65);
  } else if (shape==='square') {
    ctx.fillStyle='rgba(46,204,113,0.2)'; ctx.fillRect(cx-wd/2, cy-wd/2, wd, wd);
    ctx.strokeRect(cx-wd/2, cy-wd/2, wd, wd);
    ctx.fillStyle='#333'; ctx.font='bold 20px sans-serif';
    ctx.fillText('Area = '+wd+'² = '+(wd*wd)+' sq units', 20, 35);
    ctx.fillText('Perimeter = 4×'+wd+' = '+(4*wd)+' units', 20, 65);
  } else if (shape==='circle') {
    ctx.beginPath(); ctx.arc(cx, cy, wd, 0, Math.PI*2);
    ctx.fillStyle='rgba(231,76,60,0.2)'; ctx.fill();
    ctx.stroke();
    ctx.fillStyle='#333'; ctx.font='bold 20px sans-serif';
    ctx.fillText('Area = π×'+wd+'² = '+(Math.PI*wd*wd).toFixed(1)+' sq units', 20, 35);
    ctx.fillText('Circumference = 2π×'+wd+' = '+(2*Math.PI*wd).toFixed(1)+' units', 20, 65);
  } else if (shape==='triangle') {
    ctx.beginPath(); ctx.moveTo(cx, cy-ht/2); ctx.lineTo(cx-wd/2, cy+ht/2); ctx.lineTo(cx+wd/2, cy+ht/2); ctx.closePath();
    ctx.fillStyle='rgba(155,89,182,0.2)'; ctx.fill(); ctx.stroke();
    ctx.fillStyle='#333'; ctx.font='bold 20px sans-serif';
    ctx.fillText('Area = ½ × '+wd+' × '+ht+' = '+(0.5*wd*ht)+' sq units', 20, 35);
    const side = Math.sqrt((wd/2)*(wd/2)+ht*ht);
    ctx.fillText('Perimeter ≈ '+(2*side+wd).toFixed(1)+' units', 20, 65);
  }
} drawAP();
</script></div>'''
    return {"success": True, "html": html, "template": "area-perimeter", "title": "Area & Perimeter Explorer"}


# ─── MetAI: Concept Video Storyboard Generator (zero API key) ────────────

def metai_generate(concept, subject="Science", style="explainer"):
    context = _get_rag_context(concept, subject=subject, limit=4)
    prompt = f"""Use the following verified textbook context:
Context:
{context}

Create an HTML animated storyboard explaining "{concept}" for a Class X {subject} student.
Style: {style} educational animation.

Generate a complete self-contained HTML page with:
1. A sequence of 4-6 animated "scenes" that auto-advance or can be clicked through
2. Each scene has a title, visual diagram (use SVG or CSS art), and clear explanation text
3. Transitions between scenes (fade, slide, or zoom effects using CSS animations)
4. Progress indicator showing which scene is active
5. Play/pause and next/prev navigation controls
6. All CSS and JS inline

The HTML should be a complete, self-contained educational video storyboard that explains the concept step by step.
Use educational colors, clear typography, and engaging animations."""
    html = _llm(prompt, "You create animated HTML storyboards for education.", 3072, 0.3)
    if not html or "AI Offline" in html or len(html) < 500:
        html = metai_fallback_storyboard(concept, subject, style)
    return {"success": True, "html": html, "concept": concept, "subject": subject}


def metai_fallback_storyboard(concept, subject, style):
    esc = html_mod.escape
    scenes = [
        {"title": f"Introduction to {concept}", "icon": "📖", "color": "#4a90d9",
         "text": f"Let's explore <strong>{concept}</strong> — a key topic in {subject}. By the end, you'll understand the core concepts and how they apply in real life."},
        {"title": "The Basics", "icon": "📐", "color": "#2ecc71",
         "text": "Every topic builds on foundational knowledge. Start by understanding the core definition and why it matters."},
        {"title": "How It Works", "icon": "⚙️", "color": "#e67e22",
         "text": "The process involves several key steps that work together. Each step is important for the overall understanding."},
        {"title": "Real-World Example", "icon": "🌍", "color": "#9b59b6",
         "text": "Let's see how this applies in real life with an example you encounter every day."},
        {"title": "Key Takeaways", "icon": "⭐", "color": "#e74c3c",
         "text": "Remember these important points: understand the core principle, practice with examples, and connect to other topics."},
    ]
    slides_js = ""
    slides_html = ""
    dots_html = ""
    for i, s in enumerate(scenes):
        slides_html += f'''<div class="metai-scene" data-index="{i}" style="display:{'block' if i==0 else 'none'};padding:2rem;text-align:center;min-height:300px;">
  <div style="font-size:4rem;margin-bottom:1rem;">{s['icon']}</div>
  <h3 style="color:{s['color']};font-size:1.5rem;margin-bottom:1rem;">{s['title']}</h3>
  <div style="background:{s['color']}15;border-radius:12px;padding:1.5rem;max-width:500px;margin:0 auto;">
    <svg width="80" height="4" style="display:block;margin:0 auto 1rem;"><rect width="80" height="4" fill="{s['color']}" rx="2"/></svg>
    <p style="font-size:1.1rem;line-height:1.6;color:#333;">{s['text']}</p>
  </div>
</div>'''
        dots_html += f'<span class="metai-dot" data-index="{i}" onclick="goToScene({i})" style="display:inline-block;width:12px;height:12px;border-radius:50%;background:{s["color"]};margin:0 4px;cursor:pointer;opacity:{0.4 if i>0 else 1};"></span>'
    html = f'''<div class="metai-container" style="background:linear-gradient(135deg,#f8f9fa,#e8f4f8);border-radius:16px;padding:1.5rem;margin-top:1rem;">
  <div class="metai-scenes">{slides_html}</div>
  <div style="text-align:center;margin:1rem 0;">
    <div class="metai-dots">{dots_html}</div>
  </div>
  <div style="text-align:center;display:flex;gap:0.5rem;justify-content:center;flex-wrap:wrap;">
    <button onclick="prevScene()" style="padding:0.5rem 1.2rem;background:#4a90d9;color:#fff;border:none;border-radius:8px;cursor:pointer;font-weight:600;">◀ Previous</button>
    <span id="metai-counter" style="padding:0.5rem 1rem;font-weight:600;">1 / {len(scenes)}</span>
    <button onclick="nextScene()" style="padding:0.5rem 1.2rem;background:#4a90d9;color:#fff;border:none;border-radius:8px;cursor:pointer;font-weight:600;">Next ▶</button>
    <button onclick="toggleAutoPlay()" id="metai-play-btn" style="padding:0.5rem 1.2rem;background:#2ecc71;color:#fff;border:none;border-radius:8px;cursor:pointer;font-weight:600;">▶ Auto-Play</button>
  </div>
  <script>
  let metaiCurrent = 0; let metaiTotal = {len(scenes)}; let metaiTimer = null;
  function showScene(n) {{
    document.querySelectorAll('.metai-scene').forEach((s,i) => s.style.display = i===n ? 'block' : 'none');
    document.querySelectorAll('.metai-dot').forEach((d,i) => d.style.opacity = i===n ? '1' : '0.4');
    document.getElementById('metai-counter').textContent = (n+1) + ' / ' + metaiTotal;
    metaiCurrent = n;
  }}
  function goToScene(n) {{ showScene(n); }}
  function nextScene() {{ if(metaiCurrent < metaiTotal-1) showScene(metaiCurrent+1); }}
  function prevScene() {{ if(metaiCurrent > 0) showScene(metaiCurrent-1); }}
  function toggleAutoPlay() {{
    if(metaiTimer) {{ clearInterval(metaiTimer); metaiTimer=null; document.getElementById('metai-play-btn').textContent='▶ Auto-Play'; }}
    else {{ metaiTimer = setInterval(()=>{{ if(metaiCurrent<metaiTotal-1) nextScene(); else {{ clearInterval(metaiTimer); metaiTimer=null; }} }}, 4000);
      document.getElementById('metai-play-btn').textContent='⏸ Pause'; }}
  }}
  </script>
</div>'''
    return html


# ─── Enhanced NotebookLM: Pedagogical Concept Detailing ──────────────────

def notebooklm_pedagogical(subject, chapter, topic, concept_text=""):
    prompt = f"""Create a detailed pedagogical study guide for the topic "{topic}" in {subject} (Chapter: {chapter}).

Structure the guide as follows:

## 📚 Prerequisites
What foundational knowledge the student needs before studying this topic.

## 🎯 Learning Objectives
3-5 clear, measurable objectives for this topic.

## 🔑 Key Concepts
Break down the core concepts with simple explanations.

## 📖 Step-by-Step Explanation
Explain step by step, building from basics to deeper understanding.

## 🔗 Connections
How this topic connects to other topics in the curriculum.

## 💡 Common Misconceptions
List 2-3 common mistakes or misconceptions students have.

## ⭐ Summary
A concise summary in 3-4 bullet points.

## 📝 Practice Questions
3 questions at different difficulty levels (easy, medium, hard).

Format in Markdown with clear headings and sections.
Context: {concept_text[:1500]}"""
    result = _llm(prompt, "You are a pedagogical expert creating study guides for Class X students.", 2048, 0.3)
    if not result or "AI Offline" in result:
        result = f"""# Pedagogical Guide: {topic}

## 📚 Prerequisites
Basic understanding of foundational {subject} concepts.

## 🎯 Learning Objectives
- Understand the core definition of {topic}
- Explain key principles and processes
- Apply knowledge to solve related problems
- Connect to real-world applications

## 🔑 Key Concepts
{topic} is a fundamental concept in {subject}. Focus on understanding the basic principles first.

## 📖 Step-by-Step Explanation
1. Start with the basic definition
2. Understand the key components
3. See how they work together
4. Practice with examples

## 🔗 Connections
This topic connects to other chapters and builds a foundation for advanced study.

## 💡 Common Misconceptions
- Confusing related terms
- Skipping foundational steps
- Memorizing without understanding

## ⭐ Summary
- {topic} is essential for {subject}
- Focus on understanding, not memorizing
- Practice regularly

## 📝 Practice Questions
1. (Easy) What is {topic}?
2. (Medium) Explain how {topic} works step by step.
3. (Hard) How does {topic} connect to real-world applications?"""
    return {"success": True, "markdown": result, "title": f"Pedagogical Guide: {topic}"}


# ─── MetaAI: Contextual Learning (powered by Mistral AI) ──────────────────

def metaai_contextual_learn(topic, chapter="", subject="", level="simple"):
    """Deep contextual learning powered by Mistral/Gemini."""
    client = get_client()
    if client.available:
        response = client.contextual_learn(topic, chapter, subject, level)
        return {"success": True, "content": response, "backend": client.backend_name, "model": client.model_name}
    return {"success": False, "content": "", "backend": "none", "model": ""}


# ─── Internal Concept Storyboards & Simulated Video Lessons ────────────────

def youtube_search(query, max_results=5):
    """Search internal database for CBSE educational concept chapters using local RAG."""
    try:
        from rag_engine import get_engine
        engine = get_engine()
        chunks = engine.hybrid_search(query, limit=max_results)
        results = []
        for c in chunks:
            results.append({
                "videoId": f"local_storyboard_{c['id']}",
                "title": f"Animated Lesson: {c['title']}",
                "channel": f"CBSE {c.get('chapter_title', 'Science')}",
                "thumb": "",
                "searchUrl": f"/ai/metai?concept={urllib.parse.quote(c['title'])}&style=storyboard"
            })
        return results
    except Exception:
        return []


def youtube_video_embed_html(video_id, title="", autoplay=False):
    """Generate responsive simulated storyboard player."""
    concept = title.replace("Animated Lesson: ", "")
    return f"""
    <div class="video-container" style="position:relative;background:#1a1a2e;color:#fff;border-radius:12px;padding:1.5rem;margin:1rem 0;box-shadow:0 8px 30px rgba(0,0,0,0.15);border:1px solid #2e2e4e;">
        <h4 style="margin:0 0 1rem 0;color:#00f2fe;font-size:1.2rem;display:flex;align-items:center;gap:0.5rem;">🎬 Internal Concept Player: {html_mod.escape(concept)}</h4>
        <div style="background:#0f0f1e;border-radius:8px;padding:1.5rem;text-align:center;min-height:200px;display:flex;flex-direction:column;justify-content:center;align-items:center;border:1px dashed #444;">
            <div id="simulated-canvas-{video_id}" style="font-size:3.5rem;margin-bottom:1rem;animation: pulse 2s infinite;">📺</div>
            <div id="simulated-text-{video_id}" style="font-size:1.05rem;line-height:1.6;color:#e2e2e9;max-width:550px;margin-bottom:1.5rem;">
                This self-contained animated study module is grounded in local RAG textbook contents. Click below to view the interactive storyboard!
            </div>
            <a href="/ai/metai?concept={urllib.parse.quote(concept)}&style=storyboard" style="padding:0.7rem 1.8rem;background:linear-gradient(135deg,#00f2fe,#4facfe);color:#1a1a2e;text-decoration:none;border-radius:8px;font-weight:700;cursor:pointer;box-shadow:0 4px 15px rgba(0,242,254,0.3);display:inline-block;">Launch Interactive Storyboard</a>
        </div>
    </div>
    """


def youtube_section_html(topic, chapter="", subject=""):
    """Generate a storyboard animated section for topic/chapter pages."""
    results = youtube_search(f"{topic} {chapter} {subject}")
    cards = ""
    for r in results:
        cards += f"""
        <div class="video-card" style="background:var(--card-bg);border-radius:12px;overflow:hidden;border:1px solid var(--border);cursor:pointer;padding:1rem;transition:all 0.3s;box-shadow:0 4px 12px rgba(0,0,0,0.05);"
             onclick="window.location.href='/ai/metai?concept={urllib.parse.quote(r['title'].replace('Animated Lesson: ', ''))}&style=storyboard'">
            <div style="font-size:2rem;margin-bottom:0.5rem;">🎬</div>
            <div style="font-size:0.95rem;font-weight:600;color:var(--primary);line-height:1.3;margin-bottom:0.25rem;">{html_mod.escape(r['title'])}</div>
            <div style="font-size:0.75rem;color:var(--text-muted);">{html_mod.escape(r.get('channel',''))}</div>
        </div>"""
    
    html = f"""
    <div class="video-section" style="margin:2rem 0;padding:1.5rem;background:linear-gradient(135deg,rgba(79,172,254,0.05),rgba(0,242,254,0.05));border-radius:16px;border:1px solid var(--border);">
        <h4 style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.5rem;color:var(--primary);font-size:1.2rem;">🎬 Internal Concept Storyboards</h4>
        <p class="subtitle" style="font-size:0.85rem;color:var(--text-muted);margin-bottom:1rem;">Interactive offline animated lessons generated from verified textbook RAG context.</p>
        <div class="video-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:1rem;margin-bottom:1rem;">
            {cards}
        </div>
    </div>"""
    return html


def youtube_generate_clips(topic_id=None, chapter_id=None, topic_name=None, max_clips=8):
    """Offline storyboard playlist generator powered by local RAG engine."""
    content_segments = []
    conn = None
    try:
        from database import get_db as _get_db
        conn = _get_db()
    except Exception:
        pass

    if topic_id and conn and conn.table_exists("topics"):
        topic = conn.query_one("SELECT * FROM topics WHERE id = ?", (topic_id,))
        if topic:
            topic_name = topic_name or topic["title"]
            if conn.table_exists("chunks"):
                chunks = conn.query("SELECT * FROM chunks WHERE topic_id = ? ORDER BY seq", (topic_id,))
                for c in chunks:
                    t = c.get("title", "").strip() or topic["title"]
                    ct = (c.get("content", "") or "")
                    if ct:
                        content_segments.append({"title": t, "text": ct})
            if not content_segments and topic.get("content"):
                content_segments.append({"title": topic["title"], "text": topic["content"]})

    if not content_segments and chapter_id and conn and conn.table_exists("topics"):
        topics = conn.query("SELECT * FROM topics WHERE chapter_id = ? ORDER BY num, title", (chapter_id,))
        for t in topics:
            t_text = (t.get("content", "") or "")
            content_segments.append({"title": t["title"], "text": t_text or f"Learn about {t['title']}"})

    if not content_segments and topic_name:
        from rag_engine import get_engine
        engine = get_engine()
        results = engine.hybrid_search(topic_name, limit=max_clips)
        for r in results:
            content_segments.append({"title": r["title"], "text": r["content"]})

    if not content_segments:
        content_segments = [{"title": topic_name or "CBSE Topic", "text": "Detailed information about this topic."}]

    clips = []
    for i, seg in enumerate(content_segments[:max_clips]):
        title = seg["title"]
        text = seg["text"]
        prompt = f"""You are a concept visualizer and storyboard artist.
Given the following textbook section:
Title: {title}
Content: {text}

Generate a short animated storyboard script for this section.
Include:
1. Visual description (exactly what happens in the animation/diagram, e.g., "A leaf diagram zoom-in, highlighting stomata opening and closing")
2. Voiceover narration script (friendly, academic Class X tone, explain clearly)
3. Simulated duration in seconds (usually between 20 to 60 seconds)
4. Highlight formula or key term

Return the response in JSON format with keys:
- visual_description (string)
- voiceover_script (string)
- duration_seconds (int)
- key_formula_or_term (string)
- icon (emoji)
- color (hex code)"""
        res_text = _llm(prompt, "You output ONLY JSON format.", 512, 0.2)
        try:
            res_text_clean = re.sub(r"^```json\s*|```$", "", res_text.strip(), flags=re.MULTILINE)
            info = json.loads(res_text_clean)
        except Exception:
            info = {
                "visual_description": f"Animation showing the core principles of {title}.",
                "voiceover_script": text[:300],
                "duration_seconds": max(25, len(text.split()) // 3),
                "key_formula_or_term": title,
                "icon": "🎬",
                "color": "#4facfe"
            }
        
        clip_vo = quillbot_speak_segments(info["voiceover_script"])
        clips.append({
            "index": i + 1,
            "segment_title": title,
            "text": info["voiceover_script"],
            "visual_description": info["visual_description"],
            "key_formula_or_term": info["key_formula_or_term"],
            "icon": info.get("icon", "🎬"),
            "color": info.get("color", "#4facfe"),
            "videoId": f"local_clip_{i+1}",
            "video_title": title,
            "duration_sec": info["duration_seconds"],
            "voiceover": clip_vo,
        })

    return {
        "success": True,
        "topic": topic_name or "CBSE Topic",
        "total_clips": len(clips),
        "total_duration": sum(c["duration_sec"] for c in clips),
        "clips": clips,
    }


# ─── OpenGrok: Code, Formula & Theorem Search ──────────────────────────────

OPENGROK_URL = os.environ.get("OPENGROK_URL", "")


def opengrok_search(query, max_results=5):
    """Search code/formulas/theorems via OpenGrok API with fallback to local knowledge base."""
    client = get_client()
    return client.opengrok_search(query, max_results)


def opengrok_results_html(query):
    """Generate HTML for OpenGrok formula/theorem search results."""
    results = opengrok_search(query)
    items = ""
    for r in results:
        cat = r.get("category", "General")
        snippet = r.get("snippet", "")
        items += f"""
        <div class="og-result" style="background:var(--card-bg);border-radius:8px;padding:0.6rem 0.8rem;border:1px solid var(--border);margin-bottom:0.4rem;">
            <div style="font-size:0.88rem;font-weight:600;color:var(--primary);font-family:'Courier New',monospace;">{html_mod.escape(r['title'])}</div>
            <div style="display:flex;gap:0.5rem;margin-top:0.2rem;font-size:0.72rem;color:var(--text-muted);">
                <span class="og-category" style="background:#eef2ff;padding:0.05rem 0.4rem;border-radius:4px;">{cat}</span>
                {f'<span>{html_mod.escape(snippet[:120])}</span>' if snippet else ''}
            </div>
        </div>"""
    if not items:
        items = f'<p style="color:#888;font-size:0.85rem;">No formula/theorem results for "{html_mod.escape(query)}". Try different keywords.</p>'
    html = f"""
    <div class="opengrok-section" style="margin:1rem 0;">
        <h4 style="display:flex;align-items:center;gap:0.4rem;margin-bottom:0.5rem;color:var(--primary);">📐 Formulas & Theorems</h4>
        <div class="og-results">{items}</div>
        <p style="font-size:0.72rem;color:var(--text-muted);margin-top:0.25rem;">
            {'OpenGrok API · ' if OPENGROK_URL else 'Local Formula Database · '}
            CBSE Class 10 Mathematics & Science
        </p>
    </div>"""
    return html
