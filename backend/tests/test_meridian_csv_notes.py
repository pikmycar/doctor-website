"""Iteration 4: CSV export + Appointment notes tests.

Covers:
- GET /api/admin/appointments.csv auth required (401)
- GET /api/admin/appointments.csv authorized headers + header row
- Date range filter (inclusive on both ends)
- Empty range returns header-only CSV
- PATCH notes-only, status-only, both, empty body 400, invalid status 400, unknown id 404
- GET /api/admin/appointments returns notes field (empty string for legacy)
"""
import os
import uuid
from datetime import datetime, timezone, timedelta

import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ADMIN_EMAIL = "admin@meridianmedical.com"
ADMIN_PASSWORD = "wwpY_RDaZSaGBMcJ"


def _mongo():
    from pymongo import MongoClient
    return MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


@pytest.fixture(scope="module")
def db():
    return _mongo()


@pytest.fixture(scope="module", autouse=True)
def _reset(db):
    db.booking_attempts.delete_many({})
    db.login_attempts.delete_many({})
    yield
    # Cleanup: delete TEST_-prefixed and range-injected fake appointments
    db.appointments.delete_many({"$or": [
        {"name": {"$regex": "^TEST"}},
        {"email": {"$regex": "^(test_|csv_|notes_)"}},
    ]})
    db.booking_attempts.delete_many({})
    db.login_attempts.delete_many({})


@pytest.fixture(scope="module")
def auth_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    return s


# ---------- CSV Export ----------

