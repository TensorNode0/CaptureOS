"""Tests: per-org envelope encryption of API keys — masking, RBAC, rotation.

Uses a fresh org so no other suite's stored keys interfere."""
import os
import uuid
import pytest
import requests

BASE_URL = (os.environ.get("TEST_BASE_URL")
            or os.environ.get("REACT_APP_BACKEND_URL")
            or "http://localhost:8000").rstrip("/")

RAW_ANTHROPIC = "sk-ant-envelope-test-abcdef123456"
RAW_SAM = "SAM-ENVELOPE-TEST-9988776655"


@pytest.fixture(scope="module")
def env_org(admin_session):
    s, _ = admin_session
    r = s.post(f"{BASE_URL}/api/orgs",
               json={"name": f"Envelope Org {uuid.uuid4().hex[:6]}",
                     "naics": ["541511"], "keywords": ["crypto"], "certifyAor": True}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["id"]


class TestEnvelopeSecrets:
    def test_initial_state(self, admin_session, env_org):
        s, _ = admin_session
        r = s.get(f"{BASE_URL}/api/orgs/{env_org}/secrets", timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert body["anthropicSet"] is False
        assert body["samSet"] is False

    def test_save_masks_and_never_echoes_raw(self, admin_session, env_org):
        s, _ = admin_session
        r = s.put(f"{BASE_URL}/api/orgs/{env_org}/secrets",
                  json={"anthropicKey": RAW_ANTHROPIC, "samKey": RAW_SAM}, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["anthropicSet"] is True and body["samSet"] is True
        assert RAW_ANTHROPIC not in str(body)
        assert RAW_SAM not in str(body)
        assert "…" in body["anthropicKey"]

    def test_get_reports_key_version(self, admin_session, env_org):
        s, _ = admin_session
        body = s.get(f"{BASE_URL}/api/orgs/{env_org}/secrets", timeout=15).json()
        assert body.get("keyVersion", 0) >= 1
        assert RAW_ANTHROPIC not in str(body)

    def test_rotate_reencrypts_and_keys_survive(self, admin_session, env_org):
        s, _ = admin_session
        before = s.get(f"{BASE_URL}/api/orgs/{env_org}/secrets", timeout=15).json()
        r = s.post(f"{BASE_URL}/api/orgs/{env_org}/secrets/rotate-key", timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["keyVersion"] == before.get("keyVersion", 1) + 1
        # Masked previews are derived from decrypted plaintext, so an unchanged
        # mask proves the values survived re-encryption under the new DEK.
        after = s.get(f"{BASE_URL}/api/orgs/{env_org}/secrets", timeout=15).json()
        assert after["anthropicKey"] == before["anthropicKey"]
        assert after["samKey"] == before["samKey"]
        assert after["anthropicSet"] is True and after["samSet"] is True

    def test_masked_value_does_not_overwrite(self, admin_session, env_org):
        s, _ = admin_session
        before = s.get(f"{BASE_URL}/api/orgs/{env_org}/secrets", timeout=15).json()
        # Sending the masked preview back (as the UI would) must keep the key.
        r = s.put(f"{BASE_URL}/api/orgs/{env_org}/secrets",
                  json={"anthropicKey": before["anthropicKey"]}, timeout=15)
        assert r.status_code == 200
        after = s.get(f"{BASE_URL}/api/orgs/{env_org}/secrets", timeout=15).json()
        assert after["anthropicKey"] == before["anthropicKey"]
        assert after["anthropicSet"] is True

    def test_key_access_is_audited(self, admin_session, env_org):
        s, _ = admin_session
        r = s.get(f"{BASE_URL}/api/orgs/{env_org}/audit", timeout=15)
        assert r.status_code == 200
        actions = [a.get("action") for a in r.json()]
        assert "secrets.access" in actions, f"no secrets.access in {actions[:10]}"
        assert "secrets.rotate_key" in actions


class TestEnvelopeRBAC:
    """editor/viewer belong to the demo org, not env_org — but role checks on
    the demo org itself must also hold for the new rotate endpoint."""

    def test_editor_cannot_rotate(self, editor_session, org_id):
        s, _ = editor_session
        r = s.post(f"{BASE_URL}/api/orgs/{org_id}/secrets/rotate-key", timeout=15)
        assert r.status_code == 403

    def test_viewer_cannot_rotate(self, viewer_session, org_id):
        s, _ = viewer_session
        r = s.post(f"{BASE_URL}/api/orgs/{org_id}/secrets/rotate-key", timeout=15)
        assert r.status_code == 403

    def test_nonmember_cannot_read_secrets(self, editor_session, env_org):
        # editor is not a member of env_org at all
        s, _ = editor_session
        r = s.get(f"{BASE_URL}/api/orgs/{env_org}/secrets", timeout=15)
        assert r.status_code == 403


class TestNewProviderKeys:
    def test_emergent_and_asksage_roundtrip(self, admin_session, env_org):
        s, _ = admin_session
        r = s.put(f"{BASE_URL}/api/orgs/{env_org}/secrets",
                  json={"emergentKey": "sk-emergent-test-12345678",
                        "asksageKey": "asksage-token-abcdef99"}, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["emergentSet"] is True and body["asksageSet"] is True
        assert "…" in body["emergentKey"]  # masked preview, never the full key
        assert body["validation"]["emergent"] == "saved"
        assert body["validation"]["asksage"] == "saved"

    def test_status_endpoint_visible_to_members(self, admin_session, env_org):
        s, _ = admin_session
        r = s.get(f"{BASE_URL}/api/orgs/{env_org}/secrets/status", timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert set(body) == {"anthropicSet", "samSet", "openaiSet",
                             "emergentSet", "asksageSet"}
        assert all(isinstance(v, bool) for v in body.values())

    def test_new_keys_survive_rotation(self, admin_session, env_org):
        s, _ = admin_session
        before = s.get(f"{BASE_URL}/api/orgs/{env_org}/secrets", timeout=15).json()
        r = s.post(f"{BASE_URL}/api/orgs/{env_org}/secrets/rotate-key", timeout=15)
        assert r.status_code == 200
        after = s.get(f"{BASE_URL}/api/orgs/{env_org}/secrets", timeout=15).json()
        assert after["emergentSet"] is True and after["asksageSet"] is True
        assert after["emergentKey"] == before["emergentKey"]  # same mask -> decrypts
        assert after["keyVersion"] == before["keyVersion"] + 1
