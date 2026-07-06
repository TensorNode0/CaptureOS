# Test Credentials — GovCon Command Center

## Admin / Owner
- Email: `admin@govcon.io`
- Password: `Admin#2026`
- Role in 'Orbital Defense Systems': owner

## Editor
- Email: `editor@govcon.io`
- Password: `Editor#2026`
- Role: editor

## Viewer
- Email: `viewer@govcon.io`
- Password: `Editor#2026`
- Role: viewer

## Notes
- Demo org: **Orbital Defense Systems** (seeded with 12 opportunities + org profile).
- Email verification is MOCKED: register returns a `verifyUrl`; password reset returns `resetUrl`.
- AI 'Verify & Refresh' and 'Pull from SAM/Grants' are MOCKED (Phase 5 wires real keys).

## Auth endpoints
- POST /api/auth/register | /login | /logout | /refresh | /forgot-password | /reset-password | /verify-email
- GET  /api/auth/me
