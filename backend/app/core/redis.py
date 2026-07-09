from collections.abc import AsyncGenerator

import redis.asyncio as redis
from redis.asyncio import Redis

from app.core.config import settings

EVENTS_RAW_CHANNEL = "events:raw"

_redis_client: Redis | None = None


async def get_redis_client() -> Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def close_redis_client() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None


async def redis_health_check() -> bool:
    client = await get_redis_client()
    return await client.ping()


async def get_redis() -> AsyncGenerator[Redis, None]:
    client = await get_redis_client()
    yield client
