# Meridian Medical Studio — Product Requirements

## Original Problem Statement
Build a premium doctor / clinic website (repo: https://github.com/pikmycar/doctor-website.git) with:
- 3D hero section with interactive objects, smooth scroll animations, parallax, mouse-follow
- 3D card transitions, micro-interactions, animated buttons
- Premium gradients, lighting, glassmorphism
- Responsive motion for mobile
- Performance-conscious animations

## Architecture
- **Frontend** (`/app/frontend`): Vite + React 19 + TypeScript, Framer Motion, React Three Fiber + Drei, Three.js, react-router-dom, Lucide icons. Runs on port 3000 (`yarn start`).
- **Backend** (`/app/backend`): FastAPI on port 8001. Public: `/api/health`, `/api/availability`, `POST /api/appointments`. Auth: `/api/auth/login`, `/api/auth/logout`, `/api/auth/me`. Admin (JWT-protected): `/api/admin/appointments` (GET/PATCH), `/api/admin/stats`. MongoDB via `motor`.
- **Ingress**: `/api/*` → backend:8001, everything else → frontend:3000.

## User Personas
- Prospective private-practice patients on desktop/mobile
- Practice admin managing incoming appointment requests
- Referring physicians assessing credibility

## Core Requirements
- Editorial, calm, "Meridian medical studio" brand voice
- Accessible interactive 3D hero (reduced-motion fallback)
- Real appointment request dialog with focus trap AND live slot booking
- Private admin dashboard for the practice
- Spam-resistant public form

## Implemented (dated)
- **2026-08-11 (v1)**: 3D hero (React Three Fiber orb), animations, service cards, editorial about/approach/contact sections, appointment dialog with focus trap, responsive layout. Design guidelines generated.
- **2026-08-11 (v2)**: Repo restructured into `/app/frontend/` + `/app/backend/`. Minimal FastAPI backend. deployment_agent PASS.
- **2026-08-11 (v3)**: Appointment Storage (DB + admin retrieval), Doctor Profile section, Patient Stories testimonials, Live Availability slot picker with 5 business days × 30-min slots. testing_agent: 100% backend + 100% frontend.
- **2026-08-11 (v4 — current)**: Admin experience + trust
  - **Booking Alerts** — optional `ALERT_WEBHOOK_URL` env var; every new appointment fires a background POST + is logged into the `alerts` Mongo collection. Last alert status surfaced in the admin dashboard.
  - **Admin Dashboard at `/admin`** — react-router-dom route with LoginPanel + Dashboard. bcrypt-hashed seed admin from `ADMIN_EMAIL`/`ADMIN_PASSWORD` env vars; JWT httpOnly cookie + Bearer fallback; brute-force lockout (5 fails → 15 min); stats cards; filter tabs (All / Requested / Confirmed / Cancelled); confirm/cancel buttons on each row.
  - **Spam Shield** — hidden honeypot `website` field (position:absolute; left:-9999px; aria-hidden; tabIndex=-1) silently ignores bot submissions; IP-based rate limit at 5/hr on `POST /api/appointments` (429 with clean message); login endpoint also lockout-protected.
  - Auth playbook consulted before implementation. Idempotent admin seed on startup. Credentials stored in `/app/memory/test_credentials.md`.
  - testing_agent iteration 3: **100% backend (12/12)** + **100% frontend (17/17)**. Local pytest: **20/20** passing over HTTPS.

## Prioritized Backlog
- **P1** Real email alerts (Resend/SendGrid) — plug an API key and swap the webhook fire for an email send.
- **P1** Google Calendar OAuth sync so booked slots reflect the doctor's live calendar.
- **P2** Admin: search / date-range filter; CSV export.
- **P2** Tighten CORS to explicit origin list once cross-origin deploy scenario appears.
- **P2** Admin: bulk actions + notes per appointment.
- **P3** SEO/OpenGraph, sitemap, analytics.
- **P3** Auth: multi-admin + password reset flow.

## Next Tasks
1. Add real email delivery when the user provides a Resend/SendGrid key.
2. Google Calendar OAuth integration.
3. Admin: CSV export + date-range filter.
