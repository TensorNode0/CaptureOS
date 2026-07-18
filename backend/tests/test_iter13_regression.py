"""Iteration 13 regression: verify the 3 specific fixes from iter_12.

- refund create/deny no longer 500 (extra sanity, dedicated REGRESSION_ row)
- /approve with fake id returns 404 (never 500)
- /me/export ZIP profile.json has NEITHER password_hash NOR passwordHash keys
- /refund-requests?status=denied returned row includes decidedAt
- Cleanup: DELETE all REGRESSION_ rows for QA at teardown.
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
    # Teardown: sweep any REGRESSION_ refund_requests rows still pending for QA
    try:
        pending = s.get(f"{BASE_URL}/api/refund-requests?status=pending").json()
        for row in pending or []:
            if (row.get("reason") or "").startswith("REGRESSION_"):
                s.post(f"{BASE_URL}/api/refund-requests/{row['id']}/deny",
                       json={"adminNotes": "REGRESSION cleanup"})
    except Exception:
        pass


class TestRefundNoMore500:
    _req_id = None

    def test_submit_refund_regression(self, qa):
        r = qa.post(f"{BASE_URL}/api/refund-requests",
                    json={"reason": "REGRESSION_test1"})
        assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert data.get("ok") is True, data
        rid = data.get("requestId")
        assert rid, f"requestId missing: {data}"
        TestRefundNoMore500._req_id = rid

    def test_pending_contains_the_row(self, qa):
        r = qa.get(f"{BASE_URL}/api/refund-requests?status=pending")
        assert r.status_code == 200
        rows = r.json()
        assert any(row["id"] == TestRefundNoMore500._req_id for row in rows), \
            "newly created refund not in pending"

    def test_deny_no_more_500(self, qa):
        rid = TestRefundNoMore500._req_id
        assert rid
        r = qa.post(f"{BASE_URL}/api/refund-requests/{rid}/deny",
                    json={"adminNotes": "noted"})
        assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text}"
        assert r.json().get("ok") is True

    def test_denied_list_has_decidedAt(self, qa):
        rid = TestRefundNoMore500._req_id
        r = qa.get(f"{BASE_URL}/api/refund-requests?status=denied")
        assert r.status_code == 200
        rows = r.json()
        match = next((row for row in rows if row["id"] == rid), None)
        assert match is not None, "denied row not found"
        # decidedAt may be camelCase or snake_case
        decided = match.get("decidedAt") or match.get("decided_at")
        assert decided, f"decidedAt missing on denied row: {match}"

    def test_approve_fake_id_returns_404_not_500(self, qa):
        fake_id = str(uuid.uuid4())
        r = qa.post(f"{BASE_URL}/api/refund-requests/{fake_id}/approve", json={})
        assert r.status_code == 404, f"expected 404, got {r.status_code}: {r.text}"


class TestExportRedaction:
    def test_export_zip_redacts_password_hash(self, qa):
        r = qa.get(f"{BASE_URL}/api/auth/me/export", timeout=60)
        assert r.status_code == 200
        with zipfile.ZipFile(io.BytesIO(r.content), "r") as zf:
            prof = json.loads(zf.read("account/profile.json"))
        assert "password_hash" not in prof, f"password_hash leaked: keys={list(prof)}"
        assert "passwordHash" not in prof, f"passwordHash leaked: keys={list(prof)}"
        # sanity: email still present
        assert prof.get("email") == QA_EMAIL
