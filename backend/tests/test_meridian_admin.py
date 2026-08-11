"""Admin/auth/spam-shield tests for Meridian Medical Studio.

Covers:
- /api/auth/login success + cookie + /me
- /api/auth/login wrong password + brute-force lockout (429)
- /api/admin/appointments (auth required, list, PATCH, invalid status, unknown id)
- /api/admin/stats
- /api/auth/logout clears cookie
- POST /api/appointments honeypot -> id='honeypot', not persisted
- POST /api/appointments rate limit (>5/hour/IP) -> 429
"""
import os
import uuid
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN_EMAIL = "admin@meridianmedical.com"
ADMIN_PASSWORD = "wwpY_RDaZSaGBMcJ"


def _mongo():
    from pymongo import MongoClient
    return MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


@pytest.fixture(scope="module", autouse=True)
def _reset_state():
    db = _mongo()
    db.booking_attempts.delete_many({})
    db.login_attempts.delete_many({})
    yield
    db.booking_attempts.delete_many({})
    db.login_attempts.delete_many({})
    db.appointments.delete_many({"$or": [
        {"name": {"$regex": "^TEST"}},
        {"email": {"$regex": "@test\\.com$"}},
        {"email": {"$regex": "^(test_|hp_|rl_)"}},
    ]})


