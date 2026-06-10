import subprocess
import json
import os
import threading
import urllib.request
import re

_AVAILABLE_MODELS_CACHE = None

def _detect_ollama(url="http://localhost:11434"):
    try:
        req = urllib.request.Request(url.rstrip("/") + "/api/tags")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
            models = [m["name"] for m in data.get("models", [])]
            return url, models
    except Exception:
        return "", []

def _detect_gemini(api_key):
    return bool(api_key)

def _detect_claude(api_key):
    return bool(api_key)

class LLMClient:
    def __init__(self, model_path=None, server_url=None, claude_api_key=None, claude_model=None,
                 ollama_url=None, ollama_model=None, gemini_api_key=None, gemini_model=None):
        self.model_path = model_path or os.environ.get("LLAMA_MODEL_PATH", "")
        self.server_url = server_url or os.environ.get("LLAMA_SERVER_URL", "")
        self.claude_api_key = claude_api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.claude_model = claude_model or os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")
        
        ollama_url_env = ollama_url or os.environ.get("OLLAMA_URL", "")
        if ollama_url_env:
            self.ollama_url = ollama_url_env
            self.ollama_model = ollama_model or os.environ.get("OLLAMA_MODEL", "qwen3:latest")
        else:
            detected_url, models = _detect_ollama()
            self.ollama_url = detected_url
            preferred = self._preferred_ollama_model or os.environ.get("OLLAMA_MODEL", "")
            # Prefer non-thinking models for speed; fallback to available models
            if preferred and preferred in models:
                self.ollama_model = preferred
            else:
                # MetaAI (Llama 3/3.1) preferred for contextual learning; fallback to fast models
                priority = ["llama3.1:latest", "llama3:latest", "llama3", "mistral-cpu:latest", "qwen3:4b", "deepseek-r1:1.5b", "qwen3:latest"]
                self.ollama_model = next((m for p in priority for m in models if p in m), models[0] if models else "")
        
        self.gemini_api_key = gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
        self.gemini_model = gemini_model or os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
        # Use mistral-cpu as faster default if available (no thinking mode)
        self._preferred_ollama_model = ollama_model or os.environ.get("OLLAMA_MODEL", "")
        self.process = None
        self.lock = threading.Lock()
        self._model_priority = self._detect_priority()

    def _detect_priority(self):
        if self.gemini_api_key:
            return "gemini"
        if self.claude_api_key:
            return "claude"
        if self.ollama_url:
            return "ollama"
        if self.server_url or (self.model_path and os.path.exists(self.model_path)):
            return "local"
        return "none"

    @property
    def available(self):
        return self._model_priority != "none"

    @property
    def backend_name(self):
        return self._model_priority

    @property
    def model_name(self):
        return {
            "gemini": self.gemini_model,
            "claude": self.claude_model,
            "ollama": self.ollama_model,
            "local": self.model_path,
        }.get(self._model_priority, "none")

    def query(self, prompt, system_prompt=None, max_tokens=4096, temperature=0.3):
        if self.gemini_api_key:
            return self._query_gemini(prompt, system_prompt, max_tokens, temperature)
        if self.claude_api_key:
            return self._query_claude(prompt, system_prompt, max_tokens, temperature)
        if self.ollama_url:
            return self._query_ollama(prompt, system_prompt, max_tokens, temperature)
        if not self.available:
            return self._fallback_response(prompt)
        if self.server_url:
            return self._query_server(prompt, system_prompt, max_tokens, temperature)
        return self._query_local(prompt, system_prompt, max_tokens, temperature)

    def explain_topic(self, topic_name, chapter_name, context_text, level="simple"):
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
        return self.query(prompt, max_tokens=4096, temperature=0.3)

    def solve_problem(self, problem_text, topic_name, context_text=""):
        prompt = f"""Problem: {problem_text}
Topic: {topic_name}
Context: {context_text[:2000]}

Solve this step-by-step. Show all working, formulas used, and the final answer clearly."""
        return self.query(prompt, max_tokens=4096, temperature=0.2)

    def contextual_learn(self, topic, chapter, subject, level="simple"):
        level_instruction = {
            "simple": "Explain in very simple terms suitable for a Class X student. Use everyday examples.",
            "detailed": "Provide a thorough, textbook-quality explanation with all important details.",
            "advanced": "Provide an in-depth explanation including derivations, proofs, and connections.",
        }.get(level, "Explain clearly for a Class X student.")
        prompt = f"""You are MetaAI (Llama) — an expert CBSE Class X tutor.

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
        return self.query(prompt, system_prompt="You are MetaAI (Llama 3), a helpful CBSE Class X tutor. Respond in clear Markdown.", max_tokens=4096, temperature=0.3)

    def youtube_search(self, query, max_results=5):
        """YouTube Data API v3 search — returns embedded video HTML."""
        api_key = os.environ.get("YOUTUBE_API_KEY", "")
        if api_key:
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
            except Exception:
                return self._youtube_fallback(query)
        return self._youtube_fallback(query)

    def _youtube_fallback(self, query):
        return [{"videoId": "", "title": f"📺 CBSE Class 10: {query} — Watch on YouTube",
                 "channel": "YouTube", "thumb": "",
                 "searchUrl": f"https://www.youtube.com/results?search_query={'+'.join(query.split())}+CBSE+Class+10"}]

    def opengrok_search(self, query, max_results=5):
        """OpenGrok API for code/formulas/theorems — with fallback to local knowledge base."""
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
        import random
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

    def _query_claude(self, prompt, system_prompt, max_tokens, temperature):
        body = json.dumps({
            "model": self.claude_model,
            "max_tokens": max_tokens,
            "system": system_prompt or "You are a helpful CBSE Class X tutor.",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }).encode()
        try:
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.claude_api_key,
                    "anthropic-version": "2023-06-01",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
                text = ""
                for block in result.get("content", []):
                    if block.get("type") == "text":
                        text += block["text"]
                if text:
                    return text
                return self._fallback_response(prompt, error="Empty response from Claude")
        except Exception as e:
            return self._fallback_response(prompt, error=f"Claude API error: {e}")

    def _query_gemini(self, prompt, system_prompt, max_tokens, temperature):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_api_key}"
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
            return self._fallback_response(prompt, error=f"Gemini error: {e}")

    def _query_ollama(self, prompt, system_prompt, max_tokens, temperature):
        url = self.ollama_url.rstrip("/") + "/api/generate"
        body = json.dumps({
            "model": self.ollama_model,
            "prompt": prompt,
            "system": system_prompt or "You are a helpful CBSE Class X tutor.",
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
            "stream": False,
        }).encode()
        try:
            req = urllib.request.Request(
                url, data=body, headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read())
                text = result.get("response", "")
                if text:
                    return text
                return self._fallback_response(prompt, error="Empty response from Ollama")
        except Exception as e:
            return self._fallback_response(prompt, error=f"Ollama error: {e}")

    def _query_server(self, prompt, system_prompt, max_tokens, temperature):
        payloads = [
            {
                "prompt": prompt,
                "system_prompt": system_prompt or "You are a helpful CBSE Class X tutor.",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "n_predict": max_tokens,
            },
            {
                "model": "default",
                "messages": [
                    {"role": "system", "content": system_prompt or "You are a helpful CBSE Class X tutor."},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": False,
            },
        ]
        endpoints = ["/completions", "/v1/completions", "/v1/chat/completions", "/api/generate"]
        last_error = ""
        for base_url in [self.server_url.rstrip("/")]:
            for ep in endpoints:
                url = base_url + ep
                for payload in payloads:
                    try:
                        req = urllib.request.Request(
                            url,
                            data=json.dumps(payload).encode(),
                            headers={"Content-Type": "application/json"},
                        )
                        with urllib.request.urlopen(req, timeout=15) as resp:
                            result = json.loads(resp.read())
                            text = (result.get("content") or result.get("text")
                                    or result.get("response") or "")
                            if not text and "choices" in result:
                                text = result["choices"][0].get("message", {}).get("content", "")
                            if not text and "choices" in result:
                                text = result["choices"][0].get("text", "")
                            if text:
                                return text
                    except Exception as e:
                        last_error = str(e)
                        continue
        return self._fallback_response(prompt, error=last_error)

    def _query_local(self, prompt, system_prompt, max_tokens, temperature):
        full_prompt = system_prompt or "You are a helpful CBSE Class X tutor."
        full_prompt += "\n\n" + prompt
        try:
            result = subprocess.run(
                [self.model_path, "--prompt", full_prompt, "-n", str(max_tokens)],
                capture_output=True, text=True, timeout=30,
            )
            return result.stdout.strip() or self._fallback_response(prompt)
        except Exception as e:
            return self._fallback_response(prompt, error=str(e))

    def _fallback_response(self, prompt, error=""):
        topic_match = re.search(r"Topic: (.+)", prompt)
        topic = topic_match.group(1) if topic_match else ""
        return f"""[AI Offline Mode - LLM not loaded]

**{topic}** — Detailed Explanation

To enable AI-powered explanations:
1. (Local) Set OLLAMA_URL=http://localhost:11434 for Ollama with MetaAI (Llama 3/3.1)
2. (Cloud) Set ANTHROPIC_API_KEY for Claude AI or GEMINI_API_KEY for Gemini
3. Install llama.cpp from https://github.com/ggerganov/llama.cpp
4. Set YOUTUBE_API_KEY for video search integration
5. Set OPENGROK_URL for code/formula/theorem search

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
            "gemini_configured": bool(self.gemini_api_key),
            "claude_configured": bool(self.claude_api_key),
            "ollama_configured": bool(self.ollama_url),
            "youtube_configured": bool(os.environ.get("YOUTUBE_API_KEY", "")),
            "opengrok_configured": bool(os.environ.get("OPENGROK_URL", "")),
            "context_window": 4096,
            "metaai_ready": self.ollama_url and ("llama" in self.ollama_model.lower() or self.available),
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
