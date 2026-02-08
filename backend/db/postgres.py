"""PostgreSQL connection pool and query helpers using asyncpg."""

import asyncpg
from backend.config import config

pool: asyncpg.Pool | None = None


async def init_pool():
    global pool
    pool = await asyncpg.create_pool(config.db.postgres_url, min_size=2, max_size=10)


async def close_pool():
    global pool
    if pool:
        await pool.close()
        pool = None


async def fetch(query: str, *args) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *args)
        return [dict(r) for r in rows]


async def fetchrow(query: str, *args) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, *args)
        return dict(row) if row else None


async def fetchval(query: str, *args):
    async with pool.acquire() as conn:
        return await conn.fetchval(query, *args)


async def execute(query: str, *args) -> str:
    async with pool.acquire() as conn:
        return await conn.execute(query, *args)
