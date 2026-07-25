"""Quick integration test for exhibit + visitor endpoints."""
import json
import sys

from fastapi.testclient import TestClient

from app.core.enums import Language, Persona
from app.main import app

client = TestClient(app)
MUSEUM_ID = "9492c78a-fb08-4885-8000-c882c7469233"
PASS = 0
FAIL = 0


def check(name: str, response, expected_status: int = 200) -> dict | None:
    global PASS, FAIL
    ok = response.status_code == expected_status
    body = response.json()
    success_ok = body.get("success") is not False if "success" in body else True
    if ok and success_ok:
        PASS += 1
        print(f"  OK  {name} ({response.status_code})")
        return body
    FAIL += 1
    print(f"  FAIL {name} ({response.status_code})")
    print(json.dumps(body, indent=2, default=str)[:500])
    return None


print("=== Auth ===")
login = check(
    "POST /auth/login",
    client.post(
        "/auth/login",
        json={"email": "curator@tarik.com", "password": "Password123!"},
    ),
)
token = login.get("token") if login else None
headers = {"Authorization": f"Bearer {token}"} if token else {}

print("\n=== Exhibit CMS ===")
exhibit_body = {
    "museum_id": MUSEUM_ID,
    "title": "Ancient Axum Test",
    "slug": "ancient-axum-test",
    "source_text": "Axum was a major trading hub in ancient Ethiopia.",
    "estimated_duration": 120,
}
created = check(
    "POST /exhibits",
    client.post("/exhibits", json=exhibit_body, headers=headers),
    200,
)
exhibit_id = created["data"]["id"] if created else None

check(
    "GET /exhibits",
    client.get("/exhibits", headers=headers),
)
check(
    "GET /exhibits/{id}",
    client.get(f"/exhibits/{exhibit_id}", headers=headers) if exhibit_id else client.get("/exhibits/bad"),
)

for lang in Language:
    check(
        f"POST content {lang.value}",
        client.post(
            f"/exhibits/{exhibit_id}/content",
            json={"language": lang.value, "persona": Persona.HISTORIAN.value},
            headers=headers,
        ),
    )
    check(
        f"PATCH approve {lang.value}",
        client.patch(
            f"/exhibits/{exhibit_id}/content/{lang.value}/HISTORIAN/approve",
            headers=headers,
        ),
    )

published = check(
    "GET exhibit after publish",
    client.get(f"/exhibits/{exhibit_id}", headers=headers),
)
if published:
    status = published["data"].get("status")
    print(f"       exhibit status: {status}")
    if status != "PUBLISHED":
        FAIL += 1
        print("  FAIL exhibit not auto-published")

print("\n=== Visitor ===")
session = check(
    "POST /visitor/session",
    client.post("/visitor/session", json={"museum_id": MUSEUM_ID}),
)
session_key = session["data"]["session_key"] if session else None

check(
    "GET /experience/{key}",
    client.get(f"/experience/{session_key}") if session_key else client.get("/experience/x"),
)

check(
    "PATCH language (no auth)",
    client.patch(
        f"/experience/{session_key}",
        json={"language": "EN"},
    ) if session_key else client.patch("/experience/x", json={"language": "EN"}),
)

check(
    "GET exhibits list",
    client.get(f"/experience/{session_key}/exhibits") if session_key else client.get("/x"),
)

detail = check(
    "GET exhibit detail",
    client.get(f"/experience/{session_key}/exhibit/{exhibit_id}")
    if session_key and exhibit_id
    else client.get("/x"),
)

visit = check(
    "POST start visit",
    client.post(
        f"/experience/{session_key}/visit",
        json={"exhibit_id": exhibit_id},
    ) if session_key and exhibit_id else client.post("/x"),
)
visit_id = visit["data"]["visit_id"] if visit else None

check(
    "PATCH end visit",
    client.patch(
        f"/experience/{session_key}/visit/{visit_id}",
        json={"completed": True},
    ) if session_key and visit_id else client.patch("/x"),
)

check(
    "GET recommend",
    client.get(
        f"/experience/{session_key}/recommend",
        params={"current_exhibit_id": exhibit_id},
    ) if session_key and exhibit_id else client.get("/x"),
)

print(f"\n=== Results: {PASS} passed, {FAIL} failed ===")
sys.exit(1 if FAIL else 0)
