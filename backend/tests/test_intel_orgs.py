"""Tests: Intelligence scan guard paths, join codes, org join flow, profile
capability fields. (The scan itself needs a real Anthropic key, so only the
guard/error paths are exercised here.)"""
import os
import time
import uuid
import requests

BASE_URL = (os.environ.get("TEST_BASE_URL")
            or os.environ.get("REACT_APP_BACKEND_URL")
            or "http://localhost:8000").rstrip("/")


# --------------- Intel scan guard paths ---------------
class TestIntelScan:
    def test_viewer_cannot_scan(self, viewer_session, org_id):
        s, _ = viewer_session
        r = s.post(f"{BASE_URL}/api/orgs/{org_id}/intel/scan", json={"tier": "standard"}, timeout=15)
        assert r.status_code == 403, r.text

    def test_editor_no_key_returns_400(self, editor_session, admin_session, org_id):
        # Earlier suites may have stored a (fake) Anthropic key on the demo
        # org; scans then start a job instead of 400-ing. Handle both paths.
        sa, _ = admin_session
        cur = sa.get(f"{BASE_URL}/api/orgs/{org_id}/secrets", timeout=15).json()
        se, _ = editor_session
        r = se.post(f"{BASE_URL}/api/orgs/{org_id}/intel/scan", json={"tier": "standard"}, timeout=15)
        if cur.get("anthropicSet"):
            assert r.status_code == 200, r.text
            assert "jobId" in r.json()
        else:
            assert r.status_code == 400
            assert "Settings" in r.json().get("detail", "")

    def test_invalid_key_job_errors(self, admin_session, editor_session, org_id):
        sa, _ = admin_session
        # Set a fake key
        r = sa.put(f"{BASE_URL}/api/orgs/{org_id}/secrets",
                   json={"anthropicKey": "sk-ant-fake123"}, timeout=15)
        assert r.status_code == 200
        # Trigger scan as editor
        se, _ = editor_session
        r2 = se.post(f"{BASE_URL}/api/orgs/{org_id}/intel/scan", json={"tier": "standard"}, timeout=15)
        assert r2.status_code == 200, r2.text
        job_id = r2.json()["jobId"]
        # Poll up to ~40s
        status = None
        err_msg = None
        for _ in range(20):
            time.sleep(2)
            j = se.get(f"{BASE_URL}/api/orgs/{org_id}/intel/jobs/{job_id}", timeout=15)
            assert j.status_code == 200
            jb = j.json()
            status = jb.get("status")
            if status in ("error", "done"):
                err_msg = jb.get("error")
                break
        assert status == "error", f"Expected error status, got {status}, msg={err_msg}"
        assert err_msg, "Error message should be populated"
        assert ("Settings" in err_msg) or ("Anthropic" in err_msg) \
            or ("API" in err_msg) or ("key" in err_msg.lower()), err_msg

    def test_reports_listing_shape(self, admin_session, org_id):
        s, _ = admin_session
        r = s.get(f"{BASE_URL}/api/orgs/{org_id}/intel/reports", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# --------------- Join code ---------------
class TestJoinCode:
    def test_admin_get_code(self, admin_session, org_id):
        s, _ = admin_session
        r = s.get(f"{BASE_URL}/api/orgs/{org_id}/join-code", timeout=15)
        assert r.status_code == 200
        code = r.json().get("joinCode")
        assert isinstance(code, str) and len(code) == 8

    def test_editor_blocked_from_get_code(self, editor_session, org_id):
        s, _ = editor_session
        r = s.get(f"{BASE_URL}/api/orgs/{org_id}/join-code", timeout=15)
        assert r.status_code == 403

    def test_viewer_blocked_from_get_code(self, viewer_session, org_id):
        s, _ = viewer_session
        r = s.get(f"{BASE_URL}/api/orgs/{org_id}/join-code", timeout=15)
        assert r.status_code == 403

    def test_rotate_changes_code(self, admin_session, org_id):
        s, _ = admin_session
        before = s.get(f"{BASE_URL}/api/orgs/{org_id}/join-code", timeout=15).json()["joinCode"]
        r = s.post(f"{BASE_URL}/api/orgs/{org_id}/join-code/rotate", timeout=15)
        assert r.status_code == 200
        after = r.json()["joinCode"]
        assert after != before
        assert len(after) == 8


# --------------- Org join flow (register fresh user) ---------------
class TestOrgJoin:
    def test_join_full_flow(self, admin_session, org_id):
        sa, _ = admin_session
        code = sa.get(f"{BASE_URL}/api/orgs/{org_id}/join-code", timeout=15).json()["joinCode"]
        # register a new user
        email = f"join_{uuid.uuid4().hex[:8]}@example.com"
        pwd = "JoinP@ss1!"
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        reg = s.post(f"{BASE_URL}/api/auth/register",
                     json={"email": email, "name": "Joiner", "password": pwd}, timeout=15)
        assert reg.status_code == 200, reg.text
        # login
        r = s.post(f"{BASE_URL}/api/auth/login",
                   json={"email": email, "password": pwd}, timeout=15)
        assert r.status_code == 200
        # Secure cookies aren't sent over plain http by requests — use Bearer
        s.headers["Authorization"] = f"Bearer {s.cookies.get('access_token')}"
        # invalid code
        bad = s.post(f"{BASE_URL}/api/orgs/join", json={"code": "ZZZZZZZZ"}, timeout=15)
        assert bad.status_code == 404
        # join with real code
        j = s.post(f"{BASE_URL}/api/orgs/join", json={"code": code}, timeout=15)
        assert j.status_code == 200, j.text
        assert j.json().get("role") == "viewer"
        # me should reflect membership
        me = s.get(f"{BASE_URL}/api/auth/me", timeout=15).json()
        assert any(o["id"] == org_id for o in me.get("organizations", []))
        # joining again -> 400
        again = s.post(f"{BASE_URL}/api/orgs/join", json={"code": code}, timeout=15)
        assert again.status_code == 400


# --------------- Profile capability fields ---------------
class TestProfileCapabilities:
    def test_capability_fields_persist(self, admin_session, org_id):
        s, _ = admin_session
        prof = s.get(f"{BASE_URL}/api/orgs/{org_id}/profile", timeout=15).json()
        payload = {
            "uei": prof.get("uei", ""),
            "cage": prof.get("cage", ""),
            "samActive": bool(prof.get("samActive", False)),
            "isSmall": bool(prof.get("isSmall", True)),
            "certs": prof.get("certs") or {},
            "cmmcLevel": prof.get("cmmcLevel", "Level 1"),
            "sprsScore": prof.get("sprsScore"),
            "sizeNote": prof.get("sizeNote", ""),
            "notes": prof.get("notes", ""),
            "capabilities": "TEST cyber & cloud engineering",
            "pastPerformance": "TEST DoD prime contracts",
            "techFocus": ["zero trust", "AI/ML"],
            "differentiators": "TEST 24/7 SOC",
            "commercialization": "TEST GSA + SBIR III",
            "clearances": "TEST TS/SCI cleared engineers",
        }
        r = s.put(f"{BASE_URL}/api/orgs/{org_id}/profile", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        p2 = s.get(f"{BASE_URL}/api/orgs/{org_id}/profile", timeout=15).json()
        assert p2.get("capabilities") == payload["capabilities"]
        assert p2.get("pastPerformance") == payload["pastPerformance"]
        assert p2.get("techFocus") == payload["techFocus"]
        assert p2.get("differentiators") == payload["differentiators"]
        assert p2.get("commercialization") == payload["commercialization"]
        assert p2.get("clearances") == payload["clearances"]
