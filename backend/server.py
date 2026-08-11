from dotenv import load_dotenv
import os

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(ROOT_DIR, '.env'))

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timezone, timedelta
from typing import List, Optional
import uuid
import bcrypt
import jwt
import httpx

MONGO_URL = os.environ.get('MONGO_URL')
DB_NAME = os.environ.get('DB_NAME')
JWT_SECRET = os.environ.get('JWT_SECRET')
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')
ALERT_WEBHOOK_URL = os.environ.get('ALERT_WEBHOOK_URL', '').strip()
BOOKING_RATE_LIMIT = int(os.environ.get('BOOKING_RATE_LIMIT_PER_HOUR', '5'))

JWT_ALGO = 'HS256'
ACCESS_TTL = timedelta(hours=8)
LOGIN_LOCKOUT_MINUTES = 15
LOGIN_MAX_ATTEMPTS = 5

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

app = FastAPI(title="Meridian Medical Studio API")
api_router = APIRouter(prefix="/api")


# ---------- Models ----------

class AppointmentIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    message: Optional[str] = Field(default="", max_length=2000)
    slot_start: str
    website: Optional[str] = ""  # honeypot; real users leave blank


class Appointment(BaseModel):
    id: str
    name: str
    email: EmailStr
    message: str
    slot_start: str
    slot_end: str
    created_at: str
    status: str
    notes: str = ""


class Slot(BaseModel):
    id: str
    start: str
    end: str
    label: str
    available: bool


class DaySlots(BaseModel):
    date: str
    weekday: str
    day_label: str
    slots: List[Slot]


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class AdminMe(BaseModel):
    email: EmailStr
    role: str


class StatusIn(BaseModel):
    status: Optional[str] = None  # confirmed | cancelled | requested
    notes: Optional[str] = Field(default=None, max_length=4000)


# ---------- Slot generation ----------

BUSINESS_DAYS = 5
START_HOUR = 9
END_HOUR = 17
SLOT_MIN = 30
WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
VALID_STATUSES = {"requested", "confirmed", "cancelled"}


def next_business_days(count: int) -> List[datetime]:
    days = []
    d = datetime.now(timezone.utc).astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
    d = d + timedelta(days=1)
    while len(days) < count:
        if d.weekday() < 5:
            days.append(d)
        d = d + timedelta(days=1)
    return days


def generate_slots_for_day(day: datetime) -> List[dict]:
    slots = []
    cursor = day.replace(hour=START_HOUR, minute=0)
    end_of_day = day.replace(hour=END_HOUR, minute=0)
    while cursor < end_of_day:
        slot_end = cursor + timedelta(minutes=SLOT_MIN)
        hour_12 = cursor.hour % 12 or 12
        ampm = "AM" if cursor.hour < 12 else "PM"
        label = f"{hour_12}:{cursor.minute:02d} {ampm}"
        slots.append({"id": cursor.isoformat(), "start": cursor.isoformat(),
                      "end": slot_end.isoformat(), "label": label})
        cursor = slot_end
    return slots


# ---------- Auth helpers ----------

def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False


