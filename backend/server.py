from dotenv import load_dotenv
load_dotenv()

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

import database
from apply_migrations import apply_migrations
from seed import seed
from routers import auth, orgs, opportunities, intel, capabilities, proposals, venture, competitive, shared, ai

app = FastAPI(title="CaptureAgent API")

frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")


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


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "captureagent"}


@app.on_event("startup")
async def startup():
    pool = await database.init_pool()
    if os.environ.get("AUTO_MIGRATE", "1") == "1":
        async with pool.acquire() as conn:
            await apply_migrations(conn)
    await seed()


@app.on_event("shutdown")
async def shutdown():
    await database.close_pool()
