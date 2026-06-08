"""AI Content Enricher — generates explanations, formulas, problems for ANY topic on-the-fly"""
import json
import html as html_mod
from llm_client import get_client


def _llm(prompt, system=None, max_tokens=1024, temp=0.3):
    client = get_client()
    if client.available:
        return client.query(prompt, system, max_tokens, temp)
    return ""


def generate_explanation(topic, chapter, subject, chunk_text=""):
    prompt = f"""Create a detailed CBSE Class X explanation for:
Subject: {subject}
Chapter: {chapter}
Topic: {topic}

Generate a comprehensive explanation covering:
1. **Core Concept** — Simple definition and what it means
2. **Key Formula / Theorem** (if applicable) — Present in LaTeX math mode: $$formula$$
3. **Step-by-Step Explanation** — Break it down logically
4. **Real-Life Example** — Connect to daily life
5. **Important Terms** — Key vocabulary with definitions

Context from textbook: {chunk_text[:1500]}

Return the explanation in HTML with <p>, <strong>, <ul>, <li> tags.
Use $$...$$ for LaTeX formulas."""
    return _llm(prompt, "You are a CBSE Class X subject expert who explains concepts clearly.", 1536, 0.3)


def generate_formula_card(topic, subject):
    prompt = f"""Generate a formula/reference card for "{topic}" ({subject} CBSE Class X).

Include:
1. All relevant formulas in LaTeX: $$formula$$
2. Variable definitions
3. Important conditions or assumptions
4. Quick reference tips

Return as HTML with <div class="formula-card"> containing the content.
Use $$...$$ for LaTeX. Use <strong> for emphasis."""
    return _llm(prompt, "You generate concise formula reference cards.", 1024, 0.2)


def generate_solved_problem(topic, chapter, subject, difficulty="medium"):
    prompt = f"""Create a {difficulty}-difficulty CBSE Class X problem for:
Subject: {subject}
Chapter: {chapter}
Topic: {topic}

Return JSON with exactly these fields:
{{
  "problem": "Problem statement with any formulas in $$...$$",
  "solution": "Complete step-by-step solution showing ALL working",
  "formula_used": "The key formula(s) used, in LaTeX $$...$$",
  "answer": "Final answer only",
  "steps": ["Step 1: ...", "Step 2: ...", "Step 3: ..."],
  "difficulty": "{difficulty}",
  "topic": "{topic}"
}}

Make the problem realistic for a Class X board exam. Include numerical values where appropriate."""
    raw = _llm(prompt, "You output ONLY valid JSON, no other text.", 1024, 0.2)
    try:
        start = raw.index("{")
        end = raw.rindex("}") + 1
        return json.loads(raw[start:end])
    except (ValueError, json.JSONDecodeError):
        return {
            "problem": f"Explain the key concepts of {topic} with examples.",
            "solution": f"1. Define {topic}\n2. Explain key principles\n3. Provide a real-world example\n4. Summarize the main points",
            "formula_used": "",
            "answer": f"See step-by-step solution for {topic}.",
            "steps": [f"Step 1: Understand the definition of {topic}", f"Step 2: Identify the key components", f"Step 3: Apply to a practical example"],
            "difficulty": difficulty,
            "topic": topic,
        }


def generate_mcqs(topic, chapter, subject, count=5):
    prompt = f"""Generate {count} multiple-choice questions for Class X {subject} - {chapter} - {topic}.

Each question should have 4 options (A,B,C,D) with one correct answer.
Include a brief explanation for the correct answer.
Use formulas in $$...$$ where appropriate.

Return ONLY a valid JSON array:
[{{"question": "...", "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}}, "answer": "A", "explanation": "..."}}]"""
    raw = _llm(prompt, "You output ONLY valid JSON arrays.", 1024, 0.2)
    try:
        start = raw.index("[")
        end = raw.rindex("]") + 1
        return json.loads(raw[start:end])
    except (ValueError, json.JSONDecodeError):
        return [{"question": f"What is {topic}?", "options": {"A": "Definition A", "B": "Definition B", "C": "Definition C", "D": "Definition D"}, "answer": "A", "explanation": f"The correct definition of {topic} is option A."}]


