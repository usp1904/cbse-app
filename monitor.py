#!/usr/bin/env python3
"""24/7 CBSE App Monitor — logs errors, crawls pages, reports issues.

Usage:
    python3 monitor.py                         # run once (health + crawl + log check)
    python3 monitor.py --watch                 # continuous mode (every 60s)
    python3 monitor.py --watch --interval 300  # every 5 minutes
    python3 monitor.py --auto-fix              # attempt auto-fix on known errors
"""

import os, sys, re, time, json, subprocess, socket, argparse, traceback
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

BASE_URL = "http://localhost:9090"
LOG_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_LOG = os.environ.get("SERVER_LOG") or (
    "/tmp/server_stderr.log" if os.name != "nt" 
    else os.path.join(LOG_DIR, "server_stderr.log")
)
REPORT_LOG = os.path.join(LOG_DIR, "monitor_report.log")
ERROR_HISTORY = os.path.join(LOG_DIR, "monitor_errors.json")

CORE_PAGES = [
    "/", "/health", "/about", "/profile", "/search", "/tutor",
    "/exams", "/challenge", "/badges", "/cbq", "/mindmap",
    "/tools", "/review", "/competitive", "/electives",
    "/leaderboard", "/login", "/register",
    "/board/cbse", "/board/cbse/mathematics", "/board/cbse/science",
    "/board/cbse/english", "/board/ap", "/board/ts",
    "/ai", "/ai/studio", "/ai/diagram", "/ai/youtube",
    "/chapter/5a55a3073b21fb20", "/topic/c54fa5c59c80fd7b",
    "/notes/5a55a3073b21fb20", "/quiz/5a55a3073b21fb20",
]

API_ENDPOINTS = [
    "/api/ai/status", "/api/gamification", "/api/boards",
    "/api/search?q=quadratic", "/api/syllabus", "/api/badges",
]


def log(msg, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line)
    with open(REPORT_LOG, "a") as f:
        f.write(line + "\n")


def fetch(path, timeout=10):
    url = BASE_URL + path
    try:
        req = Request(url)
        with urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, body
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return e.code, body
    except (URLError, socket.timeout, ConnectionRefusedError) as e:
        return None, str(e)


def check_server_alive():
    status, body = fetch("/health", timeout=5)
    if status == 200:
        try:
            data = json.loads(body)
            log(f"Server alive — db={data.get('db')} llm={data.get('llm')} boards={data.get('boards')}")
            return True
        except json.JSONDecodeError:
            log("Health endpoint returned non-JSON", "WARN")
            return True
    log(f"Server NOT reachable ({status}): {body[:200]}", "FAIL")
    return False


def check_core_pages():
    errors = []
    for path in CORE_PAGES:
        status, body = fetch(path)
        if status != 200:
            errors.append((path, status, "HTTP error"))
        elif "500 Internal Server Error" in body or "Internal Server Error" in body[:2000]:
            errors.append((path, status, "500 on page content"))
        elif "Not Found" in body[:500] and status == 200:
            errors.append((path, status, "'Not Found' in content"))
    if errors:
        for path, status, reason in errors:
            log(f"PAGE FAIL: {path} → {reason} (HTTP {status})", "FAIL")
    else:
        log(f"All {len(CORE_PAGES)} core pages OK")
    return errors


def check_api_endpoints():
    errors = []
    for path in API_ENDPOINTS:
        status, body = fetch(path)
        if status != 200:
            errors.append((path, status, "HTTP error"))
        else:
            try:
                data = json.loads(body)
                if "error" in data:
                    errors.append((path, status, f"API error: {data['error']}"))
            except json.JSONDecodeError:
                errors.append((path, status, "non-JSON response"))
    if errors:
        for path, status, reason in errors:
            log(f"API FAIL: {path} → {reason} (HTTP {status})", "FAIL")
    else:
        log(f"All {len(API_ENDPOINTS)} API endpoints OK")
    return errors


def check_server_logs():
    errors = []
    if not os.path.exists(SERVER_LOG):
        log(f"Server log not found: {SERVER_LOG}", "WARN")
        return errors
    try:
        with open(SERVER_LOG, "r") as f:
            content = f.read()
    except Exception as e:
        log(f"Cannot read server log: {e}", "WARN")
        return errors

    # Check for error patterns
    patterns = [
        (r"ERROR", "ERROR"),
        (r"Traceback \(most recent call last\)", "TRACEBACK"),
        (r"HTTP 500|500 Internal Server Error", "HTTP 500"),
        (r"Exception|exception", "EXCEPTION"),
        (r"TimeoutError|timeout", "TIMEOUT"),
        (r"ConnectionError|connection refused", "CONNECTION"),
    ]
    for pattern, label in patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            count = len(matches)
            errors.append((label, count))
            if count > 5:
                log(f"Log {label}: {count} occurrences (showing last):", "WARN")
                lines = content.strip().split("\n")
                for line in lines[-5:]:
                    if re.search(pattern, line, re.IGNORECASE):
                        log(f"  {line.strip()[:200]}", "WARN")
    if not errors:
        log("Server log: no error patterns detected")
    return errors


