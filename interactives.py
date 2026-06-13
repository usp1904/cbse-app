import re
import json
import random

def extract_pairs(content):
    pairs = []
    if not content:
        return pairs
    # Find **bold terms** followed by explanations
    bold_terms = re.findall(r'\*\*(.*?)\*\*', content)
    for term in bold_terms[:6]:
        context = content[content.index(f'**{term}**'):content.index(f'**{term}**')+200]
        context = re.sub(r'\*\*.*?\*\*', '', context).strip()
        context = re.sub(r'\s+', ' ', context)[:120]
        if context and len(context) > 15:
            pairs.append((term.strip(), context.strip()))
    return pairs

def extract_steps(content):
    steps = []
    if not content:
        return steps
    numbered = re.findall(r'(?:^|\n)\s*(\d+)\.\s*(.*?)(?=\n\s*\d+\.|\Z)', content, re.DOTALL)
    for num, text in numbered:
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text).strip()
        text = re.sub(r'\s+', ' ', text)
        if text and len(text) > 10:
            steps.append(text)
    return steps

def extract_flashcards(content, topic_title):
    cards = []
    if not content:
        return cards
    bold_terms = re.findall(r'\*\*(.*?)\*\*', content)
    for term in bold_terms[:8]:
        idx = content.index(f'**{term}**')
        after = content[idx+len(term)+4:idx+250]
        after = re.sub(r'\*\*.*?\*\*', '', after).strip()
        after = re.sub(r'\s+', ' ', after)[:150]
        if after and len(after) > 15:
            cards.append({'front': term, 'back': after})
    if not cards:
        sentences = re.split(r'[.!?]+', content)
        for s in sentences[:5]:
            s = s.strip()
            if len(s) > 40:
                words = s.split()
                if len(words) >= 4:
                    front = ' '.join(words[:4]) + '...'
                    cards.append({'front': front, 'back': s})
    return cards

def extract_formulas(content):
    formulas = re.findall(r'[\w\s]+[=+\-×÷√][\w\s^²³₁₂₃₄₅₆₇₈₉₀()]+', content)
    return [f.strip() for f in formulas if len(f.strip()) > 3][:4]

def generate_match_exercise(pairs):
    if len(pairs) < 2:
        return None
    items = []
    for i, (term, defn) in enumerate(pairs):
        items.append({'id': f'm{i}', 'term': term, 'definition': defn})
    random.shuffle(items)
    html = f"""
    <div class="ix-match" id="ix-match-{id(items)}">
        <h4>Match the Terms</h4>
        <p style="color:#666;font-size:0.85rem;">Drag each term to its correct definition.</p>
        <div class="ix-match-grid">
            <div class="ix-match-col">
                {''.join(f'<div class="ix-term" draggable="true" data-id="{it["id"]}" ondragstart="ixDrag(event)">{it["term"]}</div>' for it in items)}
            </div>
            <div class="ix-match-col">
                {''.join(f'<div class="ix-def" data-match="{it["id"]}" ondrop="ixDrop(event)" ondragover="ixAllow(event)">{it["definition"]}</div>' for it in items)}
            </div>
        </div>
        <div id="ix-match-result-{id(items)}" class="ix-result"></div>
        <button class="tts-btn" onclick="ixCheckMatch('ix-match-{id(items)}')">Check Answers</button>
    </div>"""
    return html

def generate_sequence_exercise(steps):
    if len(steps) < 2:
        return None
    shuffled = list(enumerate(steps))
    random.shuffle(shuffled)
    items_html = ''.join(
        f'<div class="ix-seq-item" draggable="true" data-seq="{i}" ondragstart="ixDrag(event)">'
        f'<span class="ix-seq-num">?</span><span>{s}</span></div>'
        for i, s in shuffled
    )
    uid = id(steps)
    html = f"""
    <div class="ix-sequence" id="ix-seq-{uid}">
        <h4>Arrange in Correct Order</h4>
        <p style="color:#666;font-size:0.85rem;">Drag items into the right sequence.</p>
        <div class="ix-seq-list" ondrop="ixSeqDrop(event)" ondragover="ixAllow(event)">
            {items_html}
        </div>
        <div id="ix-seq-result-{uid}" class="ix-result"></div>
        <button class="tts-btn" onclick="ixCheckSeq('ix-seq-{uid}')">Check Order</button>
    </div>"""
    return html

