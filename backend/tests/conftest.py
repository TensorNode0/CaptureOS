import os
import pytest
import requests

BASE_URL = (os.environ.get("TEST_BASE_URL")
            or os.environ.get("REACT_APP_BACKEND_URL")
            or "http://localhost:8000")
BASE_URL = BASE_URL.rstrip("/")

ADMIN = ("admin@govcon.io", "Admin#2026")
EDITOR = ("editor@govcon.io", "Editor#2026")
VIEWER = ("viewer@govcon.io", "Editor#2026")


def _login(email, password=None, name=""):
    """Obtain an authenticated session. Auth is owned by Supabase; tests use the
    AUTH_TEST_MODE-only /auth/test-login to mint a Supabase-shaped token and
    auto-provision the profile — no live Supabase project required. Unknown
    emails are created on demand (replaces the old register+login dance)."""
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/test-login",
               json={"email": email, "name": name}, timeout=30)
    assert r.status_code == 200, f"test-login failed for {email}: {r.status_code} {r.text}"
    me = r.json()
    s.headers["Authorization"] = f"Bearer {me['accessToken']}"
    return s, me


def auth_session(email, name=""):
    """Public helper for test modules that used to register+login a fresh user."""
    return _login(email, name=name)


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def admin_session():
    return _login(*ADMIN)


@pytest.fixture(scope="session")
def editor_session():
    return _login(*EDITOR)


@pytest.fixture(scope="session")
def viewer_session():
    return _login(*VIEWER)


@pytest.fixture(scope="session")
def org_id(admin_session):
    _, me = admin_session
    orgs = me.get("organizations", [])
    assert orgs, "Admin has no organizations (is SEED_DEMO=1 set?)"
    for o in orgs:
        if "Orbital" in o["name"]:
            return o["id"]
    return orgs[0]["id"]
