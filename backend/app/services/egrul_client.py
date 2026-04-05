"""HTTP клиент для ЕГРЮЛ API с Redis-кэшированием."""
import json

import httpx
import redis.asyncio as aioredis

from app.core.config import settings
from app.core.exceptions import EgrulAPIError, OrganizationNotFoundError

_CACHE_KEY_PREFIX = "egrul:inn:"


def _cache_key(inn: str) -> str:
    return f"{_CACHE_KEY_PREFIX}{inn}"


async def fetch_egrul_data(
    inn: str, redis: aioredis.Redis, force_refresh: bool = False
) -> dict:
    """
    Возвращает сырой JSON из ЕГРЮЛ API.
    Сначала проверяет Redis-кэш (TTL = egrul_cache_ttl).
    При промахе делает HTTP-запрос и кладёт результат в кэш.
    force_refresh=True — игнорирует кэш и обновляет его.
    """
    if not force_refresh:
        cached = await redis.get(_cache_key(inn))
        if cached:
            return json.loads(cached)

    url = f"{settings.egrul_api_base_url}/{inn}.json"
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url)
        except httpx.RequestError as exc:
            raise EgrulAPIError(f"Ошибка соединения с ЕГРЮЛ API: {exc}") from exc

    if response.status_code == 404:
        raise OrganizationNotFoundError(f"Организация с ИНН {inn} не найдена")

    if response.status_code != 200:
        raise EgrulAPIError(
            f"ЕГРЮЛ API вернул статус {response.status_code}"
        )

    try:
        data = response.json()
    except Exception as exc:
        raise EgrulAPIError(f"Не удалось разобрать ответ ЕГРЮЛ API: {exc}") from exc

    if not data:
        raise OrganizationNotFoundError(f"Организация с ИНН {inn} не найдена")

    await redis.setex(_cache_key(inn), settings.egrul_cache_ttl, json.dumps(data))

    return data


async def invalidate_cache(inn: str, redis: aioredis.Redis) -> None:
    """Принудительно сбрасывает кэш для данного ИНН."""
    await redis.delete(_cache_key(inn))
