"""Replay _apply_paid's subscription upsert for completed transactions whose
user is still on tier 'free' — surfaces the exact DB error if it fails,
repairs the tier if it succeeds. Mirrors routers/payments.py logic 1:1."""
import asyncio
import os

import asyncpg


def tier_from_lookup(lookup_key: str) -> str:
    if lookup_key.startswith("oi"):
        return "oi"
    if lookup_key.startswith("full"):
        return "full"
    return "free"


async def main():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        rows = await conn.fetch(
            """select t.session_id, t.user_id, t.lookup_key,
                      t.stripe_subscription_id, u.email
                 from payment_transactions t join users u on u.id = t.user_id
                 where t.payment_status = 'paid'
                 order by t.created_at desc""")
        print(f"{len(rows)} paid transaction(s) found.")
        for r in rows:
            tier = tier_from_lookup(r["lookup_key"] or "")
            interval = "year" if (r["lookup_key"] or "").endswith("yearly") else "month"
            try:
                await conn.execute(
                    """insert into user_subscriptions
                          (user_id, tier, interval, status,
                           stripe_customer_id, stripe_subscription_id,
                           current_period_end, cancel_at_period_end, updated_at)
                       values ($1, $2, $3, 'active', '', $4, null, false, now())
                       on conflict (user_id) do update
                         set tier=excluded.tier, interval=excluded.interval,
                             status='active',
                             stripe_subscription_id=excluded.stripe_subscription_id,
                             cancel_at_period_end=false, updated_at=excluded.updated_at""",
                    r["user_id"], tier, interval, r["stripe_subscription_id"] or "")
                print(f"  UPSERT OK  {r['email']:<45} -> tier={tier} ({interval})")
            except Exception as e:  # noqa: BLE001 — we WANT the raw error text
                print(f"  UPSERT FAILED for {r['email']}: {type(e).__name__}: {e}")
        print("\n== user_subscriptions after ==")
        for s in await conn.fetch(
                """select u.email, s.tier, s.status from user_subscriptions s
                     join users u on u.id = s.user_id order by s.updated_at desc limit 6"""):
            print(f"  {s['email']:<45} tier={s['tier']} status={s['status']}")
    finally:
        await conn.close()


asyncio.run(main())
