"""Iteration 17 backend smoke — new /proposal/customer/suggest endpoint
+ regression on /proposal/customer/check + baseline health/checkout smokes.

QA user is on the FREE tier so both AI endpoints must return HTTP 402
(tier-gated to Small Teams). 402 alone confirms the wiring is in place.
"""
import os
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
ORIGIN = "https://govcon-workspace.preview.emergentagent.com"


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
    return s


# ---------- Health smoke -----------------------------------------------------
class TestHealth:
    def test_health_boot_state(self):
        r = requests.get(f"{BASE_URL}/api/health", timeout=15)
        assert r.status_code == 200, r.text
        boot = r.json().get("boot") or {}
        assert boot.get("db") == "ready", f"db not ready: {boot}"
        assert boot.get("missing_env") == [], f"missing_env: {boot}"


# ---------- Checkout smoke ---------------------------------------------------
class TestCheckoutSmoke:
    def test_oi_yearly_checkout_returns_stripe_url(self, qa):
        r = qa.post(f"{BASE_URL}/api/payments/checkout", json={
            "lookupKey": "oi_yearly", "originUrl": ORIGIN,
        }, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("url", "").startswith("https://checkout.stripe.com/"), data
        assert data.get("sessionId"), data


# ---------- New endpoint: /proposal/customer/suggest tier-gate --------------
class TestCustomerSuggestTierGate:
    """QA (free tier) must get 402 on the new POST /customer/suggest endpoint."""

    def test_suggest_returns_402_for_free_tier(self, qa):
        r = qa.post(
            f"{BASE_URL}/api/orgs/{ORG_ID}/opportunities/{OPP_ID}/proposal/customer/suggest",
            json={"engine": "claude"}, timeout=30)
        assert r.status_code == 402, f"expected 402 got {r.status_code}: {r.text}"


# ---------- Existing endpoint: /proposal/customer/check regression ----------
class TestCustomerCheckTierGate:
    """QA (free tier) must get 402 on the existing POST /customer/check endpoint."""

    def test_check_returns_402_for_free_tier(self, qa):
        r = qa.post(
            f"{BASE_URL}/api/orgs/{ORG_ID}/opportunities/{OPP_ID}/proposal/customer/check",
            json={"engine": "claude"}, timeout=30)
        assert r.status_code == 402, f"expected 402 got {r.status_code}: {r.text}"
