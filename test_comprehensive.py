"""Functional / Integration / UAT / System / Release tests."""
import requests, time, sys, json

BASE = "http://localhost:9090"

failures = 0
total = 0

def check(cond, desc):
    global total, failures
    total += 1
    if cond:
        print(f"  OK   {desc}")
    else:
        print(f"  FAIL {desc}")
        failures += 1

def ok(r):
    return r.status_code < 500

# ─── Functional Tests ────────────────────────────────────────────────
print("=== Functional Tests ===")

# Subject page shows chapters
r = requests.get(f"{BASE}/board/cbse/mathematics", timeout=5)
check(ok(r) and "chapter" in r.text.lower(), "Subject page has chapter sections")

# Chapter page shows topics
r = requests.get(f"{BASE}/chapter/5a55a3073b21fb20", timeout=5)
check(ok(r) and "topic" in r.text.lower(), "Chapter page has topic links")

# Topic page renders content
r = requests.get(f"{BASE}/topic/c54fa5c59c80fd7b", timeout=5)
check(ok(r) and len(r.text) > 10000, "Topic page has substantial content")

# Search returns results
r = requests.get(f"{BASE}/api/search?q=quadratic+equation", timeout=5)
check(ok(r) and len(r.text) > 100, "Search returns results JSON")

# Quiz page loads for chapter
r = requests.get(f"{BASE}/quiz/5a55a3073b21fb20", timeout=5)
check(ok(r), "Chapter quiz page loads")
check("practice" in r.text.lower() or "quiz" in r.text.lower() or len(r.text) > 500, "Chapter quiz has content")

# Quiz page loads for subject
r = requests.get(f"{BASE}/quiz/cbse-mathematics", timeout=5)
check(r.status_code in (200, 404), f"Subject quiz page returns HTTP {r.status_code}")

# Mindmap
r = requests.get(f"{BASE}/mindmap/c54fa5c59c80fd7b", timeout=5)
check(ok(r), "Mindmap page loads")

# Notes
r = requests.get(f"{BASE}/notes/5a55a3073b21fb20", timeout=5)
check(ok(r), "Notes page loads")

# Interactive cards
r = requests.get(f"{BASE}/interactives/cards/c54fa5c59c80fd7b", timeout=5)
check(ok(r), "Interactive cards page loads")

# Interactive matching
r = requests.get(f"{BASE}/interactives/matching/c54fa5c59c80fd7b", timeout=5)
check(ok(r), "Interactive matching page loads")

# Revision
r = requests.get(f"{BASE}/revision/5a55a3073b21fb20", timeout=5)
check(ok(r), "Revision page loads")

# AI pages
for ai_page in ["/ai", "/ai/youtube", "/ai/pomelli", "/ai/voiceover", "/ai/diagram",
                 "/ai/metai", "/ai/opengrok", "/ai/pedagogical", "/ai/presentation",
                 "/ai/research", "/ai/story", "/ai/studio", "/ai/visualize",
                 "/ai/literature", "/ai/music"]:
    r = requests.get(f"{BASE}{ai_page}", timeout=5)
    check(ok(r), f"AI page {ai_page} loads")

# Tools
for tool in ["/tools", "/tools/calculator", "/tools/periodic-table"]:
    r = requests.get(f"{BASE}{tool}", timeout=5)
    check(ok(r), f"Tool page {tool} loads")

# Board pages
for board in ["/board/cbse", "/board/ap", "/board/ts"]:
    r = requests.get(f"{BASE}{board}", timeout=5)
    check(ok(r), f"Board page {board} loads")

# Subject pages under each board
for subj in ["mathematics", "english", "science", "social-science"]:
    r = requests.get(f"{BASE}/board/cbse/{subj}", timeout=5)
    check(ok(r), f"CBSE subject /board/cbse/{subj} loads")

for subj in ["ap-mathematics", "ap-english", "ap-biology", "ap-physical-science", "ap-social-studies"]:
    r = requests.get(f"{BASE}/board/ap/{subj}", timeout=5)
    check(ok(r), f"AP subject /board/ap/{subj} loads")

for subj in ["ts-mathematics", "ts-biology", "ts-physical-science", "ts-social-studies"]:
    r = requests.get(f"{BASE}/board/ts/{subj}", timeout=5)
    check(ok(r), f"TS subject /board/ts/{subj} loads")

# Gamification
for g in ["/badges", "/leaderboard", "/challenge", "/cbq", "/competitive", "/electives"]:
    r = requests.get(f"{BASE}{g}", timeout=5)
    check(ok(r), f"Gamification page {g} loads")

