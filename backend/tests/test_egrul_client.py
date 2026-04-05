"""Тесты HTTP-клиента ЕГРЮЛ (мокаем Redis и httpx)."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import EgrulAPIError, OrganizationNotFoundError
from app.services.egrul_client import fetch_egrul_data, invalidate_cache
from tests.conftest import make_raw_egrul


def _make_redis(cached_value: str | None = None) -> AsyncMock:
    redis = AsyncMock()
    redis.get.return_value = cached_value
    redis.setex.return_value = True
    redis.delete.return_value = 1
    return redis


def _make_response(status_code: int, data: dict | None = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = data or {}
    return resp


@pytest.mark.asyncio
async def test_returns_cached_data_without_http_call():
    raw = make_raw_egrul()
    redis = _make_redis(cached_value=json.dumps(raw))

    with patch("app.services.egrul_client.httpx.AsyncClient") as mock_client:
        result = await fetch_egrul_data("7701234567", redis)

    assert result == raw
    mock_client.assert_not_called()


@pytest.mark.asyncio
async def test_fetches_from_api_on_cache_miss():
    raw = make_raw_egrul()
    redis = _make_redis(cached_value=None)
    mock_resp = _make_response(200, raw)

    with patch("app.services.egrul_client.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
        result = await fetch_egrul_data("7701234567", redis)

    assert result == raw
    redis.setex.assert_called_once()


@pytest.mark.asyncio
async def test_force_refresh_bypasses_cache():
    raw = make_raw_egrul()
    cached = make_raw_egrul(full_name="СТАРОЕ НАЗВАНИЕ")
    redis = _make_redis(cached_value=json.dumps(cached))
    mock_resp = _make_response(200, raw)

    with patch("app.services.egrul_client.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
        result = await fetch_egrul_data("7701234567", redis, force_refresh=True)

    assert result == raw
    redis.get.assert_not_called()


@pytest.mark.asyncio
async def test_404_raises_organization_not_found():
    redis = _make_redis(cached_value=None)
    mock_resp = _make_response(404)

    with patch("app.services.egrul_client.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
        with pytest.raises(OrganizationNotFoundError):
            await fetch_egrul_data("0000000000", redis)


@pytest.mark.asyncio
async def test_non_200_raises_egrul_api_error():
    redis = _make_redis(cached_value=None)
    mock_resp = _make_response(500)

    with patch("app.services.egrul_client.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
        with pytest.raises(EgrulAPIError):
            await fetch_egrul_data("7701234567", redis)


@pytest.mark.asyncio
async def test_empty_response_raises_organization_not_found():
    redis = _make_redis(cached_value=None)
    mock_resp = _make_response(200, data={})

    with patch("app.services.egrul_client.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
        with pytest.raises(OrganizationNotFoundError):
            await fetch_egrul_data("7701234567", redis)


@pytest.mark.asyncio
async def test_connection_error_raises_egrul_api_error():
    import httpx

    redis = _make_redis(cached_value=None)

    with patch("app.services.egrul_client.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=httpx.ConnectError("connection refused")
        )
        with pytest.raises(EgrulAPIError):
            await fetch_egrul_data("7701234567", redis)


@pytest.mark.asyncio
async def test_result_is_stored_in_cache():
    raw = make_raw_egrul()
    redis = _make_redis(cached_value=None)
    mock_resp = _make_response(200, raw)

    with patch("app.services.egrul_client.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
        await fetch_egrul_data("7701234567", redis)

    args = redis.setex.call_args
    key = args[0][0]
    stored = json.loads(args[0][2])
    assert "egrul:inn:7701234567" == key
    assert stored == raw


@pytest.mark.asyncio
async def test_invalidate_cache_deletes_key():
    redis = _make_redis()
    await invalidate_cache("7701234567", redis)
    redis.delete.assert_called_once_with("egrul:inn:7701234567")
