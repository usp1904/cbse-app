import json
import os
import threading
import urllib.request
import re
import logging

log = logging.getLogger("cbse.llm")

_EXPLAIN_CACHE = {}


class LLMClient:
    def __init__(self, gemini_api_key=None, gemini_model=None,
                 mistral_api_key=None, mistral_model=None):
        self._gemini_api_key = gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
        self.gemini_model = gemini_model or os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
        self._mistral_api_key = mistral_api_key or os.environ.get("MISTRAL_API_KEY", "")
        self.mistral_model = mistral_model or os.environ.get("MISTRAL_MODEL", "mistral-large-latest")
        self.process = None
        self.lock = threading.Lock()
        self._warmup()

    def __repr__(self):
        return f"<LLMClient backend={self.backend_name} model={self.model_name}>"

    @property
    def gemini_api_key(self):
        return self._gemini_api_key

    @property
    def mistral_api_key(self):
        return self._mistral_api_key

    def _warmup(self):
        pass

    @property
    def available(self):
        return bool(self._gemini_api_key or self._mistral_api_key)

    @property
    def backend_name(self):
        if self._mistral_api_key:
            return "mistral"
        if self._gemini_api_key:
            return "gemini"
        return "none"

    @property
    def model_name(self):
        if self._mistral_api_key:
            return self.mistral_model
        if self._gemini_api_key:
            return self.gemini_model
        return "none"

    def query(self, prompt, system_prompt=None, max_tokens=4096, temperature=0.3):
        if self._mistral_api_key:
            return self._query_mistral(prompt, system_prompt, max_tokens, temperature)
        if self._gemini_api_key:
            return self._query_gemini(prompt, system_prompt, max_tokens, temperature)
        return self._fallback_response(prompt)

    def explain_topic(self, topic_name, chapter_name, context_text, level="simple"):
        clean_topic = re.sub(r'[^\w\s]', '', topic_name.lower()).strip()
        greetings = {"hi", "hello", "hey", "namaste", "yo", "sup", "greetings", "good morning", "good afternoon", "good evening"}
        is_greet = clean_topic in greetings
        if not is_greet:
            words = clean_topic.split()
            if words and words[0] in greetings and len(words) <= 4:
                is_greet = True

        if is_greet:
            return "Namaste! I'm your AI Tutor powered by Mistral AI. Ask me any questions about CBSE Class X concepts, math formulas, science topics, or help with your studies. How can I help you learn today?"

        cache_key = (topic_name.strip().lower(), level)
        if cache_key in _EXPLAIN_CACHE:
            return _EXPLAIN_CACHE[cache_key]

        level_instruction = {
            "simple": "Explain in very simple terms suitable for a Class X student. Use everyday examples.",
            "detailed": "Provide a thorough, textbook-quality explanation with all important details.",
            "advanced": "Provide an in-depth explanation including derivations, proofs, and connections.",
        }.get(level, "Explain clearly for a Class X student.")
        prompt = f"""Topic: {topic_name}
Chapter: {chapter_name}

Context:
{context_text[:2000]}

{level_instruction}

Provide a clear, structured explanation covering:
1. Core concept and definition
2. Key points to remember
3. Step-by-step breakdown
4. Real-life application or example"""
        res = self.query(prompt, max_tokens=4096, temperature=0.3)
        _EXPLAIN_CACHE[cache_key] = res
        return res

    def solve_problem(self, problem_text, topic_name, context_text=""):
        prompt = f"""Problem: {problem_text}
Topic: {topic_name}
Context: {context_text[:2000]}

Please solve this problem following these strict educational guidelines:
1. **Detailed Step-by-Step Solution**: Solve the problem in detail step-by-step like a complex problem. Neatly explain each step with the proper usage of correct formulas.
2. **Shortcut Solution**: Solve the exact same problem using a fast shortcut method or alternative trick.
3. **Formula & Trick Explanation**: Explain the shortcut formula, rules, or core trick in detail.
"""
        return self.query(prompt, max_tokens=4096, temperature=0.2)

    def contextual_learn(self, topic, chapter, subject, level="simple"):
        level_instruction = {
            "simple": "Explain in very simple terms suitable for a Class X student. Use everyday examples.",
            "detailed": "Provide a thorough, textbook-quality explanation with all important details.",
            "advanced": "Provide an in-depth explanation including derivations, proofs, and connections.",
        }.get(level, "Explain clearly for a Class X student.")
        prompt = f"""You are a helpful CBSE Class X tutor.

Topic: {topic}
Chapter: {chapter}
Subject: {subject}

{level_instruction}

Provide a comprehensive contextual learning response covering:
1. Core concept explanation
2. Key formulas and theorems
3. Step-by-step problem solving approach
4. Real-life applications and examples
5. Common mistakes to avoid
6. Practice questions with answers

Use Markdown formatting for clarity."""
        return self.query(prompt, system_prompt="You are a helpful CBSE Class X tutor. Respond in clear Markdown.", max_tokens=4096, temperature=0.3)

    def youtube_search(self, query, max_results=5):
        api_key = os.environ.get("YOUTUBE_API_KEY", "")
        if api_key and len(api_key) > 8:
            import urllib.parse
            encoded = urllib.parse.quote(query + " CBSE Class 10")
            url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={encoded}&maxResults={max_results}&type=video&key={api_key}"
            try:
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read())
                    items = []
                    for item in data.get("items", []):
                        vid = item["id"]["videoId"]
                        title = item["snippet"]["title"]
                        channel = item["snippet"]["channelTitle"]
                        thumb = item["snippet"]["thumbnails"].get("medium", {}).get("url", "")
                        items.append({"videoId": vid, "title": title, "channel": channel, "thumb": thumb})
                    return items
            except Exception as e:
                err = str(e).replace(api_key, "[REDACTED]") if api_key else str(e)
                log.warning("YouTube API error (key redacted): %s", err[:200])
                return self._youtube_fallback(query)
        return self._youtube_fallback(query)

    def _youtube_fallback(self, query):
        return [{"videoId": "", "title": f"📺 CBSE Class 10: {query} — Watch on YouTube",
                 "channel": "YouTube", "thumb": "",
                 "searchUrl": f"https://www.youtube.com/results?search_query={'+'.join(query.split())}+CBSE+Class+10"}]

    def opengrok_search(self, query, max_results=5):
        import urllib.parse
        og_url = os.environ.get("OPENGROK_URL", "")
        if og_url:
            try:
                encoded = urllib.parse.quote(query)
                url = f"{og_url.rstrip('/')}/search?q={encoded}&projects=&count={max_results}"
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = resp.read().decode()
                    results = re.findall(r'<a[^>]*href="/source[^"]*"[^>]*>([^<]+)</a>', data)
                    return [{"title": r, "url": og_url + "/source", "snippet": f"OpenGrok result for: {query}"} for r in results[:max_results]]
            except Exception:
                pass
        return self._opengrok_fallback(query)

    def _opengrok_fallback(self, query):
        formulas = {
            "quadratic": [
                {"title": "Quadratic Formula: x = (-b ± √(b² - 4ac)) / 2a", "category": "Algebra"},
                {"title": "Nature of Roots: D = b² - 4ac", "category": "Algebra"},
            ],
            "pythagoras": [
                {"title": "Pythagoras Theorem: a² + b² = c²", "category": "Geometry"},
                {"title": "Pythagorean Triplets: (3,4,5), (5,12,13), (7,24,25)", "category": "Geometry"},
            ],
            "trigonometry": [
                {"title": "sin²θ + cos²θ = 1", "category": "Trigonometry"},
                {"title": "tan θ = sin θ / cos θ", "category": "Trigonometry"},
            ],
            "theorem": [
                {"title": "Euclid's Division Lemma: a = bq + r, 0 ≤ r < b", "category": "Number Theory"},
                {"title": "Fundamental Theorem of Arithmetic: Every integer > 1 has unique prime factorization", "category": "Number Theory"},
                {"title": "Basic Proportionality Theorem (Thales): If a line is parallel to one side of a triangle...", "category": "Geometry"},
            ],
            "circle": [
                {"title": "Area of Circle: A = πr²", "category": "Mensuration"},
                {"title": "Circumference: C = 2πr", "category": "Mensuration"},
            ],
        }
        ql = query.lower()
        for key, items in formulas.items():
            if key in ql:
                return [{"title": f["title"], "category": f["category"], "snippet": f"Formula from CBSE Class 10 Mathematics — {f['category']}"} for f in items]
        return [{"title": f"Theorem/Formula Search: {query}", "category": "Mathematics",
                 "snippet": "Results from CBSE Class 10 formula database. Install OpenGrok for full text search."}]

    def _query_mistral(self, prompt, system_prompt, max_tokens, temperature):
        url = "https://api.mistral.ai/v1/chat/completions"
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        body = json.dumps({
            "model": self.mistral_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }).encode()
        try:
            req = urllib.request.Request(
                url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._mistral_api_key}",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
                choices = result.get("choices", [])
                if choices:
                    text = choices[0].get("message", {}).get("content", "")
                    if text:
                        return text
                return self._fallback_response(prompt, error="Empty response from Mistral")
        except Exception as e:
            err = str(e).replace(self._mistral_api_key, "[REDACTED]") if self._mistral_api_key else str(e)
            log.warning("Mistral API error (key redacted): %s", err[:200])
            return self._fallback_response(prompt, error=f"Mistral API error: [REDACTED]")

    def _query_gemini(self, prompt, system_prompt, max_tokens, temperature):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self._gemini_api_key}"
        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": system_prompt + "\n\n" + prompt}]})
        else:
            contents.append({"role": "user", "parts": [{"text": prompt}]})
        body = json.dumps({
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        }).encode()
        try:
            req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
                candidates = result.get("candidates", [])
                if candidates:
                    text = ""
                    for part in candidates[0].get("content", {}).get("parts", []):
                        text += part.get("text", "")
                    if text:
                        return text
                return self._fallback_response(prompt, error="Empty response from Gemini")
        except Exception as e:
            err = str(e).replace(self._gemini_api_key, "[REDACTED]") if self._gemini_api_key else str(e)
            log.warning("Gemini API error (key redacted): %s", err[:200])
            return self._fallback_response(prompt, error=f"Gemini error: [REDACTED]")

    def _fallback_response(self, prompt, error=""):
        topic_match = re.search(r"Topic: (.+)", prompt)
        topic = topic_match.group(1) if topic_match else ""
        return f"""[AI Offline Mode - LLM not loaded]

**{topic}** — Detailed Explanation

To enable AI-powered explanations:
1. (Primary) Set MISTRAL_API_KEY for Mistral AI
2. (Fallback) Set GEMINI_API_KEY for Google Gemini
3. Set YOUTUBE_API_KEY for video search integration
4. Set OPENGROK_URL for code/formula/theorem search

**Key Concepts:**
• This topic covers fundamental concepts important for board exams
• Focus on understanding the core principles and their applications
• Practice with NCERT exercises to reinforce learning

**Study Tips:**
• Review the topic content chunks from the search results
• Work through the solved examples step by step
• Attempt the practice problems without looking at solutions first
{ f"\\nNote: {error}" if error else "" }"""

    def get_status(self):
        return {
            "available": self.available,
            "backend": self.backend_name,
            "model": self.model_name,
            "mistral_configured": bool(self._mistral_api_key),
            "mistral_model": self.mistral_model,
            "gemini_configured": bool(self._gemini_api_key),
            "gemini_model": self.gemini_model,
            "youtube_configured": bool(os.environ.get("YOUTUBE_API_KEY", "")),
            "opengrok_configured": bool(os.environ.get("OPENGROK_URL", "")),
            "context_window": 4096,
        }


_client = None


def get_client():
    global _client
    if _client is None:
        _client = LLMClient()
    return _client


def reset_client():
    global _client
    _client = None
