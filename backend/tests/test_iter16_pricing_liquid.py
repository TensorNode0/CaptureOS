"""Iteration 16 backend smoke — Phase 2 v2 pricing revision.

Under test:
  * Stripe catalog was re-provisioned so yearly prices are whole dollars:
      - oi_yearly   = 48000 cents  ($480/yr)
      - full_yearly = 288000 cents ($2,880/yr)
      - oi_monthly  = 4999 cents (unchanged)
      - full_monthly= 9999 cents (unchanged)
  * POST /api/payments/checkout with each lookupKey returns a valid Stripe URL.
  * Health boot state still {db:'ready', migrated:true, missing_env:[]}.
  * Existing free-tier gates still 402 (proposal / files / ai/chat).
"""
import os
import pytest
import requests
import stripe

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


# --------- Health smoke -------------------------------------------------------
class TestHealth:
    def test_health_boot_state(self):
        r = requests.get(f"{BASE_URL}/api/health", timeout=15)
        assert r.status_code == 200, r.text
        boot = r.json().get("boot") or {}
        assert boot.get("db") == "ready"
        assert boot.get("migrated") is True
        assert boot.get("missing_env") == []


# --------- Checkout: all 4 lookup keys still work ---------------------------
class TestCheckout:
    @pytest.mark.parametrize("lookup_key", [
        "oi_monthly", "oi_yearly", "full_monthly", "full_yearly"
    ])
    def test_checkout_returns_stripe_url(self, qa, lookup_key):
        r = qa.post(f"{BASE_URL}/api/payments/checkout", json={
            "lookupKey": lookup_key, "originUrl": ORIGIN,
        }, timeout=30)
        assert r.status_code == 200, f"[{lookup_key}] {r.status_code}: {r.text}"
        data = r.json()
        assert data.get("url", "").startswith("https://checkout.stripe.com/"), \
            f"[{lookup_key}] expected stripe URL, got {data}"
        assert data.get("sessionId"), f"[{lookup_key}] missing sessionId"


# --------- Stripe catalog prices are correct (48000 / 288000) --------------
class TestStripeCatalog:
    """Direct Stripe API check that yearly prices are exact whole-dollar cents."""

    @classmethod
    def setup_class(cls):
        # Load /app/backend/.env so STRIPE_SECRET_KEY is available.
        from dotenv import load_dotenv
        load_dotenv("/app/backend/.env")
        key = os.environ.get("STRIPE_SECRET_KEY")
        if not key or key == "sk_test_emergent":
            pytest.skip("STRIPE_SECRET_KEY unavailable — cannot introspect prices")
        stripe.api_key = key

    @pytest.mark.parametrize("lookup_key,expected_cents", [
        ("oi_yearly", 48000),
        ("full_yearly", 288000),
        ("oi_monthly", 4999),
        ("full_monthly", 9999),
    ])
    def test_price_amount(self, lookup_key, expected_cents):
        prices = stripe.Price.list(lookup_keys=[lookup_key], active=True, limit=1).data
        assert prices, f"no active price for {lookup_key}"
        assert prices[0].unit_amount == expected_cents, \
            f"{lookup_key} expected {expected_cents} cents, got {prices[0].unit_amount}"


# --------- Free-tier gates still 402 ---------------------------------------
class TestTierGates:
    def test_proposal_402(self, qa):
        r = qa.post(
            f"{BASE_URL}/api/orgs/{ORG_ID}/opportunities/{OPP_ID}/proposal",
            json={}, timeout=30)
        assert r.status_code == 402, r.text

    def test_files_402(self, qa):
        # Files endpoint uses multipart. Strip JSON content-type header so requests
        # can rebuild it as multipart/form-data with a proper boundary.
        headers = {k: v for k, v in qa.headers.items() if k.lower() != "content-type"}
        r = requests.post(
            f"{BASE_URL}/api/orgs/{ORG_ID}/files",
            headers=headers,
            files={"file": ("t.txt", b"hello", "text/plain")},
            timeout=30)
        assert r.status_code == 402, f"expected 402 got {r.status_code}: {r.text}"

    def test_ai_chat_402(self, qa):
        r = qa.post(f"{BASE_URL}/api/orgs/{ORG_ID}/ai/chat", json={
            "messages": [{"role": "user", "content": "hi"}],
            "engine": "claude",
        }, timeout=30)
        assert r.status_code == 402, r.text
