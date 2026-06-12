#!/usr/bin/env python3
"""Comprehensive E2E Test Suite — validates every route, link, and API endpoint.

Usage:
    python3 test_e2e.py              # test live server at localhost:9090
    python3 test_e2e.py --url http://example.com:9090  # custom URL
    python3 test_e2e.py --check-links   # also validate all page links
"""
import sys
import os
import re
import time
import json
import urllib.request
import urllib.error
import http.client
import socket
import traceback
from urllib.parse import urljoin

BASE_URL = "http://localhost:9090"
CHECK_LINKS = False
PASS = 0
FAIL = 0
WARN = 0
ERROR_LOG = []


def log(msg, level="INFO"):
    icons = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️", "INFO": "ℹ️"}
    print(f"  {icons.get(level, '•')} {msg}")


def test(path, expected_code=200, check_content=True, desc=""):
    global PASS, FAIL
    label = desc or path
    url = urljoin(BASE_URL, path)
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            code = resp.status
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        code = e.code
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
    except (urllib.error.URLError, socket.timeout, ConnectionRefusedError) as e:
        log(f"{label} → Connection FAILED: {e}", "FAIL")
        FAIL += 1
        ERROR_LOG.append((path, str(e)))
        return False

    ok = True
    if code != expected_code:
        log(f"{label} → Expected {expected_code}, got {code}", "FAIL")
        FAIL += 1
        ERROR_LOG.append((path, f"HTTP {code} (expected {expected_code})"))
        ok = False
    elif check_content and ("500 Internal Server Error" in body or "Internal Server Error" in body):
        log(f"{label} → 200 but page shows 500 ERROR", "FAIL")
        FAIL += 1
        ERROR_LOG.append((path, "500 Internal Server Error on page"))
        ok = False
    elif check_content and "Not Found" in body[:500]:
        log(f"{label} → 200 but page shows 'Not Found'", "FAIL")
        FAIL += 1
        ok = False
    else:
        if check_content:
            log(f"{label} → OK ({len(body)} bytes)", "PASS")
        else:
            log(f"{label} → OK", "PASS")
        PASS += 1
    return ok and body


def test_api(path, method="GET", data=None, expected_key=None):
    global PASS, FAIL
    url = urljoin(BASE_URL, path)
    try:
        if method == "POST":
            body = urllib.parse.urlencode(data or {}).encode()
            req = urllib.request.Request(url, data=body, method="POST")
            req.add_header("Content-Type", "application/x-www-form-urlencoded")
        else:
            req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp_body = resp.read().decode()
            json_body = json.loads(resp_body)
    except Exception as e:
        log(f"API {path} → FAIL: {e}", "FAIL")
        FAIL += 1
        ERROR_LOG.append((path, str(e)))
        return None

    ok = True
    if expected_key and expected_key not in json_body:
        log(f"API {path} → missing key '{expected_key}'", "FAIL")
        FAIL += 1
        ok = False
    elif "error" in json_body:
        log(f"API {path} → returned error: {json_body['error']}", "FAIL")
        FAIL += 1
        ok = False
    else:
        log(f"API {path} → OK", "PASS")
        PASS += 1
    return json_body if ok else None


def check_page_links(path, html):
    """Validate all internal links on a page resolve."""
    global PASS, FAIL
    links = set(re.findall(r'href=[\'"](.*?)[\'"]', html))
    internal_links = set()
    for l in links:
        if l.startswith("javascript:") or l.startswith("#") or l.startswith("data:") or l == "":
            continue
        if l.startswith("http") and BASE_URL not in l:
            continue
        if l.startswith("/"):
            internal_links.add(l)
        elif l.startswith("http") and BASE_URL in l:
            internal_links.add(l.replace(BASE_URL, ""))

    if not internal_links:
        log(f"  {path}: no internal links to check", "WARN")
        return

    broken = 0
    for link in sorted(internal_links):
        try:
            req = urllib.request.Request(urljoin(BASE_URL, link))
            with urllib.request.urlopen(req, timeout=10) as resp:
                code = resp.status
                body = resp.read().decode("utf-8", errors="replace")
                if code != 200:
                    broken += 1
                    log(f"  Link {link} → HTTP {code}", "FAIL")
                elif "500 Internal Server Error" in body:
                    broken += 1
                    log(f"  Link {link} → 200 but 500 on page", "FAIL")
        except Exception as e:
            broken += 1
            log(f"  Link {link} → FAILED: {e}", "FAIL")

    total = len(internal_links)
    if broken == 0:
        log(f"  {path}: all {total} internal links OK", "PASS")
        PASS += 1
    else:
        log(f"  {path}: {broken}/{total} links broken", "FAIL")
        FAIL += 1


# ═══════════════════════════════════════════════════════════════════════════
# TEST SUITE
# ═══════════════════════════════════════════════════════════════════════════

