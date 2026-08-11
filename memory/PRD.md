# Meridian Medical Studio — Product Requirements

## Original Problem Statement
Build a premium doctor / clinic website (repo: https://github.com/pikmycar/doctor-website.git) with:
- 3D hero section with interactive objects
- Smooth scroll-based animations, parallax and depth
- Mouse-follow / hover interactions
- 3D card transitions
- Micro-interactions & animated buttons
- Premium gradients, lighting, shadows, glassmorphism
- Responsive motion for mobile
- Performance-conscious animations

## Architecture
- **Frontend** (`/app/frontend`): Vite + React 19 + TypeScript, Framer Motion, React Three Fiber + Drei, Three.js, Lucide icons. Runs on port 3000 (`yarn start` → `vite`).
- **Backend** (`/app/backend`): FastAPI on port 8001. Endpoints `/api/health`, `/api/availability`, `POST/GET /api/appointments`. MongoDB via `motor` (env `MONGO_URL`, `DB_NAME`).
- **Ingress**: `/api/*` → backend:8001, everything else → frontend:3000.

## User Personas
- Prospective private-practice patients browsing on desktop/mobile
- Existing patients booking or exploring the practice's approach
- Referring physicians assessing credibility

## Core Requirements (Static)
- Editorial, calm, "Meridian medical studio" brand voice
- Accessible interactive 3D hero (with reduced-motion fallback)
- Appointment request dialog with focus trap AND real slot booking
- Responsive across breakpoints

## Implemented (dated)
- **2026-08-11 (v1)**: 3D hero (React Three Fiber orb), scroll animations, service cards, about/approach/contact sections, appointment dialog with focus trap, responsive layout. Design guidelines generated. testing_agent iteration 1 passed.
- **2026-08-11 (v2)**: Repo restructured into `/app/frontend/` + `/app/backend/` for platform deploy. Minimal FastAPI backend added. deployment_agent PASS.
- **2026-08-11 (v3 - current)**: Four features shipped end-to-end
  - **Appointment Storage** — `POST /api/appointments` validates & persists to Mongo; `GET /api/appointments` lists (reverse chrono).
  - **Doctor Profile** section (#doctor) with editorial portrait, bio, philosophy, 4 credentials, dedicated CTA.
  - **Patient Stories** section (#stories) with 3 testimonial cards + 3D hover tilt.
  - **Live Availability** — `GET /api/availability` returns rolling 5 business days × 16 30-min slots (9am–4:30pm); dialog now shows day tabs + slot grid, disables booked slots, updates CTA label, and syncs on submit. Includes 400 (invalid slot) and 409 (already booked) guards.
  - Nav updated with "Your doctor" and "Stories" links. Testing agent iteration 2: 100% backend (8/8), 100% frontend (13/13).

## Prioritized Backlog
- **P1** Email/SMS alert to the practice when a new appointment arrives (Resend or Twilio) — needs API key
- **P1** Admin-only appointments dashboard (list, mark confirmed/cancelled)
- **P2** Google Calendar sync so booked slots reflect the doctor's real calendar
- **P2** Rate-limit / basic anti-spam on `POST /api/appointments`
- **P2** SEO / OpenGraph tags and sitemap
- **P3** Analytics + form completion metrics
- **P3** Patient stories with real quotes and consent management

## Next Tasks
1. Wire an email/SMS notification when a new appointment arrives (Resend recommended).
2. Add a lightweight admin dashboard at `/admin` behind a password.
3. Consider Google Calendar OAuth integration for real availability sync.
