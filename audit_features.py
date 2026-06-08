"""
Comprehensive feature audit: check every feature for real content vs empty stubs.
"""
import subprocess, json, sys, os, re, urllib.request, urllib.error

HOST = "http://localhost:9090"
CHROME = os.path.expanduser("~/chrome-dist/chrome-linux64/chrome")

def fetch(path):
    url = f"{HOST}{path}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=15)
        body = resp.read().decode("utf-8", errors="replace")
        return resp.status, body
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:
        return 0, str(e)

def chrome_dom(path):
    url = HOST + path
    result = subprocess.run([
        CHROME, "--headless", "--disable-gpu", "--no-sandbox",
        "--disable-dev-shm-usage", "--dump-dom", url
    ], capture_output=True, text=True, timeout=30)
    return result.stdout

FEATURES = [
    # (name, route, check_func)
    ("Home", "/", lambda b: len(b) > 1000),
    ("Register", "/register", lambda b: "register" in b.lower() and "password" in b.lower()),
    ("Login", "/login", lambda b: "login" in b.lower() and "password" in b.lower()),
    ("Profile", "/profile", lambda b: "profile" in b.lower() or "xp" in b.lower()),
    ("CBSE Mathematics", "/cbse/mathematics", lambda b: "mathematics" in b.lower() and "chapter" in b.lower()),
    ("CBSE Science", "/cbse/science", lambda b: "science" in b.lower() and "chapter" in b.lower()),
    ("CBSE English", "/cbse/english", lambda b: "english" in b.lower()),
    ("CBSE Social Science", "/cbse/social-science", lambda b: "social" in b.lower()),
    ("CBSE French", "/cbse/french", lambda b: "french" in b.lower() and "chapter" in b.lower()),
    ("CBSE AI", "/cbse/artificial-intelligence", lambda b: "intelligence" in b.lower()),
    ("CBSE IT", "/cbse/information-technology", lambda b: "information technology" in b.lower()),
    ("Chapter Detail", "/cbse/science/chapter/66784b1aae110fea", lambda b: "nutrition" in b.lower() or "chapter" in b.lower()),
    ("Topic Detail", "/topic/70a4cb4871fa1c7e", lambda b: len(b) > 2000),
    ("Board Page", "/board/cbse", lambda b: "cbse" in b.lower() and "subject" in b.lower()),
    ("AP Board", "/board/ap", lambda b: "andhra" in b.lower()),
    ("TS Board", "/board/ts", lambda b: "telangana" in b.lower()),
    ("Smart Quiz", "/game/quiz", lambda b: "quiz" in b.lower()),
    ("Flashcards", "/game/flashcard", lambda b: "flashcard" in b.lower() or "card" in b.lower()),
    ("Exam Centre", "/exams", lambda b: "exam" in b.lower() and "cbq" in b.lower()),
    ("CBQ Hub", "/cbq", lambda b: "case" in b.lower() or "cbq" in b.lower()),
    ("Daily Challenge", "/challenge", lambda b: "challenge" in b.lower() and "daily" in b.lower()),
    ("Badges", "/badges", lambda b: ("badge" in b.lower() or "nep" in b.lower()) and len(b) > 2000),
    ("Competitive Hub", "/competitive", lambda b: "competitive" in b.lower() or "ntse" in b.lower()),
    ("Electives Hub", "/electives", lambda b: "elective" in b.lower() or "skill" in b.lower()),
    ("Spaced Review", "/review", lambda b: "review" in b.lower() or "spaced" in b.lower()),
    ("AI Tutor Hub", "/tutor", lambda b: "tutor" in b.lower()),
    ("Knowledge Graph", "/knowledge-graph", lambda b: "graph" in b.lower() or "knowledge" in b.lower()),
    ("Learn Hub", "/learn-hub", lambda b: "learn" in b.lower()),
    ("Search", "/search?q=photosynthesis", lambda b: "photosynthesis" in b.lower() or "result" in b.lower()),
    ("About", "/about", lambda b: "class x" in b.lower() and "cbse" in b.lower()),
    ("Mind Map", "/mindmap/", lambda b: "mind" in b.lower() or "map" in b.lower()),
    ("Tools", "/tools", lambda b: "tool" in b.lower() or "calculator" in b.lower()),
    ("Parent Report", "/parent-report", lambda b: "parent" in b.lower() or "progress" in b.lower()),
    ("Profile-Analytics", "/profile", lambda b: "quiz" in b.lower() and "xp" in b.lower()),
    ("Notes", "/cbse/science/chapter/66784b1aae110fea", lambda b: "notes" in b.lower()),
    ("Elective Detail", "/electives/vedic-maths", lambda b: "vedic" in b.lower() or "math" in b.lower()),
    ("Monitor Dashboard", "/health", lambda b: "ok" in b.lower()),
    ("TTS Languages", "/api/voiceover/languages", lambda b: "en-IN" in b),
    ("Service Worker", "/sw.js", lambda b: "serviceWorker" in b or "self." in b),
    ("PWA Manifest", "/manifest.json", lambda b: "name" in b and "start_url" in b),
    ("CSS", "/style.css", lambda b: ":root" in b or "body" in b),
]

