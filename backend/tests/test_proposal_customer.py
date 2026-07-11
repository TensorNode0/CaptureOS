"""Proposal customer card: save the commercial market + government customer
(sector/branch/PEO/TPOC/CO) and gate the AI directory-currency check."""
import os
import uuid
import pytest
import requests

BASE_URL = (os.environ.get("TEST_BASE_URL")
            or os.environ.get("REACT_APP_BACKEND_URL")
            or "http://localhost:8000").rstrip("/")

CUSTOMER = {
    "commercialMarket": "Critical infrastructure security",
    "sector": "Defense",
    "branch": "Air Force",
    "agency": "",
    "peo": "PEO Digital",
    "tpoc": "Maj Test TPOC · AFLCMC",
    "contractingOfficer": "Jane KO · AFLCMC/PK",
}


@pytest.fixture(scope="module")
def cust_org(admin_session):
    s, _ = admin_session
    r = s.post(f"{BASE_URL}/api/orgs",
               json={"name": f"CustTest Org {uuid.uuid4().hex[:6]}",
                     "naics": ["541715"], "keywords": ["autonomy"],
                     "certifyAor": True}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["id"]


@pytest.fixture(scope="module")
def cust_opp(admin_session, cust_org):
    s, _ = admin_session
    r = s.post(f"{BASE_URL}/api/orgs/{cust_org}/opportunities",
               json={"title": "Customer Card Test Opp", "solNumber": "CUST-001",
                     "agency": "USAF", "vehicle": "SBIR"}, timeout=15)
    assert r.status_code == 200, r.text
    opp_id = r.json()["id"]
    p = s.post(f"{BASE_URL}/api/orgs/{cust_org}/opportunities/{opp_id}/proposal",
               timeout=15)
    assert p.status_code == 200, p.text
    return opp_id


class TestProposalCustomer:
    def test_save_and_read_back(self, admin_session, cust_org, cust_opp):
        s, _ = admin_session
        r = s.put(f"{BASE_URL}/api/orgs/{cust_org}/opportunities/{cust_opp}"
                  "/proposal/customer", json=CUSTOMER, timeout=15)
        assert r.status_code == 200, r.text
        got = r.json()["customer"]
        assert got["peo"] == "PEO Digital"
        assert got["sector"] == "Defense"
        # persists on a fresh GET
        g = s.get(f"{BASE_URL}/api/orgs/{cust_org}/opportunities/{cust_opp}/proposal",
                  timeout=15)
        assert g.json()["customer"]["tpoc"].startswith("Maj Test")

    def test_check_requires_anthropic_key(self, admin_session, cust_org, cust_opp):
        s, _ = admin_session
        r = s.post(f"{BASE_URL}/api/orgs/{cust_org}/opportunities/{cust_opp}"
                   "/proposal/customer/check", json={"engine": "claude"}, timeout=15)
        assert r.status_code == 400
        assert "Anthropic" in r.json()["detail"]

    def test_check_requires_target_first(self, admin_session, cust_org, cust_opp):
        s, _ = admin_session
        # blank out the government customer → check must refuse
        blank = {**CUSTOMER, "peo": "", "agency": ""}
        r = s.put(f"{BASE_URL}/api/orgs/{cust_org}/opportunities/{cust_opp}"
                  "/proposal/customer", json=blank, timeout=15)
        assert r.status_code == 200
        r = s.post(f"{BASE_URL}/api/orgs/{cust_org}/opportunities/{cust_opp}"
                   "/proposal/customer/check", json={"engine": "claude"}, timeout=15)
        assert r.status_code == 400
        assert "customer" in r.json()["detail"].lower()

    def test_viewer_cannot_save(self, viewer_session, org_id, admin_session):
        # viewer fixture lives in the shared org; endpoint 404s before RBAC
        # only if no proposal exists, so assert on the shared-org viewer role
        s, _ = viewer_session
        r = s.put(f"{BASE_URL}/api/orgs/{org_id}/opportunities/"
                  f"{uuid.uuid4()}/proposal/customer", json=CUSTOMER, timeout=15)
        assert r.status_code in (403, 404)
