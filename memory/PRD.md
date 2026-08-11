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
- **Backend** (`/app/backend`): FastAPI on port 8001, exposes `/api/` and `/api/health`. MongoDB via `motor` (env vars `MONGO_URL`, `DB_NAME`). Placeholder — no business endpoints yet.
- **Ingress**: `/api/*` → backend:8001, everything else → frontend:3000.

## User Personas
- Prospective private-practice patients browsing on desktop/mobile
- Existing patients booking or exploring the practice's approach
- Referring physicians assessing credibility

## Core Requirements (Static)
- Editorial, calm, "Meridian medical studio" brand voice
- Accessible interactive 3D hero (with reduced-motion fallback)
- Appointment request dialog with focus trap
- Responsive across breakpoints
- No visual regressions from earlier iteration

## Implemented (dated)
- **2026-08-11**: Frontend restructured into `/app/frontend/`; minimal FastAPI backend scaffolded at `/app/backend/` with `/api/health`; env files added; Vite server bound to 0.0.0.0:3000 with `allowedHosts: true`; supervisor services green; deployment_agent PASS.
- **2026-08-11** (prior session): 3D hero (React Three Fiber orb), scroll animations, service cards, appointment dialog with focus trap, responsive layout, design guidelines, testing_agent iteration 1 passed.

## Prioritized Backlog
- **P1** Wire appointment dialog `POST /api/appointments` to store requests in Mongo and (optionally) email routing.
- **P1** Live availability / calendar embed for booking.
- **P2** Doctor bio + patient stories section.
- **P2** SEO / OpenGraph tags and sitemap.
- **P3** Analytics + form spam protection.

## Next Tasks
1. Add appointment persistence endpoint + hook up the dialog form.
2. Add a doctor profile section with photo, credentials, and philosophy.
3. Consider Stripe/booking integration if user wants paid consults.
