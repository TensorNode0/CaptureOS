"""Subcontractor role: rank-0 members see ONLY explicitly granted proposal
resources, with read/write enforced server-side."""
import os
import uuid
import pytest
import requests

BASE_URL = (os.environ.get("TEST_BASE_URL")
            or os.environ.get("REACT_APP_BACKEND_URL")
            or "http://localhost:8000").rstrip("/")


def _register(email, name="Sub C. Ontractor", password=None):
    """Auth is owned by Supabase; test-login mints a token and auto-provisions
    the profile (replaces the old register flow)."""
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/test-login",
               json={"email": email, "name": name}, timeout=15)
    assert r.status_code == 200, r.text
    me = r.json()
    s.headers["Authorization"] = f"Bearer {me['accessToken']}"
    return s, me


@pytest.fixture(scope="module")
def sub_user():
    return _register(f"sub{uuid.uuid4().hex[:8]}@subco.example")


@pytest.fixture(scope="module")
def sub_membership(admin_session, sub_user, org_id):
    sa, _ = admin_session
    _, sub_me = sub_user
    r = sa.post(f"{BASE_URL}/api/orgs/{org_id}/members/invite",
                json={"email": sub_me["email"], "role": "subcontractor"}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["membershipId"]


@pytest.fixture(scope="module")
def shared_doc(editor_session, org_id):
    """An opportunity + proposal doc to share (capture manager creates)."""
    se, _ = editor_session
    opp = se.post(f"{BASE_URL}/api/orgs/{org_id}/opportunities",
                  json={"title": "Sub Share Opp", "vehicle": "RFP"}, timeout=15).json()
    prop = se.post(f"{BASE_URL}/api/orgs/{org_id}/opportunities/{opp['id']}/proposal",
                   timeout=15).json()
    doc = next(d for d in prop["documents"] if d["fmt"] == "docx")
    return opp, doc


class TestSubcontractor:
    def test_blocked_from_app_endpoints(self, sub_user, sub_membership, org_id):
        s, _ = sub_user
        assert s.get(f"{BASE_URL}/api/orgs/{org_id}/opportunities",
                     timeout=15).status_code == 403
        assert s.get(f"{BASE_URL}/api/orgs/{org_id}/proposals",
                     timeout=15).status_code == 403
        assert s.get(f"{BASE_URL}/api/orgs/{org_id}/secrets/status",
                     timeout=15).status_code == 403

    def test_grant_read_then_enforce(self, admin_session, sub_user, sub_membership,
                                     shared_doc, org_id):
        sa, _ = admin_session
        s, _ = sub_user
        opp, doc = shared_doc
        g = sa.put(f"{BASE_URL}/api/orgs/{org_id}/members/{sub_membership}/grants",
                   json={"opportunityId": opp["id"], "grants": [
                       {"resourceType": "proposal_doc", "resourceId": doc["id"],
                        "access": "read"}]}, timeout=15)
        assert g.status_code == 200, g.text

        shared = s.get(f"{BASE_URL}/api/orgs/{org_id}/shared", timeout=15)
        assert shared.status_code == 200
        items = [i for i in shared.json() if i["resourceType"] == "proposal_doc"]
        assert len(items) == 1 and items[0]["access"] == "read"
        assert items[0]["opportunity"]["title"] == "Sub Share Opp"

        upd = s.put(f"{BASE_URL}/api/orgs/{org_id}/shared/{items[0]['grantId']}",
                    json={"contentMd": "# nope"}, timeout=15)
        assert upd.status_code == 403  # read-only share

    def test_write_grant_updates_live_doc(self, admin_session, editor_session,
                                          sub_user, sub_membership, shared_doc, org_id):
        sa, _ = admin_session
        se, _ = editor_session
        s, _ = sub_user
        opp, doc = shared_doc
        sa.put(f"{BASE_URL}/api/orgs/{org_id}/members/{sub_membership}/grants",
               json={"opportunityId": opp["id"], "grants": [
                   {"resourceType": "proposal_doc", "resourceId": doc["id"],
                    "access": "write"}]}, timeout=15)
        gid = next(i["grantId"] for i in
                   s.get(f"{BASE_URL}/api/orgs/{org_id}/shared", timeout=15).json()
                   if i["resourceType"] == "proposal_doc")
        ok = s.put(f"{BASE_URL}/api/orgs/{org_id}/shared/{gid}",
                   json={"contentMd": "# Subcontractor section\n\nOur part."}, timeout=15)
        assert ok.status_code == 200, ok.text
        live = se.get(f"{BASE_URL}/api/orgs/{org_id}/opportunities/{opp['id']}/proposal",
                      timeout=15).json()
        live_doc = next(d for d in live["documents"] if d["id"] == doc["id"])
        assert "Subcontractor section" in live_doc["contentMd"]
        assert live_doc["status"] == "edited"

    def test_non_subcontractor_cannot_use_shared(self, admin_session, org_id):
        s, _ = admin_session
        assert s.get(f"{BASE_URL}/api/orgs/{org_id}/shared",
                     timeout=15).status_code == 403

    def test_invalid_section_rejected(self, admin_session, sub_membership,
                                      shared_doc, org_id):
        sa, _ = admin_session
        opp, _ = shared_doc
        r = sa.put(f"{BASE_URL}/api/orgs/{org_id}/members/{sub_membership}/grants",
                   json={"opportunityId": opp["id"], "grants": [
                       {"resourceType": "capability_section", "resourceId": "bogus",
                        "access": "read"}]}, timeout=15)
        assert r.status_code == 400
