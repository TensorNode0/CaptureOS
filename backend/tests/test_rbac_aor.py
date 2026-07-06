"""AOR certification, domain-based signup routing, functional roles,
join-request approval, and entity-info edit grants."""
import os
import uuid
import pytest
import requests

BASE_URL = (os.environ.get("TEST_BASE_URL")
            or os.environ.get("REACT_APP_BACKEND_URL")
            or "http://localhost:8000").rstrip("/")

DOMAIN = f"d{uuid.uuid4().hex[:10]}.example"


def _register(email, name="Test User", password="Passw0rd!xx"):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/register",
               json={"email": email, "name": name, "password": password}, timeout=15)
    assert r.status_code == 200, r.text
    # requests won't send Secure cookies over plain http — use Bearer instead
    token = s.cookies.get("access_token")
    if token:
        s.headers["Authorization"] = f"Bearer {token}"
    return s, r.json()


@pytest.fixture(scope="module")
def alice():
    return _register(f"alice@{DOMAIN}", "Alice AOR")


@pytest.fixture(scope="module")
def bob():
    return _register(f"bob@{DOMAIN}", "Bob Writer")


@pytest.fixture(scope="module")
def alice_org(alice):
    s, _ = alice
    r = s.post(f"{BASE_URL}/api/orgs",
               json={"name": f"Acme Federal {DOMAIN[:6]}", "naics": ["541715"],
                     "keywords": ["autonomy"], "certifyAor": True}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()


class TestAorCertification:
    def test_create_org_requires_aor_certification(self, alice):
        s, _ = alice
        r = s.post(f"{BASE_URL}/api/orgs",
                   json={"name": "NoCert Inc", "certifyAor": False}, timeout=15)
        assert r.status_code == 400
        assert "Authorized" in r.json()["detail"]

    def test_first_domain_user_becomes_admin(self, alice_org):
        assert alice_org["role"] == "admin"
        assert alice_org["domain"] == DOMAIN

    def test_domain_status_shows_claimed_org(self, alice, alice_org):
        s, _ = alice
        r = s.get(f"{BASE_URL}/api/orgs/domain-status", timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert body["publicDomain"] is False
        assert body["org"]["id"] == alice_org["id"]


class TestDomainJoinFlow:
    def test_bob_cannot_create_second_org_for_domain(self, bob, alice_org):
        s, _ = bob
        r = s.post(f"{BASE_URL}/api/orgs",
                   json={"name": "Shadow Acme", "certifyAor": True}, timeout=15)
        assert r.status_code == 409
        assert "join" in r.json()["detail"].lower()

    def test_bob_requests_to_join(self, bob, alice_org):
        s, _ = bob
        r = s.post(f"{BASE_URL}/api/orgs/{alice_org['id']}/join-request", timeout=15)
        assert r.status_code == 200
        assert r.json()["status"] == "pending"

    def test_pending_bob_has_no_access(self, bob, alice_org):
        s, _ = bob
        r = s.get(f"{BASE_URL}/api/orgs/{alice_org['id']}/opportunities", timeout=15)
        assert r.status_code == 403
        me = s.get(f"{BASE_URL}/api/auth/me", timeout=15).json()
        assert any(o["id"] == alice_org["id"] for o in me.get("pendingOrganizations", []))

    def test_admin_approves_bob_as_proposal_writer(self, alice, bob, alice_org):
        sa, _ = alice
        members = sa.get(f"{BASE_URL}/api/orgs/{alice_org['id']}/members", timeout=15).json()
        pending = next(m for m in members if m["status"] == "pending")
        r = sa.post(f"{BASE_URL}/api/orgs/{alice_org['id']}/members/{pending['id']}/approve",
                    json={"role": "proposal_writer"}, timeout=15)
        assert r.status_code == 200, r.text
        sb, _ = bob
        me = sb.get(f"{BASE_URL}/api/auth/me", timeout=15).json()
        org = next(o for o in me["organizations"] if o["id"] == alice_org["id"])
        assert org["role"] == "proposal_writer"

    def test_writer_can_contribute_but_not_create_proposals(self, bob, alice_org):
        s, _ = bob
        opp = s.post(f"{BASE_URL}/api/orgs/{alice_org['id']}/opportunities",
                     json={"title": "Writer Opp", "vehicle": "RFP"}, timeout=15)
        assert opp.status_code == 200, opp.text  # contributor rank can add opps
        r = s.post(f"{BASE_URL}/api/orgs/{alice_org['id']}/opportunities/"
                   f"{opp.json()['id']}/proposal", timeout=15)
        assert r.status_code == 403  # only the capture manager creates proposals


class TestEntityEditGrants:
    """In the demo org, editor@govcon.io is the capture manager."""

    def _profile_payload(self, s, org_id):
        p = s.get(f"{BASE_URL}/api/orgs/{org_id}/profile", timeout=15).json()
        return {
            "uei": p.get("uei") or "", "cage": p.get("cage") or "",
            "samActive": bool(p.get("samActive")), "isSmall": bool(p.get("isSmall", True)),
            "certs": p.get("certs") or {}, "cmmcLevel": p.get("cmmcLevel") or "Level 1",
            "sprsScore": p.get("sprsScore"), "sizeNote": p.get("sizeNote") or "",
            "notes": p.get("notes") or "", "capabilities": p.get("capabilities") or "",
            "pastPerformance": p.get("pastPerformance") or "",
            "techFocus": p.get("techFocus") or [],
            "differentiators": p.get("differentiators") or "",
            "commercialization": p.get("commercialization") or "",
            "clearances": p.get("clearances") or "",
        }

    def test_cm_cannot_edit_entity_info(self, editor_session, org_id):
        s, _ = editor_session
        payload = self._profile_payload(s, org_id)
        r = s.put(f"{BASE_URL}/api/orgs/{org_id}/profile", json=payload, timeout=15)
        assert r.status_code == 403
        assert "Request edit access" in r.json()["detail"]

    def test_cm_requests_deny_then_approve(self, editor_session, admin_session, org_id):
        se, _ = editor_session
        sa, _ = admin_session
        # request -> deny
        r = se.post(f"{BASE_URL}/api/orgs/{org_id}/profile/edit-request", timeout=15)
        assert r.status_code == 200
        reqs = sa.get(f"{BASE_URL}/api/orgs/{org_id}/profile/edit-requests", timeout=15).json()
        pending = next(x for x in reqs if x["status"] == "pending")
        d = sa.post(f"{BASE_URL}/api/orgs/{org_id}/profile/edit-requests/{pending['id']}/decide",
                    json={"approve": False}, timeout=15)
        assert d.status_code == 200 and d.json()["status"] == "denied"
        # still blocked
        payload = self._profile_payload(se, org_id)
        assert se.put(f"{BASE_URL}/api/orgs/{org_id}/profile",
                      json=payload, timeout=15).status_code == 403
        # re-request -> approve -> 24h grant
        se.post(f"{BASE_URL}/api/orgs/{org_id}/profile/edit-request", timeout=15)
        reqs = sa.get(f"{BASE_URL}/api/orgs/{org_id}/profile/edit-requests", timeout=15).json()
        pending = next(x for x in reqs if x["status"] == "pending")
        a = sa.post(f"{BASE_URL}/api/orgs/{org_id}/profile/edit-requests/{pending['id']}/decide",
                    json={"approve": True}, timeout=15)
        assert a.status_code == 200 and a.json()["status"] == "approved"
        prof = se.get(f"{BASE_URL}/api/orgs/{org_id}/profile", timeout=15).json()
        assert prof["canEdit"] is True
        u = se.put(f"{BASE_URL}/api/orgs/{org_id}/profile", json=payload, timeout=15)
        assert u.status_code == 200, u.text

    def test_viewer_cannot_request_edit(self, viewer_session, org_id):
        s, _ = viewer_session
        r = s.post(f"{BASE_URL}/api/orgs/{org_id}/profile/edit-request", timeout=15)
        assert r.status_code == 403
