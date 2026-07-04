"""Per-organization envelope encryption for API keys.

Model:
- Every organization gets a random 256-bit data-encryption key (DEK).
- API-key values are encrypted (Fernet/AES-128-CBC+HMAC) with the org's DEK.
- The DEK is never stored in plaintext: it is wrapped (encrypted) by the
  master key SECRETS_ENC_KEY, which lives only in the server environment —
  never in the database, the repo, or any API response.
- Rotating an org's DEK re-encrypts that org's secrets under a fresh key and
  bumps key_version.
- Every decrypt-for-use is audit-logged with a purpose tag, giving orgs a
  verifiable access trail (CMMC/NIST 800-171 3.1.x / 3.3.x support).

Plaintext keys exist only transiently in server memory at the moment of an
outbound SAM/Anthropic/OpenAI call and are never returned to any client
(admins see masked previews only).
"""
import os
from cryptography.fernet import Fernet, InvalidToken

import database as db
from utils import as_uuid, now_utc

_master = Fernet(os.environ["SECRETS_ENC_KEY"].encode())

KEY_COLUMNS = {"anthropic": "anthropic_key", "sam": "sam_key", "openai": "openai_key"}


def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 6:
        return "•" * len(value)
    return value[:3] + "…" + value[-4:]


def _wrap_dek(dek: bytes) -> str:
    return _master.encrypt(dek).decode()


def _unwrap_dek(wrapped: str):
    if not wrapped:
        return None
    try:
        return Fernet(_master.decrypt(wrapped.encode()))
    except (InvalidToken, ValueError):
        return None


def _decrypt(dek_fernet, token: str) -> str:
    """Decrypt a stored value: org DEK first, then legacy master-key format
    (rows written before envelope encryption existed)."""
    if not token:
        return ""
    if dek_fernet is not None:
        try:
            return dek_fernet.decrypt(token.encode()).decode()
        except (InvalidToken, ValueError):
            pass
    try:
        return _master.decrypt(token.encode()).decode()
    except (InvalidToken, ValueError):
        return ""


async def _get_row(org_id):
    return await db.fetchrow("select * from org_secrets where organization_id = $1",
                             as_uuid(org_id))


async def _audit_access(org_id, user, purpose, keys_used):
    await db.execute(
        """insert into audit_log (organization_id, user_id, user_email, user_name,
                                  action, target, meta)
           values ($1, $2, $3, $4, 'secrets.access', $5, $6)""",
        as_uuid(org_id), as_uuid((user or {}).get("id")),
        (user or {}).get("email"), (user or {}).get("name"),
        purpose, {"keys": keys_used})


async def get_keys(org_id, user=None, purpose="") -> dict:
    """Decrypt the org's API keys for immediate server-side use.
    Returns {"anthropic": str, "sam": str, "openai": str} ("" when unset).
    Logs an org-visible 'secrets.access' audit event when keys are present."""
    row = await _get_row(org_id)
    if not row:
        return {name: "" for name in KEY_COLUMNS}
    dek = _unwrap_dek(row.get("dek_wrapped", ""))
    out = {name: _decrypt(dek, row.get(col, "")) for name, col in KEY_COLUMNS.items()}
    used = [name for name, v in out.items() if v]
    if purpose and used:
        await _audit_access(org_id, user, purpose, used)
    return out


async def ensure_dek(org_id):
    """Get (creating if needed) the org's DEK. Returns (Fernet, row)."""
    row = await _get_row(org_id)
    if row and row.get("dek_wrapped"):
        dek = _unwrap_dek(row["dek_wrapped"])
        if dek is not None:
            return dek, row
    raw = Fernet.generate_key()
    wrapped = _wrap_dek(raw)
    if row:
        row = await db.fetchrow(
            "update org_secrets set dek_wrapped = $2 where organization_id = $1 returning *",
            as_uuid(org_id), wrapped)
    else:
        row = await db.fetchrow(
            """insert into org_secrets (organization_id, dek_wrapped)
               values ($1, $2) returning *""",
            as_uuid(org_id), wrapped)
    return Fernet(raw), row


async def store_keys(org_id, updates: dict, updated_by):
    """Encrypt-and-store API keys with the org DEK.

    updates: {"anthropic": newValue|None, ...} — None/masked values keep the
    existing key; kept values are re-encrypted under the DEK (normalizing any
    legacy master-key ciphertext). Returns the decrypted current values."""
    dek, row = await ensure_dek(org_id)
    current = {name: _decrypt(dek, (row or {}).get(col, ""))
               for name, col in KEY_COLUMNS.items()}
    for name, new_value in updates.items():
        if name not in KEY_COLUMNS:
            continue
        if new_value is not None and new_value.strip() and "…" not in new_value:
            current[name] = new_value.strip()
    encrypted = {col: (dek.encrypt(current[name].encode()).decode() if current[name] else "")
                 for name, col in KEY_COLUMNS.items()}
    await db.execute(
        """update org_secrets
           set anthropic_key = $2, sam_key = $3, openai_key = $4,
               updated_by = $5, updated_at = $6
           where organization_id = $1""",
        as_uuid(org_id), encrypted["anthropic_key"], encrypted["sam_key"],
        encrypted["openai_key"], as_uuid(updated_by), now_utc())
    return current


async def rotate_key(org_id, rotated_by):
    """Re-encrypt the org's secrets under a brand-new DEK. Returns new version."""
    dek, row = await ensure_dek(org_id)
    current = {name: _decrypt(dek, row.get(col, "")) for name, col in KEY_COLUMNS.items()}
    new_raw = Fernet.generate_key()
    new_dek = Fernet(new_raw)
    encrypted = {col: (new_dek.encrypt(current[name].encode()).decode() if current[name] else "")
                 for name, col in KEY_COLUMNS.items()}
    fresh = await db.fetchrow(
        """update org_secrets
           set dek_wrapped = $2, anthropic_key = $3, sam_key = $4, openai_key = $5,
               key_version = key_version + 1, updated_by = $6, updated_at = $7
           where organization_id = $1
           returning key_version""",
        as_uuid(org_id), _wrap_dek(new_raw), encrypted["anthropic_key"],
        encrypted["sam_key"], encrypted["openai_key"], as_uuid(rotated_by), now_utc())
    return fresh["key_version"]
