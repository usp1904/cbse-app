"""
System validation: crawl all pages, verify links, APIs, and HTML structure.
"""

import sys
import os
import subprocess
import time
import urllib.request
import urllib.parse
import urllib.error
import json
import re
import html.parser
import traceback

HOST = "http://localhost:9090"
errors = []
warnings = []

def fetch(path):
    url = f"{HOST}{path}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Validator/1.0"})
        resp = urllib.request.urlopen(req, timeout=10)
        content = resp.read().decode("utf-8", errors="replace")
        return resp.status, content, dict(resp.headers)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return e.code, body, dict(e.headers)
    except Exception as e:
        return 0, str(e), {}

def ok(path, label=""):
    print(f"  OK  {path} {label}")

def fail(path, msg):
    errors.append((path, msg))
    print(f"  FAIL {path}: {msg}")

def warn(path, msg):
    warnings.append((path, msg))
    print(f"  WARN {path}: {msg}")

class LinkExtractor(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.in_a = False
        self.in_script = False
        self.scripts = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and "href" in attrs:
            self.links.append(attrs["href"])
        if tag == "script" and "src" in attrs:
            self.links.append(attrs["src"])
        if tag == "script":
            self.in_script = True
            self._script_content = ""
        if tag == "form" and "action" in attrs:
            self.links.append(attrs["action"])
        if tag in ("link",) and "href" in attrs:
            h = attrs["href"]
            if h.endswith(".css") or "icon" in attrs.get("rel", ""):
                self.links.append(h)
        if tag in ("img", "source") and "src" in attrs:
            self.links.append(attrs["src"])
    def handle_endtag(self, tag):
        if tag == "script":
            self.in_script = False
            self.scripts.append(self._script_content)
    def handle_data(self, data):
        if self.in_script:
            self._script_content += data

PAGE_ROUTES = [
    "/", "/register", "/login", "/profile", "/logout",
    "/cbq", "/electives", "/competitive", "/revision", "/analytics",
    "/mindmap", "/exams", "/review", "/learn-hub", "/knowledge-graph",
    "/knowledge-graph/subject/mathematics", "/knowledge-graph/concept/sci-life",
    "/game/quiz", "/game/flashcard", "/gamification", "/study-plan",
    "/tools", "/tools/calculator", "/tools/periodic-table",
    "/cbse/mathematics", "/cbse/science", "/cbse/english", "/cbse/social-science",
    "/cbse/science/chapter/66784b1aae110fea",
    "/topic/70a4cb4871fa1c7e",
    "/cbse/french", "/cbse/artificial-intelligence", "/cbse/information-technology",
]

API_ROUTES = [
    "/api/daily-challenge",
    "/api/question-bank?board=cbse&subject=science&limit=3",
    "/api/model-paper?board=cbse&subject=science&num=3",
    "/api/explain?topic=Photosynthesis&chapter=Life+Processes&level=simple",
    "/api/search?q=photosynthesis",
    "/api/study?chapter_id=66784b1aae110fea",
    "/api/doubts?topic=photosynthesis",
    "/api/notebooklm?board=cbse&subject=science",
    "/api/recommendations",
    "/api/lifeline?type=hint&chapter_id=66784b1aae110fea",
    "/api/cbq?board=cbse&subject=science&count=2",
    "/api/mock-exam/start?board=cbse&subject=science&template=balanced",
    "/api/gamification",
    "/api/knowledge-graph/subject/mathematics",
    "/api/knowledge-graph/concept/sci-life",
    "/api/pillars",
    "/api/pillars/main-subjects",
]

def validate_html(html_content, path):
    """Check for basic HTML well-formedness and extract issues."""
    issues = []
    # Check for common HTML issues
    if not html_content.strip():
        issues.append("Empty page body")
    # Check for unclosed tags (basic)
    for tag in ["div", "section", "table", "form", "ul", "ol"]:
        opens = len(re.findall(f"<{tag}[\\s>]", html_content))
        closes = len(re.findall(f"</{tag}>", html_content))
        if opens != closes and opens > 0:
            issues.append(f"Mismatched <{tag}> tags: {opens} open, {closes} close")
    return issues

def validate_json(body, path):
    """Check if response is valid JSON and has expected structure."""
    try:
        data = json.loads(body)
        return data, None
    except json.JSONDecodeError as e:
        return None, str(e)

def check_subject_content(status, body, path):
    """Verify subject page shows correct subject (no cross-mapping)."""
    if status != 200:
        return
    subject_keywords = {
        "/cbse/mathematics": "Mathematics",
        "/cbse/science": "Science",
        "/cbse/english": "English",
        "/cbse/social-science": ["Social Science", "Social Science"],
    }
    for route, expected in subject_keywords.items():
        if path == route or path.startswith(route + "/"):
            if isinstance(expected, list):
                found = any(e.lower() in body.lower() for e in expected)
            else:
                found = expected.lower() in body.lower()
            if not found:
                fail(route, f"Subject '{expected}' not found in page content")
            return

def check_errors_in_page(body, path):
    """Check for error messages rendered in the page."""
    error_patterns = [
        "Internal Server Error",
        "Traceback (most recent call last)",
        "An error occurred",
        "could not be found",
        "Page not found",
    ]
    for pat in error_patterns:
        if pat.lower() in body.lower():
            warn(path, f"Possible error text in page: '{pat}'")
            return

def main():
    print("=" * 60)
    print("CBSE Learning App - System Validation")
    print("=" * 60)

    # Step 1: Check server is running
    print("\n[1] Checking server status...")
    status, body, headers = fetch("/")
    if status == 200:
        ok("/", f"(HTTP {status})")
    else:
        fail("/", f"Server not responding (HTTP {status})")
        return

    # Step 2: Validate all page routes
    print(f"\n[2] Validating {len(PAGE_ROUTES)} page routes...")
    pages_content = {}
    for route in PAGE_ROUTES:
        status, body, headers = fetch(route)
        if status == 200:
            ok(route)
            pages_content[route] = body
            issues = validate_html(body, route)
            for iss in issues:
                warn(route, iss)
            check_errors_in_page(body, route)
            check_subject_content(status, body, route)
        elif status == 404:
            fail(route, f"HTTP {status} - Page not found")
        else:
            fail(route, f"HTTP {status}")

    # Step 3: Validate all API routes
    print(f"\n[3] Validating {len(API_ROUTES)} API routes...")
    for route in API_ROUTES:
        status, body, headers = fetch(route)
        if status == 200:
            data, jerr = validate_json(body, route)
            if jerr:
                warn(route, f"Invalid JSON: {jerr[:100]}")
            else:
                ok(route)
        else:
            fail(route, f"HTTP {status}")

    # Step 4: Crawl all links on each page
    print(f"\n[4] Crawling page links...")
    all_links = set()
    for route, body in pages_content.items():
        extractor = LinkExtractor()
        try:
            extractor.feed(body)
        except Exception as e:
            warn(route, f"HTML parse error: {e}")
            continue

        for link in extractor.links:
            resolved = urllib.parse.urljoin(route, link)
            # Only check internal links
            if resolved.startswith("/") and not resolved.startswith("//"):
                all_links.add(resolved)
            elif resolved.startswith(HOST):
                all_links.add(resolved.replace(HOST, ""))

    print(f"  Found {len(all_links)} unique internal links to check...")
    link_errors = 0
    for link in sorted(all_links):
        # Skip external URLs, anchors, javascript, mailto
        if link.startswith(("http://", "https://", "//", "javascript:", "mailto:", "#", "data:")):
            continue
        status, body, _ = fetch(link)
        if status == 200:
            ok(link)
        elif status == 404:
            fail(link, f"Orphan link (HTTP {status})")
            link_errors += 1
        else:
            fail(link, f"HTTP {status}")
            link_errors += 1

    # Step 5: Check JavaScript syntax
    print(f"\n[5] Checking inline JavaScript syntax...")
    js_ok = 0
    js_fail = 0
    for route, body in pages_content.items():
        extractor = LinkExtractor()
        extractor.feed(body)
        for script_content in extractor.scripts:
            if not script_content.strip():
                continue
            # Basic JS syntax check via python
            try:
                compile(script_content, f"<inline js in {route}>", "exec")
                js_ok += 1
            except SyntaxError as e:
                warn(route, f"JS SyntaxError: {e}")
                js_fail += 1
    print(f"  {js_ok} inline scripts OK, {js_fail} with issues")

    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    print(f"  Routes tested: {len(PAGE_ROUTES) + len(API_ROUTES)}")
    print(f"  Links checked: {len(all_links)}")
    print(f"  Errors:   {len(errors)}")
    print(f"  Warnings: {len(warnings)}")

    if errors:
        print("\n  FAILURES:")
        for path, msg in errors:
            print(f"    - [{path}] {msg}")
    if warnings:
        print("\n  WARNINGS:")
        for path, msg in warnings:
            print(f"    - [{path}] {msg}")

    return len(errors) == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
