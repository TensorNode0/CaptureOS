"""
Iteration 8 — AI engine per-org selection & Emergent proxy live-fix regression.

Verifies:
  * /api/health basic regression
  * Login flow with QA account (JWT httpOnly cookies)
  * /orgs/{org}/ai/options: 4 engines returned with correct emergent model list
  * Save Emergent key to org secrets → engine flips to configured=true
  * POST /opportunities/verify (engine=emergent, model=claude-sonnet-4-6, low)
      – must NOT return "Name or service not known"
      – must return 200 with a summary
  * POST /opportunities/verify (engine=openai) with no OpenAI key → 400 that
      names OpenAI (not Anthropic)
"""
import os
import time
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") \
           or "https://govcon-workspace.preview.emergentagent.com"

QA_EMAIL = "qa.captureagent@testmail.dev"
QA_PASS = "CaptureQA#2026"

EMERGENT_MODELS_EXPECTED = {
    "claude-sonnet-4-6", "gpt-5.4", "gpt-4o", "gemini-3.1-pro-preview",
}


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": QA_EMAIL, "password": QA_PASS}, timeout=30)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text[:400]}"
    return s


@pytest.fixture(scope="module")
def org_id(session):
    r = session.get(f"{BASE_URL}/api/orgs", timeout=30)
    assert r.status_code == 200, r.text[:300]
    orgs = r.json()
    for o in orgs:
        if o.get("name") == "QA Verification Org":
            return o["id"]
    assert orgs, "No orgs on QA account"
    return orgs[0]["id"]


# ------------- Health / regression -------------
def test_health():
    r = requests.get(f"{BASE_URL}/api/health", timeout=20)
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"


def test_login_regression(session):
    r = session.get(f"{BASE_URL}/api/auth/me", timeout=20)
    assert r.status_code == 200, r.text[:200]
    me = r.json()
    assert me.get("email") == QA_EMAIL


# ------------- /ai/options -------------
def test_ai_options_shape(session, org_id):
    r = session.get(f"{BASE_URL}/api/orgs/{org_id}/ai/options", timeout=30)
    assert r.status_code == 200, r.text[:400]
    data = r.json()
    engines = data.get("engines") or []
    ids = {e["id"] for e in engines}
    assert ids == {"claude", "openai", "emergent", "asksage"}, f"engines: {ids}"
    for e in engines:
        assert "configured" in e and isinstance(e["configured"], bool)
        assert "models" in e and isinstance(e["models"], list)
    # Emergent catalog: exactly the 4 approved models (no claude-sonnet-5)
    emergent = next(e for e in engines if e["id"] == "emergent")
    model_ids = {m["id"] for m in emergent["models"]}
    assert model_ids == EMERGENT_MODELS_EXPECTED, (
        f"Emergent models mismatch: got {model_ids}")


def _emergent_key():
    val = os.environ.get("EMERGENT_LLM_KEY")
    if val:
        return val
    try:
        with open("/app/backend/.env") as f:
            for line in f:
                if line.strip().startswith("EMERGENT_LLM_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return "sk-emergent-1B6253fE6BeD8Ed6bF"


# ------------- Save Emergent key + configured flip -------------
def test_save_emergent_key_and_configured_flip(session, org_id):
    key = _emergent_key()
    assert key
    r = session.put(f"{BASE_URL}/api/orgs/{org_id}/secrets",
                    json={"emergentKey": key}, timeout=30)
    assert r.status_code == 200, f"save secrets failed: {r.status_code} {r.text[:300]}"
    body = r.json()
    assert body.get("ok") is True
    # /ai/options must reflect configured=true
    r = session.get(f"{BASE_URL}/api/orgs/{org_id}/ai/options", timeout=30)
    assert r.status_code == 200
    emergent = next(e for e in r.json()["engines"] if e["id"] == "emergent")
    assert emergent["configured"] is True, "Emergent still not configured after save"


# ------------- Ensure at least 1 opportunity exists -------------
@pytest.fixture(scope="module")
def opportunity_id(session, org_id):
    r = session.get(f"{BASE_URL}/api/orgs/{org_id}/opportunities", timeout=30)
    assert r.status_code == 200
    opps = r.json()
    if opps:
        return opps[0]["id"]
    due = time.strftime("%Y-%m-%d",
                        time.gmtime(time.time() + 45 * 86400))
    r = session.post(
        f"{BASE_URL}/api/orgs/{org_id}/opportunities",
        json={"title": "TEST_iter8_verify_target", "agency": "TEST", "vehicle": "RFP",
              "dueDate": due},
        timeout=30)
    assert r.status_code in (200, 201), r.text[:300]
    return r.json()["id"]


# ------------- CRITICAL: live emergent verify (single low-cost call) -------------
def test_emergent_verify_live(session, org_id, opportunity_id):
    body = {"engine": "emergent", "model": "claude-sonnet-4-6", "effort": "low"}
    r = session.post(f"{BASE_URL}/api/orgs/{org_id}/opportunities/verify",
                     json=body, timeout=240)
    text = r.text[:1500]
    # The former bug signature
    assert "Name or service not known" not in text, (
        f"Emergent proxy still resolving wrong host: {text}")
    assert r.status_code == 200, f"verify HTTP {r.status_code}: {text}"
    data = r.json()
    assert data.get("ok") is True
    assert "summary" in data
    assert "verified" in data["summary"]


# ------------- Engine key gating: OpenAI without a saved key -------------
def test_openai_verify_no_key_returns_openai_error(session, org_id):
    """POST verify with engine=openai when no OpenAI key exists → 400 mentioning
    OpenAI (must NOT be the Anthropic error path)."""
    # Skip if OpenAI is already configured
    r = session.get(f"{BASE_URL}/api/orgs/{org_id}/ai/options", timeout=30)
    openai_conf = any(e["id"] == "openai" and e["configured"]
                      for e in r.json()["engines"])
    if openai_conf:
        pytest.skip("OpenAI key already configured on QA org — can't test gating")
    r = session.post(f"{BASE_URL}/api/orgs/{org_id}/opportunities/verify",
                     json={"engine": "openai"}, timeout=30)
    assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text[:400]}"
    body = r.text
    assert "OpenAI" in body, f"error not about OpenAI: {body[:300]}"
    assert "Anthropic" not in body, f"error still mentions Anthropic: {body[:300]}"


# ------------- Cleanup: delete TEST_iter8 opportunity if we created it -------------
def test_zz_cleanup_test_opportunity(session, org_id):
    r = session.get(f"{BASE_URL}/api/orgs/{org_id}/opportunities", timeout=30)
    if r.status_code != 200:
        pytest.skip("could not list opps for cleanup")
    for o in r.json():
        if (o.get("title") or "").startswith("TEST_iter8"):
            session.delete(
                f"{BASE_URL}/api/orgs/{org_id}/opportunities/{o['id']}",
                timeout=30)
