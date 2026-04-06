"""Тесты сервиса отслеживания изменений (мокаем репозитории и egrul_client)."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import OrganizationNotFoundError
from app.services.tracking_service import (
    _detect_changes,
    add_tracked_inn,
    check_all_tracked_inns,
    check_inn,
)
from tests.conftest import make_raw_egrul


# ---------------------------------------------------------------------------
# _detect_changes — чистая функция
# ---------------------------------------------------------------------------

def test_detect_changes_same_hash_returns_empty():
    raw = make_raw_egrul()
    from app.services.tracking_service import _compute_hash
    h = _compute_hash(raw)
    result = _detect_changes(h, h, raw, MagicMock())
    assert result == []


def test_detect_changes_no_previous_hash_returns_initial():
    raw = make_raw_egrul()
    from app.services.egrul_parser import parse_egrul_response
    from app.services.tracking_service import _compute_hash
    h = _compute_hash(raw)
    result = _detect_changes(None, h, None, parse_egrul_response(raw))
    assert len(result) == 1
    assert result[0]["field"] == "initial"


def test_detect_changes_name_changed():
    from app.services.egrul_parser import parse_egrul_response
    from app.services.tracking_service import _compute_hash

    old_raw = make_raw_egrul(full_name="ООО СТАРОЕ")
    new_raw = make_raw_egrul(full_name="ООО НОВОЕ")
    old_hash = _compute_hash(old_raw)
    new_hash = _compute_hash(new_raw)

    result = _detect_changes(old_hash, new_hash, old_raw, parse_egrul_response(new_raw))
    fields = [c["field"] for c in result]

    assert "Полное наименование" in fields


def test_detect_changes_director_changed():
    from app.services.egrul_parser import parse_egrul_response
    from app.services.tracking_service import _compute_hash

    old_raw = make_raw_egrul(director_name="ИВАНОВ ИВАН ИВАНОВИЧ")
    new_raw = make_raw_egrul(director_name="ПЕТРОВ ПЁТР ПЕТРОВИЧ")
    old_hash = _compute_hash(old_raw)
    new_hash = _compute_hash(new_raw)

    result = _detect_changes(old_hash, new_hash, old_raw, parse_egrul_response(new_raw))
    fields = [c["field"] for c in result]

    assert "Руководитель" in fields


def test_detect_changes_capital_changed():
    from app.services.egrul_parser import parse_egrul_response
    from app.services.tracking_service import _compute_hash

    old_raw = make_raw_egrul(capital="10000")
    new_raw = make_raw_egrul(capital="50000")
    old_hash = _compute_hash(old_raw)
    new_hash = _compute_hash(new_raw)

    result = _detect_changes(old_hash, new_hash, old_raw, parse_egrul_response(new_raw))
    fields = [c["field"] for c in result]

    assert "Уставный капитал" in fields


def test_detect_changes_misc_when_hash_differs_but_fields_same():
    """Хэш отличается, но ни одно из отслеживаемых полей не изменилось."""
    from app.services.egrul_parser import parse_egrul_response
    from app.services.tracking_service import _compute_hash

    old_raw = make_raw_egrul()
    new_raw = make_raw_egrul()
    # Искусственно делаем разные хэши, не меняя отслеживаемые поля
    new_raw["СвЮЛ"]["@attributes"]["__extra"] = "noise"

    old_hash = _compute_hash(old_raw)
    new_hash = _compute_hash(new_raw)

    result = _detect_changes(old_hash, new_hash, old_raw, parse_egrul_response(new_raw))

    assert len(result) == 1
    assert result[0]["field"] == "прочие изменения"


# ---------------------------------------------------------------------------
# add_tracked_inn
# ---------------------------------------------------------------------------

def _make_tracked(inn: str = "7701234567", is_active: bool = True) -> MagicMock:
    tracked = MagicMock()
    tracked.id = uuid.uuid4()
    tracked.inn = inn
    tracked.is_active = is_active
    tracked.last_data_hash = None
    tracked.last_raw_response = None
    return tracked


@pytest.mark.asyncio
async def test_add_tracked_inn_creates_new():
    raw = make_raw_egrul()
    session = AsyncMock()
    redis = AsyncMock()

    with (
        patch("app.services.tracking_service.fetch_egrul_data", return_value=raw),
        patch("app.services.tracking_service.TrackedInnRepository") as MockRepo,
    ):
        repo_instance = AsyncMock()
        repo_instance.get_by_inn.return_value = None
        MockRepo.return_value = repo_instance

        org = await add_tracked_inn("7701234567", session, redis)

    repo_instance.create.assert_called_once()
    assert org.inn == "7701234567"


@pytest.mark.asyncio
async def test_add_tracked_inn_reactivates_inactive():
    raw = make_raw_egrul()
    session = AsyncMock()
    redis = AsyncMock()
    existing = _make_tracked(is_active=False)

    with (
        patch("app.services.tracking_service.fetch_egrul_data", return_value=raw),
        patch("app.services.tracking_service.TrackedInnRepository") as MockRepo,
    ):
        repo_instance = AsyncMock()
        repo_instance.get_by_inn.return_value = existing
        MockRepo.return_value = repo_instance

        await add_tracked_inn("7701234567", session, redis)

    assert existing.is_active is True
    repo_instance.update_check.assert_called_once()


@pytest.mark.asyncio
async def test_add_tracked_inn_skips_already_active():
    raw = make_raw_egrul()
    session = AsyncMock()
    redis = AsyncMock()
    existing = _make_tracked(is_active=True)

    with (
        patch("app.services.tracking_service.fetch_egrul_data", return_value=raw),
        patch("app.services.tracking_service.TrackedInnRepository") as MockRepo,
    ):
        repo_instance = AsyncMock()
        repo_instance.get_by_inn.return_value = existing
        MockRepo.return_value = repo_instance

        await add_tracked_inn("7701234567", session, redis)

    repo_instance.create.assert_not_called()
    repo_instance.update_check.assert_not_called()


# ---------------------------------------------------------------------------
# check_inn
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_check_inn_raises_when_not_tracked():
    session = AsyncMock()
    redis = AsyncMock()

    with patch("app.services.tracking_service.TrackedInnRepository") as MockRepo:
        repo_instance = AsyncMock()
        repo_instance.get_by_inn.return_value = None
        MockRepo.return_value = repo_instance

        with pytest.raises(OrganizationNotFoundError):
            await check_inn("0000000000", session, redis)


@pytest.mark.asyncio
async def test_check_inn_no_changes():
    from app.services.tracking_service import _compute_hash

    raw = make_raw_egrul()
    h = _compute_hash(raw)
    session = AsyncMock()
    redis = AsyncMock()
    tracked = _make_tracked()
    tracked.last_data_hash = h
    tracked.last_raw_response = raw

    with (
        patch("app.services.tracking_service.fetch_egrul_data", return_value=raw),
        patch("app.services.tracking_service.TrackedInnRepository") as MockRepo,
        patch("app.services.tracking_service.TrackingChangeRepository") as MockChangeRepo,
    ):
        repo_instance = AsyncMock()
        repo_instance.get_by_inn.return_value = tracked
        MockRepo.return_value = repo_instance

        change_repo_instance = AsyncMock()
        MockChangeRepo.return_value = change_repo_instance

        result = await check_inn("7701234567", session, redis)

    assert result["changed"] is False
    assert result["changed_fields"] == []
    change_repo_instance.create.assert_not_called()


@pytest.mark.asyncio
async def test_check_inn_detects_name_change_and_saves():
    from app.services.tracking_service import _compute_hash

    old_raw = make_raw_egrul(full_name="ООО СТАРОЕ")
    new_raw = make_raw_egrul(full_name="ООО НОВОЕ")
    old_hash = _compute_hash(old_raw)

    session = AsyncMock()
    redis = AsyncMock()
    tracked = _make_tracked()
    tracked.last_data_hash = old_hash
    tracked.last_raw_response = old_raw

    with (
        patch("app.services.tracking_service.fetch_egrul_data", return_value=new_raw),
        patch("app.services.tracking_service.TrackedInnRepository") as MockRepo,
        patch("app.services.tracking_service.TrackingChangeRepository") as MockChangeRepo,
    ):
        repo_instance = AsyncMock()
        repo_instance.get_by_inn.return_value = tracked
        MockRepo.return_value = repo_instance

        change_repo_instance = AsyncMock()
        MockChangeRepo.return_value = change_repo_instance

        result = await check_inn("7701234567", session, redis)

    assert result["changed"] is True
    assert "Полное наименование" in [c["field"] for c in result["changed_fields"]]
    change_repo_instance.create.assert_called_once()


@pytest.mark.asyncio
async def test_check_inn_updates_hash_and_raw_after_check():
    from app.services.tracking_service import _compute_hash

    raw = make_raw_egrul()
    h = _compute_hash(raw)
    session = AsyncMock()
    redis = AsyncMock()
    tracked = _make_tracked()
    tracked.last_data_hash = h
    tracked.last_raw_response = raw

    with (
        patch("app.services.tracking_service.fetch_egrul_data", return_value=raw),
        patch("app.services.tracking_service.TrackedInnRepository") as MockRepo,
        patch("app.services.tracking_service.TrackingChangeRepository") as MockChangeRepo,
    ):
        repo_instance = AsyncMock()
        repo_instance.get_by_inn.return_value = tracked
        MockRepo.return_value = repo_instance
        MockChangeRepo.return_value = AsyncMock()

        await check_inn("7701234567", session, redis)

    repo_instance.update_check.assert_called_once()
    call_kwargs = repo_instance.update_check.call_args.kwargs
    assert call_kwargs.get("raw_response") == raw


# ---------------------------------------------------------------------------
# check_all_tracked_inns
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_check_all_skips_errors_silently():
    from app.core.exceptions import EgrulAPIError

    session = AsyncMock()
    redis = AsyncMock()

    with (
        patch("app.services.tracking_service.TrackedInnRepository") as MockRepo,
        patch("app.services.tracking_service.check_inn", side_effect=EgrulAPIError("api down")),
    ):
        repo_instance = AsyncMock()
        tracked = _make_tracked(inn="7701234567")
        repo_instance.get_list.return_value = [tracked]
        MockRepo.return_value = repo_instance

        # Не должно бросить исключение
        await check_all_tracked_inns(session, redis)


@pytest.mark.asyncio
async def test_check_all_processes_each_active_inn():
    session = AsyncMock()
    redis = AsyncMock()

    inns = ["7701234567", "7709876543"]

    with (
        patch("app.services.tracking_service.TrackedInnRepository") as MockRepo,
        patch("app.services.tracking_service.check_inn", new_callable=AsyncMock) as mock_check,
    ):
        repo_instance = AsyncMock()
        repo_instance.get_list.return_value = [_make_tracked(inn=i) for i in inns]
        MockRepo.return_value = repo_instance

        await check_all_tracked_inns(session, redis)

    assert mock_check.call_count == 2
    called_inns = {call.args[0] for call in mock_check.call_args_list}
    assert called_inns == set(inns)
