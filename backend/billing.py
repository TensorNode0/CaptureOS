"""Tier gating for feature access.

Sits ON TOP of RBAC (org role): even if a user has editor/admin on their org,
their subscription tier may still block Federal Proposals / Investment Deals /
Accelerator Applications. `oi` ($49) → scans + opportunities only. `full` ($99)
→ everything. `enterprise` → everything, sales-led.

Two shapes exported:
  * `require_full_tier` — FastAPI dependency that returns the caller's ctx as
    long as their sub is 'full' or 'enterprise' (or the org has NEVER paid but
    the platform owner grandfathered them via env var).
  * `assert_full_tier(user)` — imperative helper for endpoints whose main gate
    is `require_role(...)` but which also need a tier check inside the body
    (e.g. venture-doc endpoints where we only block a subset of `kind`s).

The database source of truth is `user_subscriptions.tier`. A missing row is
treated as `free` — same as the /api/payments/me endpoint.
"""
import os
from typing import Iterable

from fastapi import Depends, HTTPException, Path

import database as db
from auth_utils import get_current_user
from rbac import _build_ctx
from utils import as_uuid


# Business tiers we care about, in ascending order of privilege.
_TIER_RANK = {"free": 0, "oi": 1, "full": 2, "enterprise": 3}

# Venture-doc kinds that require the `full` tier. Scans (accelerator_scan,
# investor_scan) are intentionally EXCLUDED — those live on the Private Capital
# / Accelerators tabs which the $49 tier retains full access to.
FULL_TIER_VENTURE_KINDS = {"investor_email", "pitch_deck", "business_plan",
                           "financials", "accelerator_application"}


def _grandfathered_emails() -> set:
    """Comma-separated email allowlist (env var) that bypasses tier gating.
    Used for the platform owner + demo accounts in QA."""
    raw = os.environ.get("BILLING_TIER_ALLOWLIST") or ""
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


async def _user_tier(user: dict) -> str:
    row = await db.fetchrow(
        "select tier, status from user_subscriptions where user_id = $1",
        as_uuid(user["id"]))
    if not row:
        return "free"
    # A subscription that has been cancelled/failed should NOT retain tier
    # access after the grace period — but our webhook already flips `tier` to
    # 'free' when Stripe reports canceled/unpaid, so trust the stored value.
    return row["tier"] or "free"


def _tier_allowed(tier: str, min_tier: str) -> bool:
    return _TIER_RANK.get(tier, 0) >= _TIER_RANK.get(min_tier, 99)


async def assert_tier(user: dict, min_tier: str) -> str:
    """Raise 402 Payment Required if the caller's tier doesn't meet min_tier.
    Returns the effective tier (useful for callers that log it)."""
    if (user.get("email") or "").lower() in _grandfathered_emails():
        return "enterprise"
    tier = await _user_tier(user)
    if not _tier_allowed(tier, min_tier):
        raise HTTPException(
            status_code=402,
            detail=(
                f"This feature is only available on the Full Capture plan. "
                f"Upgrade at /pricing to unlock it."
            ))
    return tier


async def assert_full_tier(user: dict) -> str:
    return await assert_tier(user, "full")


def require_tier(min_tier: str):
    """FastAPI dependency: enforces tier AND returns the standard org ctx so
    routes can chain onto it just like `require_role(...)`."""
    async def _dep(orgId: str = Path(...), user: dict = Depends(get_current_user)):
        await assert_tier(user, min_tier)
        return await _build_ctx(orgId, user)
    return _dep


def gate_kinds(kind: str, restricted: Iterable[str] = FULL_TIER_VENTURE_KINDS) -> bool:
    return kind in set(restricted)
