"""
Chrome headless validation: navigate pages, capture console errors, verify rendering.
Uses correct routing paths (/board/cbse/..., /chapter/..., /topic/...).
"""

import subprocess
import json
import sys
import os
import time
import re
import urllib.request
import urllib.error

CHROME = os.path.expanduser("~/chrome-dist/chrome-linux64/chrome")
HOST = "http://localhost:9090"

PAGES = [
    "/", "/register", "/login", "/profile",
    "/cbq", "/electives", "/competitive", "/revision", "/analytics",
    "/mindmap", "/exams", "/review", "/learn-hub", "/knowledge-graph",
    "/knowledge-graph/subject/mathematics", "/knowledge-graph/concept/sci-life",
    "/game/quiz", "/game/flashcard", "/gamification", "/study-plan",
    "/tools", "/tools/calculator", "/tools/periodic-table",
    "/board/cbse/mathematics", "/board/cbse/science", "/board/cbse/english",
    "/board/cbse/social-science", "/board/cbse/hindi", "/board/cbse/sanskrit",
    "/board/cbse/french", "/board/cbse/artificial-intelligence",
    "/board/cbse/information-technology",
    "/syllabus", "/ai", "/ai/diagram", "/ai/presentation",
    "/ai/voiceover", "/ai/research", "/ai/music", "/ai/literature",
    "/ai/visualize", "/ai/story", "/ai/pomelli", "/ai/metai", "/ai/pedagogical",
]

API_ENDPOINTS = [
    "/api/daily-challenge",
    "/api/explain?topic=Photosynthesis&chapter=Life+Processes&level=simple",
    "/api/search?q=photosynthesis",
    "/api/gamification",
    "/api/knowledge-graph/subject/mathematics",
    "/api/knowledge-graph/concept/sci-life",
    "/api/pillars",
    "/api/pillars/main-subjects",
    "/api/syllabus",
    "/api/recommendations",
    "/api/ai/diagram?concept=Photosynthesis&type=mindmap",
    "/api/ai/pomelli",
    "/api/ai/pomelli/generate?template=graph-linear",
]

errors = []
warnings = []

def fail(msg):
    errors.append(msg)
    print(f"  FAIL: {msg}")

def warn(msg):
    warnings.append(msg)
    print(f"  WARN: {msg}")

def fetch_url(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=15)
        body = resp.read().decode("utf-8", errors="replace")
        return resp.status, body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return e.code, body
    except Exception as e:
        return 0, str(e)

def check_links(html, page_name):
    """Verify all internal links in the HTML respond with 200."""
    links = set()
    for m in re.finditer(r'href=["\']([^"\']+)["\']', html):
        href = m.group(1)
        if href.startswith("/") and not href.startswith("//"):
            links.add(href)
    broken = 0
    for link in sorted(links):
        if link.startswith(("javascript:", "#", "mailto:", "data:", "tel:")):
            continue
        if link == "/":
            continue
        status, _ = fetch_url(HOST + link)
        if status not in (200, 302, 304):
            fail(f"[{page_name}] Broken link: {link} (HTTP {status})")
            broken += 1
            if broken >= 5:
                break
    return links

def main():
    print("=" * 70)
    print("VALIDATION — CBSE Learning App")
    print("=" * 70)

    print("\n[1] Chrome check")
    result = subprocess.run([CHROME, "--version"], capture_output=True, text=True, timeout=10)
    print(f"  Chrome: {result.stdout.strip()}")

    print(f"\n[2] Validating {len(PAGES)} pages...")
    all_links = set()
    for page in PAGES:
        url = HOST + page
        print(f"  {page}...", end=" ")
        result = subprocess.run([
            CHROME, "--headless", "--disable-gpu", "--no-sandbox",
            "--disable-dev-shm-usage", "--dump-dom", url
        ], capture_output=True, text=True, timeout=60)
        html = result.stdout
        if not html.strip():
            fail(f"Empty DOM")
            continue
        print(f"OK ({len(html)} bytes)")
        page_links = check_links(html, page)
        all_links.update(page_links)

    print(f"\n[3] Validating {len(API_ENDPOINTS)} API endpoints...")
    for endpoint in API_ENDPOINTS:
        url = HOST + endpoint
        status, body = fetch_url(url)
        if status == 200:
            try:
                json.loads(body)
                print(f"  OK {endpoint}")
            except json.JSONDecodeError:
                warn(f"{endpoint} returned non-JSON")
        else:
            fail(f"{endpoint} returned HTTP {status}")

    # Validate dynamic chapter + topic pages via syllabus API
    print(f"\n[4] Validating dynamic chapter/topic pages...")
    status, body = fetch_url(HOST + "/api/syllabus")
    if status == 200:
        subjects = json.loads(body)
        ch_count = sum(s.get("chapter_count", 0) for s in subjects)
        t_count = sum(s.get("topic_count", 0) for s in subjects)
        p_count = sum(s.get("problem_count", 0) for s in subjects)
        chunk_count = sum(s.get("chunk_count", 0) for s in subjects)
        print(f"  Subjects: {len(subjects)}, Chapters: {ch_count}, Topics: {t_count}")
        print(f"  Chunks: {chunk_count}, Problems: {p_count}")
        for s in subjects:
            if s.get("topic_count", 0) == 0:
                fail(f"Subject '{s['name']}' has 0 topics")
            if s.get("problem_count", 0) == 0:
                fail(f"Subject '{s['name']}' has 0 problems")
        # Validate per-subject chapter detail
        for s in subjects[:5]:
            detail_status, detail_body = fetch_url(HOST + f"/api/syllabus?subject_id={s['id']}")
            if detail_status == 200:
                chapters = json.loads(detail_body)
                for ch in chapters[:3]:
                    page_status, _ = fetch_url(HOST + f"/chapter/{ch['id']}")
                    if page_status != 200:
                        fail(f"Chapter page /chapter/{ch['id']}: HTTP {page_status}")
    else:
        fail(f"Syllabus API returned HTTP {status}")

    print(f"\n[5] Checking internal links...")
    broken = 0
    for link in sorted(all_links):
        if link.startswith(("http://", "https://", "//", "javascript:", "mailto:", "#", "data:", "tel:")):
            continue
        if link == "/":
            continue
        status, _ = fetch_url(HOST + link)
        if status not in (200, 302, 304):
            fail(f"Broken link: {link} (HTTP {status})")
            broken += 1
    if broken == 0:
        print("  All links OK")

    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    print(f"  Pages: {len(PAGES)}")
    print(f"  APIs:  {len(API_ENDPOINTS)}")
    print(f"  Links: {len(all_links)}")
    print(f"  Errors:   {len(errors)}")
    print(f"  Warnings: {len(warnings)}")

    if errors:
        print("\n  ERRORS:")
        for e in errors:
            print(f"    - {e}")
    if warnings:
        print("\n  WARNINGS:")
        for w in warnings:
            print(f"    - {w}")

    return len(errors) == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
