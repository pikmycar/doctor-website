# Meridian Medical Studio — Product Requirements

## Original Problem Statement
Build a premium doctor / clinic website (repo: https://github.com/pikmycar/doctor-website.git) with:
- 3D hero section, smooth scroll animations, parallax, mouse-follow, 3D card transitions
- Premium gradients, glassmorphism, micro-interactions
- Responsive, performance-conscious animations

## Architecture
- **Frontend** (`/app/frontend`): Vite + React 19 + TS, Framer Motion, R3F + Drei, Three.js, react-router-dom.
- **Backend** (`/app/backend`): FastAPI on 8001. Public: `/api/health`, `/api/availability`, `POST /api/appointments` (honeypot + rate limit). Auth: `/api/auth/login|logout|me`. Admin (JWT): `/api/admin/appointments` (GET/PATCH — status &/or notes), `/api/admin/appointments.csv`, `/api/admin/stats`.
- Ingress: `/api/*` → 8001, everything else → 3000.

## User Personas
- Prospective private-practice patients (desktop/mobile)
- Practice admin managing incoming appointment requests
- Referring physicians assessing credibility

## Implemented (dated)
- **2026-08-11 v1**: 3D hero + editorial layout + services + appointment dialog.
- **2026-08-11 v2**: Repo restructure into `/app/frontend` + `/app/backend`. Minimal FastAPI backend.
- **2026-08-11 v3**: Appointment storage, Doctor Profile, Patient Stories, Live Availability (5 days × 30-min slots). 100% tests.
- **2026-08-11 v4**: Admin dashboard + Booking Alerts (webhook + DB log) + Spam Shield (honeypot + IP rate limit). 100% tests.
- **2026-08-11 v5 (current)**: Admin polish
  - **CSV Export** — `GET /api/admin/appointments.csv?date_from&date_to` streams CSV with headers `id,name,email,slot_start,slot_end,status,notes,message,created_at`; date pickers + Download button in the dashboard.
  - **Appointment Notes** — new `notes` field on Appointment; `PATCH /api/admin/appointments/{id}` accepts optional `status`/`notes`; per-card private note editor with "Unsaved changes" → "✓ Saved" states.
  - Fixed oldstyle numeral rendering (stat cards, day tabs, approach stats) with `font-variant-numeric: lining-nums tabular-nums`.
  - testing_agent iteration 4: **31/31 pytest** + all frontend + regressions pass.

## Prioritized Backlog (deferred)
- **P0** Real Emails via Resend/SendGrid (deferred — needs API key)
- **P0** Google Calendar OAuth sync (deferred — needs Google Cloud OAuth credentials)
- **P1** Admin: search / free-text filter, bulk actions
- **P2** Tighten CORS to explicit origin list for future cross-origin deploys
- **P2** Multi-admin + password reset flow
- **P3** SEO/OpenGraph, sitemap, analytics
- **P3** Public "download consent" watermark on CSV export

## Next Tasks
1. Wire real email sending (Resend recommended) when user provides API key.
2. Google Calendar OAuth to sync doctor's real schedule with the availability endpoint.
3. Admin: search bar + bulk confirm/cancel.
