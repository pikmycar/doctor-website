from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timezone, timedelta
from typing import List, Optional
import os
import uuid
from dotenv import load_dotenv

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(ROOT_DIR, '.env'))

MONGO_URL = os.environ.get('MONGO_URL')
DB_NAME = os.environ.get('DB_NAME')

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

app = FastAPI(title="Meridian Medical Studio API")
api_router = APIRouter(prefix="/api")


# ---------- Models ----------

class AppointmentIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    message: Optional[str] = Field(default="", max_length=2000)
    slot_start: str  # ISO string, must match an available slot


class Appointment(BaseModel):
    id: str
    name: str
    email: EmailStr
    message: str
    slot_start: str
    slot_end: str
    created_at: str
    status: str


class Slot(BaseModel):
    id: str            # ISO start string used as slot id
    start: str
    end: str
    label: str         # "9:00 AM"
    available: bool


class DaySlots(BaseModel):
    date: str          # YYYY-MM-DD
    weekday: str       # "Mon", "Tue"...
    day_label: str     # "Mon 12"
    slots: List[Slot]


# ---------- Slot generation ----------

BUSINESS_DAYS = 5           # rolling 5 business days
START_HOUR = 9
END_HOUR = 17               # exclusive; last slot 4:30 PM
SLOT_MIN = 30
WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def next_business_days(count: int) -> List[datetime]:
    days = []
    d = datetime.now(timezone.utc).astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
    # Start from tomorrow to avoid same-day pressure
    d = d + timedelta(days=1)
    while len(days) < count:
        if d.weekday() < 5:  # Mon-Fri
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
        slots.append({
            "id": cursor.isoformat(),
            "start": cursor.isoformat(),
            "end": slot_end.isoformat(),
            "label": label,
        })
        cursor = slot_end
    return slots


# ---------- Routes ----------

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
        slots = [
            Slot(
                id=s["id"],
                start=s["start"],
                end=s["end"],
                label=s["label"],
                available=s["id"] not in booked,
            )
            for s in raw_slots
        ]
        payload.append(DaySlots(
            date=d.strftime("%Y-%m-%d"),
            weekday=WEEKDAY_NAMES[d.weekday()],
            day_label=f"{WEEKDAY_NAMES[d.weekday()]} {d.day}",
            slots=slots,
        ))
    return payload


@api_router.post("/appointments", response_model=Appointment, status_code=201)
async def create_appointment(payload: AppointmentIn):
    # Validate slot exists in the currently generated window and is not already booked
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
    }
    await db.appointments.insert_one(doc)
    return Appointment(**doc)


@api_router.get("/appointments", response_model=List[Appointment])
async def list_appointments():
    docs = await db.appointments.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return [Appointment(**d) for d in docs]


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