def run_tests():
    global PASS, FAIL, WARN
    print(f"\n{'='*60}")
    print(f"📋 CBSE E2E TEST SUITE — {BASE_URL}")
    print(f"{'='*60}\n")

    # ── 1. Core Pages ──
    print("─── 1. Core Pages ───")
    test("/")
    test("/health")
    test("/about")
    test("/profile")
    test("/search")
    test("/tutor")
    test("/exams")
    test("/challenge")
    test("/badges")
    test("/cbq")
    test("/mindmap")
    test("/tools")
    test("/review")
    test("/competitive")
    test("/electives")
    test("/leaderboard")
    test("/login")

    # ── 2. Board Routes ──
    print("\n─── 2. Board Routes ───")
    test("/board/cbse")
    test("/board/cbse/mathematics")
    test("/board/cbse/science")
    test("/board/cbse/english")
    test("/board/cbse/hindi")
    test("/board/cbse/sanskrit")
    test("/board/cbse/french")
    test("/board/cbse/social-science")
    test("/board/cbse/ai")
    test("/board/cbse/it")
    test("/board/ap")
    test("/board/ap/ap-mathematics")
    test("/board/ap/ap-physical-science")
    test("/board/ap/ap-biology")
    test("/board/ap/ap-social-studies")
    test("/board/ap/ap-english")
    test("/board/ts")
    test("/board/ts/ts-mathematics")
    test("/board/ts/ts-physical-science")
    test("/board/ts/ts-biology")
    test("/board/ts/ts-social-studies")

    # ── 3. Chapter & Topic Routes ──
    print("\n─── 3. Chapter & Topic Routes ───")
    test("/chapter/5a55a3073b21fb20")
    test("/chapter/2babc5d7bd61f442")
    test("/chapter/6196963a75b5a2d6")
    test("/chapter/fc819eccc9a26bf1")
    test("/chapter/4e5a61afb73b4f00")
    test("/chapter/b34779be28e1fc24")
    test("/chapter/74de398d2c5f0e6c")
    test("/chapter/b6209911458a599d")
    test("/topic/c54fa5c59c80fd7b")
    test("/topic/e002621a9a5ca84e")
    test("/topic/851cc75de240d0be")
    test("/topic/64db4dd1396ef444")

    # ── 4. Content Routes ──
    print("\n─── 4. Content Routes ───")
    test("/notes/5a55a3073b21fb20")
    test("/revision/5a55a3073b21fb20")
    test("/quiz/5a55a3073b21fb20")
    test("/mindmap/c54fa5c59c80fd7b")
    test("/interactives/matching/c54fa5c59c80fd7b")
    test("/interactives/cards/c54fa5c59c80fd7b")

    # ── 5. AI Routes ──
    print("\n─── 5. AI Routes ───")
    test("/ai")
    test("/ai/studio")
    test("/ai/diagram")
    test("/ai/presentation")
    test("/ai/voiceover")
    test("/ai/research")
    test("/ai/music")
    test("/ai/literature")
    test("/ai/visualize")
    test("/ai/story")
    test("/ai/pomelli")
    test("/ai/metai")
    test("/ai/pedagogical")
    test("/ai/youtube")
    test("/ai/opengrok")

    # ── 6. Game & Tools Routes ──
    print("\n─── 6. Game & Tools Routes ───")
    test("/tools/calculator")
    test("/tools/periodic-table")

    # ── 7. API Endpoints ──
    print("\n─── 7. API Endpoints ───")
    test_api("/api/ai/status", expected_key="backend")
    test_api("/health", expected_key="status")
    test_api("/api/gamification", expected_key="xp")
    test_api("/api/search?q=quadratic+equation", expected_key="results")
    test_api("/api/ai/youtube/generate?topic_name=Photosynthesis&max_clips=3", expected_key="clips")

    # Tutor API (suggest serves HTML page, not JSON)
    test("/api/tutor/suggest")

    # ── 8. API: Tutor Start + Answer + Complete ──
    print("\n─── 8. API: Tutor Flow ───")
    start = test_api(
        "/api/tutor/start", method="POST",
        data={"topic_id": "c54fa5c59c80fd7b"},
        expected_key="session_id"
    )
    if start:
        sid = start["session_id"]
        ans = test_api(
            "/api/tutor/answer", method="POST",
            data={"session_id": str(sid), "question": "Test Q",
                  "qtype": "concept", "model_answer": "MA",
                  "student_answer": "SA"},
            expected_key="answer_id"
        )
        if ans:
            aid = ans["answer_id"]
            test_api(
                "/api/tutor/remedial", method="POST",
                data={"answer_id": str(aid), "self_assessment": "correct",
                      "session_id": str(sid)},
                expected_key="status"
            )
        test_api(
            "/api/tutor/complete", method="POST",
            data={"session_id": str(sid)},
            expected_key="status"
        )

    # ── 9. Chapter/Topic Detail API ──
    print("\n─── 9. Content API ───")
    test_api("/api/search?q=Euclid&limit=3", expected_key="results")
    # suggest serves HTML page, tested above

    # ── 10. Page Content Quality ──
    print("\n─── 10. Page Content Quality ───")
    for p in ["/", "/board/cbse", "/board/cbse/mathematics",
              "/chapter/5a55a3073b21fb20", "/topic/c54fa5c59c80fd7b",
              "/ai", "/exams", "/profile", "/review"]:
        html = test(p, check_content=True)
        if html and CHECK_LINKS:
            check_page_links(p, html)

    # ── Summary ──
    total = PASS + FAIL
    print(f"\n{'='*60}")
    print(f"📊 RESULTS: {PASS} passed / {FAIL} failed / {total} total")
    print(f"{'='*60}")

    if FAIL > 0:
        print(f"\n❌ FAILURES ({FAIL}):")
        for path, reason in ERROR_LOG[:20]:
            print(f"  {path}: {reason}")
        sys.exit(1)
    else:
        print(f"\n✅ ALL {PASS} TESTS PASSED")
        sys.exit(0)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="CBSE E2E Test Suite")
    parser.add_argument("--url", default="http://localhost:9090", help="Base URL")
    parser.add_argument("--check-links", action="store_true", help="Validate page links")
    args = parser.parse_args()
    BASE_URL = args.url.rstrip("/")
    CHECK_LINKS = args.check_links
    run_tests()
