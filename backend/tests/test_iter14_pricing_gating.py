"""Iteration 14 regression: new Phase 2 pricing + expanded tier gating.

Covers:
- Stripe checkout with new lookup keys (oi_monthly $49.99, full_monthly $99.99,
  oi_yearly $479.90, full_yearly $2,879.71). We hit checkout and, when
  STRIPE_SECRET_KEY is available, additionally use stripe.Price.retrieve
  via lookup_keys to assert the underlying unit_amounts.
- Tier gating (new for OI/free): GET/POST /api/orgs/{orgId}/files → 402,
  GET /api/orgs/{orgId}/files/{fileId}/url → 402,
  POST /api/orgs/{orgId}/ai/chat → 402.
- Regression: GET /api/orgs/{orgId}/opportunities → 200,
  GET /api/orgs/{orgId}/venture-docs?kind=investor_scan → 200,
  POST /api/refund-requests → 200 (writer_audit(None,...) fix intact),
  GET /api/auth/me/export → 200 zip without password_hash/passwordHash.
"""
import io
import json
import os
import uuid
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
    # Teardown: sweep any REGRESSION14_ refund_requests rows still pending
    try:
        pending = s.get(f"{BASE_URL}/api/refund-requests?status=pending").json()
        for row in pending or []:
            if (row.get("reason") or "").startswith("REGRESSION14_"):
                s.post(f"{BASE_URL}/api/refund-requests/{row['id']}/deny",
                       json={"adminNotes": "REGRESSION14 cleanup"})
    except Exception:
        pass


# --------------------- New pricing: Stripe checkout ---------------------

EXPECTED_AMOUNTS = {
    "oi_monthly":   4999,
    "full_monthly": 9999,
    "oi_yearly":   47990,
    "full_yearly": 287971,
}


class TestNewPricingCheckout:
    @pytest.mark.parametrize("lookup_key", list(EXPECTED_AMOUNTS.keys()))
    def test_checkout_creates_url(self, qa, lookup_key):
        r = qa.post(f"{BASE_URL}/api/payments/checkout", json={
            "lookupKey": lookup_key,
            "originUrl": "https://govcon-workspace.preview.emergentagent.com",
        })
        assert r.status_code == 200, f"{lookup_key}: {r.status_code} {r.text}"
        data = r.json()
        assert data.get("url", "").startswith("https://checkout.stripe.com/"), \
            f"{lookup_key}: expected stripe URL, got {data}"
        assert data.get("sessionId"), f"{lookup_key}: missing sessionId"


class TestStripePriceCatalog:
    """Directly inspect Stripe to verify unit_amount on each lookup_key."""

    @pytest.fixture(scope="class")
    def stripe_client(self):
        try:
            import stripe as _stripe
        except ImportError:
            pytest.skip("stripe package not installed")
        # Load STRIPE_SECRET_KEY from backend .env
        try:
            from dotenv import load_dotenv
            load_dotenv("/app/backend/.env")
        except Exception:
            pass
        key = os.environ.get("STRIPE_SECRET_KEY", "")
        if not key or not key.startswith("sk_"):
            pytest.skip("STRIPE_SECRET_KEY not configured")
        _stripe.api_key = key
        return _stripe

    @pytest.mark.parametrize("lookup_key,expected", list(EXPECTED_AMOUNTS.items()))
    def test_price_unit_amount(self, stripe_client, lookup_key, expected):
        prices = stripe_client.Price.list(
            lookup_keys=[lookup_key], active=True, limit=1).data
        assert prices, f"No active Stripe price with lookup_key={lookup_key}"
        p = prices[0]
        assert p.unit_amount == expected, \
            f"{lookup_key}: expected {expected}, got {p.unit_amount}"
        assert p.currency == "usd"
        # Seat limit metadata
        expected_seats = 3 if lookup_key == "full_yearly" else 1
        seat = (p.metadata or {}).get("seat_limit")
        assert seat == str(expected_seats), \
            f"{lookup_key}: expected seat_limit={expected_seats}, got {seat}"


# --------------------- NEW tier gating: files + AI chat ---------------------

class TestTierGatingFiles:
    def test_list_files_gated(self, qa):
        r = qa.get(f"{BASE_URL}/api/orgs/{ORG_ID}/files")
        assert r.status_code == 402, f"expected 402, got {r.status_code}: {r.text}"
        detail = (r.json().get("detail") or "").lower()
        assert "full capture" in detail, f"missing tier msg: {r.json()}"

    def test_upload_file_gated(self, qa):
        # Multipart upload; drop the JSON content-type header the session sets
        sess = requests.Session()
        sess.headers.update({"Authorization": qa.headers["Authorization"]})
        files = {"file": ("t.txt", b"hello", "text/plain")}
        data = {"category": "capability_statements"}
        r = sess.post(f"{BASE_URL}/api/orgs/{ORG_ID}/files",
                      files=files, data=data, timeout=30)
        assert r.status_code == 402, f"expected 402, got {r.status_code}: {r.text}"

    def test_download_url_gated_before_404(self, qa):
        fake = str(uuid.uuid4())
        r = qa.get(f"{BASE_URL}/api/orgs/{ORG_ID}/files/{fake}/url")
        # gate must fire before the 404 lookup
        assert r.status_code == 402, f"expected 402, got {r.status_code}: {r.text}"


class TestTierGatingAIChat:
    def test_ai_chat_gated(self, qa):
        r = qa.post(f"{BASE_URL}/api/orgs/{ORG_ID}/ai/chat", json={
            "messages": [{"role": "user", "content": "hi"}],
            "engine": "claude",
        })
        assert r.status_code == 402, f"expected 402, got {r.status_code}: {r.text}"
        detail = (r.json().get("detail") or "").lower()
        assert "full capture" in detail, f"missing tier msg: {r.json()}"


# --------------------- Regressions: still-working endpoints ---------------------

class TestRegressionEndpoints:
    def test_opportunities_list_free_ok(self, qa):
        r = qa.get(f"{BASE_URL}/api/orgs/{ORG_ID}/opportunities?limit=3")
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)

    def test_venture_docs_investor_scan_kind_ok(self, qa):
        r = qa.get(f"{BASE_URL}/api/orgs/{ORG_ID}/venture-docs?kind=investor_scan")
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)

    @pytest.mark.parametrize("kind", ["pitch_deck", "business_plan",
                                      "accelerator_application"])
    def test_venture_docs_restricted_still_gated(self, qa, kind):
        r = qa.post(f"{BASE_URL}/api/orgs/{ORG_ID}/venture-docs", json={
            "kind": kind, "title": f"TEST_iter14_{kind}"})
        assert r.status_code == 402, f"kind={kind}: {r.status_code} {r.text}"

    def test_refund_request_still_200(self, qa):
        r = qa.post(f"{BASE_URL}/api/refund-requests",
                    json={"reason": "REGRESSION14_iter14 sanity"})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("ok") is True
        assert data.get("requestId")

    def test_export_zip_no_password_hash(self, qa):
        r = qa.get(f"{BASE_URL}/api/auth/me/export", timeout=60)
        assert r.status_code == 200
        with zipfile.ZipFile(io.BytesIO(r.content), "r") as zf:
            prof = json.loads(zf.read("account/profile.json"))
        assert "password_hash" not in prof
        assert "passwordHash" not in prof
        assert prof.get("email") == QA_EMAIL
