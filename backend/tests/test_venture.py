"""Venture workspace endpoints: doc kinds (incl. web-search scans) and the
from-program application-form generator (template fallback without a key)."""
import os
import requests

BASE_URL = (os.environ.get("TEST_BASE_URL")
            or os.environ.get("REACT_APP_BACKEND_URL")
            or "http://localhost:8000").rstrip("/")


class TestVentureDocs:
    def test_scan_kinds_accepted(self, admin_session, org_id):
        s, _ = admin_session
        for kind in ("investor_scan", "accelerator_scan"):
            r = s.post(f"{BASE_URL}/api/orgs/{org_id}/venture-docs",
                       json={"kind": kind}, timeout=15)
            assert r.status_code == 200, r.text
            assert r.json()["kind"] == kind

    def test_unknown_kind_rejected(self, admin_session, org_id):
        s, _ = admin_session
        r = s.post(f"{BASE_URL}/api/orgs/{org_id}/venture-docs",
                   json={"kind": "world_domination_plan"}, timeout=15)
        assert r.status_code == 400


class TestFromProgram:
    def test_without_key_returns_template_doc(self, admin_session, org_id):
        s, _ = admin_session
        r = s.post(f"{BASE_URL}/api/orgs/{org_id}/venture-docs/from-program",
                   json={"name": "QA Test Accelerator"}, timeout=30)
        assert r.status_code == 200, r.text
        doc = r.json()
        assert doc["kind"] == "accelerator_application"
        assert doc["target"] == "QA Test Accelerator"
        # no Anthropic key in the test org → generic template scaffold
        assert "[FILL]" in doc["contentMd"]
        assert "QA Test Accelerator" in doc["contentMd"]

    def test_bad_url_scheme_rejected(self, admin_session, org_id):
        s, _ = admin_session
        r = s.post(f"{BASE_URL}/api/orgs/{org_id}/venture-docs/from-program",
                   json={"name": "QA Test Accelerator",
                         "url": "ftp://example.com/apply"}, timeout=15)
        assert r.status_code == 400

    def test_name_min_length(self, admin_session, org_id):
        s, _ = admin_session
        r = s.post(f"{BASE_URL}/api/orgs/{org_id}/venture-docs/from-program",
                   json={"name": "Q"}, timeout=15)
        assert r.status_code == 422  # pydantic min_length

    def test_viewer_cannot_create(self, viewer_session, org_id):
        s, _ = viewer_session
        r = s.post(f"{BASE_URL}/api/orgs/{org_id}/venture-docs/from-program",
                   json={"name": "QA Test Accelerator"}, timeout=15)
        assert r.status_code == 403
