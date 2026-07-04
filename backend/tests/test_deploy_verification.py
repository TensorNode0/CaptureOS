"""
Deployment verification for CaptureAgent (external Supabase backend).
Covers: health, register+verify-email (mocked), login, create org, get secrets (masked).
DO NOT test AI/SAM scan endpoints (they need real API keys).
"""
import os
from urllib.parse import urlparse, parse_qs

import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") \
    if os.environ.get("REACT_APP_BACKEND_URL") \
    else "https://govcon-workspace.preview.emergentagent.com"

QA_EMAIL = "qa.captureagent@testmail.dev"
QA_PASSWORD = "CaptureQA#2026"
QA_NAME = "QA Capture"
QA_ORG_NAME = "QA Verification Org"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def state():
    # shared state across tests in this module
    return {"verify_token": None, "org_id": None}


# --- 1. Health -------------------------------------------------------------
def test_health(session):
    r = session.get(f"{BASE_URL}/api/health")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body == {"status": "ok", "service": "captureagent"}, body


# --- 2. Register (mocked email) --------------------------------------------
def test_register_returns_verify_url(session, state):
    payload = {"email": QA_EMAIL, "name": QA_NAME, "password": QA_PASSWORD}
    r = session.post(f"{BASE_URL}/api/auth/register", json=payload)
    # Accept 200 (fresh) or 400 (already exists from prior run)
    if r.status_code == 400 and "already exists" in r.text.lower():
        pytest.skip("QA user already exists from prior run; skipping fresh register")
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    data = r.json()
    # required fields
    assert data.get("email") == QA_EMAIL
    assert data.get("name") == QA_NAME
    assert "id" in data
    assert "verifyUrl" in data and data["verifyUrl"], data
    # cookies set
    assert session.cookies.get("access_token"), "access_token cookie not set"
    # verifyUrl format: {FRONTEND_URL}/verify-email?token=...
    q = parse_qs(urlparse(data["verifyUrl"]).query)
    token = (q.get("token") or [None])[0]
    assert token, f"no token in verifyUrl {data['verifyUrl']}"
    state["verify_token"] = token
    # password hash never leaked
    assert "passwordHash" not in data and "password_hash" not in data


# --- 2b. Verify email using extracted token --------------------------------
def test_verify_email(session, state):
    tok = state.get("verify_token")
    if not tok:
        pytest.skip("no verify token captured (register was skipped)")
    r = session.post(f"{BASE_URL}/api/auth/verify-email", json={"token": tok})
    assert r.status_code == 200, r.text
    assert r.json() == {"ok": True}


# --- 3. Login --------------------------------------------------------------
def test_login(session):
    fresh = requests.Session()
    fresh.headers.update({"Content-Type": "application/json"})
    r = fresh.post(f"{BASE_URL}/api/auth/login",
                   json={"email": QA_EMAIL, "password": QA_PASSWORD})
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    data = r.json()
    assert data.get("email") == QA_EMAIL
    assert "organizations" in data
    assert fresh.cookies.get("access_token"), "access_token cookie not set after login"
    # store cookies on shared session for downstream tests
    session.cookies.update(fresh.cookies)


# --- 3b. /me works with cookie --------------------------------------------
def test_me_with_cookie(session):
    r = session.get(f"{BASE_URL}/api/auth/me")
    assert r.status_code == 200, r.text
    assert r.json().get("email") == QA_EMAIL


# --- 4. Create organization ------------------------------------------------
def test_create_org(session, state):
    # If user already has an org from a previous run, reuse it
    r_list = session.get(f"{BASE_URL}/api/orgs")
    assert r_list.status_code == 200, r_list.text
    existing = r_list.json()
    if existing:
        state["org_id"] = existing[0]["id"]
        return
    r = session.post(f"{BASE_URL}/api/orgs", json={
        "name": QA_ORG_NAME, "naics": [], "keywords": []
    })
    assert r.status_code == 200, f"create org failed: {r.status_code} {r.text}"
    org = r.json()
    assert org["name"] == QA_ORG_NAME
    assert "id" in org
    assert org.get("role") == "owner"
    state["org_id"] = org["id"]


# --- 5. Get secrets returns masked payload --------------------------------
def test_get_secrets_masked(session, state):
    org_id = state.get("org_id")
    assert org_id, "no org id"
    r = session.get(f"{BASE_URL}/api/orgs/{org_id}/secrets")
    assert r.status_code == 200, r.text
    body = r.json()
    # keys present with masked previews (no real values)
    for k in ("anthropicKey", "samKey", "openaiKey",
              "anthropicSet", "samSet", "openaiSet"):
        assert k in body, f"missing {k} in {body}"
    # Freshly created org — nothing set yet
    assert body["anthropicSet"] is False
    assert body["samSet"] is False
    assert body["openaiSet"] is False
