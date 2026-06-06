import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL") or "https://8d626961-5fb0-4ff9-bfac-7fe303cdef56.preview.emergentagent.com"
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
    assert orgs, "Admin has no organizations"
    # Find Orbital Defense Systems
    for o in orgs:
        if "Orbital" in o["name"]:
            return o["id"]
    return orgs[0]["id"]