def load_error_history():
    if os.path.exists(ERROR_HISTORY):
        try:
            with open(ERROR_HISTORY) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_error_history(data):
    try:
        with open(ERROR_HISTORY, "w") as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        log(f"Cannot save error history: {e}", "WARN")


def run_once(auto_fix=False, mode="server"):
    log("=== MONITOR RUN START ===")
    errors = {"server": [], "pages": [], "api": [], "logs": []}

    alive = check_server_alive()
    if not alive:
        log("Server is down — attempting restart...", "FAIL")
        if auto_fix:
            try:
                # Platform-independent stdout path
                stdout_path = (
                    "/tmp/server_stdout.log" if os.name != "nt" 
                    else os.path.join(LOG_DIR, "server_stdout.log")
                )
                
                # Determine script and command args based on mode
                if mode == "mesh":
                    script_to_run = os.path.join(LOG_DIR, "mesh_lb.py")
                    if not os.path.exists(script_to_run):
                        script_to_run = os.path.join(LOG_DIR, "_archive", "mesh_lb.py")
                    cmd = [sys.executable, script_to_run]
                else:
                    cmd = [sys.executable, os.path.join(LOG_DIR, "server.py")]
                
                log(f"Server restart initiated in {mode} mode: {' '.join(cmd)}", "FIX")
                subprocess.Popen(
                    cmd,
                    cwd=LOG_DIR,
                    stdout=open(stdout_path, "a"),
                    stderr=open(SERVER_LOG, "a"),
                )
                time.sleep(5)
                if check_server_alive():
                    log("Server restart successful", "FIX")
                else:
                    log("Server restart failed — check manually", "FAIL")
            except Exception as e:
                log(f"Restart failed: {e}", "FAIL")
        else:
            log("Use --auto-fix to enable auto-restart", "WARN")

    if alive:
        log("--- Page check ---")
        page_errors = check_core_pages()
        errors["pages"] = page_errors

        log("--- API check ---")
        api_errors = check_api_endpoints()
        errors["api"] = api_errors

    log("--- Log check ---")
    log_errors = check_server_logs()
    errors["logs"] = log_errors

    # Track persistent errors
    history = load_error_history()
    today = datetime.now().strftime("%Y-%m-%d")
    if today not in history:
        history[today] = {"runs": 0, "page_fails": 0, "api_fails": 0, "log_fails": 0}
    history[today]["runs"] += 1
    history[today]["page_fails"] += len(errors["pages"])
    history[today]["api_fails"] += len(errors["api"])
    history[today]["log_fails"] += len(errors["logs"])
    save_error_history(history)

    total = len(errors["pages"]) + len(errors["api"]) + len(errors["logs"])
    status = "PASS" if total == 0 else f"FAIL ({total} issues)"
    log(f"=== MONITOR RUN END — {status} ===")
    return total


def watch_mode(interval=60, auto_fix=False, mode="server"):
    log(f"Starting 24/7 watch mode — interval={interval}s auto_fix={auto_fix} mode={mode}")
    log(f"Report log: {REPORT_LOG}")
    log(f"Error history: {ERROR_HISTORY}")
    while True:
        try:
            run_once(auto_fix=auto_fix, mode=mode)
        except Exception as e:
            log(f"Monitor crashed: {traceback.format_exc()}", "FAIL")
        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="CBSE App 24/7 Monitor")
    parser.add_argument("--watch", action="store_true", help="Continuous monitoring mode")
    parser.add_argument("--interval", type=int, default=60, help="Check interval in seconds (default: 60)")
    parser.add_argument("--auto-fix", action="store_true", help="Attempt auto-fix on failures")
    parser.add_argument("--mode", choices=["server", "mesh"], default="server", help="Server mode to start on auto-fix")
    args = parser.parse_args()

    if args.watch:
        watch_mode(interval=args.interval, auto_fix=args.auto_fix, mode=args.mode)
    else:
        sys.exit(run_once(auto_fix=args.auto_fix, mode=args.mode))


if __name__ == "__main__":
    main()
