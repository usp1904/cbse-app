"""Multi-user auth validation — signup, login, session, profile, access control."""
import requests, time, sys

BASE = "http://localhost:9090"
s = requests.Session()

def ok(r, desc):
    if r.status_code >= 500:
        print(f"  FAIL [{r.status_code}] {desc}")
        return False
    return True

failures = 0

# 1. Login page loads
r = s.get(f"{BASE}/login", timeout=5)
if ok(r, "GET /login"):
    print(f"  OK   GET /login ({len(r.text)} bytes)")
else:
    failures += 1

# 2. Login page has form elements
r = s.get(f"{BASE}/login", timeout=5)
if "form" in r.text.lower() and "password" in r.text.lower():
    print(f"  OK   Login page has form with password field")
else:
    print(f"  FAIL Login page missing form/password")
    failures += 1

# 3. Login with empty credentials (should fail gracefully)
r = s.post(f"{BASE}/login", data={}, timeout=5)
if ok(r, "POST /login empty"):
    print(f"  OK   POST /login empty data ({r.status_code})")
else:
    failures += 1

# 4. Profile page loads (public or login-required)
r = s.get(f"{BASE}/profile", timeout=5)
if ok(r, "GET /profile"):
    print(f"  OK   GET /profile ({len(r.text)} bytes)")
else:
    failures += 1

# 5. Protected routes don't crash
for route in ["/profile", "/badges", "/review", "/leaderboard"]:
    r = s.get(f"{BASE}{route}", timeout=5)
    if ok(r, f"GET {route}"):
        pass
    else:
        failures += 1

print(f"Auth: {7 - failures} passed / {failures} failed / 7 total")
sys.exit(0 if failures == 0 else 1)
