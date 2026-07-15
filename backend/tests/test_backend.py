"""CaptureOS — Backend API tests (run against a local stack; see qa/)."""
import os
import time
import uuid
import requests
import pytest

BASE_URL = (os.environ.get("TEST_BASE_URL")
            or os.environ.get("REACT_APP_BACKEND_URL")
            or "http://localhost:8000").rstrip("/")


# ---------------- Health ----------------
class TestHealth:
    def test_health(self):
        r = requests.get(f"{BASE_URL}/api/health", timeout=15)
        assert r.status_code == 200
        assert r.json().get("status") == "ok"


# ---------------- Auth (Supabase Auth) ----------------
class TestAuth:
    def test_session_admin(self, admin_session):
        s, me = admin_session
        assert me["email"] == "admin@govcon.io"
        assert any(o["role"] in ("owner", "admin") for o in me["organizations"])
        # bearer token drives the session (no server-set auth cookie)
        assert s.headers.get("Authorization", "").startswith("Bearer ")

    def test_me_unauthenticated(self):
        r = requests.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert r.status_code == 401

    def test_me_invalid_token(self):
        r = requests.get(f"{BASE_URL}/api/auth/me", timeout=15,
                         headers={"Authorization": "Bearer not-a-real-jwt"})
        assert r.status_code == 401

    def test_me_authenticated(self, admin_session):
        s, _ = admin_session
        r = s.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert "password_hash" not in body and "passwordHash" not in body

    def test_test_login_provisions_new_user(self):
        # a never-seen email is auto-provisioned as a profile + gets a token
        email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        r = requests.post(f"{BASE_URL}/api/auth/test-login",
                          json={"email": email, "name": "Test User"}, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["email"] == email and data["accessToken"]
        # the minted token authenticates against /me
        r2 = requests.get(f"{BASE_URL}/api/auth/me", timeout=15,
                          headers={"Authorization": f"Bearer {data['accessToken']}"})
        assert r2.status_code == 200 and r2.json()["email"] == email

    def test_retired_endpoints_are_gone(self):
        for path in ("register", "login", "forgot-password", "verify-email"):
            r = requests.post(f"{BASE_URL}/api/auth/{path}", json={}, timeout=15)
            assert r.status_code in (404, 405), f"{path} should be retired, got {r.status_code}"


# ---------------- Org listing / scoping ----------------
class TestOrgs:
    def test_list_orgs(self, admin_session):
        s, _ = admin_session
        r = s.get(f"{BASE_URL}/api/orgs", timeout=15)
        assert r.status_code == 200
        names = [o["name"] for o in r.json()]
        assert any("Orbital" in n for n in names)

    def test_get_org_profile(self, admin_session, org_id):
        s, _ = admin_session
        r = s.get(f"{BASE_URL}/api/orgs/{org_id}/profile", timeout=15)
        assert r.status_code == 200
        assert "certs" in r.json()


# ---------------- Opportunities CRUD & decoration ----------------
class TestOpportunities:
    def test_list_seeded(self, admin_session, org_id):
        s, _ = admin_session
        r = s.get(f"{BASE_URL}/api/orgs/{org_id}/opportunities", timeout=15)
        assert r.status_code == 200
        opps = r.json()
        assert len(opps) >= 12, f"Expected >=12 seeded opps, got {len(opps)}"
        # eligibility decoration present
        assert "eligibility" in opps[0]
        assert opps[0]["eligibility"]["verdict"] in {"open", "eligible", "verify", "not_certified"}

    def test_editor_can_crud(self, editor_session, org_id):
        s, _ = editor_session
        title = f"TEST_OPP_{uuid.uuid4().hex[:6]}"
        # create
        c = s.post(f"{BASE_URL}/api/orgs/{org_id}/opportunities",
                   json={"title": title, "solNumber": "TEST-001", "agency": "DoD",
                         "vehicle": "RFP", "setAside": "8(a)", "ceiling": 1000000},
                   timeout=15)
        assert c.status_code == 200, c.text
        opp = c.json()
        opp_id = opp["id"]
        assert opp["title"] == title
        # get
        g = s.get(f"{BASE_URL}/api/orgs/{org_id}/opportunities/{opp_id}", timeout=15)
        assert g.status_code == 200
        # update
        u = s.put(f"{BASE_URL}/api/orgs/{org_id}/opportunities/{opp_id}",
                  json={"stage": "Qualifying", "pwin": 65, "proposalStrength": 72.5}, timeout=15)
        assert u.status_code == 200
        # verify persistence
        g2 = s.get(f"{BASE_URL}/api/orgs/{org_id}/opportunities/{opp_id}", timeout=15)
        assert g2.json()["stage"] == "Qualifying"
        assert g2.json()["pwin"] == 65
        # delete
        d = s.delete(f"{BASE_URL}/api/orgs/{org_id}/opportunities/{opp_id}", timeout=15)
        assert d.status_code == 200
        g3 = s.get(f"{BASE_URL}/api/orgs/{org_id}/opportunities/{opp_id}", timeout=15)
        assert g3.status_code == 404

    def test_verify_requires_api_key(self, editor_session, org_id):
        """Verify & Refresh is LIVE — without an Anthropic key it must 400
        with a helpful message (never a 500)."""
        s, _ = editor_session
        r = s.post(f"{BASE_URL}/api/orgs/{org_id}/opportunities/verify", timeout=30)
        assert r.status_code == 400, r.text
        assert "Anthropic" in r.json().get("detail", "")

    def test_pull_requires_api_key(self, editor_session, org_id):
        """SAM/Grants pull is LIVE — without a SAM key it must 400."""
        s, _ = editor_session
        r = s.post(f"{BASE_URL}/api/orgs/{org_id}/opportunities/pull", timeout=30)
        assert r.status_code == 400, r.text
        assert "SAM" in r.json().get("detail", "")


# ---------------- RBAC ----------------
class TestRBAC:
    def test_viewer_blocked_from_create_opp(self, viewer_session, org_id):
        s, _ = viewer_session
        r = s.post(f"{BASE_URL}/api/orgs/{org_id}/opportunities",
                   json={"title": "Should Fail"}, timeout=15)
        assert r.status_code == 403, f"expected 403, got {r.status_code} {r.text}"

    def test_viewer_blocked_from_verify(self, viewer_session, org_id):
        s, _ = viewer_session
        r = s.post(f"{BASE_URL}/api/orgs/{org_id}/opportunities/verify", timeout=15)
        assert r.status_code == 403

    def test_viewer_blocked_from_pull(self, viewer_session, org_id):
        s, _ = viewer_session
        r = s.post(f"{BASE_URL}/api/orgs/{org_id}/opportunities/pull", timeout=15)
        assert r.status_code == 403

    def test_viewer_blocked_from_members(self, viewer_session, org_id):
        s, _ = viewer_session
        r = s.get(f"{BASE_URL}/api/orgs/{org_id}/members", timeout=15)
        assert r.status_code == 403

    def test_viewer_blocked_from_secrets(self, viewer_session, org_id):
        s, _ = viewer_session
        r = s.get(f"{BASE_URL}/api/orgs/{org_id}/secrets", timeout=15)
        assert r.status_code == 403

    def test_viewer_can_read_opps(self, viewer_session, org_id):
        s, _ = viewer_session
        r = s.get(f"{BASE_URL}/api/orgs/{org_id}/opportunities", timeout=15)
        assert r.status_code == 200

    def test_editor_blocked_from_members(self, editor_session, org_id):
        s, _ = editor_session
        r = s.get(f"{BASE_URL}/api/orgs/{org_id}/members", timeout=15)
        assert r.status_code == 403

    def test_editor_blocked_from_secrets(self, editor_session, org_id):
        s, _ = editor_session
        r = s.get(f"{BASE_URL}/api/orgs/{org_id}/secrets", timeout=15)
        assert r.status_code == 403

    def test_editor_blocked_from_org_update(self, editor_session, org_id):
        s, _ = editor_session
        r = s.put(f"{BASE_URL}/api/orgs/{org_id}",
                  json={"name": "Hacked", "naics": [], "keywords": []}, timeout=15)
        assert r.status_code == 403


# ---------------- Members / Admin ----------------
class TestMembers:
    def test_list_members(self, admin_session, org_id):
        s, _ = admin_session
        r = s.get(f"{BASE_URL}/api/orgs/{org_id}/members", timeout=15)
        assert r.status_code == 200
        members = r.json()
        emails = [m.get("email") for m in members]
        assert "admin@govcon.io" in emails
        assert "editor@govcon.io" in emails

    def test_invite_change_role_remove(self, admin_session, org_id):
        s, _ = admin_session
        email = f"invite_{uuid.uuid4().hex[:6]}@example.com"
        # invite
        r = s.post(f"{BASE_URL}/api/orgs/{org_id}/members/invite",
                   json={"email": email, "role": "editor"}, timeout=15)
        assert r.status_code == 200
        mid = r.json()["membershipId"]
        assert r.json()["status"] == "invited"
        # change role
        u = s.put(f"{BASE_URL}/api/orgs/{org_id}/members/{mid}",
                  json={"role": "viewer"}, timeout=15)
        assert u.status_code == 200
        # remove
        d = s.delete(f"{BASE_URL}/api/orgs/{org_id}/members/{mid}", timeout=15)
        assert d.status_code == 200

    def test_audit_log(self, admin_session, org_id):
        s, _ = admin_session
        r = s.get(f"{BASE_URL}/api/orgs/{org_id}/audit", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ---------------- Secrets masking ----------------
class TestSecrets:
    def test_save_and_mask(self, admin_session, org_id):
        s, _ = admin_session
        raw_key = "sk-ant-test1234567890abcdef"
        sam_key = "SAM-LIVE-9988776655"
        r = s.put(f"{BASE_URL}/api/orgs/{org_id}/secrets",
                  json={"anthropicKey": raw_key, "samKey": sam_key}, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["anthropicSet"] is True
        assert body["samSet"] is True
        # masked, contains ellipsis and never the raw secret
        assert raw_key not in body["anthropicKey"]
        assert "…" in body["anthropicKey"]
        assert sam_key not in body["samKey"]
        assert "…" in body["samKey"]
        # GET also masked
        g = s.get(f"{BASE_URL}/api/orgs/{org_id}/secrets", timeout=15)
        assert g.status_code == 200
        assert raw_key not in g.json()["anthropicKey"]
        assert g.json()["anthropicSet"] is True


# ---------------- Profile & Eligibility ----------------
class TestProfileEligibility:
    def test_update_profile_changes_eligibility(self, admin_session, editor_session, org_id):
        sa, _ = admin_session
        se, _ = editor_session
        # Find opp with 8(a) set-aside
        opps = sa.get(f"{BASE_URL}/api/orgs/{org_id}/opportunities", timeout=15).json()
        target = next((o for o in opps if o.get("setAside") == "8(a)"), None)
        if not target:
            # create one
            c = se.post(f"{BASE_URL}/api/orgs/{org_id}/opportunities",
                        json={"title": "TEST_8A_ELIG", "setAside": "8(a)"}, timeout=15)
            target = c.json()
        # Save current profile
        profile = sa.get(f"{BASE_URL}/api/orgs/{org_id}/profile", timeout=15).json()
        certs = dict(profile.get("certs") or {})
        original_eightA = certs.get("eightA", False)
        # Toggle on 8(a)
        new_certs = {**certs, "eightA": True}
        body = {**{k: profile.get(k) for k in
                   ["uei", "cage", "samActive", "isSmall", "cmmcLevel", "sprsScore", "sizeNote", "notes"]},
                "certs": new_certs}
        body = {k: (v if v is not None else "") for k, v in body.items()}
        body["certs"] = new_certs
        body["samActive"] = bool(profile.get("samActive"))
        body["isSmall"] = bool(profile.get("isSmall", True))
        r = sa.put(f"{BASE_URL}/api/orgs/{org_id}/profile", json=body, timeout=15)
        assert r.status_code == 200, r.text
        # Re-fetch opps, target should now be eligible
        opps2 = sa.get(f"{BASE_URL}/api/orgs/{org_id}/opportunities", timeout=15).json()
        t2 = next(o for o in opps2 if o["id"] == target["id"])
        assert t2["eligibility"]["verdict"] == "eligible"
        # Toggle back
        new_certs2 = {**new_certs, "eightA": original_eightA}
        body["certs"] = new_certs2
        sa.put(f"{BASE_URL}/api/orgs/{org_id}/profile", json=body, timeout=15)
