"""Redis async client for live state and pub/sub."""

import redis.asyncio as aioredis
from backend.config import config

client: aioredis.Redis | None = None


async def init_redis():
    global client
    client = aioredis.from_url(config.db.redis_url, decode_responses=True)


async def close_redis():
    global client
    if client:
        await client.aclose()
        client = None


async def publish(channel: str, message: str):
    if client:
        await client.publish(channel, message)


async def get_client() -> aioredis.Redis:
    if client is None:
        await init_redis()
    return client
