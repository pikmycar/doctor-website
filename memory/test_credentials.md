# Meridian Medical Studio – Test Credentials

## Admin dashboard
- URL: `/admin` (e.g. `https://24e3528c-bcfb-4601-b1bc-945f6d9cc3e6.preview.emergentagent.com/admin`)
- Email: `admin@meridianmedical.com`
- Password: `wwpY_RDaZSaGBMcJ`
- Role: admin

To change these, edit `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `/app/backend/.env` and restart the backend. The seed logic is idempotent — updating the password in `.env` will rehash on next startup without duplicating the user.

## Auth endpoints
- `POST /api/auth/login` — body `{ "email": ..., "password": ... }` → sets httpOnly `access_token` cookie + returns `{ email, role, access_token }`
- `POST /api/auth/logout` — clears cookie
- `GET  /api/auth/me` — returns `{ email, role }` for the authenticated admin

## Protected admin endpoints
- `GET  /api/admin/appointments`
- `PATCH /api/admin/appointments/{id}` — body `{ "status": "requested" | "confirmed" | "cancelled" }`
- `GET  /api/admin/stats`

## Booking alerts webhook
- Set `ALERT_WEBHOOK_URL` in `/app/backend/.env` to a Zapier / Make / Discord / n8n webhook URL to receive `POST` alerts for every new appointment. When blank (current default) alerts are only logged in the `alerts` collection.

## Spam protection
- Honeypot: form contains a hidden `website` field — submissions with any value are silently accepted but never persisted.
- Rate limit: max **5** booking attempts per IP per rolling hour (configurable via `BOOKING_RATE_LIMIT_PER_HOUR`). Login endpoint locks an IP+email out after 5 failed attempts for 15 minutes.
