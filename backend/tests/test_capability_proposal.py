"""Tests: proposed-capability + proposal-package endpoints.

AI generation needs a real Anthropic key, so these tests cover guard paths,
CRUD, and the export pipeline (docx/xlsx/pptx/zip) with injected content.
A fresh org is created per session for isolation (no API keys set)."""
import os
import uuid
import pytest
import requests

BASE_URL = (os.environ.get("TEST_BASE_URL")
            or os.environ.get("REACT_APP_BACKEND_URL")
            or "http://localhost:8000").rstrip("/")

DOCX_MAGIC = b"PK\x03\x04"  # OOXML/zip container


@pytest.fixture(scope="module")
def fresh_org(admin_session):
    s, _ = admin_session
    r = s.post(f"{BASE_URL}/api/orgs",
               json={"name": f"CapTest Org {uuid.uuid4().hex[:6]}",
                     "naics": ["541715"], "keywords": ["autonomy"], "certifyAor": True}, timeout=15)
    assert r.status_code == 200, r.text
    org_id = r.json()["id"]
    # Proposal/capability creation is capture_manager-only: bring in the demo
    # capture lead (existing user -> membership becomes active immediately).
    inv = s.post(f"{BASE_URL}/api/orgs/{org_id}/members/invite",
                 json={"email": "editor@govcon.io", "role": "capture_manager"}, timeout=15)
    assert inv.status_code == 200, inv.text
    return org_id


@pytest.fixture(scope="module")
def cm_session(editor_session, fresh_org):
    """The capture-manager session for the fresh org."""
    return editor_session