def create_access_token(email: str) -> str:
    payload = {
        "sub": email,
        "role": "admin",
        "type": "access",
        "exp": datetime.now(timezone.utc) + ACCESS_TTL,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


async def get_current_admin(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        if payload.get("type") != "access" or payload.get("role") != "admin":
            raise HTTPException(status_code=401, detail="Invalid token")
        if payload.get("sub") != ADMIN_EMAIL:
            raise HTTPException(status_code=401, detail="Invalid admin")
        return {"email": payload["sub"], "role": "admin"}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ---------- Startup / Seed ----------

@app.on_event("startup")
async def on_startup():
    await db.users.create_index("email", unique=True)
    await db.appointments.create_index("slot_start")
    await db.appointments.create_index("created_at")
    await db.login_attempts.create_index("identifier")
    await db.login_attempts.create_index(
        "expires_at", expireAfterSeconds=0
    )
    await db.booking_attempts.create_index("ip")
    await db.booking_attempts.create_index(
        "expires_at", expireAfterSeconds=0
    )

    existing = await db.users.find_one({"email": ADMIN_EMAIL})
    if existing is None:
        await db.users.insert_one({
            "email": ADMIN_EMAIL,
            "password_hash": hash_password(ADMIN_PASSWORD),
            "role": "admin",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    elif not verify_password(ADMIN_PASSWORD, existing["password_hash"]):
        await db.users.update_one(
            {"email": ADMIN_EMAIL},
            {"$set": {"password_hash": hash_password(ADMIN_PASSWORD)}},
        )


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()


# ---------- Alert webhook ----------

async def dispatch_webhook_alert(appointment: dict):
    payload = {
        "event": "appointment.created",
        "appointment": appointment,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    record = {
        "id": str(uuid.uuid4()),
        "appointment_id": appointment["id"],
        "created_at": payload["timestamp"],
        "status": "logged",
        "webhook_status": None,
        "webhook_url": ALERT_WEBHOOK_URL or None,
    }
    if ALERT_WEBHOOK_URL:
        try:
            async with httpx.AsyncClient(timeout=5.0) as http:
                r = await http.post(ALERT_WEBHOOK_URL, json=payload)
            record["status"] = "sent" if r.is_success else "failed"
            record["webhook_status"] = r.status_code
        except Exception as e:
            record["status"] = "failed"
            record["webhook_status"] = str(e)[:200]
    await db.alerts.insert_one(record)


# ---------- Public routes ----------

@api_router.get("/")
async def root():
    return {"service": "meridian-medical-studio", "status": "ok"}


@api_router.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@api_router.get("/availability", response_model=List[DaySlots])
async def get_availability():
    days = next_business_days(BUSINESS_DAYS)
    booked_cursor = db.appointments.find(
        {"status": {"$ne": "cancelled"}},
        {"slot_start": 1, "_id": 0},
    )
    booked = {doc["slot_start"] async for doc in booked_cursor}

    payload: List[DaySlots] = []
    for d in days:
        raw_slots = generate_slots_for_day(d)
        slots = [Slot(id=s["id"], start=s["start"], end=s["end"], label=s["label"],
                      available=s["id"] not in booked) for s in raw_slots]
        payload.append(DaySlots(
            date=d.strftime("%Y-%m-%d"),
            weekday=WEEKDAY_NAMES[d.weekday()],
            day_label=f"{WEEKDAY_NAMES[d.weekday()]} {d.day}",
            slots=slots,
        ))
    return payload


@api_router.post("/appointments", response_model=Appointment, status_code=201)
async def create_appointment(payload: AppointmentIn, request: Request, background: BackgroundTasks):
    ip = client_ip(request)

    # Honeypot – silently return a fake success without persisting
    if payload.website and payload.website.strip():
        return Appointment(
            id="honeypot",
            name=payload.name,
            email=payload.email,
            message="",
            slot_start=payload.slot_start,
            slot_end=payload.slot_start,
            created_at=datetime.now(timezone.utc).isoformat(),
            status="ignored",
        )

    # Rate limit: N attempts per IP per rolling hour
    window_start = datetime.now(timezone.utc) - timedelta(hours=1)
    recent = await db.booking_attempts.count_documents(
        {"ip": ip, "created_at": {"$gte": window_start.isoformat()}}
    )
    if recent >= BOOKING_RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Too many booking attempts. Please try again shortly.",
        )
    await db.booking_attempts.insert_one({
        "ip": ip,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=2),
    })

    # Validate slot
    days = next_business_days(BUSINESS_DAYS)
    valid_ids = set()
    slot_end_lookup = {}
    for d in days:
        for s in generate_slots_for_day(d):
            valid_ids.add(s["id"])
            slot_end_lookup[s["id"]] = s["end"]
    if payload.slot_start not in valid_ids:
        raise HTTPException(status_code=400, detail="Selected time is no longer available.")

    existing = await db.appointments.find_one(
        {"slot_start": payload.slot_start, "status": {"$ne": "cancelled"}}
    )
    if existing:
        raise HTTPException(status_code=409, detail="That slot was just taken. Please choose another.")

    doc = {
        "id": str(uuid.uuid4()),
        "name": payload.name.strip(),
        "email": payload.email,
        "message": (payload.message or "").strip(),
        "slot_start": payload.slot_start,
        "slot_end": slot_end_lookup[payload.slot_start],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "requested",
        "notes": "",
    }
    await db.appointments.insert_one(doc)
    background.add_task(dispatch_webhook_alert, doc)
    return Appointment(**doc)


# ---------- Auth routes ----------

auth_router = APIRouter(prefix="/api/auth")


@auth_router.post("/login")
async def admin_login(payload: LoginIn, request: Request, response: Response):
    ip = client_ip(request)
    identifier = f"{ip}:{payload.email.lower()}"
    now = datetime.now(timezone.utc)

    attempt = await db.login_attempts.find_one({"identifier": identifier})
    if attempt and attempt.get("locked_until") and datetime.fromisoformat(attempt["locked_until"]) > now:
        raise HTTPException(status_code=429, detail="Too many attempts. Try again later.")

    user = await db.users.find_one({"email": payload.email.lower()})
    if not user or not verify_password(payload.password, user["password_hash"]):
        count = (attempt["count"] if attempt else 0) + 1
        locked_until = now + timedelta(minutes=LOGIN_LOCKOUT_MINUTES) if count >= LOGIN_MAX_ATTEMPTS else None
        await db.login_attempts.update_one(
            {"identifier": identifier},
            {"$set": {
                "identifier": identifier,
                "count": count,
                "locked_until": locked_until.isoformat() if locked_until else None,
                "expires_at": now + timedelta(hours=1),
            }},
            upsert=True,
        )
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    await db.login_attempts.delete_one({"identifier": identifier})
    token = create_access_token(user["email"])
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=int(ACCESS_TTL.total_seconds()),
        path="/",
    )
    return {"email": user["email"], "role": user["role"], "access_token": token}


@auth_router.post("/logout")
async def admin_logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"ok": True}


@auth_router.get("/me", response_model=AdminMe)
async def admin_me(admin: dict = Depends(get_current_admin)):
    return AdminMe(email=admin["email"], role=admin["role"])


# ---------- Admin routes ----------

admin_router = APIRouter(prefix="/api/admin", dependencies=[Depends(get_current_admin)])


@admin_router.get("/appointments", response_model=List[Appointment])
async def admin_list_appointments():
    docs = await db.appointments.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    for d in docs:
        d.setdefault("notes", "")
    return [Appointment(**d) for d in docs]


@admin_router.patch("/appointments/{appointment_id}", response_model=Appointment)
async def admin_update_status(appointment_id: str, payload: StatusIn):
    updates: dict = {}
    if payload.status is not None:
        if payload.status not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid status.")
        updates["status"] = payload.status
    if payload.notes is not None:
        updates["notes"] = payload.notes.strip()
    if not updates:
        raise HTTPException(status_code=400, detail="Nothing to update.")
    result = await db.appointments.find_one_and_update(
        {"id": appointment_id},
        {"$set": updates},
        return_document=True,
        projection={"_id": 0},
    )
    if not result:
        raise HTTPException(status_code=404, detail="Appointment not found.")
    # Older docs may not have a notes field yet
    result.setdefault("notes", "")
    return Appointment(**result)


@admin_router.get("/appointments.csv")
async def admin_export_csv(date_from: Optional[str] = None, date_to: Optional[str] = None):
    """Export appointments as CSV, optionally filtered by slot_start date range (YYYY-MM-DD inclusive)."""
    query: dict = {}
    if date_from or date_to:
        rng: dict = {}
        if date_from:
            rng["$gte"] = date_from
        if date_to:
            # slot_start is ISO like 2026-08-13T...; use a lexicographic upper bound
            rng["$lt"] = date_to + "T99"
        query["slot_start"] = rng

    docs = await db.appointments.find(query, {"_id": 0}).sort("slot_start", 1).to_list(5000)
    import io
    import csv
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "name", "email", "slot_start", "slot_end", "status", "notes", "message", "created_at"])
    for d in docs:
        writer.writerow([
            d.get("id", ""),
            d.get("name", ""),
            d.get("email", ""),
            d.get("slot_start", ""),
            d.get("slot_end", ""),
            d.get("status", ""),
            d.get("notes", ""),
            d.get("message", ""),
            d.get("created_at", ""),
        ])
    filename = f"meridian-appointments-{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@admin_router.get("/stats")
async def admin_stats():
    total = await db.appointments.count_documents({})
    by_status = {}
    for s in VALID_STATUSES:
        by_status[s] = await db.appointments.count_documents({"status": s})
    last_alert = await db.alerts.find_one({}, sort=[("created_at", -1)])
    if last_alert:
        last_alert.pop("_id", None)
    return {"total": total, "by_status": by_status, "last_alert": last_alert}


# ---------- Mount ----------

app.include_router(api_router)
app.include_router(auth_router)
app.include_router(admin_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
