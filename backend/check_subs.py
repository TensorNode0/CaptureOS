"""Read-only diagnostic: recent payment transactions + subscription tiers."""
import asyncio
import os

import asyncpg


async def main():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        print("== payment_transactions (latest 5) ==")
        for r in await conn.fetch(
                """select session_id, lookup_key, amount_cents, status,
                          payment_status, created_at
                     from payment_transactions order by created_at desc limit 5"""):
            print(f"  {r['created_at']:%m-%d %H:%M}  {r['lookup_key']:<13} "
                  f"{r['amount_cents']:>7}c  status={r['status']}/{r['payment_status']} "
                  f" sid={r['session_id'][:24]}…")
        print("\n== user_subscriptions ==")
        for r in await conn.fetch(
                """select u.email, s.tier, s.interval, s.status,
                          s.current_period_end, s.updated_at
                     from user_subscriptions s join users u on u.id = s.user_id
                     order by s.updated_at desc limit 10"""):
            print(f"  {r['email']:<45} tier={r['tier'] or 'free':<10} "
                  f"{r['interval'] or '-':<6} status={r['status']} "
                  f"end={r['current_period_end']}")
    finally:
        await conn.close()


asyncio.run(main())
