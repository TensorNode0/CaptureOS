"""App-layer encryption for sensitive user-entered content.

Reuses the per-organization envelope key from org_keys (a random org DEK that
is itself wrapped by the master SECRETS_ENC_KEY) so that free-text a user or
the AI produces — proposal/application/investor/competitive content and
org-profile narrative fields — is stored as ciphertext at rest, on top of
Supabase's own disk encryption.

Encrypted values carry an "enc:v1:" prefix, so ciphertext and legacy plaintext
can coexist during backfill: decrypt is a passthrough for anything without the
prefix. Only encrypt org-scoped fields that are NEVER filtered/sorted/queried
in SQL — never emails, titles, statuses, dates, or amounts.
"""
import json

from cryptography.fernet import InvalidToken

import org_keys

PREFIX = "enc:v1:"


def is_encrypted(value) -> bool:
    return isinstance(value, str) and value.startswith(PREFIX)


async def encrypt_text(org_id, text):
    """Encrypt a string under the org's DEK. None/'' pass through unchanged."""
    if not text:
        return text
    if is_encrypted(text):
        return text  # already encrypted — idempotent
    dek, _ = await org_keys.ensure_dek(org_id)
    return PREFIX + dek.encrypt(text.encode("utf-8")).decode()


async def decrypt_text(org_id, value):
    """Decrypt a stored value. Legacy plaintext (no prefix) passes through, so
    reads keep working before/after backfill."""
    if not is_encrypted(value):
        return value
    dek, _ = await org_keys.ensure_dek(org_id)
    try:
        return dek.decrypt(value[len(PREFIX):].encode()).decode()
    except (InvalidToken, ValueError):
        return value  # never hard-fail a read on a decrypt hiccup


async def encrypt_json(org_id, data):
    """Encrypt a JSON-serializable object to a single ciphertext string."""
    if data in (None, {}, []):
        return data
    return await encrypt_text(org_id, json.dumps(data, separators=(",", ":")))


async def decrypt_json(org_id, value):
    """Inverse of encrypt_json. A plaintext dict/list (already decrypted or
    never encrypted) passes through untouched."""
    if not is_encrypted(value):
        return value
    plain = await decrypt_text(org_id, value)
    try:
        return json.loads(plain)
    except (json.JSONDecodeError, TypeError):
        return plain
