"""PostgreSQL (Supabase) data layer — asyncpg pool + thin query helpers.

DATABASE_URL accepts any PostgreSQL URI, including the Supabase session-pooler
connection string. JSONB columns are transparently encoded/decoded to Python
dicts/lists.
"""
import os
import json

import asyncpg

_pool: asyncpg.Pool | None = None


async def _init_conn(conn: asyncpg.Connection):
    await conn.set_type_codec(
        "jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
    )
    await conn.set_type_codec(
        "json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
    )


async def init_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            os.environ["DATABASE_URL"],
            min_size=1,
            max_size=int(os.environ.get("DB_POOL_MAX", "10")),
            init=_init_conn,
            # Supabase's pooler (pgbouncer transaction mode) rejects prepared
            # statement reuse; a zero cache keeps both modes working.
            statement_cache_size=0,
        )
    return _pool


async def close_pool():
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("DB pool not initialized — call init_pool() first")
    return _pool


async def fetch(query: str, *args) -> list[dict]:
    rows = await pool().fetch(query, *args)
    return [dict(r) for r in rows]


async def fetchrow(query: str, *args) -> dict | None:
    row = await pool().fetchrow(query, *args)
    return dict(row) if row is not None else None


async def fetchval(query: str, *args):
    return await pool().fetchval(query, *args)


async def execute(query: str, *args) -> str:
    return await pool().execute(query, *args)
