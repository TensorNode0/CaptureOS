"""Tests for new endpoints: Intelligence scan/reports, Join code, Org join, Profile capability fields."""
import os
import time
import uuid
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "").rstrip("/")
ORG_ID = "6a23e286bc6ad92b27c235f0"


# --------------- Intel scan guard paths ---------------
class TestIntelScan:
    def test_viewer_cannot_scan(self, viewer_session):
        s, _ = viewer_session
        r = s.post(f"{BASE_URL}/api/orgs/{ORG_ID}/intel/scan", json={"tier": "standard"}, timeout=15)
        assert r.status_code == 403, r.text

    def test_editor_no_key_returns_400(self, editor_session, admin_session):
        # Ensure no anthropic key set first (admin clears via empty PUT)
        sa, _ = admin_session
        # Save current secrets state
        cur = sa.get(f"{BASE_URL}/api/orgs/{ORG_ID}/secrets", timeout=15).json()
        anthropic_was_set = cur.get("anthropicSet")
        # Clear by writing an empty value directly into DB-via-API? Endpoint preserves existing on empty.
        # Skip this test if a key is already set (cannot null it without DB access).
        if anthropic_was_set:
            # If a key exists, attempting scan as editor should NOT 400-no-key.
            se, _ = editor_session
            r = se.post(f"{BASE_URL}/api/orgs/{ORG_ID}/intel/scan", json={"tier": "standard"}, timeout=15)
            # With a fake key already set, it returns jobId
            assert r.status_code == 200, r.text
            assert "jobId" in r.json()
            return
        se, _ = editor_session
        r = se.post(f"{BASE_URL}/api/orgs/{ORG_ID}/intel/scan", json={"tier": "standard"}, timeout=15)
        assert r.status_code == 400
        assert "Settings" in r.json().get("detail", "")

    def test_invalid_key_job_errors(self, admin_session, editor_session):
        sa, _ = admin_session
        # Set a fake key
        r = sa.put(f"{BASE_URL}/api/orgs/{ORG_ID}/secrets",
                   json={"anthropicKey": "sk-ant-fake123"}, timeout=15)
        assert r.status_code == 200
        # Trigger scan as editor
        se, _ = editor_session
        r2 = se.post(f"{BASE_URL}/api/orgs/{ORG_ID}/intel/scan", json={"tier": "standard"}, timeout=15)
        assert r2.status_code == 200, r2.text
        job_id = r2.json()["jobId"]
        # Poll up to ~40s
        status = None
        err_msg = None
        for _ in range(20):
            time.sleep(2)
            j = se.get(f"{BASE_URL}/api/orgs/{ORG_ID}/intel/jobs/{job_id}", timeout=15)
            assert j.status_code == 200
            jb = j.json()
            status = jb.get("status")
            if status in ("error", "done"):
                err_msg = jb.get("error")
                break
        assert status == "error", f"Expected error status, got {status}, msg={err_msg}"
        assert err_msg, "Error message should be populated"
        # Helpful: mentions Settings or Anthropic
        assert ("Settings" in err_msg) or ("Anthropic" in err_msg) or ("API" in err_msg) or ("key" in err_msg.lower()), err_msg