class TestCsvExport:
    def test_csv_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/admin/appointments.csv", timeout=15)
        assert r.status_code == 401

    def test_csv_headers_and_first_line(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/admin/appointments.csv", timeout=15)
        assert r.status_code == 200
        ctype = r.headers.get("Content-Type", "")
        assert "text/csv" in ctype, f"Content-Type is {ctype}"
        cdisp = r.headers.get("Content-Disposition", "")
        assert "attachment" in cdisp.lower()
        first_line = r.text.splitlines()[0]
        assert first_line == "id,name,email,slot_start,slot_end,status,notes,message,created_at"

    def test_csv_date_range_filter(self, auth_session, db):
        # Insert 3 fake appointments on 3 different past days directly into DB.
        base = datetime.now(timezone.utc).replace(hour=10, minute=0, second=0, microsecond=0)
        d1 = (base - timedelta(days=10)).isoformat()  # outside (below)
        d2 = (base - timedelta(days=5)).isoformat()   # inside
        d3 = (base - timedelta(days=1)).isoformat()   # outside (above)

        docs = []
        for iso, tag in [(d1, "csv_a"), (d2, "csv_b"), (d3, "csv_c")]:
            docs.append({
                "id": str(uuid.uuid4()),
                "name": f"TEST_{tag}",
                "email": f"{tag}@test.com",
                "message": "",
                "slot_start": iso,
                "slot_end": iso,
                "created_at": iso,
                "status": "requested",
                "notes": "",
            })
        db.appointments.insert_many(docs)

        # Range that only covers d2
        from_date = (base - timedelta(days=7)).strftime("%Y-%m-%d")
        to_date = (base - timedelta(days=3)).strftime("%Y-%m-%d")
        r = auth_session.get(
            f"{BASE_URL}/api/admin/appointments.csv?date_from={from_date}&date_to={to_date}",
            timeout=15,
        )
        assert r.status_code == 200
        body = r.text
        assert "TEST_csv_b" in body
        assert "TEST_csv_a" not in body
        assert "TEST_csv_c" not in body

        # Inclusive-both-ends check: range = exact date of d2
        exact_date = base.replace() - timedelta(days=5)
        exact_str = exact_date.strftime("%Y-%m-%d")
        r2 = auth_session.get(
            f"{BASE_URL}/api/admin/appointments.csv?date_from={exact_str}&date_to={exact_str}",
            timeout=15,
        )
        assert r2.status_code == 200
        assert "TEST_csv_b" in r2.text

    def test_csv_no_rows_returns_header_only(self, auth_session):
        # Choose an old date range guaranteed to have no rows
        r = auth_session.get(
            f"{BASE_URL}/api/admin/appointments.csv?date_from=1990-01-01&date_to=1990-01-02",
            timeout=15,
        )
        assert r.status_code == 200
        lines = [l for l in r.text.splitlines() if l.strip()]
        assert len(lines) == 1
        assert lines[0].startswith("id,name,email,slot_start,slot_end,status,notes,message,created_at")


# ---------- Notes / PATCH ----------

def _pick_slot(session):
    r = session.get(f"{BASE_URL}/api/availability", timeout=15)
    for d in r.json():
        for s in d["slots"]:
            if s["available"]:
                return s
    return None


class TestNotesPatch:
    @pytest.fixture(scope="class")
    def sample_appointment_id(self, auth_session, db):
        # Reset rate limits to be safe
        db.booking_attempts.delete_many({})
        slot = _pick_slot(auth_session)
        assert slot
        unique = uuid.uuid4().hex[:8]
        r = auth_session.post(f"{BASE_URL}/api/appointments", json={
            "name": f"TEST_notes_{unique}",
            "email": f"notes_{unique}@test.com",
            "message": "",
            "slot_start": slot["start"],
        }, timeout=15)
        assert r.status_code == 201, r.text
        return r.json()["id"]

    def test_patch_notes_only(self, auth_session, sample_appointment_id):
        r = auth_session.patch(
            f"{BASE_URL}/api/admin/appointments/{sample_appointment_id}",
            json={"notes": "Bring lab results"}, timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["notes"] == "Bring lab results"
        assert data["status"] == "requested"  # unchanged
        # verify persistence via list
        r2 = auth_session.get(f"{BASE_URL}/api/admin/appointments", timeout=15)
        assert r2.status_code == 200
        match = next((a for a in r2.json() if a["id"] == sample_appointment_id), None)
        assert match and match["notes"] == "Bring lab results" and match["status"] == "requested"

    def test_patch_status_only_still_works(self, auth_session, sample_appointment_id):
        r = auth_session.patch(
            f"{BASE_URL}/api/admin/appointments/{sample_appointment_id}",
            json={"status": "confirmed"}, timeout=15,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "confirmed"
        assert data["notes"] == "Bring lab results"  # unchanged

    def test_patch_both_fields(self, auth_session, sample_appointment_id):
        r = auth_session.patch(
            f"{BASE_URL}/api/admin/appointments/{sample_appointment_id}",
            json={"status": "cancelled", "notes": "Patient rescheduled"}, timeout=15,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "cancelled"
        assert data["notes"] == "Patient rescheduled"

    def test_patch_empty_body_400(self, auth_session, sample_appointment_id):
        r = auth_session.patch(
            f"{BASE_URL}/api/admin/appointments/{sample_appointment_id}",
            json={}, timeout=15,
        )
        assert r.status_code == 400
        assert "Nothing to update" in r.json().get("detail", "")

    def test_patch_invalid_status_400(self, auth_session, sample_appointment_id):
        r = auth_session.patch(
            f"{BASE_URL}/api/admin/appointments/{sample_appointment_id}",
            json={"status": "bogus"}, timeout=15,
        )
        assert r.status_code == 400
        assert "Invalid status" in r.json().get("detail", "")

    def test_patch_unknown_id_404(self, auth_session):
        r = auth_session.patch(
            f"{BASE_URL}/api/admin/appointments/nonexistent-xyz",
            json={"notes": "x"}, timeout=15,
        )
        assert r.status_code == 404

    def test_list_returns_notes_field_including_legacy(self, auth_session, db):
        # Inject a legacy doc without notes field
        legacy = {
            "id": str(uuid.uuid4()),
            "name": "TEST_legacy",
            "email": "notes_legacy@test.com",
            "message": "",
            "slot_start": datetime.now(timezone.utc).isoformat(),
            "slot_end": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "requested",
            # no 'notes' key
        }
        db.appointments.insert_one(legacy)
        r = auth_session.get(f"{BASE_URL}/api/admin/appointments", timeout=15)
        assert r.status_code == 200
        found = next((a for a in r.json() if a["id"] == legacy["id"]), None)
        assert found is not None
        assert "notes" in found
        assert found["notes"] == ""
