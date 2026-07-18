"""Phase 2 billing / tier gating / refunds / GDPR export tests.

Uses real Supabase password grant to log in the QA account
(qa.captureagent@testmail.dev). The QA account is a platform_owner but
NOT grandfathered on billing, so `tier=free` and the tier gate should
actively fire on Federal Proposals / Investment Deals / Accelerator
Applications write endpoints.

DO NOT run any real Stripe payment/webhook flow — only sanity check
checkout URL creation and webhook rejection on invalid signature.
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
ORG_ID = "499e35c6-ca12-4589-aa1a-ae22bdb72c07"

QA_EMAIL = "qa.captureagent@testmail.dev"
QA_PASSWORD = "CaptureQA#2026"
NON_OWNER_EMAIL = "verify.check.1783329822@testmail.dev"
NON_OWNER_PASSWORD = "VerifyCheck#2026"


def _supabase_login(email, password):
    r = requests.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
        json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"supabase login failed for {email}: {r.status_code} {r.text[:300]}"
    return r.json()["access_token"]


def _session(token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def qa_session():
    return _session(_supabase_login(QA_EMAIL, QA_PASSWORD))


@pytest.fixture(scope="module")
def non_owner_session():
    return _session(_supabase_login(NON_OWNER_EMAIL, NON_OWNER_PASSWORD))


# --------------------- /api/payments/me ---------------------

class TestPaymentsMe:
    def test_me_returns_free_tier_platform_owner(self, qa_session):
        r = qa_session.get(f"{BASE_URL}/api/payments/me")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["tier"] == "free", f"expected free tier, got {data}"
        assert data["status"] == "free", f"expected status=free, got {data}"
        assert data["isPlatformOwner"] is True, f"expected isPlatformOwner=true, got {data}"


# --------------------- /api/payments/checkout ---------------------

class TestCheckout:
    def test_checkout_full_monthly(self, qa_session):
        r = qa_session.post(f"{BASE_URL}/api/payments/checkout", json={
            "lookupKey": "full_monthly",
            "originUrl": "https://govcon-workspace.preview.emergentagent.com",
        })
        assert r.status_code == 200, f"checkout failed: {r.status_code} {r.text}"
        data = r.json()
        assert data["url"].startswith("https://checkout.stripe.com/"), \
            f"expected stripe url, got {data['url']}"
        assert data.get("sessionId"), "sessionId missing"

    def test_checkout_oi_yearly(self, qa_session):
        r = qa_session.post(f"{BASE_URL}/api/payments/checkout", json={
            "lookupKey": "oi_yearly",
            "originUrl": "https://govcon-workspace.preview.emergentagent.com",
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["url"].startswith("https://checkout.stripe.com/")
        assert data.get("sessionId")

    def test_checkout_invalid_lookup_key(self, qa_session):
        r = qa_session.post(f"{BASE_URL}/api/payments/checkout", json={
            "lookupKey": "totally_bogus_plan",
            "originUrl": "https://govcon-workspace.preview.emergentagent.com",
        })
        assert r.status_code == 400, f"expected 400, got {r.status_code} {r.text}"
        detail = (r.json().get("detail") or "").lower()
        assert "unknown plan" in detail or "plan" in detail, \
            f"expected helpful error, got {r.json()}"


# --------------------- /api/payments/portal ---------------------

class TestPortal:
    def test_portal_without_subscription(self, qa_session):
        r = qa_session.post(f"{BASE_URL}/api/payments/portal", json={
            "returnUrl": "https://govcon-workspace.preview.emergentagent.com/settings"
        })
        assert r.status_code == 400, r.text
        assert "no active subscription" in (r.json().get("detail") or "").lower()


# --------------------- Tier gating (HTTP 402) ---------------------

class TestTierGating:
    def test_proposals_create_gated(self, qa_session):
        # Get one opportunity id to POST against
        opps = qa_session.get(f"{BASE_URL}/api/orgs/{ORG_ID}/opportunities?limit=1").json()
        assert isinstance(opps, list) and opps, f"expected opportunities list, got {opps}"
        opp_id = opps[0]["id"]
        r = qa_session.post(f"{BASE_URL}/api/orgs/{ORG_ID}/opportunities/{opp_id}/proposal", json={})
        assert r.status_code == 402, f"expected 402, got {r.status_code}: {r.text}"
        assert "full capture" in (r.json().get("detail") or "").lower()

    @pytest.mark.parametrize("kind", ["pitch_deck", "business_plan", "accelerator_application"])
    def test_venture_docs_restricted_kinds_gated(self, qa_session, kind):
        r = qa_session.post(f"{BASE_URL}/api/orgs/{ORG_ID}/venture-docs", json={
            "kind": kind, "title": f"TEST_{kind}"
        })
        assert r.status_code == 402, f"kind={kind} expected 402, got {r.status_code}: {r.text}"

    def test_venture_docs_investor_scan_allowed_free(self, qa_session):
        r = qa_session.post(f"{BASE_URL}/api/orgs/{ORG_ID}/venture-docs", json={
            "kind": "investor_scan", "title": "TEST_investor_scan"
        })
        assert r.status_code in (200, 201), f"scan should be allowed, got {r.status_code}: {r.text}"
        doc = r.json()
        # cleanup
        doc_id = doc.get("id") or (doc.get("doc") or {}).get("id")
        if doc_id:
            qa_session.delete(f"{BASE_URL}/api/orgs/{ORG_ID}/venture-docs/{doc_id}")

    def test_venture_from_program_gated(self, qa_session):
        r = qa_session.post(
            f"{BASE_URL}/api/orgs/{ORG_ID}/venture-docs/from-program",
            json={"name": "TEST Program", "url": ""})
        # Endpoint fully gated → 402 (may also 404/400 if program not found, but tier
        # gate should fire first).
        assert r.status_code == 402, f"expected 402, got {r.status_code}: {r.text}"


# --------------------- Refund workflow ---------------------

class TestRefunds:
    _req_id = None

    def test_submit_refund_request(self, qa_session):
        r = qa_session.post(f"{BASE_URL}/api/refund-requests",
                            json={"reason": "TEST_refund by pytest"})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("ok") is True
        assert data.get("requestId")
        TestRefunds._req_id = data["requestId"]

    def test_list_pending_as_owner(self, qa_session):
        r = qa_session.get(f"{BASE_URL}/api/refund-requests?status=pending")
        assert r.status_code == 200, r.text
        rows = r.json()
        assert isinstance(rows, list)
        assert any(row["id"] == TestRefunds._req_id for row in rows), \
            f"submitted refund {TestRefunds._req_id} not in pending list"

    def test_list_forbidden_for_non_owner(self, non_owner_session):
        r = non_owner_session.get(f"{BASE_URL}/api/refund-requests?status=pending")
        assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text}"

    def test_deny_refund_and_appears_in_denied(self, qa_session):
        assert TestRefunds._req_id, "no refund id from earlier test"
        r = qa_session.post(
            f"{BASE_URL}/api/refund-requests/{TestRefunds._req_id}/deny",
            json={"adminNotes": "TEST denial by pytest"})
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True
        r2 = qa_session.get(f"{BASE_URL}/api/refund-requests?status=denied")
        assert r2.status_code == 200
        assert any(row["id"] == TestRefunds._req_id for row in r2.json()), \
            "denied refund not in denied list"


# --------------------- GDPR export ---------------------

class TestExport:
    def test_export_zip_shape(self, qa_session):
        r = qa_session.get(f"{BASE_URL}/api/auth/me/export", timeout=60)
        assert r.status_code == 200, f"export failed: {r.status_code} {r.text[:400]}"
        buf = io.BytesIO(r.content)
        with zipfile.ZipFile(buf, "r") as zf:
            names = zf.namelist()
            assert "README.txt" in names
            assert "account/profile.json" in names
            assert "account/subscription.json" in names
            assert "account/memberships.json" in names
            # Per-org subfolder
            org_folder_prefix = f"organizations/{ORG_ID}/"
            org_files_expected = ["organization.json", "opportunities.json",
                                  "proposals.json", "venture_docs.json",
                                  "org_files.json", "audit_log.json"]
            for f in org_files_expected:
                assert org_folder_prefix + f in names, \
                    f"missing {org_folder_prefix + f} in zip; got {names[:40]}"
            # sanity: profile.json parses and has an email
            profile = json.loads(zf.read("account/profile.json"))
            assert profile.get("email") == QA_EMAIL


# --------------------- Stripe webhook signature ---------------------

class TestWebhookSignature:
    def test_invalid_signature_returns_400(self):
        # No auth headers needed for webhook endpoint
        r = requests.post(f"{BASE_URL}/api/stripe/webhook",
                          data=b'{"type":"noop","data":{"object":{}}}',
                          headers={"stripe-signature": "t=1,v1=bogussignature",
                                   "Content-Type": "application/json"},
                          timeout=15)
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"
        assert "invalid signature" in (r.json().get("detail") or "").lower()
