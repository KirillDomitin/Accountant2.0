"""HTTP клиент для ЕГРЮЛ API с Redis-кэшированием."""
import json
import logging

import httpx
import redis.asyncio as aioredis

from app.core.config import settings
from app.core.exceptions import EgrulAPIError, OrganizationNotFoundError

logger = logging.getLogger(__name__)

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
            logger.info("Cache hit for INN %s", inn)
            return json.loads(cached)

    logger.info("Fetching EGRUL data for INN %s (force_refresh=%s)", inn, force_refresh)
    url = f"{settings.egrul_api_base_url}/{inn}.json"
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url)
        except httpx.RequestError as exc:
            logger.error("Connection error to EGRUL API for INN %s: %s", inn, exc)
            raise EgrulAPIError(f"Ошибка соединения с ЕГРЮЛ API: {exc}") from exc

    if response.status_code == 404:
        logger.info("Organization not found in EGRUL for INN %s", inn)
        raise OrganizationNotFoundError(f"Организация с ИНН {inn} не найдена")

    if response.status_code != 200:
        logger.error("EGRUL API returned status %s for INN %s", response.status_code, inn)
        raise EgrulAPIError(
            f"ЕГРЮЛ API вернул статус {response.status_code}"
        )

    try:
        data = response.json()
    except Exception as exc:
        logger.error("Failed to parse EGRUL API response for INN %s: %s", inn, exc)
        raise EgrulAPIError(f"Не удалось разобрать ответ ЕГРЮЛ API: {exc}") from exc

    if not data:
        logger.info("Empty response from EGRUL for INN %s", inn)
        raise OrganizationNotFoundError(f"Организация с ИНН {inn} не найдена")

    await redis.setex(_cache_key(inn), settings.egrul_cache_ttl, json.dumps(data))
    logger.info("EGRUL data cached for INN %s (TTL=%ds)", inn, settings.egrul_cache_ttl)

    return data


async def invalidate_cache(inn: str, redis: aioredis.Redis) -> None:
    """Принудительно сбрасывает кэш для данного ИНН."""
    await redis.delete(_cache_key(inn))
