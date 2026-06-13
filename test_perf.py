"""Performance/load validation — response times, concurrent connections."""
import requests, time, sys, concurrent.futures

BASE = "http://localhost:9090"

PAGE_SLOW_THRESHOLD = 0.5  # 500ms
API_SLOW_THRESHOLD = 1.0   # 1s
CONCURRENT_WORKERS = 10

pages = [
    "/", "/about", "/ai", "/board/cbse", "/board/cbse/mathematics",
    "/chapter/5a55a3073b21fb20", "/topic/c54fa5c59c80fd7b",
    "/exams", "/search", "/tools", "/tutor", "/audit-dashboard",
    "/ai/youtube", "/ai/pomelli", "/ai/voiceover", "/ai/diagram",
]

apis = [
    "/api/search?q=quadratic+equation",
    "/api/ai/status",
    "/api/gamification",
]

def timed_get(url, desc):
    start = time.time()
    try:
        r = requests.get(url, timeout=10)
        elapsed = time.time() - start
        return {"ok": r.status_code < 500, "elapsed": elapsed, "desc": desc, "status": r.status_code}
    except Exception as e:
        return {"ok": False, "elapsed": time.time() - start, "desc": desc, "error": str(e)}

# Sequential page load timing
page_failures = 0
print("--- Page Load Times ---")
for p in pages:
    res = timed_get(f"{BASE}{p}", p)
    status = "OK" if res["ok"] else f"FAIL({res['status']})"
    slow = " ⚠ SLOW" if res["elapsed"] > PAGE_SLOW_THRESHOLD else ""
    if not res["ok"]:
        page_failures += 1
    print(f"  {status} {res['elapsed']*1000:6.0f}ms {p}{slow}")

# API timing
print("--- API Response Times ---")
api_failures = 0
for a in apis:
    res = timed_get(f"{BASE}{a}", a)
    status = "OK" if res["ok"] else f"FAIL({res['status']})"
    slow = " ⚠ SLOW" if res["elapsed"] > API_SLOW_THRESHOLD else ""
    if not res["ok"]:
        api_failures += 1
    print(f"  {status} {res['elapsed']*1000:6.0f}ms {a}{slow}")

# Concurrent load test
print(f"\n--- Concurrent Load ({CONCURRENT_WORKERS} workers) ---")
targets = pages[:5]  # Top 5 pages
concurrent_start = time.time()
with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_WORKERS) as ex:
    futures = [ex.submit(timed_get, f"{BASE}{p}", p) for p in targets * 5]
    con_results = [f.result() for f in concurrent.futures.as_completed(futures)]

con_elapsed = time.time() - concurrent_start
con_ok = sum(1 for r in con_results if r["ok"])
con_total = len(con_results)
con_failures = con_total - con_ok
avg_con = sum(r["elapsed"] for r in con_results) / con_total * 1000
print(f"  {con_ok}/{con_total} OK in {con_elapsed:.2f}s (avg {avg_con:.0f}ms)")

total_failures = page_failures + api_failures + con_failures
print(f"\nPerf: {len(pages)+len(apis)+con_total - total_failures} passed / {total_failures} failed / {len(pages)+len(apis)+con_total} total")
sys.exit(0 if total_failures == 0 else 1)
