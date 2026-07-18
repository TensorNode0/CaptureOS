"""One-off Stripe catalog bootstrap. Idempotent — re-run any time.

Creates three products (Opportunity Intelligence · $49, Full Capture · $99,
Enterprise · contact-us) with monthly + yearly prices. Yearly gets a
15% discount from 12× monthly (rounded to the nearest cent).
Enterprise has no Stripe price — sales-led.

Each product carries `metadata.emergent_product_id` for stable lookup so we
never depend on Stripe-generated IDs. Prices are looked up by `lookup_key`.

Run: `python -m setup_stripe`.
"""
import os
import sys

import stripe
from dotenv import load_dotenv


PRODUCTS = [
    {
        "emergent_product_id": "captureagent_oi",
        "name": "Opportunity Intelligence",
        "description": ("Scans for new federal opportunities, private capital, and "
                        "accelerators — no proposal or application generation."),
        "monthly_cents": 4900,
        "tax_code": "txcd_10103001",  # SaaS
        "tier": "oi",
    },
    {
        "emergent_product_id": "captureagent_full",
        "name": "Full Capture & Proposal Generation",
        "description": ("Everything in Opportunity Intelligence, plus AI proposal, "
                        "investor email, and accelerator application drafting."),
        "monthly_cents": 9900,
        "tax_code": "txcd_10103001",
        "tier": "full",
    },
]


def _yearly_cents(monthly_cents: int) -> int:
    """12x monthly with a 15% discount, rounded to the nearest cent."""
    return round(monthly_cents * 12 * 0.85)


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


def _ensure_price(product_id, lookup_key, amount_cents, interval, currency="usd"):
    existing = stripe.Price.list(lookup_keys=[lookup_key], active=True, limit=1).data
    if existing:
        p = existing[0]
        if p.unit_amount == amount_cents and p.currency == currency:
            return p
        # Amount changed → deactivate old price so lookup_key can be reassigned.
        stripe.Price.modify(p.id, active=False, lookup_key=None)
    return stripe.Price.create(
        product=product_id, unit_amount=amount_cents, currency=currency,
        lookup_key=lookup_key, transfer_lookup_key=True,
        recurring={"interval": interval})


def main():
    load_dotenv("/app/backend/.env")
    key = os.environ.get("STRIPE_SECRET_KEY") or "sk_test_emergent"
    if not key or key == "sk_test_emergent":
        print("[stripe] using default emergent key — sandbox not provisioned yet?")
    stripe.api_key = key

    for entry in PRODUCTS:
        product = _get_or_create_product(entry)
        m = _ensure_price(product.id,
                          f"{entry['tier']}_monthly", entry["monthly_cents"], "month")
        y = _ensure_price(product.id,
                          f"{entry['tier']}_yearly",  _yearly_cents(entry["monthly_cents"]), "year")
        print(f"[stripe] {entry['name']:40s} monthly={m.lookup_key} ${m.unit_amount/100:.2f} "
              f"yearly={y.lookup_key} ${y.unit_amount/100:.2f}")


if __name__ == "__main__":
    main()
