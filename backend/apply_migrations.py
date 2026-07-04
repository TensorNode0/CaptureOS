"""Apply SQL migrations in supabase/migrations/ to DATABASE_URL.

Usage:  python apply_migrations.py
Also invoked automatically by the server at startup (AUTO_MIGRATE=1, default).
Tracks applied files in schema_migrations; each migration runs in its own
transaction, in filename order.
"""
import os
import asyncio
import pathlib

import asyncpg
from dotenv import load_dotenv

MIGRATIONS_DIR = pathlib.Path(__file__).resolve().parent.parent / "supabase" / "migrations"


async def apply_migrations(conn: asyncpg.Connection | None = None):
    own_conn = conn is None
    if own_conn:
        conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        await conn.execute(
            """create table if not exists schema_migrations (
                   filename   text primary key,
                   applied_at timestamptz not null default now()
               )"""
        )
        applied = {
            r["filename"]
            for r in await conn.fetch("select filename from schema_migrations")
        }
        pending = sorted(
            p for p in MIGRATIONS_DIR.glob("*.sql") if p.name not in applied
        )
        for path in pending:
            sql = path.read_text(encoding="utf-8")
            async with conn.transaction():
                await conn.execute(sql)
                await conn.execute(
                    "insert into schema_migrations (filename) values ($1)", path.name
                )
            print(f"[migrate] applied {path.name}")
        if not pending:
            print("[migrate] up to date")
    finally:
        if own_conn:
            await conn.close()


if __name__ == "__main__":
    load_dotenv()
    asyncio.run(apply_migrations())
