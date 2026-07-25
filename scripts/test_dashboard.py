"""Test dashboard endpoints."""
import json
import sys

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
MUSEUM_ID = "9492c78a-fb08-4885-8000-c882c7469233"
PASS = FAIL = 0


def login(email: str) -> str:
    r = client.post("/auth/login", json={"email": email, "password": "Password123!"})
    assert r.status_code == 200, r.json()
    return r.json()["token"]


def check(name: str, r, code=200) -> dict | None:
    global PASS, FAIL
    body = r.json()
    ok = r.status_code == code and body.get("success") is not False
    if ok or (code != 200 and r.status_code == code):
        PASS += 1
        print(f"  OK  {name} ({r.status_code})")
        return body if r.status_code == 200 else None
    FAIL += 1
    print(f"  FAIL {name} ({r.status_code})")
    print(json.dumps(body, indent=2, default=str)[:400])
    return None


print("=== Super Admin ===")
sa = {"Authorization": f"Bearer {login('superadmin@tarik.com')}"}
overview = check(
    "GET /dashboard/overview",
    client.get("/dashboard/overview", headers=sa, params={"museum_id": MUSEUM_ID}),
)
if overview:
    print("       overview:", json.dumps(overview["data"], default=str)[:300])
check("GET /dashboard/museums", client.get("/dashboard/museums", headers=sa))
check(
    "GET /dashboard/exhibits",
    client.get("/dashboard/exhibits", headers=sa, params={"museum_id": MUSEUM_ID}),
)
check(
    "GET /dashboard/content-review",
    client.get("/dashboard/content-review", headers=sa, params={"museum_id": MUSEUM_ID}),
)
check(
    "GET /dashboard/analytics (no museum_id -> 400)",
    client.get("/dashboard/analytics", headers=sa),
    code=400,
)
analytics = check(
    "GET /dashboard/analytics",
    client.get("/dashboard/analytics", headers=sa, params={"museum_id": MUSEUM_ID}),
)
if analytics:
    print("       analytics:", json.dumps(analytics["data"], default=str))

print("\n=== Museum Admin ===")
ma = {"Authorization": f"Bearer {login('museumadmin@tarik.com')}"}
check("GET /dashboard/overview", client.get("/dashboard/overview", headers=ma))
check("GET /dashboard/museums (403)", client.get("/dashboard/museums", headers=ma), code=403)
check("GET /dashboard/exhibits", client.get("/dashboard/exhibits", headers=ma))
check("GET /dashboard/content-review", client.get("/dashboard/content-review", headers=ma))
check("GET /dashboard/analytics", client.get("/dashboard/analytics", headers=ma))

print("\n=== Curator ===")
cu = {"Authorization": f"Bearer {login('curator@tarik.com')}"}
check("GET /dashboard/exhibits", client.get("/dashboard/exhibits", headers=cu))
check("GET /dashboard/analytics (403)", client.get("/dashboard/analytics", headers=cu), code=403)

print(f"\n=== Results: {PASS} passed, {FAIL} failed ===")
sys.exit(1 if FAIL else 0)
