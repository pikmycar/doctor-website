"""Backend API tests for Meridian Medical Studio."""
import os
import uuid
import pytest
import requests
from datetime import datetime

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://24e3528c-bcfb-4601-b1bc-945f6d9cc3e6.preview.emergentagent.com").rstrip("/")

# Track created appointment IDs for cleanup via direct mongo (best-effort)
CREATED_SLOTS = []


@pytest.fixture(scope="session")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---------- Health ----------
def test_health(api):
    r = api.get(f"{BASE_URL}/api/health", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "healthy"
    assert "timestamp" in data


# ---------- Availability ----------
def test_availability_structure(api):
    r = api.get(f"{BASE_URL}/api/availability", timeout=15)
    assert r.status_code == 200
    days = r.json()
    assert isinstance(days, list)
    assert len(days) == 5
    for d in days:
        assert set(["date", "weekday", "day_label", "slots"]).issubset(d.keys())
        assert len(d["slots"]) == 16
        # First and last slot labels
        assert d["slots"][0]["label"] == "9:00 AM"
        assert d["slots"][-1]["label"] == "4:30 PM"
        for s in d["slots"]:
            assert isinstance(s["available"], bool)
            assert "id" in s and "start" in s and "end" in s


# ---------- Appointment creation success ----------
def _pick_available_slot(api):
    r = api.get(f"{BASE_URL}/api/availability", timeout=15)
    for d in r.json():
        for s in d["slots"]:
            if s["available"]:
                return s
    return None


def test_create_appointment_success_and_persistence(api):
    slot = _pick_available_slot(api)
    assert slot is not None, "No available slot"
    unique = uuid.uuid4().hex[:8]
    payload = {
        "name": f"TEST_User_{unique}",
        "email": f"test_{unique}@example.com",
        "message": "TEST appointment",
        "slot_start": slot["start"],
    }
    r = api.post(f"{BASE_URL}/api/appointments", json=payload, timeout=15)
    assert r.status_code == 201, r.text
    data = r.json()
    for key in ["id", "name", "email", "message", "slot_start", "slot_end", "created_at", "status"]:
        assert key in data
    assert data["status"] == "requested"
    assert data["slot_start"] == slot["start"]
    assert data["name"] == payload["name"]
    CREATED_SLOTS.append(slot["start"])

    # Verify slot now unavailable
    r2 = api.get(f"{BASE_URL}/api/availability", timeout=15)
    found = False
    for d in r2.json():
        for s in d["slots"]:
            if s["id"] == slot["id"]:
                found = True
                assert s["available"] is False
    assert found, "Slot not found in fresh availability"

    # Verify listing (reverse chronological) via admin endpoint
    login = api.post(f"{BASE_URL}/api/auth/login",
                     json={"email": "admin@meridianmedical.com", "password": "wwpY_RDaZSaGBMcJ"}, timeout=15)
    assert login.status_code == 200
    token = login.json()["access_token"]
    r3 = api.get(f"{BASE_URL}/api/admin/appointments",
                 headers={"Authorization": f"Bearer {token}"}, timeout=15)
    assert r3.status_code == 200
    listing = r3.json()
    assert any(a["id"] == data["id"] for a in listing)
    # reverse chronological check
    times = [a["created_at"] for a in listing]
    assert times == sorted(times, reverse=True)


# ---------- Duplicate (409) ----------
def test_create_appointment_duplicate_conflict(api):
    slot = _pick_available_slot(api)
    assert slot is not None
    unique = uuid.uuid4().hex[:8]
    base = {
        "name": f"TEST_Dup_{unique}",
        "email": f"dup_{unique}@example.com",
        "message": "",
        "slot_start": slot["start"],
    }
    r1 = api.post(f"{BASE_URL}/api/appointments", json=base, timeout=15)
    assert r1.status_code == 201
    CREATED_SLOTS.append(slot["start"])

    r2 = api.post(f"{BASE_URL}/api/appointments", json={**base, "email": f"dup2_{unique}@example.com"}, timeout=15)
    assert r2.status_code == 409
    assert "just taken" in r2.json().get("detail", "").lower()


# ---------- Invalid slot (400) ----------
def test_create_appointment_invalid_slot(api):
    payload = {
        "name": "TEST_Invalid",
        "email": "invalid_slot@example.com",
        "message": "",
        "slot_start": "2000-01-01T09:00:00+00:00",
    }
    r = api.post(f"{BASE_URL}/api/appointments", json=payload, timeout=15)
    assert r.status_code == 400
    assert "no longer available" in r.json().get("detail", "").lower()


# ---------- Validation (422) ----------
def test_create_appointment_missing_name(api):
    slot = _pick_available_slot(api)
    payload = {"name": "", "email": "x@example.com", "slot_start": slot["start"] if slot else "x"}
    r = api.post(f"{BASE_URL}/api/appointments", json=payload, timeout=15)
    assert r.status_code == 422


def test_create_appointment_invalid_email(api):
    slot = _pick_available_slot(api)
    payload = {"name": "TEST_Bad", "email": "not-an-email", "slot_start": slot["start"] if slot else "x"}
    r = api.post(f"{BASE_URL}/api/appointments", json=payload, timeout=15)
    assert r.status_code == 422


# ---------- Cleanup ----------
def test_zzz_cleanup():
    """Best-effort cleanup of test appointments via direct mongo."""
    try:
        from pymongo import MongoClient
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.environ.get("DB_NAME", "meridian_medical_studio")
        c = MongoClient(mongo_url)
        res = c[db_name].appointments.delete_many({
            "$or": [
                {"name": {"$regex": "^TEST_"}},
                {"email": {"$regex": "^(test_|dup_|dup2_|invalid_)"}},
            ]
        })
        print(f"Cleaned {res.deleted_count} test appointments")
    except Exception as e:
        print(f"Cleanup failed: {e}")
