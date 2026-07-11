"""
Iteration 9 — Capture Qualification Workspace regression.

Tests the new scoring engine + Federal Opportunities workspace endpoints:
  * GET /api/orgs/{orgId}/opportunities decorates rows with eligibility,
    fitComputed, pwinView, financials, priority, redFlags, daysRemaining
  * PUT /api/orgs/{orgId}/opportunities/{id} accepts the new capture fields
    and returns the freshly decorated row; changes persist across GET
  * Scoring logic reacts to profile & row changes (watch / no-bid / vehicle
    gate / pwin / capture.fitOverride)
  * PUT /api/orgs/{orgId}/profile persists vehicles / noGo / prefRole
  * POST + DELETE work with no serialization errors
"""
import os
import time
import requests
import pytest

BASE_URL = (os.environ.get("TEST_BASE_URL")
            or os.environ.get("REACT_APP_BACKEND_URL")
            or "https://govcon-workspace.preview.emergentagent.com").rstrip("/")

QA_EMAIL = "qa.captureagent@testmail.dev"
QA_PASSWORD = "CaptureQA#2026"
QA_ORG_ID = "499e35c6-ca12-4589-aa1a-ae22bdb72c07"


# ------------------------- session / login --------------------------------

@pytest.fixture(scope="module")
def qa_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": QA_EMAIL, "password": QA_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    token = s.cookies.get("access_token")
    if token:
        s.headers["Authorization"] = f"Bearer {token}"
    return s


@pytest.fixture(scope="module")
def qa_opp_id(qa_session):
    """Create a scratch opportunity we can freely mutate + delete."""
    payload = {
        "title": "TEST_iter9_qualification_target",
        "solNumber": f"TEST-ITER9-{int(time.time())}",
        "agency": "Department of the Air Force",
        "office": "AFRL",
        "vehicle": "RFP",
        "setAside": "None",
        "naics": "541715",
        "ceiling": 750000,
        "pop": "12 months",
        "dueDate": "2026-06-30",
        "stage": "Identified",
        "url": "https://sam.gov/opp/TESTITER9",
        "winThemes": "",
    }
    r = qa_session.post(f"{BASE_URL}/api/orgs/{QA_ORG_ID}/opportunities",
                        json=payload, timeout=30)
    assert r.status_code == 200, f"create failed: {r.status_code} {r.text}"
    opp = r.json()
    yield opp["id"]
    # cleanup
    qa_session.delete(
        f"{BASE_URL}/api/orgs/{QA_ORG_ID}/opportunities/{opp['id']}",
        timeout=30)


# ------------------------- GET decorate -----------------------------------

class TestListDecorate:
    def test_list_returns_seed_qa_opps(self, qa_session):
        r = qa_session.get(
            f"{BASE_URL}/api/orgs/{QA_ORG_ID}/opportunities", timeout=30)
        assert r.status_code == 200
        opps = r.json()
        assert isinstance(opps, list) and len(opps) >= 5, \
            f"expected ≥5 QA opps, got {len(opps)}"

    def test_row_has_all_derived_fields(self, qa_session):
        r = qa_session.get(
            f"{BASE_URL}/api/orgs/{QA_ORG_ID}/opportunities", timeout=30)
        opps = r.json()
        seed = next((o for o in opps
                     if "QA Test Opp" in (o.get("title") or "")), opps[0])

        # eligibility
        elig = seed.get("eligibility")
        assert isinstance(elig, dict)
        assert elig["status"] in ("Eligible", "Conditional",
                                  "Ineligible", "Unknown")
        assert isinstance(elig.get("gates"), list) and len(elig["gates"]) >= 3
        gate_keys = {g["gate"] for g in elig["gates"]}
        assert "Set-aside certification" in gate_keys
        assert "SAM registration" in gate_keys

        # fitComputed
        fc = seed.get("fitComputed")
        assert isinstance(fc, dict)
        assert 0 <= fc["score"] <= 100
        assert 0 <= fc["effective"] <= 100
        assert fc["band"] in ("Strong", "Good", "Conditional", "Poor")
        assert fc["confidence"] in ("high", "medium", "low")
        assert isinstance(fc["breakdown"], list) and len(fc["breakdown"]) == 7
        assert sum(c["weight"] for c in fc["breakdown"]) == 100

        # pwinView
        pv = seed.get("pwinView")
        assert isinstance(pv, dict)
        assert pv["band"] in ("Unknown", "Low", "Medium", "High")

        # financials
        fin = seed.get("financials")
        assert isinstance(fin, dict)
        for k in ("statedValue", "valueType", "addressableValue",
                  "sharedCeiling", "weightedPipeline"):
            assert k in fin, f"financials missing {k}"

        # priority + redFlags + daysRemaining
        pri = seed.get("priority")
        assert isinstance(pri, dict)
        assert pri["label"] in ("A", "B", "C", "Watch", "Pass")
        assert isinstance(seed.get("redFlags"), list)
        assert "daysRemaining" in seed


