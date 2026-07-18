"""Iteration 15 smoke test — post deploy-hardening rewrite of server.py.

Fix under test: startup handler now (a) logs missing required env vars instead
of raising KeyError, (b) wraps DB pool + migrations + seed in try/except so the
pod stays alive, (c) /api/health always answers and now includes a boot object
with keys `db`, `migrated`, `missing_env`.

This is a 6-endpoint smoke, NOT a full 42-test regression. If everything here
passes, prod deploy can be retried with confidence.
"""
import io
import json
import os
import zipfile

import pytest
import requests

BASE_URL = (os.environ.get("TEST_BASE_URL")
            or os.environ.get("REACT_APP_BACKEND_URL")
            or "https://govcon-workspace.preview.emergentagent.com").rstrip("/")

SUPABASE_URL = "https://rmhdccypaaemmqdsfhcm.supabase.co"
SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJt"
    "aGRjY3lwYWFlbW1xZHNmaGNtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODMxMjAzNTUsImV4"
    "cCI6MjA5ODY5NjM1NX0.kBJaczjlS_L0USkQ-vkG9gnpJLe_hKcOhenUy7iRnu8"
)

QA_EMAIL = "qa.captureagent@testmail.dev"
QA_PASSWORD = "CaptureQA#2026"
ORG_ID = "499e35c6-ca12-4589-aa1a-ae22bdb72c07"
OPP_ID = "6f59d50c-b0c2-4730-aa72-eddda8dda686"
DEPLOY_REGRESSION_REASON = "DEPLOY_REGRESSION iter15 smoke"


def _login(email, password):
    r = requests.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
        json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def qa():
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {_login(QA_EMAIL, QA_PASSWORD)}",
                      "Content-Type": "application/json"})
    yield s
    # Teardown: sweep any DEPLOY_REGRESSION refund_requests rows we created.
    try:
        pending = s.get(f"{BASE_URL}/api/refund-requests?status=pending").json()
        for row in (pending or []):
            if (row.get("reason") or "").startswith("DEPLOY_REGRESSION"):
                s.post(f"{BASE_URL}/api/refund-requests/{row['id']}/deny",
                       json={"adminNotes": "DEPLOY_REGRESSION cleanup"})
    except Exception:
        pass


# --------- Startup hardening: /api/health boot state ------------------------

class TestHealthBootState:
    def test_health_200_with_boot_state(self):
        r = requests.get(f"{BASE_URL}/api/health", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("status") == "ok"
        assert data.get("service") == "captureagent"
        boot = data.get("boot") or {}
        assert boot.get("db") == "ready", f"boot.db={boot.get('db')}"
        assert boot.get("migrated") is True, f"boot.migrated={boot.get('migrated')}"
        assert boot.get("missing_env") == [], f"boot.missing_env={boot.get('missing_env')}"


# --------- 6 critical spot-check endpoints ---------------------------------

class TestSpotCheckEndpoints:
    # a) GET /api/payments/me
    def test_a_payments_me_qa(self, qa):
        r = qa.get(f"{BASE_URL}/api/payments/me", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("tier") == "free", f"tier={data.get('tier')}"
        assert data.get("isPlatformOwner") is True, \
            f"isPlatformOwner={data.get('isPlatformOwner')}"
        assert data.get("status") == "free", f"status={data.get('status')}"

    # b) POST /api/payments/checkout full_monthly → valid Stripe URL
    def test_b_checkout_full_monthly(self, qa):
        r = qa.post(f"{BASE_URL}/api/payments/checkout", json={
            "lookupKey": "full_monthly",
            "originUrl": "https://govcon-workspace.preview.emergentagent.com",
        }, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("url", "").startswith("https://checkout.stripe.com/"), \
            f"expected stripe URL, got {data}"
        assert data.get("sessionId")

    # c) POST /api/orgs/{orgId}/opportunities/{oppId}/proposal → 402 (tier)
    def test_c_opportunity_proposal_402(self, qa):
        r = qa.post(
            f"{BASE_URL}/api/orgs/{ORG_ID}/opportunities/{OPP_ID}/proposal",
            json={}, timeout=30)
        assert r.status_code == 402, f"expected 402, got {r.status_code}: {r.text}"
        detail = (r.json().get("detail") or "").lower()
        assert "full capture" in detail, f"missing tier msg: {r.json()}"

    # d) POST /api/refund-requests → 200 ok:true (write_audit(None,...) works)
    def test_d_refund_request_ok(self, qa):
        r = qa.post(f"{BASE_URL}/api/refund-requests",
                    json={"reason": DEPLOY_REGRESSION_REASON}, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("ok") is True, f"ok={data.get('ok')}"
        assert data.get("requestId"), "missing requestId"

    # e) GET /api/auth/me/export → 200 valid ZIP, no password_hash in profile.json
    def test_e_export_zip_no_password_hash(self, qa):
        r = qa.get(f"{BASE_URL}/api/auth/me/export", timeout=60)
        assert r.status_code == 200, r.text
        with zipfile.ZipFile(io.BytesIO(r.content), "r") as zf:
            names = zf.namelist()
            assert "account/profile.json" in names, f"missing profile.json: {names}"
            prof = json.loads(zf.read("account/profile.json"))
        assert "password_hash" not in prof
        assert "passwordHash" not in prof
        assert prof.get("email") == QA_EMAIL

    # f) POST /api/orgs/{orgId}/ai/chat → 402 (tier gate)
    def test_f_ai_chat_402(self, qa):
        r = qa.post(f"{BASE_URL}/api/orgs/{ORG_ID}/ai/chat", json={
            "messages": [{"role": "user", "content": "hi"}],
            "engine": "claude",
        }, timeout=30)
        assert r.status_code == 402, f"expected 402, got {r.status_code}: {r.text}"
        detail = (r.json().get("detail") or "").lower()
        assert "full capture" in detail, f"missing tier msg: {r.json()}"


# --------- Anonymous routes still work (auth surface not broken) -----------

class TestAnonRoutes:
    def test_login_endpoint_reachable_wrong_creds(self):
        """The /login page is client-side; auth itself hits Supabase directly.
        This asserts that hitting Supabase with a bad password still returns 400
        (not a network/CORS error caused by broken preview backend)."""
        r = requests.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
            headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
            json={"email": QA_EMAIL, "password": "wrong-password-xxx"}, timeout=30)
        assert r.status_code in (400, 401), f"unexpected: {r.status_code} {r.text}"

    def test_public_pricing_endpoint_reachable(self):
        # /api/public/* endpoints (if any) or just re-hit /api/health to confirm
        # anonymous routing is intact.
        r = requests.get(f"{BASE_URL}/api/health", timeout=15)
        assert r.status_code == 200