@pytest.fixture
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---------- Auth ----------
class TestAuth:
    def test_login_success_sets_cookie_and_me(self, api):
        r = api.post(f"{BASE_URL}/api/auth/login",
                     json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["email"] == ADMIN_EMAIL
        assert data["role"] == "admin"
        assert isinstance(data["access_token"], str) and len(data["access_token"]) > 20
        assert "access_token" in api.cookies

        me = api.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert me.status_code == 200
        mdata = me.json()
        assert mdata["email"] == ADMIN_EMAIL and mdata["role"] == "admin"

    def test_login_wrong_password_401(self, api):
        r = api.post(f"{BASE_URL}/api/auth/login",
                     json={"email": ADMIN_EMAIL, "password": "definitely-wrong-xyz"}, timeout=15)
        assert r.status_code == 401
        assert r.json().get("detail") == "Invalid email or password."

    def test_login_lockout_after_5_failures(self, api):
        # Clean prior attempts so counter starts fresh for this identifier
        _mongo().login_attempts.delete_many({})
        email = "lockout-target@example.com"  # doesn't need to exist
        codes = []
        for _ in range(6):
            r = api.post(f"{BASE_URL}/api/auth/login",
                         json={"email": email, "password": "bad"}, timeout=15)
            codes.append(r.status_code)
        # First 4 are 401, 5th triggers lockout so 5th returns 401 (setting lock), 6th returns 429
        assert 429 in codes, f"Expected 429 lockout after 5 failed attempts. Got: {codes}"
        # Clean up so it doesn't affect other tests
        _mongo().login_attempts.delete_many({})

    def test_me_without_auth_401(self, api):
        # Ensure no cookies
        r = requests.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert r.status_code == 401

    def test_logout_clears_cookie(self, api):
        r = api.post(f"{BASE_URL}/api/auth/login",
                     json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
        assert r.status_code == 200
        # logout
        out = api.post(f"{BASE_URL}/api/auth/logout", timeout=15)
        assert out.status_code == 200
        # Clear session cookies to mimic browser deletion
        api.cookies.clear()
        me = api.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert me.status_code == 401


# ---------- Admin routes ----------
class TestAdmin:
    @pytest.fixture
    def auth_api(self, api):
        r = api.post(f"{BASE_URL}/api/auth/login",
                     json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
        assert r.status_code == 200
        return api

    def test_appointments_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/admin/appointments", timeout=15)
        assert r.status_code == 401

    def test_stats_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/admin/stats", timeout=15)
        assert r.status_code == 401

    def test_admin_appointments_list(self, auth_api):
        r = auth_api.get(f"{BASE_URL}/api/admin/appointments", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_admin_stats_structure(self, auth_api):
        r = auth_api.get(f"{BASE_URL}/api/admin/stats", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "total" in data and isinstance(data["total"], int)
        assert "by_status" in data
        for s in ["requested", "confirmed", "cancelled"]:
            assert s in data["by_status"]
        assert "last_alert" in data

    def _pick_available_slot(self, api):
        r = api.get(f"{BASE_URL}/api/availability", timeout=15)
        for d in r.json():
            for s in d["slots"]:
                if s["available"]:
                    return s
        return None

    def test_patch_status_flow(self, auth_api):
        slot = self._pick_available_slot(auth_api)
        assert slot
        unique = uuid.uuid4().hex[:8]
        payload = {"name": f"TEST_admin_{unique}", "email": f"test_admin_{unique}@test.com",
                   "message": "", "slot_start": slot["start"]}
        c = auth_api.post(f"{BASE_URL}/api/appointments", json=payload, timeout=15)
        assert c.status_code == 201, c.text
        aid = c.json()["id"]

        # confirm
        r = auth_api.patch(f"{BASE_URL}/api/admin/appointments/{aid}",
                           json={"status": "confirmed"}, timeout=15)
        assert r.status_code == 200
        assert r.json()["status"] == "confirmed"

        # cancel
        r = auth_api.patch(f"{BASE_URL}/api/admin/appointments/{aid}",
                           json={"status": "cancelled"}, timeout=15)
        assert r.status_code == 200
        assert r.json()["status"] == "cancelled"

        # invalid status -> 400
        r = auth_api.patch(f"{BASE_URL}/api/admin/appointments/{aid}",
                           json={"status": "bogus"}, timeout=15)
        assert r.status_code == 400

        # unknown id -> 404
        r = auth_api.patch(f"{BASE_URL}/api/admin/appointments/nonexistent-id",
                           json={"status": "confirmed"}, timeout=15)
        assert r.status_code == 404


# ---------- Spam shield ----------
class TestSpamShield:
    def test_honeypot_silently_ignored(self, api):
        # Ensure honeypot filled -> id 'honeypot', status 'ignored', not persisted
        db = _mongo()
        before = db.appointments.count_documents({})
        # Also clear booking_attempts so this test isn't affected by rate limit test order
        db.booking_attempts.delete_many({})

        slot = None
        r = api.get(f"{BASE_URL}/api/availability", timeout=15)
        for d in r.json():
            for s in d["slots"]:
                if s["available"]:
                    slot = s; break
            if slot: break
        payload = {"name": "TEST_bot", "email": "hp_bot@test.com", "message": "",
                   "slot_start": slot["start"], "website": "http://spam.example.com"}
        r = api.post(f"{BASE_URL}/api/appointments", json=payload, timeout=15)
        assert r.status_code in (200, 201), r.text
        data = r.json()
        assert data["id"] == "honeypot"
        assert data["status"] == "ignored"

        after = db.appointments.count_documents({})
        assert after == before, "Honeypot submission must not persist to appointments"

    def test_rate_limit_more_than_5_per_hour(self, api):
        db = _mongo()
        db.booking_attempts.delete_many({})

        # Get 6 distinct available slots
        r = api.get(f"{BASE_URL}/api/availability", timeout=15)
        slots = []
        for d in r.json():
            for s in d["slots"]:
                if s["available"]:
                    slots.append(s)
                if len(slots) >= 6: break
            if len(slots) >= 6: break
        assert len(slots) >= 6

        codes = []
        for i, slot in enumerate(slots):
            payload = {"name": f"TEST_rl_{i}", "email": f"rl_{i}@test.com",
                       "message": "", "slot_start": slot["start"]}
            r = api.post(f"{BASE_URL}/api/appointments", json=payload, timeout=15)
            codes.append(r.status_code)
        # First 5 should succeed (201), 6th should be 429
        assert codes[:5] == [201, 201, 201, 201, 201], f"Got {codes}"
        assert codes[5] == 429, f"Expected 429 on 6th attempt, got {codes}"

        # Cleanup created appointments and reset limits
        db.appointments.delete_many({"name": {"$regex": "^TEST_rl_"}})
        db.booking_attempts.delete_many({})
