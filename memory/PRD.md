# Meridian Medical Studio — Product Requirements

## Original Problem Statement
Build a premium doctor / clinic website with 3D hero, smooth scroll animations, parallax, mouse-follow, 3D card transitions, glassmorphism, and responsive performance-conscious motion. Repo: https://github.com/pikmycar/doctor-website.git.

## Architecture
- **Frontend** (`/app/frontend`): Vite + React 19 + TS, Framer Motion, R3F + Drei, Three.js, react-router-dom.
- **Backend** (`/app/backend`): FastAPI on 8001. Public: `/api/health`, `/api/availability`, `POST /api/appointments` (honeypot + rate limit). Auth: `/api/auth/login|logout|me`. Admin (JWT): `/api/admin/appointments` (GET/PATCH status &/or notes), `POST /api/admin/appointments/bulk`, `/api/admin/appointments.csv`, `/api/admin/stats`.
- Ingress: `/api/*` → 8001, everything else → 3000.

## User Personas
- Prospective private-practice patients (desktop/mobile)
- Practice admin managing incoming appointment requests
- Referring physicians assessing credibility

## Implemented (dated)
- **2026-08-11 v1**: 3D hero + editorial layout + services + appointment dialog.
- **2026-08-11 v2**: Repo restructure → `/app/frontend` + `/app/backend`, minimal FastAPI backend.
- **2026-08-11 v3**: Appointment storage, Doctor Profile, Patient Stories, Live Availability (5 days × 30-min slots). 100% tests.
- **2026-08-11 v4**: Admin dashboard + Booking Alerts webhook + Spam Shield (honeypot + rate limit). JWT auth. 100% tests.
- **2026-08-11 v5**: CSV Export + Appointment Notes + numerals polish. 31/31 tests.
- **2026-08-11 v6 (current)**: Admin triage tools
  - **Admin Search** — search bar filters live over name/email/notes/message; combines with status tabs; shows "N of M" match count and empty-state per query.
  - **Bulk Actions** — checkbox per card; forest-toned action bar with Select-all-visible / Clear / Confirm-all / Cancel-all; hits `POST /api/admin/appointments/bulk` with pydantic-bounded `ids` (1–200) and validated status; optimistic UI + rollback on failure.
  - testing_agent iteration 5: **41/41 pytest** + 100% frontend + regressions all pass.

## Deferred (backlog)
- **P0** Real Emails via Resend (needs API key) — deferred per user
- **P0** Google Calendar OAuth Sync (needs Google Cloud OAuth credentials) — deferred per user
- **P1** Add `not_found` count + inline "Bulk update failed" toast on error
- **P1** Auto-prune selection when items leave filter (or show "M hidden")
- **P2** Tighten CORS to explicit origins for future cross-origin deploys
- **P2** Multi-admin + password reset flow
- **P3** SEO/OpenGraph, sitemap, analytics
- **P3** Search inside CSV export (currently unfiltered by search query)

## Next Tasks
1. Wire real email sending (Resend recommended) when user provides an API key.
2. Google Calendar OAuth so booked slots block off her live calendar.
3. Persist search+filter state to the URL so admins can bookmark specific views.