def generate_theorem_breakdown(topic, subject):
    prompt = f"""Create a theorem/principle breakdown for "{topic}" ({subject} CBSE Class X).

Structure:
1. **Statement** — The theorem/principle clearly stated
2. **Given/Required** — What we know and what to prove
3. **Proof/Derivation** — Step-by-step logical reasoning with formulas in $$...$$
4. **Conclusion** — What the theorem tells us
5. **Application** — Where this is used in problems

Return as HTML with <p>, <ol>, <li> tags. Use $$...$$ for LaTeX."""
    return _llm(prompt, "You are a mathematics/science educator who explains theorems clearly.", 1536, 0.3)


def generate_experiment_breakdown(topic, subject):
    prompt = f"""Create a laboratory experiment breakdown for "{topic}" ({subject} CBSE Class X).

Structure:
1. **Aim** — Purpose of the experiment
2. **Materials Required** — List of equipment
3. **Theory** — Background concepts with formulas in $$...$$
4. **Procedure** — Step-by-step instructions
5. **Observations** — What to record (table format)
6. **Calculation** — How to compute results with formulas
7. **Result** — Expected outcome
8. **Precautions** — Safety notes

Return as HTML with <p>, <ol>, <li>, <table> tags. Use $$...$$ for LaTeX."""
    return _llm(prompt, "You are a science lab instructor.", 1536, 0.3)


def enrich_topic_content(topic, chapter, subject, chunk_text="", topic_type="concept"):
    explanation = generate_explanation(topic, chapter, subject, chunk_text)
    formula_card = generate_formula_card(topic, subject)
    problems = [generate_solved_problem(topic, chapter, subject, d) for d in ["easy", "medium", "hard"]]
    mcqs = generate_mcqs(topic, chapter, subject, 3)

    if topic_type == "theorem":
        special = generate_theorem_breakdown(topic, subject)
    elif topic_type == "experiment":
        special = generate_experiment_breakdown(topic, subject)
    else:
        special = ""

    return {
        "explanation": explanation if explanation and "AI Offline" not in explanation else "",
        "formula_card": formula_card if formula_card and "AI Offline" not in formula_card else "",
        "problems": problems,
        "mcqs": mcqs,
        "special": special,
    }


def format_ai_content(enriched):
    html = ""
    if enriched.get("explanation"):
        html += f'<div class="ai-section"><h3>📖 Detailed Explanation</h3><div class="ai-content">{enriched["explanation"]}</div></div>'
    if enriched.get("formula_card"):
        html += f'<div class="ai-section"><h3>📐 Formula Reference</h3><div class="ai-content">{enriched["formula_card"]}</div></div>'
    if enriched.get("special"):
        html += f'<div class="ai-section"><h3>🔬 Detailed Breakdown</h3><div class="ai-content">{enriched["special"]}</div></div>'
    if enriched.get("problems"):
        html += '<div class="ai-section"><h3>✏️ Solved Problems</h3>'
        for i, p in enumerate(enriched["problems"]):
            if not p.get("problem"):
                continue
            html += f'<div class="problem-box">'
            html += f'<div class="problem-header">Problem {i+1} ({p.get("difficulty","medium").title()})</div>'
            html += f'<div class="problem-text">{p.get("problem","")}</div>'
            if p.get("formula_used"):
                html += f'<div class="formula-used">Formula: {p["formula_used"]}</div>'
            html += f'<details><summary style="cursor:pointer;color:#0f3460;font-weight:500;">🔍 Show Solution</summary>'
            html += f'<div class="solution-steps"><ol>'
            for s in p.get("steps", []):
                html += f'<li>{s}</li>'
            html += f'</ol></div>'
            if p.get("answer"):
                html += f'<div class="final-answer"><strong>Answer:</strong> {p["answer"]}</div>'
            html += f'</details></div>'
        html += '</div>'
    if enriched.get("mcqs"):
        html += '<div class="ai-section"><h3>🎯 Practice MCQs</h3>'
        for i, q in enumerate(enriched["mcqs"]):
            if not q.get("question"):
                continue
            html += f'<div class="mcq-box" data-answer="{q.get("answer","")}">'
            html += f'<p><strong>Q{i+1}.</strong> {q.get("question","")}</p>'
            for k, v in q.get("options", {}).items():
                html += f'<label class="mcq-option"><input type="radio" name="mcq-{i}" value="{k}" onchange="checkMCQ(this)"> {k}. {v}</label><br>'
            html += f'<div class="mcq-feedback" style="display:none;margin-top:0.3rem;"></div></div>'
        html += '</div>'
    return html
