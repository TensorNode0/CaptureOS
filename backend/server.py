from dotenv import load_dotenv
load_dotenv()

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import ensure_indexes
from seed import seed
from routers import auth, orgs, opportunities

app = FastAPI(title="GovCon Command Center API")

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


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "govcon-command-center"}


@app.on_event("startup")
async def startup():
    await ensure_indexes()
    await seed()