def generate_flashcard_exercise(cards):
    if not cards:
        return None
    uid = id(cards)
    cards_html = ''.join(
        f'<div class="ix-flip-card" onclick="ixFlip(this)">'
        f'<div class="ix-flip-inner"><div class="ix-flip-front"><p>{c["front"]}</p></div>'
        f'<div class="ix-flip-back"><p>{c["back"]}</p></div></div></div>'
        for c in cards
    )
    html = f"""
    <div class="ix-flashcards" id="ix-flash-{uid}">
        <h4>Flashcards</h4>
        <p style="color:#666;font-size:0.85rem;">Tap a card to flip it.</p>
        <div class="ix-flip-grid">
            {cards_html}
        </div>
    </div>"""
    return html

def generate_interactives(topic_title, topic_content, chunks):
    content_all = topic_content or ''
    for c in chunks:
        content_all += '\n' + (c['content'] or '')

    pairs = extract_pairs(content_all)
    steps = extract_steps(content_all)
    cards = extract_flashcards(content_all, topic_title)
    formulas = extract_formulas(content_all)

    exercises = []
    for fn in [generate_match_exercise, generate_sequence_exercise, generate_flashcard_exercise]:
        args = {'pairs': pairs, 'steps': steps, 'cards': cards}
        key = {'generate_match_exercise': 'pairs', 'generate_sequence_exercise': 'steps', 'generate_flashcard_exercise': 'cards'}[fn.__name__]
        ex = fn(**{key: args[key]})
        if ex:
            exercises.append(ex)
    return exercises

def get_interactives_js():
    return """
function ixAllow(e) { e.preventDefault(); }
function ixDrag(e) { e.dataTransfer.setData('text', e.target.dataset.id || e.target.dataset.seq); }
function ixDrop(e) { e.preventDefault();
    var id = e.dataTransfer.getData('text');
    var target = e.target.closest('.ix-def');
    if(target) { target.dataset.match = id; target.style.background = '#eef2ff'; }
}
function ixFindTerm(container, id) {
    var terms = container.querySelectorAll('.ix-term');
    for (var i = 0; i < terms.length; i++) {
        if (terms[i].dataset.id === id) return terms[i];
    }
    return null;
}
function ixCheckMatch(containerId) {
    var container = document.getElementById(containerId);
    if (!container) return;
    var defs = container.querySelectorAll('.ix-def');
    var correct = 0, total = defs.length;
    defs.forEach(function(d) {
        var expected = d.dataset.match;
        var termEl = ixFindTerm(container, expected);
        d.style.border = (termEl && termEl.closest('.ix-match-col').nextElementSibling === d.parentElement) ? '2px solid #22c55e' : '2px solid #ef4444';
        if(termEl && termEl.closest('.ix-match-col').nextElementSibling === d.parentElement) correct++;
    });
    var res = document.getElementById(containerId.replace('ix-match-','ix-match-result-'));
    if (res) res.innerHTML = '<p>'+correct+'/'+total+' correct</p>';
}
function ixSeqDrop(e) { e.preventDefault();
    var id = e.dataTransfer.getData('text');
    var items = document.querySelectorAll('.ix-seq-item');
    var item = null;
    for (var i = 0; i < items.length; i++) {
        if (items[i].dataset.seq === id) { item = items[i]; break; }
    }
    var list = e.target.closest('.ix-seq-list');
    var target = e.target.closest('.ix-seq-item');
    if(item && list) list.insertBefore(item, target ? target.nextElementSibling : null);
}
function ixCheckSeq(containerId) {
    var container = document.getElementById(containerId);
    if (!container) return;
    var items = container.querySelectorAll('.ix-seq-item');
    var correct = 0, total = items.length;
    var seqNums = container.querySelectorAll('.ix-seq-num');
    items.forEach(function(item, i) {
        var expected = i;
        var actual = parseInt(item.dataset.seq);
        item.style.border = (actual === expected) ? '2px solid #22c55e' : '2px solid #ef4444';
        if (seqNums[i]) seqNums[i].textContent = (actual === expected) ? (i+1) : '✗';
        if(actual === expected) correct++;
    });
    var res = document.getElementById(containerId.replace('ix-seq-','ix-seq-result-'));
    if (res) res.innerHTML = '<p>'+correct+'/'+total+' correct</p>';
}
function ixFlip(card) { card.classList.toggle('ix-flipped'); }
"""
