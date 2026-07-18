"""Stripe billing endpoints.

Public/user endpoints:
  POST /api/payments/checkout          → create a Stripe Checkout Session
  GET  /api/payments/status/{sid}      → poll payment_transactions (unauth)
  POST /api/payments/portal            → billing portal for cancel/update
  GET  /api/payments/me                → current user's subscription state
  POST /api/refund-requests            → user requests a refund
  POST /api/stripe/webhook             → Stripe → us (idempotent)

Platform (CaptureAgent-owned) endpoints — no UI label saying "super admin":
  GET  /api/refund-requests            → list pending
  POST /api/refund-requests/{id}/approve
  POST /api/refund-requests/{id}/deny

Tier gating is enforced by `require_tier(min_tier)` in `billing.py`.
"""
import os
from typing import Optional

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

import database as db
from auth_utils import get_current_user
from utils import as_uuid, now_utc
from domain import write_audit


router = APIRouter(prefix="/api", tags=["billing"])


def _stripe_key() -> str:
    return os.environ.get("STRIPE_SECRET_KEY") or "sk_test_emergent"


def _ensure_stripe():
    """Assign the API key on every call so tests can monkey-patch env vars."""
    stripe.api_key = _stripe_key()


def _tier_from_lookup(lookup_key: str) -> str:
    """Map a price lookup key like `full_yearly` → business tier `full`."""
    if lookup_key.startswith("oi"):
        return "oi"
    if lookup_key.startswith("full"):
        return "full"
    return "free"


# -------- CaptureAgent role helper (never surfaced as "super admin" in UI) --------

def _is_platform_owner(user: dict) -> bool:
    """Emails allowed to approve refunds / view pending refund queue. Configured
    via env var CAPTUREAGENT_OWNER_EMAILS (comma-separated). If unset in a
    preview environment we fall back to the QA test account so E2E flows work."""
    allow = [e.strip().lower() for e in
             (os.environ.get("CAPTUREAGENT_OWNER_EMAILS") or "").split(",") if e.strip()]
    if not allow and os.environ.get("AUTH_TEST_MODE", "0") == "1":
        allow = ["qa.captureagent@testmail.dev"]
    return (user.get("email") or "").lower() in allow


def require_platform_owner(user: dict = Depends(get_current_user)) -> dict:
    if not _is_platform_owner(user):
        raise HTTPException(status_code=403, detail="Not authorized.")
    return user


# ------------------------------ Checkout ------------------------------

class CheckoutIn(BaseModel):
    lookupKey: str          # e.g. "oi_monthly", "full_yearly"
    originUrl: str          # window.location.origin from the frontend


@router.post("/payments/checkout")
async def create_checkout(body: CheckoutIn, user: dict = Depends(get_current_user)):
    """Create a Stripe Checkout Session for the requested price. Uses
    allow_promotion_codes=True so the customer can type in codes I create on
    the Stripe Dashboard — no custom coupon admin required."""
    _ensure_stripe()
    prices = stripe.Price.list(lookup_keys=[body.lookupKey], active=True, limit=1).data
    if not prices:
        raise HTTPException(status_code=400,
            detail=f"Unknown plan: {body.lookupKey}. Run backend `setup_stripe.py`?")
    price = prices[0]
    if not price.recurring:
        raise HTTPException(status_code=400, detail="Selected price is not a subscription.")
    origin = body.originUrl.rstrip("/")
    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price.id, "quantity": 1}],
            customer_email=user.get("email"),
            allow_promotion_codes=True,
            client_reference_id=str(user["id"]),
            success_url=f"{origin}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{origin}/pricing?checkout=cancel",
            metadata={"user_id": str(user["id"]), "lookup_key": body.lookupKey,
                      "tier": _tier_from_lookup(body.lookupKey)},
            subscription_data={"metadata": {"user_id": str(user["id"]),
                                            "lookup_key": body.lookupKey,
                                            "tier": _tier_from_lookup(body.lookupKey)}},
        )
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=502,
            detail=f"Stripe rejected the request: {e.user_message or str(e)}")

    await db.execute(
        """insert into payment_transactions
              (session_id, user_id, lookup_key, amount_cents, currency,
               status, payment_status)
           values ($1, $2, $3, $4, $5, 'initiated', 'pending')
           on conflict (session_id) do nothing""",
        session.id, as_uuid(user["id"]), body.lookupKey,
        price.unit_amount or 0, price.currency)
    return {"url": session.url, "sessionId": session.id}