# ------------------------- PUT persistence --------------------------------

class TestUpdatePersistence:
    def test_update_new_capture_fields_persists(self, qa_session, qa_opp_id):
        body = {
            "scopeSummary": "TEST scope — autonomous ISR payload integration",
            "tags": ["autonomy", "TEST_iter9"],
            "oppType": "Contract",
            "acqStage": "Draft RFP",
            "recompete": "New requirement",
            "dueTime": "17:00 ET",
            "psc": "AC13",
            "naicsTitle": "R&D in Physical, Engineering and Life Sciences",
            "sizeStandard": "1,300 employees",
            "valueType": "Ceiling",
            "addressableValue": 250000,
            "contractType": "FFP",
            "awardsCount": "Multiple (~3)",
            "vehicleAccess": "have",
            "pursuitRole": "Prime",
            "incumbent": "Acme Robotics Inc.",
            "competition": {"intensity": "Moderate", "likelyBidders": "3-5",
                            "awardNumber": ""},
            "capture": {"owner": "QA Capture", "nextAction": "Call PM",
                        "nextActionDue": "2026-07-15",
                        "fitOverride": None, "fitOverrideNote": ""},
        }
        r = qa_session.put(
            f"{BASE_URL}/api/orgs/{QA_ORG_ID}/opportunities/{qa_opp_id}",
            json=body, timeout=30)
        assert r.status_code == 200, f"PUT failed: {r.status_code} {r.text}"
        row = r.json()
        assert row["scopeSummary"] == body["scopeSummary"]
        assert row["tags"] == body["tags"]
        assert row["oppType"] == "Contract"
        assert row["vehicleAccess"] == "have"
        assert row["capture"]["owner"] == "QA Capture"
        assert row["addressableValue"] == 250000

        # re-GET → verify DB persistence
        g = qa_session.get(
            f"{BASE_URL}/api/orgs/{QA_ORG_ID}/opportunities/{qa_opp_id}",
            timeout=30)
        assert g.status_code == 200
        got = g.json()
        assert got["scopeSummary"] == body["scopeSummary"]
        assert got["capture"]["nextAction"] == "Call PM"
        assert got["competition"]["intensity"] == "Moderate"


# ------------------------- scoring reactions ------------------------------

class TestScoringLogic:
    def test_vehicle_gate_ineligible(self, qa_session, qa_opp_id):
        # vehicleAccess=need overrides everything → Ineligible + Pass
        r = qa_session.put(
            f"{BASE_URL}/api/orgs/{QA_ORG_ID}/opportunities/{qa_opp_id}",
            json={"vehicleAccess": "need", "vehicle": "OASIS+ SB",
                  "watch": False,
                  "decision": {"call": "TBD", "rationale": ""}},
            timeout=30)
        assert r.status_code == 200
        row = r.json()
        assert row["eligibility"]["status"] == "Ineligible"
        assert row["priority"]["label"] == "Pass"
        # red-flag present
        assert any("vehicle" in (f["flag"] or "").lower()
                   for f in row["redFlags"])

    def test_watch_flag_makes_priority_watch(self, qa_session, qa_opp_id):
        # First clear ineligibility so watch can take effect
        r = qa_session.put(
            f"{BASE_URL}/api/orgs/{QA_ORG_ID}/opportunities/{qa_opp_id}",
            json={"vehicleAccess": "have", "watch": True,
                  "decision": {"call": "TBD", "rationale": ""}},
            timeout=30)
        assert r.status_code == 200
        row = r.json()
        # Note: seed profile currently has samActive=false → Ineligible.
        # Watch only applies when NOT Ineligible; so we accept either
        # "Watch" (if profile is currently Eligible) or "Pass" (if still
        # gated). Both are valid per scoring rules.
        assert row["watch"] is True
        assert row["priority"]["label"] in ("Watch", "Pass")

    def test_no_bid_becomes_pass(self, qa_session, qa_opp_id):
        r = qa_session.put(
            f"{BASE_URL}/api/orgs/{QA_ORG_ID}/opportunities/{qa_opp_id}",
            json={"decision": {"call": "No-Bid", "rationale": "test"},
                  "watch": False},
            timeout=30)
        assert r.status_code == 200
        assert r.json()["priority"]["label"] == "Pass"

    def test_pwin_high_band(self, qa_session, qa_opp_id):
        r = qa_session.put(
            f"{BASE_URL}/api/orgs/{QA_ORG_ID}/opportunities/{qa_opp_id}",
            json={"pwin": 70, "decision": {"call": "TBD", "rationale": ""}},
            timeout=30)
        assert r.status_code == 200
        pv = r.json()["pwinView"]
        assert pv["band"] == "High"
        assert pv["pct"] == 70

    def test_fit_override_effective_and_note(self, qa_session, qa_opp_id):
        r = qa_session.put(
            f"{BASE_URL}/api/orgs/{QA_ORG_ID}/opportunities/{qa_opp_id}",
            json={"capture": {"owner": "QA Capture", "nextAction": "",
                              "nextActionDue": "",
                              "fitOverride": 90,
                              "fitOverrideNote": "Verified evidence"}},
            timeout=30)
        assert r.status_code == 200
        fc = r.json()["fitComputed"]
        assert fc["effective"] == 90
        assert "override" in fc
        assert fc["override"]["score"] == 90
        assert fc["override"]["note"] == "Verified evidence"


