from dotenv import load_dotenv
load_dotenv()

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import database
from apply_migrations import apply_migrations
from seed import seed
from routers import auth, orgs, opportunities, intel, capabilities, proposals

app = FastAPI(title="CaptureAgent API")

frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
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
