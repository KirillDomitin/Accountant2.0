from collections.abc import AsyncGenerator

import redis.asyncio as aioredis

from app.core.config import settings

redis_client: aioredis.Redis | None = None


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    async with aioredis.from_url(settings.redis_url, decode_responses=True) as client:
        yield client


async def init_redis() -> None:
    global redis_client
    redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)


async def close_redis() -> None:
    global redis_client
    if redis_client:
        await redis_client.aclose()
        redis_client = None