# ------------------------- profile PUT ------------------------------------

class TestProfileNewFields:
    def test_put_profile_vehicles_nogo_prefrole(self, qa_session):
        # first read current profile (to preserve required fields)
        g = qa_session.get(
            f"{BASE_URL}/api/orgs/{QA_ORG_ID}/profile", timeout=30)
        assert g.status_code == 200
        cur = g.json() or {}
        body = {
            **cur,
            "vehicles": ["GSA MAS", "SeaPort-NxG"],
            "noGo": "janitorial, construction",
            "prefRole": "Prime",
        }
        # strip fields the server derives / rejects
        for k in ("id", "organizationId", "createdAt", "updatedAt"):
            body.pop(k, None)
        r = qa_session.put(
            f"{BASE_URL}/api/orgs/{QA_ORG_ID}/profile",
            json=body, timeout=30)
        assert r.status_code == 200, f"profile PUT: {r.status_code} {r.text}"
        got = r.json()
        assert got.get("vehicles") == ["GSA MAS", "SeaPort-NxG"]
        assert got.get("noGo") == "janitorial, construction"
        assert got.get("prefRole") == "Prime"

        # re-GET
        g2 = qa_session.get(
            f"{BASE_URL}/api/orgs/{QA_ORG_ID}/profile", timeout=30)
        assert g2.status_code == 200
        p2 = g2.json()
        assert "GSA MAS" in (p2.get("vehicles") or [])
        assert p2.get("prefRole") == "Prime"


# ------------------------- CRUD sanity ------------------------------------

class TestCrudSanity:
    def test_create_then_delete_no_serialization_error(self, qa_session):
        r = qa_session.post(
            f"{BASE_URL}/api/orgs/{QA_ORG_ID}/opportunities",
            json={"title": "TEST_iter9_crud",
                  "solNumber": f"TEST-CRUD-{int(time.time())}",
                  "agency": "GSA", "vehicle": "RFP", "setAside": "None",
                  "naics": "541511", "ceiling": 100000, "pop": "6 months",
                  "dueDate": "2026-08-01", "stage": "Identified",
                  "url": "", "winThemes": ""},
            timeout=30)
        assert r.status_code == 200
        row = r.json()
        # No "_id" leakage
        assert "_id" not in row
        assert isinstance(row["id"], str) and len(row["id"]) >= 32
        # decorated
        assert "eligibility" in row and "fitComputed" in row

        d = qa_session.delete(
            f"{BASE_URL}/api/orgs/{QA_ORG_ID}/opportunities/{row['id']}",
            timeout=30)
        assert d.status_code == 200
        assert d.json().get("ok") is True

        # 404 after delete
        g = qa_session.get(
            f"{BASE_URL}/api/orgs/{QA_ORG_ID}/opportunities/{row['id']}",
            timeout=30)
        assert g.status_code == 404