@pytest.fixture(scope="module")
def opp_id(admin_session, fresh_org):
    s, _ = admin_session
    r = s.post(f"{BASE_URL}/api/orgs/{fresh_org}/opportunities",
               json={"title": "Capability Test Opp", "solNumber": "CAP-TEST-001",
                     "agency": "USAF", "vehicle": "SBIR", "setAside": "Total Small Business",
                     "ceiling": 1500000}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["id"]


SAMPLE_CONTENT = {
    "title": "Autonomous Test Capability",
    "abstract": "A test abstract for the proposed capability.",
    "executiveSummary": "## Summary\n\nThis is a **test** executive summary.\n\n- Point one\n- Point two",
    "keywords": ["autonomy", "testing"],
    "charts": [{"type": "pie", "title": "Budget Mix",
                "data": [{"name": "Labor", "value": 60}, {"name": "Materials", "value": 40}]}],
    "tables": [{"title": "Traceability", "headers": ["Req", "Response"],
                "rows": [["R1", "Section 2.1"]]}],
    "sow": {"scope": "Test scope paragraph.",
            "tasks": [{"number": "1.0", "title": "Design", "description": "Design the system.",
                       "deliverables": ["SDD"]}]},
    "scheduleMonths": 12,
    "wbs": [{"code": "1.1", "task": "Design", "owner": "Lead Engineer",
             "startMonth": 1, "endMonth": 3}],
    "budget": {"ceiling": 1500000,
               "items": [{"category": "Direct Labor", "description": "Eng team", "cost": 900000},
                         {"category": "Materials", "description": "Prototype parts", "cost": 300000}],
               "narrative": "Estimated bottom-up."},
}


class TestCapability:
    def test_get_none_initially(self, admin_session, fresh_org, opp_id):
        s, _ = admin_session
        r = s.get(f"{BASE_URL}/api/orgs/{fresh_org}/opportunities/{opp_id}/capability", timeout=15)
        assert r.status_code == 200
        assert r.json() is None

    def test_generate_requires_api_key(self, cm_session, fresh_org, opp_id):
        s, _ = cm_session
        r = s.post(f"{BASE_URL}/api/orgs/{fresh_org}/opportunities/{opp_id}/capability/generate",
                   timeout=15)
        assert r.status_code == 400
        assert "Anthropic" in r.json().get("detail", "")

    def test_admin_blocked_from_generate(self, admin_session, fresh_org, opp_id):
        # Strict rule: only the capture manager creates capability work.
        s, _ = admin_session
        r = s.post(f"{BASE_URL}/api/orgs/{fresh_org}/opportunities/{opp_id}/capability/generate",
                   timeout=15)
        assert r.status_code == 403
        assert "capture_manager" in r.json().get("detail", "")

    def test_edit_without_capability_404(self, admin_session, fresh_org, opp_id):
        s, _ = admin_session
        r = s.put(f"{BASE_URL}/api/orgs/{fresh_org}/opportunities/{opp_id}/capability",
                  json={"content": SAMPLE_CONTENT}, timeout=15)
        assert r.status_code == 404

    def test_viewer_blocked_from_generate(self, viewer_session, admin_session, fresh_org, opp_id):
        # viewer is not a member of the fresh org -> 403 either way
        s, _ = viewer_session
        r = s.post(f"{BASE_URL}/api/orgs/{fresh_org}/opportunities/{opp_id}/capability/generate",
                   timeout=15)
        assert r.status_code == 403


class TestProposalPackage:
    def test_admin_blocked_from_create_package(self, admin_session, fresh_org, opp_id):
        s, _ = admin_session
        r = s.post(f"{BASE_URL}/api/orgs/{fresh_org}/opportunities/{opp_id}/proposal", timeout=15)
        assert r.status_code == 403

    def test_create_package_sbir_volume_set(self, cm_session, fresh_org, opp_id):
        s, _ = cm_session
        r = s.post(f"{BASE_URL}/api/orgs/{fresh_org}/opportunities/{opp_id}/proposal", timeout=15)
        assert r.status_code == 200, r.text
        docs = r.json()["documents"]
        types = {d["docType"] for d in docs}
        # SBIR set
        assert "technical_volume" in types
        assert "commercialization_plan" in types
        assert "cost_volume" in types
        assert "briefing_deck" in types
        assert all(d["status"] == "empty" for d in docs)

    def test_create_is_idempotent(self, cm_session, fresh_org, opp_id):
        s, _ = cm_session
        r1 = s.post(f"{BASE_URL}/api/orgs/{fresh_org}/opportunities/{opp_id}/proposal", timeout=15)
        r2 = s.post(f"{BASE_URL}/api/orgs/{fresh_org}/opportunities/{opp_id}/proposal", timeout=15)
        assert r1.json()["id"] == r2.json()["id"]
        assert len(r1.json()["documents"]) == len(r2.json()["documents"])

    def test_draft_requires_api_key(self, admin_session, fresh_org, opp_id):
        s, _ = admin_session
        prop = s.get(f"{BASE_URL}/api/orgs/{fresh_org}/opportunities/{opp_id}/proposal",
                     timeout=15).json()
        doc = prop["documents"][0]
        r = s.post(f"{BASE_URL}/api/orgs/{fresh_org}/opportunities/{opp_id}"
                   f"/proposal/documents/{doc['id']}/draft",
                   json={"engine": "claude"}, timeout=15)
        assert r.status_code == 400
        assert "Anthropic" in r.json().get("detail", "")

    def test_download_empty_doc_400(self, admin_session, fresh_org, opp_id):
        s, _ = admin_session
        prop = s.get(f"{BASE_URL}/api/orgs/{fresh_org}/opportunities/{opp_id}/proposal",
                     timeout=15).json()
        doc = prop["documents"][0]
        r = s.get(f"{BASE_URL}/api/orgs/{fresh_org}/opportunities/{opp_id}"
                  f"/proposal/documents/{doc['id']}/download", timeout=15)
        assert r.status_code == 400

    def test_edit_finalize_download_docx(self, admin_session, fresh_org, opp_id):
        s, _ = admin_session
        prop = s.get(f"{BASE_URL}/api/orgs/{fresh_org}/opportunities/{opp_id}/proposal",
                     timeout=15).json()
        doc = next(d for d in prop["documents"] if d["fmt"] == "docx")
        md = "# Technical Volume\n\n## Approach\n\nWe **deliver**.\n\n| Task | Owner |\n|---|---|\n| 1.0 | PM |\n\n- Bullet one\n- Bullet two"
        u = s.put(f"{BASE_URL}/api/orgs/{fresh_org}/opportunities/{opp_id}"
                  f"/proposal/documents/{doc['id']}",
                  json={"contentMd": md}, timeout=15)
        assert u.status_code == 200, u.text
        assert u.json()["status"] == "edited"
        # finalize
        f = s.post(f"{BASE_URL}/api/orgs/{fresh_org}/opportunities/{opp_id}"
                   f"/proposal/documents/{doc['id']}/finalize", timeout=15)
        assert f.status_code == 200
        assert f.json()["status"] == "final"
        # download
        d = s.get(f"{BASE_URL}/api/orgs/{fresh_org}/opportunities/{opp_id}"
                  f"/proposal/documents/{doc['id']}/download", timeout=30)
        assert d.status_code == 200, d.text
        assert d.content[:4] == DOCX_MAGIC
        assert "wordprocessingml" in d.headers.get("content-type", "")

    def test_edit_download_xlsx(self, admin_session, fresh_org, opp_id):
        s, _ = admin_session
        prop = s.get(f"{BASE_URL}/api/orgs/{fresh_org}/opportunities/{opp_id}/proposal",
                     timeout=15).json()
        doc = next(d for d in prop["documents"] if d["fmt"] == "xlsx")
        payload = {"contentJson": {
            "currency": "USD",
            "rows": [{"category": "Direct Labor", "item": "PM", "basis": "6 FTE-mo", "cost": 120000},
                     {"category": "Travel", "item": "Kickoff", "basis": "2 trips", "cost": 6000}],
            "narrative": "Bottom-up estimate.",
            "assumptions": ["FY26 rates"],
        }}
        u = s.put(f"{BASE_URL}/api/orgs/{fresh_org}/opportunities/{opp_id}"
                  f"/proposal/documents/{doc['id']}", json=payload, timeout=15)
        assert u.status_code == 200, u.text
        d = s.get(f"{BASE_URL}/api/orgs/{fresh_org}/opportunities/{opp_id}"
                  f"/proposal/documents/{doc['id']}/download", timeout=30)
        assert d.status_code == 200
        assert d.content[:4] == DOCX_MAGIC
        assert "spreadsheetml" in d.headers.get("content-type", "")

    def test_edit_download_pptx(self, admin_session, fresh_org, opp_id):
        s, _ = admin_session
        prop = s.get(f"{BASE_URL}/api/orgs/{fresh_org}/opportunities/{opp_id}/proposal",
                     timeout=15).json()
        doc = next(d for d in prop["documents"] if d["fmt"] == "pptx")
        payload = {"contentJson": {"slides": [
            {"title": "Autonomous Test Capability", "bullets": ["One-line tagline"]},
            {"title": "The Problem", "bullets": ["Pain 1", "Pain 2"], "notes": "Speak slowly."},
        ]}}
        u = s.put(f"{BASE_URL}/api/orgs/{fresh_org}/opportunities/{opp_id}"
                  f"/proposal/documents/{doc['id']}", json=payload, timeout=15)
        assert u.status_code == 200, u.text
        d = s.get(f"{BASE_URL}/api/orgs/{fresh_org}/opportunities/{opp_id}"
                  f"/proposal/documents/{doc['id']}/download", timeout=30)
        assert d.status_code == 200
        assert d.content[:4] == DOCX_MAGIC
        assert "presentationml" in d.headers.get("content-type", "")

    def test_download_zip_package(self, admin_session, fresh_org, opp_id):
        s, _ = admin_session
        r = s.get(f"{BASE_URL}/api/orgs/{fresh_org}/opportunities/{opp_id}"
                  f"/proposal/download-zip", timeout=60)
        assert r.status_code == 200, r.text
        assert r.content[:4] == DOCX_MAGIC  # zip magic
        assert "zip" in r.headers.get("content-type", "")
        assert len(r.content) > 1000


class TestSubmission:
    def test_cm_blocked_from_submit(self, cm_session, fresh_org, opp_id):
        s, _ = cm_session
        r = s.post(f"{BASE_URL}/api/orgs/{fresh_org}/opportunities/{opp_id}/proposal/submit",
                   timeout=15)
        assert r.status_code == 403

    def test_admin_submits_and_stage_updates(self, admin_session, fresh_org, opp_id):
        s, _ = admin_session
        r = s.post(f"{BASE_URL}/api/orgs/{fresh_org}/opportunities/{opp_id}/proposal/submit",
                   timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "submitted"
        # double-submit blocked
        again = s.post(f"{BASE_URL}/api/orgs/{fresh_org}/opportunities/{opp_id}/proposal/submit",
                       timeout=15)
        assert again.status_code == 400
        # opportunity stage moved to Submitted
        opp = s.get(f"{BASE_URL}/api/orgs/{fresh_org}/opportunities/{opp_id}", timeout=15).json()
        assert opp["stage"] == "Submitted"