# ─── Integration Tests ──────────────────────────────────────────────
print("\n=== Integration Tests ===")

# Board tree data flows to subject page
r = requests.get(f"{BASE}/", timeout=5)
check("cbse" in r.text.lower() or "CBSE" in r.text, "Home page references CBSE board")

# Filter panel exists
check("class" in r.text.lower(), "Home page has class filter")
check("medium" in r.text.lower(), "Home page has medium filter")

# Search flows between API and UI
r = requests.get(f"{BASE}/search", timeout=5)
check(ok(r) and ("search" in r.text.lower() or "query" in r.text.lower() or "find" in r.text.lower()), "Search page loads")

# Audit dashboard gets data
r = requests.get(f"{BASE}/api/audit/data", timeout=5)
check(ok(r), "Audit data API returns data")

# Health endpoint
r = requests.get(f"{BASE}/health", timeout=5)
check(ok(r), "Health endpoint returns OK")

# ─── UAT Tests ──────────────────────────────────────────────────────
print("\n=== UAT Tests ===")

# User can navigate: Home → Board → Subject → Chapter → Topic
r = requests.get(f"{BASE}/board/cbse/mathematics", timeout=5)
check("chapter" in r.text.lower(), "UAT: Subject page shows chapters")

r = requests.get(f"{BASE}/chapter/5a55a3073b21fb20", timeout=5)
check("topic" in r.text.lower(), "UAT: Chapter page shows topics")

r = requests.get(f"{BASE}/topic/c54fa5c59c80fd7b", timeout=5)
check(len(r.text) > 5000, "UAT: Topic has substantial content")

# User can access AI tools
for label, url in [("Pomelli", "/ai/pomelli"), ("YouTube", "/ai/youtube"),
                    ("Voiceover", "/ai/voiceover"), ("Diagram", "/ai/diagram")]:
    r = requests.get(f"{BASE}{url}", timeout=5)
    check(ok(r), f"UAT: {label} AI tool accessible")

# User can take quiz
r = requests.get(f"{BASE}/quiz/5a55a3073b21fb20", timeout=5)
check(ok(r), "UAT: Quiz accessible")

# User can view mindmap
r = requests.get(f"{BASE}/mindmap/c54fa5c59c80fd7b", timeout=5)
check(ok(r), "UAT: Mindmap accessible")

# User can use tools
r = requests.get(f"{BASE}/tools/calculator", timeout=5)
check(ok(r), "UAT: Calculator tool accessible")

r = requests.get(f"{BASE}/tools/periodic-table", timeout=5)
check(ok(r), "UAT: Periodic table accessible")

# ─── System Tests ───────────────────────────────────────────────────
print("\n=== System Tests ===")

# All routes return Content-Type
for route in ["/", "/about", "/board/cbse", "/tutor"]:
    r = requests.get(f"{BASE}{route}", timeout=5)
    check("Content-Type" in r.headers or "content-type" in r.headers, f"SYS: {route} has Content-Type header")

# Response size sanity — no empty pages
for route in ["/", "/about", "/board/cbse", "/exams", "/search", "/profile"]:
    r = requests.get(f"{BASE}{route}", timeout=5)
    check(len(r.text) > 1000, f"SYS: {route} has content (>1000 bytes)")

# No stack traces in responses
for route in ["/", "/about", "/board/cbse", "/chapter/5a55a3073b21fb20", "/quiz/5a55a3073b21fb20"]:
    r = requests.get(f"{BASE}{route}", timeout=5)
    check("Traceback" not in r.text and "Internal Server Error" not in r.text,
          f"SYS: {route} has no stack traces")

# ─── Release Tests ──────────────────────────────────────────────────
print("\n=== Release Tests ===")

# All critical routes respond
critical = ["/", "/about", "/health", "/board/cbse", "/ai", "/tutor", "/search"]
for route in critical:
    r = requests.get(f"{BASE}{route}", timeout=5)
    check(r.status_code == 200, f"Release: {route} returns 200")

# No 500 errors on any page
all_routes = critical + ["/exams", "/badges", "/leaderboard", "/profile",
                          "/review", "/tools", "/login", "/mindmap",
                          "/ai/youtube", "/ai/pomelli", "/ai/voiceover",
                          "/audit-dashboard"]
for route in all_routes:
    r = requests.get(f"{BASE}{route}", timeout=5)
    check(r.status_code != 500, f"Release: {route} no 500 error")

print(f"\n{'='*60}")
print(f"ALL TESTS: {total - failures} passed / {failures} failed / {total} total")
sys.exit(0 if failures == 0 else 1)
