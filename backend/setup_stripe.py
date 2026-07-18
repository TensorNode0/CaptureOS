"""One-off Stripe catalog bootstrap. Idempotent — re-run any time.

Creates three products (Opportunity Intelligence · $49.99, Full Capture ·
$99.99, Enterprise · contact-us) with monthly + yearly prices.

Pricing model (customer-visible):
  * OI monthly:   $49.99/user/mo — single seat
  * OI yearly:    $479.90/user/yr — single seat, 20% off vs. 12 × monthly
  * Full monthly: $99.99/user/mo — single seat
  * Full yearly:  $2,879.71 — bundles up to 3 seats (3 × 12 × $99.99 × 0.80)
  * Enterprise: sales-led, no Stripe price

Each product carries `metadata.emergent_product_id` for stable lookup so we
never depend on Stripe-generated IDs. Prices are looked up by `lookup_key`.
When we change unit_amount, the old Stripe price is archived (its lookup_key
freed) and a new price is created reusing the same lookup_key — that way the
backend code never needs to change to pick up new pricing.

Run: `python -m setup_stripe`.
"""
import os

import stripe
from dotenv import load_dotenv


# Yearly rows are FLAT prices — not derived from monthly at run time — because
# some plans bundle multiple seats (Full yearly = 3 seats). Keeping the number
# explicit avoids ambiguity between "per seat" and "per subscription".
PRODUCTS = [
    {
        "emergent_product_id": "captureagent_oi",
        "name": "Opportunity Intelligence",
        "description": ("Federal opportunity intel, competitive analysis, and "
                        "private-capital + accelerator scans. Single-user seat."),
        "tax_code": "txcd_10103001",   # SaaS
        "tier": "oi",
        "prices": [
            {"lookup_key": "oi_monthly", "amount_cents": 4999, "interval": "month",
             "seat_limit": 1},
            {"lookup_key": "oi_yearly",  "amount_cents": 48000, "interval": "year",
             "seat_limit": 1},
        ],
    },
    {
        "emergent_product_id": "captureagent_full",
        "name": "Full Capture & Proposal Generation",
        "description": ("Everything in Opportunity Intelligence, plus AI drafting "
                        "for federal proposals, investor decks/emails/plans, and "
                        "accelerator applications. Includes disk storage and the "
                        "AI chat assistant."),
        "tax_code": "txcd_10103001",
        "tier": "full",
        "prices": [
            {"lookup_key": "full_monthly", "amount_cents": 9999, "interval": "month",
             "seat_limit": 1},
            # 3 seats bundled — priced at $2,880/yr for readability (20% off vs.
            # 3 × 12 × $99.99 = $3,599.64 baseline).
            {"lookup_key": "full_yearly",  "amount_cents": 288000, "interval": "year",
             "seat_limit": 3},
        ],
    },
]


def _get_or_create_product(entry):
    for p in stripe.Product.list(active=True, limit=100).auto_paging_iter():
        meta = p.to_dict().get("metadata", {}) or {}
        if meta.get("emergent_product_id") == entry["emergent_product_id"]:
            # Keep description/tax_code fresh so edits here take effect on next run.
            stripe.Product.modify(p.id, name=entry["name"],
                                  description=entry.get("description", ""),
                                  tax_code=entry.get("tax_code"),
                                  metadata={**meta, "tier": entry["tier"]})
            return p
    return stripe.Product.create(
        name=entry["name"], description=entry.get("description", ""),
        tax_code=entry.get("tax_code"),
        metadata={"managed_by": "captureagent",
                  "emergent_product_id": entry["emergent_product_id"],
                  "tier": entry["tier"]})


def _ensure_price(product_id, lookup_key, amount_cents, interval,
                  seat_limit: int, currency: str = "usd"):
    existing = stripe.Price.list(lookup_keys=[lookup_key], active=True, limit=1).data
    if existing:
        p = existing[0]
        if (p.unit_amount == amount_cents and p.currency == currency
                and (p.metadata or {}).get("seat_limit") == str(seat_limit)):
            return p
        # Anything drifted → archive the existing price so lookup_key + amount
        # can move onto the new active price without collision.
        stripe.Price.modify(p.id, active=False, lookup_key=None)
    return stripe.Price.create(
        product=product_id, unit_amount=amount_cents, currency=currency,
        lookup_key=lookup_key, transfer_lookup_key=True,
        recurring={"interval": interval},
        metadata={"seat_limit": str(seat_limit)})


def main():
    load_dotenv("/app/backend/.env")
    key = os.environ.get("STRIPE_SECRET_KEY") or "sk_test_emergent"
    if not key or key == "sk_test_emergent":
        print("[stripe] using default emergent key — sandbox not provisioned yet?")
    stripe.api_key = key

    for entry in PRODUCTS:
        product = _get_or_create_product(entry)
        for pr in entry["prices"]:
            price = _ensure_price(product.id, pr["lookup_key"], pr["amount_cents"],
                                  pr["interval"], pr["seat_limit"])
            print(f"[stripe] {entry['name']:42s} {price.lookup_key:14s} "
                  f"${price.unit_amount/100:>9,.2f}/{pr['interval']:<5s} "
                  f"seats={pr['seat_limit']}")


if __name__ == "__main__":
    main()
