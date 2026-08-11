"""Bulk admin endpoint tests for Meridian Medical Studio.

Covers POST /api/admin/appointments/bulk including:
- 401 without auth
- 400 invalid status
- 422 empty ids / >200 ids
- 200 with mix of valid + nonexistent ids (matched/modified counts)
- DB persistence verified via GET
"""
import os
import uuid
import pytest
import requests
from datetime import datetime, timezone

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN_EMAIL = "admin@meridianmedical.com"
ADMIN_PASSWORD = "wwpY_RDaZSaGBMcJ"


def _mongo():
    from pymongo import MongoClient
    return MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _seed_appt(db, name, status="requested", notes="", message=""):
    aid = f"bulk_{uuid.uuid4().hex[:10]}"
    now = datetime.now(timezone.utc).isoformat()
    db.appointments.insert_one({
        "id": aid,
        "name": name,
        "email": f"{aid}@test.com",
        "message": message,
        "slot_start": now,
        "slot_end": now,
        "created_at": now,
        "status": status,
        "notes": notes,
    })
    return aid


@pytest.fixture(scope="module", autouse=True)
def _clean():
    db = _mongo()
    db.appointments.delete_many({"$or": [{"id": {"$regex": "^bulk_"}}, {"name": {"$regex": "^TEST_bulk"}}]})
    db.booking_attempts.delete_many({})
    db.login_attempts.delete_many({})
    yield
    db.appointments.delete_many({"$or": [{"id": {"$regex": "^bulk_"}}, {"name": {"$regex": "^TEST_bulk"}}]})
    db.booking_attempts.delete_many({})
    db.login_attempts.delete_many({})


@pytest.fixture
def auth_api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200
    return s


class TestBulk:
    def test_bulk_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/admin/appointments/bulk",
                          json={"ids": ["x"], "status": "confirmed"}, timeout=15)
        assert r.status_code == 401

    def test_bulk_confirm_two_valid_updates_db(self, auth_api):
        db = _mongo()
        a1 = _seed_appt(db, "TEST_bulk_a")
        a2 = _seed_appt(db, "TEST_bulk_b")
        r = auth_api.post(f"{BASE_URL}/api/admin/appointments/bulk",
                          json={"ids": [a1, a2], "status": "confirmed"}, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data == {"matched": 2, "modified": 2, "status": "confirmed"}
        # Verify DB persistence
        for aid in (a1, a2):
            doc = db.appointments.find_one({"id": aid})
            assert doc["status"] == "confirmed"

    def test_bulk_invalid_status_400(self, auth_api):
        db = _mongo()
        a1 = _seed_appt(db, "TEST_bulk_c")
        r = auth_api.post(f"{BASE_URL}/api/admin/appointments/bulk",
                          json={"ids": [a1], "status": "bogus"}, timeout=15)
        assert r.status_code == 400
        assert r.json().get("detail") == "Invalid status."

    def test_bulk_empty_ids_422(self, auth_api):
        r = auth_api.post(f"{BASE_URL}/api/admin/appointments/bulk",
                          json={"ids": [], "status": "confirmed"}, timeout=15)
        assert r.status_code == 422

    def test_bulk_over_200_ids_422(self, auth_api):
        ids = [f"nope_{i}" for i in range(201)]
        r = auth_api.post(f"{BASE_URL}/api/admin/appointments/bulk",
                          json={"ids": ids, "status": "confirmed"}, timeout=15)
        assert r.status_code == 422

    def test_bulk_all_nonexistent_returns_zero(self, auth_api):
        r = auth_api.post(f"{BASE_URL}/api/admin/appointments/bulk",
                          json={"ids": ["ghost-1", "ghost-2"], "status": "confirmed"}, timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["matched"] == 0
        assert data["modified"] == 0
        assert data["status"] == "confirmed"

    def test_bulk_mixed_valid_and_nonexistent(self, auth_api):
        db = _mongo()
        a1 = _seed_appt(db, "TEST_bulk_d", status="requested")
        a2 = _seed_appt(db, "TEST_bulk_e", status="requested")
        r = auth_api.post(f"{BASE_URL}/api/admin/appointments/bulk",
                          json={"ids": [a1, a2, "ghost-x", "ghost-y"], "status": "cancelled"}, timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["matched"] == 2
        assert data["modified"] == 2

    def test_bulk_already_target_status_modified_less(self, auth_api):
        db = _mongo()
        a1 = _seed_appt(db, "TEST_bulk_f", status="confirmed")  # already target
        a2 = _seed_appt(db, "TEST_bulk_g", status="requested")
        r = auth_api.post(f"{BASE_URL}/api/admin/appointments/bulk",
                          json={"ids": [a1, a2], "status": "confirmed"}, timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["matched"] == 2
        assert data["modified"] == 1  # a1 already confirmed → not modified

    def test_single_patch_still_works_status_only(self, auth_api):
        db = _mongo()
        a1 = _seed_appt(db, "TEST_bulk_h", status="requested")
        r = auth_api.patch(f"{BASE_URL}/api/admin/appointments/{a1}",
                           json={"status": "confirmed"}, timeout=15)
        assert r.status_code == 200
        assert r.json()["status"] == "confirmed"

    def test_single_patch_still_works_notes_only(self, auth_api):
        db = _mongo()
        a1 = _seed_appt(db, "TEST_bulk_i", notes="")
        r = auth_api.patch(f"{BASE_URL}/api/admin/appointments/{a1}",
                           json={"notes": "hello notes"}, timeout=15)
        assert r.status_code == 200
        assert r.json()["notes"] == "hello notes"
