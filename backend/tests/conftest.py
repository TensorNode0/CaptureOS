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


def _login(email, password):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text}"
    me = r.json()
    # Auth cookies are flagged Secure (correct for browsers, incl. localhost),
    # but python-requests won't send Secure cookies over plain http — so tests
    # authenticate via the Bearer header the API also accepts.
    token = s.cookies.get("access_token")
    if token:
        s.headers["Authorization"] = f"Bearer {token}"
    return s, me


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
