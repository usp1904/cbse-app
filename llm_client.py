import subprocess
import json
import os
import threading


class LLMClient:
    def __init__(self, model_path=None, server_url=None, claude_api_key=None, claude_model=None,
                 ollama_url=None, ollama_model=None, gemini_api_key=None, gemini_model=None):
        self.model_path = model_path or os.environ.get("LLAMA_MODEL_PATH", "")
        self.server_url = server_url or os.environ.get("LLAMA_SERVER_URL", "")
        self.claude_api_key = claude_api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.claude_model = claude_model or os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")
        self.ollama_url = ollama_url or os.environ.get("OLLAMA_URL", "")
        self.ollama_model = ollama_model or os.environ.get("OLLAMA_MODEL", "qwen3:latest")
        self.gemini_api_key = gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
        self.gemini_model = gemini_model or os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
        self.process = None
        self.lock = threading.Lock()

    @property
    def available(self):
        if self.claude_api_key:
            return True
        if self.gemini_api_key:
            return True
        if self.ollama_url:
            return True
        return bool(self.model_path and os.path.exists(self.model_path)) or bool(self.server_url)

    def query(self, prompt, system_prompt=None, max_tokens=512, temperature=0.3):
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
        return self.query(prompt, max_tokens=1024, temperature=0.3)

    def solve_problem(self, problem_text, topic_name, context_text=""):
        prompt = f"""Problem: {problem_text}
Topic: {topic_name}
Context: {context_text[:1000]}

Solve this step-by-step. Show all working, formulas used, and the final answer clearly."""
        return self.query(prompt, max_tokens=1024, temperature=0.2)

    def _query_claude(self, prompt, system_prompt, max_tokens, temperature):
        import urllib.request
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
            with urllib.request.urlopen(req, timeout=60) as resp:
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
        import urllib.request
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
            with urllib.request.urlopen(req, timeout=60) as resp:
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
        import urllib.request
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
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read())
                text = result.get("response", "")
                if text:
                    return text
                return self._fallback_response(prompt, error="Empty response from Ollama")
        except Exception as e:
            return self._fallback_response(prompt, error=f"Ollama error: {e}")

    def _query_server(self, prompt, system_prompt, max_tokens, temperature):
        import urllib.request
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
                        with urllib.request.urlopen(req, timeout=30) as resp:
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
                capture_output=True, text=True, timeout=60,
            )
            return result.stdout.strip() or self._fallback_response(prompt)
        except Exception as e:
            return self._fallback_response(prompt, error=str(e))

    def _fallback_response(self, prompt, error=""):
        topic_match = __import__("re").search(r"Topic: (.+)", prompt)
        topic = topic_match.group(1) if topic_match else ""
        return f"""[AI Offline Mode - LLM not loaded]

**{topic}** — Detailed Explanation

To enable AI-powered explanations:
1. (Local) Set OLLAMA_URL=http://localhost:11434 for Ollama (e.g. qwen3)
2. (Cloud) Set ANTHROPIC_API_KEY for Claude AI
3. Install llama.cpp from https://github.com/ggerganov/llama.cpp
4. Set LLAMA_MODEL_PATH or LLAMA_SERVER_URL env var

**Key Concepts:**
• This topic covers fundamental concepts important for board exams
• Focus on understanding the core principles and their applications
• Practice with NCERT exercises to reinforce learning

**Study Tips:**
• Review the topic content chunks from the search results
• Work through the solved examples step by step
• Attempt the practice problems without looking at solutions first
{ f"\\nNote: {error}" if error else "" }"""


_client = None

def get_client():
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
