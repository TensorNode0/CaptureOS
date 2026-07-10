"""Competitive-analysis endpoints: validation, RBAC, and report lifecycle.
(External calls happen in a background task and are not awaited by tests.)"""
import os
import requests

BASE_URL = (os.environ.get("TEST_BASE_URL")
            or os.environ.get("REACT_APP_BACKEND_URL")
            or "http://localhost:8000").rstrip("/")


class TestCompetitive:
    def test_list_initially_empty_shape(self, admin_session, org_id):
        s, _ = admin_session
        r = s.get(f"{BASE_URL}/api/orgs/{org_id}/competitive", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_naics_must_be_numeric(self, admin_session, org_id):
        s, _ = admin_session
        r = s.post(f"{BASE_URL}/api/orgs/{org_id}/competitive",
                   json={"competitor": "Acme Defense", "naics": "not-a-code"}, timeout=15)
        assert r.status_code == 400

    def test_competitor_min_length(self, admin_session, org_id):
        s, _ = admin_session
        r = s.post(f"{BASE_URL}/api/orgs/{org_id}/competitive",
                   json={"competitor": "A"}, timeout=15)
        assert r.status_code == 422  # pydantic min_length

    def test_create_returns_running_report(self, admin_session, org_id):
        s, _ = admin_session
        r = s.post(f"{BASE_URL}/api/orgs/{org_id}/competitive",
                   json={"competitor": "QA Test Competitor Inc", "naics": "541715"},
                   timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "running" and body["reportId"]
        # report row exists and is fetchable regardless of background outcome
        rep = s.get(f"{BASE_URL}/api/orgs/{org_id}/competitive/{body['reportId']}",
                    timeout=15)
        assert rep.status_code == 200
        assert rep.json()["competitor"] == "QA Test Competitor Inc"

    def test_viewer_cannot_start_analysis(self, viewer_session, org_id):
        s, _ = viewer_session
        r = s.post(f"{BASE_URL}/api/orgs/{org_id}/competitive",
                   json={"competitor": "Acme Defense"}, timeout=15)
        assert r.status_code == 403

    def test_viewer_can_read_reports(self, viewer_session, org_id):
        s, _ = viewer_session
        r = s.get(f"{BASE_URL}/api/orgs/{org_id}/competitive", timeout=15)
        assert r.status_code == 200