@router.get("/payments/status/{session_id}")
async def payment_status(session_id: str):
    """Unauth polling endpoint — returns only session_id/status/payment_status.
    Also inline-syncs from Stripe on any pending record so we don't stall if
    the webhook is delayed."""
    _ensure_stripe()
    row = await db.fetchrow(
        "select * from payment_transactions where session_id = $1", session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if row["payment_status"] != "paid":
        try:
            s = stripe.checkout.Session.retrieve(session_id)
            if s.payment_status == "paid" or s.status == "complete":
                await _apply_paid(session_id, s)
                row = await db.fetchrow(
                    "select * from payment_transactions where session_id = $1", session_id)
        except stripe.error.StripeError:
            pass
    return {"sessionId": row["session_id"],
            "status": row["status"],
            "paymentStatus": row["payment_status"]}


# ------------------------------ Billing Portal ------------------------------

class PortalIn(BaseModel):
    returnUrl: str


@router.post("/payments/portal")
async def billing_portal(body: PortalIn, user: dict = Depends(get_current_user)):
    """Create a Stripe billing portal session so the customer can cancel or
    update payment method on Stripe-hosted UI. Cancel-anytime with grace lives
    natively in the portal — we don't need to build cancel UI ourselves."""
    _ensure_stripe()
    sub = await db.fetchrow(
        "select * from user_subscriptions where user_id = $1", as_uuid(user["id"]))
    if not sub or not sub["stripe_customer_id"]:
        raise HTTPException(status_code=400,
            detail="No active subscription — you can subscribe from the Pricing page.")
    try:
        portal = stripe.billing_portal.Session.create(
            customer=sub["stripe_customer_id"],
            return_url=body.returnUrl or "https://captureagent.us/settings")
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {"url": portal.url}


# ------------------------------ Current subscription ------------------------------

@router.get("/payments/me")
async def my_subscription(user: dict = Depends(get_current_user)):
    """Return the caller's subscription snapshot (tier gating source of truth
    on the client). Auto-creates a `free` row so we always return SOMETHING."""
    row = await db.fetchrow(
        "select * from user_subscriptions where user_id = $1", as_uuid(user["id"]))
    if not row:
        row = await db.fetchrow(
            "insert into user_subscriptions (user_id) values ($1) returning *",
            as_uuid(user["id"]))
    return {
        "tier": row["tier"], "interval": row["interval"], "status": row["status"],
        "currentPeriodEnd": row["current_period_end"].isoformat() if row["current_period_end"] else None,
        "cancelAtPeriodEnd": row["cancel_at_period_end"],
        "isPlatformOwner": _is_platform_owner(user),
    }


# ------------------------------ Refund workflow ------------------------------

class RefundRequestIn(BaseModel):
    reason: str = Field(default="", max_length=1000)


@router.post("/refund-requests")
async def submit_refund_request(body: RefundRequestIn, user: dict = Depends(get_current_user)):
    """User submits a refund request. Captured against their most recent
    payment; CaptureAgent reviews on /admin (they alone approve)."""
    sub = await db.fetchrow(
        "select * from user_subscriptions where user_id = $1", as_uuid(user["id"]))
    tx = await db.fetchrow(
        """select * from payment_transactions
             where user_id = $1 and payment_status = 'paid'
             order by created_at desc limit 1""",
        as_uuid(user["id"]))
    row = await db.fetchrow(
        """insert into refund_requests
              (user_id, email, subscription_id, payment_intent_id, charge_id,
               reason)
           values ($1, $2, $3, $4, $5, $6)
           returning *""",
        as_uuid(user["id"]), user.get("email") or "",
        (sub or {}).get("stripe_subscription_id", ""),
        (tx or {}).get("stripe_payment_intent_id", ""),
        (tx or {}).get("stripe_charge_id", ""),
        body.reason)
    await write_audit(None, user, "billing.refund_request",
                      user.get("email"), {"reason": (body.reason or "")[:120]})
    return {"ok": True, "requestId": str(row["id"])}


@router.get("/refund-requests")
async def list_refund_requests(status: str = "pending",
                               user: dict = Depends(require_platform_owner)):
    rows = await db.fetch(
        """select id, user_id, email, subscription_id, payment_intent_id,
                  amount_cents_requested, amount_cents_refunded, reason,
                  status, requested_at, decided_at
             from refund_requests
             where status = $1
             order by requested_at desc limit 200""",
        status)
    return [{"id": str(r["id"]), "userId": str(r["user_id"]),
             "email": r["email"], "subscriptionId": r["subscription_id"],
             "paymentIntentId": r["payment_intent_id"],
             "amountCentsRequested": r["amount_cents_requested"],
             "amountCentsRefunded": r["amount_cents_refunded"],
             "reason": r["reason"], "status": r["status"],
             "requestedAt": r["requested_at"].isoformat() if r["requested_at"] else None,
             "decidedAt": r["decided_at"].isoformat() if r["decided_at"] else None}
            for r in rows]


class RefundDecisionIn(BaseModel):
    amountCents: Optional[int] = None    # None → full refund
    adminNotes: str = Field(default="", max_length=1000)


@router.post("/refund-requests/{req_id}/approve")
async def approve_refund(req_id: str, body: RefundDecisionIn,
                         user: dict = Depends(require_platform_owner)):
    """Approve a refund + issue it via Stripe. Full by default, partial when
    body.amountCents is provided (in cents)."""
    _ensure_stripe()
    r = await db.fetchrow(
        "select * from refund_requests where id = $1 and status = 'pending'",
        as_uuid(req_id))
    if not r:
        raise HTTPException(status_code=404, detail="Refund request not found or already decided.")
    pi = r["payment_intent_id"]
    if not pi:
        raise HTTPException(status_code=400,
            detail="No payment_intent on record — nothing to refund. Ask the user to reach out with their receipt.")
    try:
        params = {"payment_intent": pi}
        if body.amountCents:
            params["amount"] = int(body.amountCents)
        refund = stripe.Refund.create(**params)
    except stripe.error.StripeError as e:
        await db.execute(
            "update refund_requests set status = 'failed', admin_notes = $2, decided_at = $3, decided_by = $4 where id = $1",
            as_uuid(req_id), f"Stripe error: {e.user_message or e}", now_utc(), as_uuid(user["id"]))
        raise HTTPException(status_code=502, detail=str(e))
    await db.execute(
        """update refund_requests
             set status = 'approved',
                 amount_cents_refunded = $2,
                 stripe_refund_id = $3,
                 admin_notes = $4,
                 decided_at = $5,
                 decided_by = $6
             where id = $1""",
        as_uuid(req_id), int(refund.amount or 0), refund.id, body.adminNotes,
        now_utc(), as_uuid(user["id"]))
    await write_audit(None, user, "billing.refund_approved", r["email"],
                      {"amountCents": int(refund.amount or 0), "refundId": refund.id})
    return {"ok": True, "refundId": refund.id, "amountCents": int(refund.amount or 0)}


@router.post("/refund-requests/{req_id}/deny")
async def deny_refund(req_id: str, body: RefundDecisionIn,
                      user: dict = Depends(require_platform_owner)):
    r = await db.fetchrow(
        "select * from refund_requests where id = $1 and status = 'pending'",
        as_uuid(req_id))
    if not r:
        raise HTTPException(status_code=404, detail="Refund request not found or already decided.")
    await db.execute(
        """update refund_requests set status='denied', admin_notes=$2,
             decided_at=$3, decided_by=$4 where id=$1""",
        as_uuid(req_id), body.adminNotes, now_utc(), as_uuid(user["id"]))
    await write_audit(None, user, "billing.refund_denied", r["email"],
                      {"reason": (body.adminNotes or "")[:200]})
    return {"ok": True}


# ------------------------------ Webhook ------------------------------

async def _apply_paid(session_id: str, session_obj):
    """Idempotent flip of a checkout session to paid + subscription upsert."""
    lookup = (session_obj.metadata or {}).get("lookup_key", "")
    tier = _tier_from_lookup(lookup)
    interval = "year" if lookup.endswith("yearly") else "month"
    sub_id = session_obj.subscription or ""
    cust = session_obj.customer or ""
    pi = session_obj.payment_intent or ""
    await db.execute(
        """update payment_transactions
             set status='completed', payment_status='paid',
                 stripe_subscription_id=$2, stripe_payment_intent_id=$3,
                 updated_at=$4
             where session_id=$1 and payment_status <> 'paid'""",
        session_id, sub_id, pi, now_utc())
    user_id = (session_obj.metadata or {}).get("user_id", "") \
              or session_obj.client_reference_id
    if not user_id:
        return
    # Pull the period end from the sub object so cancel-anytime grace works.
    period_end = None
    if sub_id:
        try:
            sub = stripe.Subscription.retrieve(sub_id)
            if sub.current_period_end:
                from datetime import datetime, timezone
                period_end = datetime.fromtimestamp(sub.current_period_end, tz=timezone.utc)
        except stripe.error.StripeError:
            pass
    await db.execute(
        """insert into user_subscriptions
              (user_id, tier, interval, status,
               stripe_customer_id, stripe_subscription_id, current_period_end,
               cancel_at_period_end, updated_at)
           values ($1, $2, $3, 'active', $4, $5, $6, false, $7)
           on conflict (user_id) do update
             set tier=excluded.tier, interval=excluded.interval, status='active',
                 stripe_customer_id=excluded.stripe_customer_id,
                 stripe_subscription_id=excluded.stripe_subscription_id,
                 current_period_end=excluded.current_period_end,
                 cancel_at_period_end=false, updated_at=excluded.updated_at""",
        as_uuid(user_id), tier, interval, cust, sub_id, period_end, now_utc())


@router.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    _ensure_stripe()
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    try:
        if secret:
            event = stripe.Webhook.construct_event(payload, sig, secret)
        else:
            # Sandbox / local dev — accept unverified events. Never in prod.
            import json as _json
            event = _json.loads(payload.decode("utf-8"))
    except (stripe.error.SignatureVerificationError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid signature")

    obj = event["data"]["object"] if isinstance(event, dict) else event.data.object
    t = event["type"] if isinstance(event, dict) else event.type

    if t == "checkout.session.completed":
        await _apply_paid(obj["id"] if isinstance(obj, dict) else obj.id,
                          obj if not isinstance(obj, dict) else stripe.checkout.Session.retrieve(obj["id"]))

    elif t in ("customer.subscription.updated", "customer.subscription.deleted"):
        sub_id = obj["id"] if isinstance(obj, dict) else obj.id
        status = obj["status"] if isinstance(obj, dict) else obj.status
        cancel_at_pe = obj["cancel_at_period_end"] if isinstance(obj, dict) else obj.cancel_at_period_end
        cpe = obj["current_period_end"] if isinstance(obj, dict) else obj.current_period_end
        from datetime import datetime, timezone
        period_end = datetime.fromtimestamp(cpe, tz=timezone.utc) if cpe else None
        new_tier_input = obj.get("metadata", {}).get("tier") if isinstance(obj, dict) \
                          else (obj.metadata or {}).get("tier")
        set_free = t == "customer.subscription.deleted" or status in ("canceled", "unpaid")
        await db.execute(
            """update user_subscriptions
                 set status = $2,
                     tier = case when $3 then 'free' else coalesce(nullif($4,''), tier) end,
                     current_period_end = $5,
                     cancel_at_period_end = $6,
                     canceled_at = case when $3 then $7 else canceled_at end,
                     updated_at = $7
               where stripe_subscription_id = $1""",
            sub_id, status, set_free, new_tier_input or "",
            period_end, bool(cancel_at_pe), now_utc())

    elif t == "charge.refunded":
        pi = obj["payment_intent"] if isinstance(obj, dict) else obj.payment_intent
        await db.execute(
            """update payment_transactions set status='refunded', payment_status='refunded',
                 updated_at=$2 where stripe_payment_intent_id=$1""",
            pi, now_utc())

    elif t == "invoice.paid":
        # Nothing extra — subscription.updated fires alongside and carries the
        # period_end we care about.
        pass

    return {"ok": True}
