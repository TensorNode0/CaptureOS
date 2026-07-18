"""One-shot CaptureAgent Stripe catalog provisioner (standalone).

Creates or updates the 3 products + 4 prices in your live (or test) Stripe
account so the app's checkout URLs resolve.

Usage from PowerShell (Windows) or any shell:

    pip install stripe
    python provision_stripe.py sk_live_YOUR_KEY_HERE

Pass the key on the command line so it never touches your disk.

Safe to re-run: idempotent. If a price already exists with the right
amount + interval + seat_limit, nothing changes. If the amount drifted,
the old price is archived (lookup_key freed) and a new price is created
reusing the same lookup_key via transfer_lookup_key=True.
"""
import sys
import stripe

PRODUCTS = [
    {
        "emergent_product_id": "captureagent_oi",
        "name": "Opportunity Intelligence",
        "description": ("Federal opportunity intel, competitive analysis, and "
                        "private-capital + accelerator scans. Single-user seat."),
        "tax_code": "txcd_10103001",
        "tier": "oi",
        "prices": [
            {"lookup_key": "oi_monthly", "amount_cents": 4999,  "interval": "month", "seat_limit": 1},
            {"lookup_key": "oi_yearly",  "amount_cents": 48000, "interval": "year",  "seat_limit": 1},
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
            {"lookup_key": "full_monthly", "amount_cents": 9999,   "interval": "month", "seat_limit": 1},
            {"lookup_key": "full_yearly",  "amount_cents": 288000, "interval": "year",  "seat_limit": 3},
        ],
    },
]


def _get_or_create_product(entry):
    for p in stripe.Product.list(active=True, limit=100).auto_paging_iter():
        meta = p.to_dict().get("metadata", {}) or {}
        if meta.get("emergent_product_id") == entry["emergent_product_id"]:
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
                  seat_limit, currency="usd"):
    existing = stripe.Price.list(lookup_keys=[lookup_key], active=True, limit=1).data
    if existing:
        p = existing[0]
        if (p.unit_amount == amount_cents and p.currency == currency
                and (p.metadata or {}).get("seat_limit") == str(seat_limit)):
            return p
        stripe.Price.modify(p.id, active=False, lookup_key=None)
    return stripe.Price.create(
        product=product_id, unit_amount=amount_cents, currency=currency,
        lookup_key=lookup_key, transfer_lookup_key=True,
        recurring={"interval": interval},
        metadata={"seat_limit": str(seat_limit)})


def main(key):
    stripe.api_key = key
    mode = "LIVE" if key.startswith("sk_live_") or key.startswith("rk_live_") else "TEST"
    print(f"[stripe] Provisioning against Stripe in {mode} mode\n")
    for entry in PRODUCTS:
        product = _get_or_create_product(entry)
        for pr in entry["prices"]:
            price = _ensure_price(product.id, pr["lookup_key"], pr["amount_cents"],
                                  pr["interval"], pr["seat_limit"])
            print(f"  {entry['name']:42s}  {price.lookup_key:14s}  "
                  f"${price.unit_amount/100:>9,.2f}/{pr['interval']:<5s}  "
                  f"seats={pr['seat_limit']}")
    print("\n[stripe] Done. Verify at https://dashboard.stripe.com/products")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python provision_stripe.py sk_live_YOUR_KEY_HERE")
        print("       (or an rk_live_ Restricted Key with read+write on Products, Prices)")
        sys.exit(1)
    main(sys.argv[1].strip())