DB_CHECKS = [
    ("Boards count", "SELECT COUNT(*) FROM boards", lambda c: c > 0),
    ("Subjects count", "SELECT COUNT(*) FROM subjects", lambda c: c > 0),
    ("Chapters count", "SELECT COUNT(*) FROM chapters", lambda c: c > 0),
    ("Topics count", "SELECT COUNT(*) FROM topics", lambda c: c > 0),
    ("Chunks count", "SELECT COUNT(*) FROM chunks", lambda c: c > 0),
    ("Knowledge Graph concepts", "SELECT COUNT(*) FROM knowledge_graph", lambda c: c > 0),
    ("Content pillars", "SELECT COUNT(*) FROM content_pillars", lambda c: c == 4),
    ("Pillar content items", "SELECT COUNT(*) FROM pillar_content", lambda c: c > 0),
    ("Questions in bank", "SELECT COUNT(*) FROM problems", lambda c: c > 0),
    ("Daily challenges", "SELECT COUNT(*) FROM daily_challenges", lambda c: c > 0),
]

def main():
    fails = []
    warns = []

    print("=" * 70)
    print("COMPREHENSIVE FEATURE AUDIT")
    print("=" * 70)

    # 1. Page rendering audit
    print(f"\n{'='*70}")
    print("PAGE FEATURES (Chrome rendering check)")
    print(f"{'='*70}")

    for name, route, check_fn in FEATURES:
        dom = chrome_dom(route)
        if not dom.strip():
            fails.append((name, route, "Empty DOM returned"))
            print(f"  FAIL {name:35s} {route:45s} Empty DOM")
            continue

        # Check for error indicators
        has_error = any(p in dom.lower() for p in [
            "traceback", "internal server error", "not found", "an error occurred"
        ])

        if has_error:
            fails.append((name, route, "Error page rendered"))
            print(f"  FAIL {name:35s} {route:45s} Error in page")
            continue

        # Check content quality
        if not check_fn(dom):
            warns.append((name, route, f"Content check failed ({len(dom)} bytes)"))
            print(f"  WARN {name:35s} {route:45s} {len(dom):6d} bytes - low content")
            continue

        print(f"  OK   {name:35s} {route:45s} {len(dom):6d} bytes")

    # 2. Data audit
    print(f"\n{'='*70}")
    print("DATABASE CONTENT AUDIT")
    print(f"{'='*70}")

    import database
    conn = database.get_conn()
    for name, query, check_fn in DB_CHECKS:
        try:
            row = conn.execute(query).fetchone()
            val = row[0]
            if check_fn(val):
                print(f"  OK   {name:40s} = {val}")
            else:
                warns.append((name, "", f"Check failed: {val}"))
                print(f"  WARN {name:40s} = {val} (unexpected)")
        except Exception as e:
            fails.append((name, "", f"Query error: {e}"))
            print(f"  FAIL {name:40s} Error: {e}")

    # 3. Check for state board data
    print(f"\n{'='*70}")
    print("STATE BOARD DATA CHECK")
    print(f"{'='*70}")
    for board in ["ap", "ts"]:
        subs = conn.execute("SELECT id, name FROM subjects WHERE board_id=?", (board,)).fetchall()
        if subs:
            for s in subs:
                chaps = conn.execute("SELECT COUNT(*) FROM chapters WHERE subject_id=?", (s["id"],)).fetchone()[0]
                topics = conn.execute("SELECT COUNT(*) FROM topics WHERE chapter_id IN (SELECT id FROM chapters WHERE subject_id=?)", (s["id"],)).fetchone()[0]
                print(f"  OK   {board:5s}/{s['name']:20s} {chaps:3d} chapters, {topics:3d} topics")
        else:
            warns.append((f"Board {board}", "", "No subjects found"))
            print(f"  WARN {board:5s} No subjects in database")

    # 4. Content quality check
    print(f"\n{'='*70}")
    print("CONTENT QUALITY CHECK")
    print(f"{'='*70}")
    
    # Check if content is real vs generic/placeholder
    chunks = conn.execute("SELECT content FROM chunks LIMIT 10").fetchall()
    placeholder_count = 0
    for c in chunks:
        content = c[0] or ""
        if any(p in content.lower() for p in ["this is a", "placeholder", "lorem ipsum", "sample content"]):
            placeholder_count += 1

    total_chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    if total_chunks > 0:
        pct = (placeholder_count / min(10, total_chunks)) * 100
        if pct > 50:
            warns.append(("Content", "", f"{pct:.0f}% chunks look like placeholder text"))
            print(f"  WARN {pct:.0f}% chunks are placeholders ({placeholder_count}/10 sampled)")
        else:
            print(f"  OK   Content appears genuine ({total_chunks} total chunks)")

    # Check for generic AI-generated content patterns
    generic_terms = ["this topic covers", "this section explains", "this concept is important"]
    generic_count = 0
    for c in chunks:
        content = (c[0] or "").lower()[:100]
        if any(t in content for t in generic_terms):
            generic_count += 1
    if generic_count > 0:
        pct = (generic_count / min(10, total_chunks)) * 100
        if pct > 50:
            warns.append(("Content", "", f"{pct:.0f}% chunks have boilerplate AI text"))
            print(f"  WARN {pct:.0f}% chunks have boilerplate content")

    # Summary
    print(f"\n{'='*70}")
    print("AUDIT SUMMARY")
    print(f"{'='*70}")
    print(f"  Pages checked: {len(FEATURES)}")
    print(f"  DB queries:    {len(DB_CHECKS)}")
    print(f"  Failures: {len(fails)}")
    print(f"  Warnings: {len(warns)}")

    if fails:
        print(f"\n  FAILURES:")
        for name, route, msg in fails:
            print(f"    - [{name}] ({route}) {msg}")

    if warns:
        print(f"\n  WARNINGS:")
        for name, route, msg in warns:
            print(f"    - [{name}] ({route}) {msg}")

    return len(fails) == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
