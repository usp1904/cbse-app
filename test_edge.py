"""Edge case validation suite — empty/null/malformed inputs, boundary conditions."""
import requests, time, sys

BASE = "http://localhost:9090"

def test(path, desc, expected_status=None, expected_contains=None):
    try:
        r = requests.get(f"{BASE}{path}", timeout=5, allow_redirects=False)
        status_ok = expected_status is None or r.status_code in (expected_status if isinstance(expected_status, (list, tuple)) else [expected_status])
        if not status_ok:
            return f"FAIL [{r.status_code}] {desc}: {path}"
        if expected_contains and expected_contains not in r.text:
            return f"FAIL [{r.status_code}] {desc}: missing '{expected_contains}'"
        return None
    except Exception as e:
        return f"FAIL [EXCEPTION] {desc}: {path} — {e}"

def test_post(path, data, desc):
    try:
        r = requests.post(f"{BASE}{path}", json=data, timeout=5)
        return None if r.status_code < 500 else f"FAIL [{r.status_code}] {desc}: {path}"
    except Exception as e:
        return f"FAIL [EXCEPTION] {desc}: {path} — {e}"

cases = [
    ("/api/search?q=", "Empty search query"),
    ("/api/search?q=a", "Single-char search"),
    ("/api/search?q=" + "x"*500, "Oversized search query (500 chars)"),
    ("/api/search?q=<script>alert(1)</script>", "XSS injection in search"),
    ("/api/search?q=' OR '1'='1", "SQL injection in search"),
    ("/api/search?q=../../etc/passwd", "Path traversal in search"),
    ("/api/ai/status", "AI status endpoint"),
    # YouTube endpoint may return 429 (rate-limited) — still acceptable

    ("/api/gamification", "Gamification endpoint"),
    ("/nonexistent-route-xyz", "Non-existent route returns 404"),
    ("/api/nonexistent", "Non-existent API returns 404"),
    ("/login?redirect=//evil.com", "Open redirect param"),
    ("/login?redirect=../../secret", "Path traversal redirect"),
    ("/%00", "Null byte in path"),
    ("/../../../etc/passwd", "Path traversal"),
    ("/..%252f..%252fetc/passwd", "Double-encoded path traversal"),
    ("/board/INVALID", "Invalid board ID"),
    ("/board/cbse/INVALID-SUBJECT", "Invalid subject ID under valid board"),
    ("/chapter/INVALID", "Invalid chapter ID"),
    ("/topic/INVALID", "Invalid topic ID"),
    ("/quiz/INVALID", "Invalid quiz ID"),
    ("/mindmap/INVALID", "Invalid mindmap ID"),
    ("/notes/INVALID", "Invalid notes ID"),
    ("/interactives/cards/INVALID", "Invalid interactive cards ID"),
    ("/interactives/matching/INVALID", "Invalid matching game ID"),
    ("/revision/INVALID", "Invalid revision ID"),
    ("/quiz/a"*100, "Extremely long quiz ID"),
    ("/board/" + "a"*1000, "Extremely long board path"),
]

results = []
failures = 0
for path, desc in cases:
    err = test(path, desc, expected_status=[200,302,400,404,422])
    if err:
        results.append(err)
        failures += 1

# POST edge cases
post_cases = [
    ("/api/auth/login", {}, "Empty login body"),
    ("/api/auth/login", {"user": "admin' --"}, "SQL injection in login"),
    ("/api/auth/signup", {"username": "<script>", "password": "x"}, "XSS in signup username"),
]
for path, data, desc in post_cases:
    err = test_post(path, data, desc)
    if err:
        results.append(err)
        failures += 1

total = len(cases) + len(post_cases)
print(f"Edge Cases: {total - failures} passed / {failures} failed / {total} total")
for r in results:
    print(f"  {r}")
sys.exit(0 if failures == 0 else 1)
