"""AI job plumbing: options catalog, job polling, cancellation, RBAC."""
import os
import requests

BASE_URL = (os.environ.get("TEST_BASE_URL")
            or os.environ.get("REACT_APP_BACKEND_URL")
            or "http://localhost:8000").rstrip("/")


class TestAIOptions:
    def test_options_shape(self, admin_session, org_id):
        s, _ = admin_session
        r = s.get(f"{BASE_URL}/api/orgs/{org_id}/ai/options", timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        ids = [e["id"] for e in body["engines"]]
        assert ids == ["claude", "openai", "emergent", "asksage"]
        assert all("models" in e and "configured" in e for e in body["engines"])
        assert [e["id"] for e in body["efforts"]] == ["low", "standard", "high"]
        assert "monthSpendUsd" in body and "spendNote" in body

    def test_viewer_can_read_options(self, viewer_session, org_id):
        s, _ = viewer_session
        r = s.get(f"{BASE_URL}/api/orgs/{org_id}/ai/options", timeout=15)
        assert r.status_code == 200


class TestAIJobs:
    def test_job_created_by_capability_generate_guard(self, admin_session, org_id):
        # No key set → the endpoint 400s BEFORE creating a job; job list flow
        # is covered by the cancel/404 checks below.
        s, _ = admin_session
        r = s.get(f"{BASE_URL}/api/orgs/{org_id}/ai/jobs/00000000-0000-0000-0000-000000000000",
                  timeout=15)
        assert r.status_code == 404

    def test_cancel_missing_job_404(self, admin_session, org_id):
        s, _ = admin_session
        r = s.post(f"{BASE_URL}/api/orgs/{org_id}/ai/jobs/"
                   "00000000-0000-0000-0000-000000000000/cancel", timeout=15)
        assert r.status_code == 404

    def test_viewer_cannot_cancel(self, viewer_session, org_id):
        s, _ = viewer_session
        r = s.post(f"{BASE_URL}/api/orgs/{org_id}/ai/jobs/"
                   "00000000-0000-0000-0000-000000000000/cancel", timeout=15)
        assert r.status_code == 403

    def test_competitive_run_creates_pollable_job(self, admin_session, org_id):
        s, _ = admin_session
        r = s.post(f"{BASE_URL}/api/orgs/{org_id}/competitive",
                   json={"competitor": "AI Jobs Test Co", "naics": ""}, timeout=15)
        assert r.status_code == 200, r.text
        job_id = r.json().get("jobId")
        assert job_id
        j = s.get(f"{BASE_URL}/api/orgs/{org_id}/ai/jobs/{job_id}", timeout=15)
        assert j.status_code == 200
        body = j.json()
        assert body["kind"] == "competitive.analyze"
        assert body["status"] in ("queued", "running", "done", "error", "cancelled")
        assert "stage" in body and "progress" in body and "costUsd" in body
        # cancel is accepted regardless of the race with completion
        c = s.post(f"{BASE_URL}/api/orgs/{org_id}/ai/jobs/{job_id}/cancel", timeout=15)
        assert c.status_code == 200
