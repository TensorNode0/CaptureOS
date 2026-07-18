from dotenv import load_dotenv
load_dotenv()

import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

import database
from apply_migrations import apply_migrations
from seed import seed
from routers import auth, orgs, opportunities, intel, capabilities, proposals, venture, competitive, shared, ai, public, files, payments

logger = logging.getLogger("captureagent")
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="CaptureAgent API")

frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")

# Env vars that MUST be present in production. When any is missing we still
# let the process boot so /api/health responds (readiness probe succeeds and
# operators can see the log line explaining what's wrong), but we log a loud
# warning so the failure is obvious in the deploy logs.
_REQUIRED_ENVS = [
    "DATABASE_URL",
    "SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_JWT_SECRET",
    "SECRETS_ENC_KEY", "JWT_SECRET",
]


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Baseline security headers on every API response (NIST 800-171 3.13.x)."""
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        # The API serves JSON/files only — a restrictive CSP is safe here.
        response.headers.setdefault("Content-Security-Policy",
                                    "default-src 'none'; frame-ancestors 'none'")
        if frontend_url.startswith("https"):
            response.headers.setdefault("Strict-Transport-Security",
                                        "max-age=31536000; includeSubDomains")
        return response


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(orgs.router)
app.include_router(opportunities.router)
app.include_router(intel.router)
app.include_router(capabilities.router)
app.include_router(proposals.router)
app.include_router(venture.router)
app.include_router(competitive.router)
app.include_router(shared.router)
app.include_router(ai.router)
app.include_router(public.router)
app.include_router(files.router)
app.include_router(payments.router)


# Boot-state flag. Even if DB init fails, `/api/health` still answers so the
# K8s readiness probe passes and operators can read the crash log — otherwise
# the pod hits a silent 10-minute deploy timeout with no signal.
_BOOT_STATE = {"db": "pending", "migrated": False, "missing_env": []}


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "captureagent", "boot": _BOOT_STATE}


@app.on_event("startup")
async def startup():
    # 1) Env-var sanity check — log LOUDLY before anything else touches env.
    missing = [k for k in _REQUIRED_ENVS if not os.environ.get(k)]
    _BOOT_STATE["missing_env"] = missing
    if missing:
        logger.error(
            "STARTUP: %d required env var(s) are missing: %s — pod will "
            "answer /api/health but API routes will 5xx until fixed.",
            len(missing), ", ".join(missing))
        return  # Don't crash — let the pod become ready so logs are readable.

    # 2) DB pool.
    try:
        pool = await database.init_pool()
        _BOOT_STATE["db"] = "ready"
        logger.info("STARTUP: DB pool initialised.")
    except Exception as e:
        _BOOT_STATE["db"] = f"error: {type(e).__name__}: {e}"
        logger.exception("STARTUP: DB pool init failed. Continuing so /api/health "
                         "stays live — API routes will 5xx until reachable.")
        return

    # 3) Auto-migrations (safe to disable in prod via AUTO_MIGRATE=0).
    if os.environ.get("AUTO_MIGRATE", "1") == "1":
        try:
            async with pool.acquire() as conn:
                await apply_migrations(conn)
            _BOOT_STATE["migrated"] = True
        except Exception:
            logger.exception("STARTUP: migrations failed — the pod stays up but "
                             "features that rely on new columns may 5xx.")

    # 4) Optional demo seed (SEED_DEMO=1 only).
    try:
        await seed()
    except Exception:
        logger.exception("STARTUP: demo seed failed — non-fatal.")


@app.on_event("shutdown")
async def shutdown():
    await database.close_pool()