# --------------- Intel reports / SAMPLE rendering ---------------
class TestIntelReports:
    def test_list_includes_sample(self, admin_session):
        s, _ = admin_session
        r = s.get(f"{BASE_URL}/api/orgs/{ORG_ID}/intel/reports", timeout=15)
        assert r.status_code == 200
        reports = r.json()
        assert len(reports) >= 1
        # Sample is marked with model label ending "(SAMPLE)"
        sample = next((rep for rep in reports if "SAMPLE" in (rep.get("model") or "")), None)
        assert sample, f"No SAMPLE report found in {reports}"

    def test_get_report_full(self, admin_session):
        s, _ = admin_session
        reports = s.get(f"{BASE_URL}/api/orgs/{ORG_ID}/intel/reports", timeout=15).json()
        sample = next(r for r in reports if "SAMPLE" in (r.get("model") or ""))
        r = s.get(f"{BASE_URL}/api/orgs/{ORG_ID}/intel/reports/{sample['id']}", timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert "report" in body
        opps = body["report"].get("opportunities")
        assert isinstance(opps, list) and len(opps) > 0


# --------------- Add to pipeline ---------------
class TestIntelAddToPipeline:
    def test_add_then_duplicate(self, admin_session, editor_session):
        sa, _ = admin_session
        se, _ = editor_session
        reports = sa.get(f"{BASE_URL}/api/orgs/{ORG_ID}/intel/reports", timeout=15).json()
        sample = next(r for r in reports if "SAMPLE" in (r.get("model") or ""))
        rep = sa.get(f"{BASE_URL}/api/orgs/{ORG_ID}/intel/reports/{sample['id']}", timeout=15).json()
        opps = rep["report"]["opportunities"]
        # Pick the last index — least likely to already be in pipeline
        idx_to_use = None
        before_count = len(sa.get(f"{BASE_URL}/api/orgs/{ORG_ID}/opportunities", timeout=15).json())
        for idx in reversed(range(len(opps))):
            r = se.post(f"{BASE_URL}/api/orgs/{ORG_ID}/intel/reports/{sample['id']}/add/{idx}", timeout=15)
            if r.status_code == 200:
                idx_to_use = idx
                break
        assert idx_to_use is not None, "Could not add any opportunity from sample (all duplicate?)"
        after_count = len(sa.get(f"{BASE_URL}/api/orgs/{ORG_ID}/opportunities", timeout=15).json())
        assert after_count == before_count + 1
        # Duplicate call
        sol = (opps[idx_to_use].get("solNumber") or "").strip()
        if sol and sol != "TBD":
            r2 = se.post(f"{BASE_URL}/api/orgs/{ORG_ID}/intel/reports/{sample['id']}/add/{idx_to_use}", timeout=15)
            assert r2.status_code == 400, r2.text
            assert "pipeline" in r2.json().get("detail", "").lower() or "already" in r2.json().get("detail", "").lower()


# --------------- Join code ---------------
class TestJoinCode:
    def test_admin_get_code(self, admin_session):
        s, _ = admin_session
        r = s.get(f"{BASE_URL}/api/orgs/{ORG_ID}/join-code", timeout=15)
        assert r.status_code == 200
        code = r.json().get("joinCode")
        assert isinstance(code, str) and len(code) == 8

    def test_editor_blocked_from_get_code(self, editor_session):
        s, _ = editor_session
        r = s.get(f"{BASE_URL}/api/orgs/{ORG_ID}/join-code", timeout=15)
        assert r.status_code == 403

    def test_viewer_blocked_from_get_code(self, viewer_session):
        s, _ = viewer_session
        r = s.get(f"{BASE_URL}/api/orgs/{ORG_ID}/join-code", timeout=15)
        assert r.status_code == 403

    def test_rotate_changes_code(self, admin_session):
        s, _ = admin_session
        before = s.get(f"{BASE_URL}/api/orgs/{ORG_ID}/join-code", timeout=15).json()["joinCode"]
        r = s.post(f"{BASE_URL}/api/orgs/{ORG_ID}/join-code/rotate", timeout=15)
        assert r.status_code == 200
        after = r.json()["joinCode"]
        assert after != before
        assert len(after) == 8


# --------------- Org join flow (register fresh user) ---------------
class TestOrgJoin:
    def test_join_full_flow(self, admin_session):
        sa, _ = admin_session
        code = sa.get(f"{BASE_URL}/api/orgs/{ORG_ID}/join-code", timeout=15).json()["joinCode"]
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
        # invalid code
        bad = s.post(f"{BASE_URL}/api/orgs/join", json={"code": "ZZZZZZZZ"}, timeout=15)
        assert bad.status_code == 404
        # join with real code
        j = s.post(f"{BASE_URL}/api/orgs/join", json={"code": code}, timeout=15)
        assert j.status_code == 200, j.text
        assert j.json().get("role") == "viewer"
        # me should reflect membership
        me = s.get(f"{BASE_URL}/api/auth/me", timeout=15).json()
        assert any(o["id"] == ORG_ID for o in me.get("organizations", []))
        # joining again -> 400
        again = s.post(f"{BASE_URL}/api/orgs/join", json={"code": code}, timeout=15)
        assert again.status_code == 400


# --------------- Profile capability fields ---------------
class TestProfileCapabilities:
    def test_capability_fields_persist(self, admin_session):
        s, _ = admin_session
        prof = s.get(f"{BASE_URL}/api/orgs/{ORG_ID}/profile", timeout=15).json()
        # Carry forward existing values
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
        r = s.put(f"{BASE_URL}/api/orgs/{ORG_ID}/profile", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        # GET to verify persistence
        p2 = s.get(f"{BASE_URL}/api/orgs/{ORG_ID}/profile", timeout=15).json()
        assert p2.get("capabilities") == payload["capabilities"]
        assert p2.get("pastPerformance") == payload["pastPerformance"]
        assert p2.get("techFocus") == payload["techFocus"]
        assert p2.get("differentiators") == payload["differentiators"]
        assert p2.get("commercialization") == payload["commercialization"]
        assert p2.get("clearances") == payload["clearances"]
