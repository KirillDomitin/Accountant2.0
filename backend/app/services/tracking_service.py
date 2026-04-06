"""Бизнес-логика отслеживания изменений по ИНН."""
import hashlib
import json
import logging
import uuid
from dataclasses import asdict

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EgrulAPIError, OrganizationNotFoundError

logger = logging.getLogger(__name__)
from app.repositories.tracked_inn import TrackedInnRepository
from app.repositories.tracking_change import TrackingChangeRepository
from app.services.egrul_client import fetch_egrul_data
from app.services.egrul_parser import OrganizationData, parse_egrul_response


def _compute_hash(raw: dict) -> str:
    return hashlib.sha256(
        json.dumps(raw, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def _fmt_director(d: object | None) -> str:
    if d is None:
        return "—"
    return f"{d.full_name} ({d.role_label})"  # type: ignore[union-attr]


def _fmt_address(a: object) -> str:
    parts = [a.index, a.region, a.street, a.building]  # type: ignore[union-attr]
    return ", ".join(p for p in parts if p)


def _detect_changes(
    old_hash: str | None,
    new_hash: str,
    old_org: dict | None,
    new_org: OrganizationData,
) -> list[dict]:
    """Возвращает список изменений с указанием старых и новых значений."""
    if old_hash == new_hash:
        return []
    if old_org is None:
        return [{"field": "initial", "old": "", "new": ""}]

    old = parse_egrul_response(old_org)
    comparisons = [
        ("Полное наименование", old.full_name, new_org.full_name),
        ("Краткое наименование", old.short_name, new_org.short_name),
        ("Адрес", _fmt_address(old.address), _fmt_address(new_org.address)),
        ("Руководитель", _fmt_director(old.director), _fmt_director(new_org.director)),
        ("Уставный капитал", old.authorized_capital, new_org.authorized_capital),
        ("Дата регистрации", old.registration_date, new_org.registration_date),
        ("Основной ОКВЭД", old.okved_main, new_org.okved_main),
    ]
    changed = [
        {"field": name, "old": str(old_val or "—"), "new": str(new_val or "—")}
        for name, old_val, new_val in comparisons
        if old_val != new_val
    ]
    return changed if changed else [{"field": "прочие изменения", "old": "", "new": ""}]


async def add_tracked_inn(
    inn: str,
    session: AsyncSession,
    redis: aioredis.Redis,
    user_id: uuid.UUID | None = None,
) -> OrganizationData:
    """Добавляет ИНН в отслеживание. Если уже есть — реактивирует."""
    repo = TrackedInnRepository(session)
    existing = await repo.get_by_inn(inn, user_id=user_id)

    raw = await fetch_egrul_data(inn, redis)
    org = parse_egrul_response(raw)
    data_hash = _compute_hash(raw)
    org_name = org.short_name or org.full_name

    if existing:
        if not existing.is_active:
            existing.is_active = True
            await repo.update_check(existing, data_hash, org_name, raw_response=raw)
            logger.info("Tracking reactivated for INN %s (%s)", inn, org_name)
        else:
            logger.info("Tracking already active for INN %s (%s)", inn, org_name)
        return org

    await repo.create(inn=inn, org_name=org_name, data_hash=data_hash, raw_response=raw, user_id=user_id)
    logger.info("Tracking added for INN %s (%s, user=%s)", inn, org_name, user_id)
    return org


async def check_inn(
    inn: str,
    session: AsyncSession,
    redis: aioredis.Redis,
    force_refresh: bool = True,
    user_id: uuid.UUID | None = None,
) -> dict:
    """
    Проверяет изменения для одного ИНН.
    Возвращает dict: {changed, org_name, changed_fields}.
    """
    inn_repo = TrackedInnRepository(session)
    change_repo = TrackingChangeRepository(session)

    tracked = await inn_repo.get_by_inn(inn, user_id=user_id)
    if not tracked:
        raise OrganizationNotFoundError(f"ИНН {inn} не найден в списке отслеживания")

    raw = await fetch_egrul_data(inn, redis, force_refresh=force_refresh)
    org = parse_egrul_response(raw)
    new_hash = _compute_hash(raw)
    org_name = org.short_name or org.full_name

    changed_fields = _detect_changes(tracked.last_data_hash, new_hash, tracked.last_raw_response, org)

    is_initial = bool(changed_fields) and changed_fields[0]["field"] == "initial"
    has_real_changes = bool(changed_fields) and not is_initial

    if has_real_changes:
        fields = [c["field"] for c in changed_fields]
        logger.info("Changes detected for INN %s (%s): %s", inn, org_name, ", ".join(fields))
        await change_repo.create(
            tracked_inn_id=tracked.id,
            change_description={
                "previous_hash": tracked.last_data_hash,
                "new_hash": new_hash,
                "changed_fields": changed_fields,
            },
        )
        await inn_repo.set_pending(tracked, new_hash, raw, changed_fields)
        await inn_repo.update_last_checked(tracked, org_name)
    else:
        logger.info("No changes for INN %s (%s)", inn, org_name)
        await inn_repo.update_check(tracked, new_hash, org_name, raw_response=raw)

    return {
        "changed": has_real_changes,
        "org_name": org_name,
        "changed_fields": changed_fields if not is_initial else [],
    }


async def confirm_tracked_inn(inn: str, session: AsyncSession, user_id: uuid.UUID | None = None) -> None:
    """Подтверждает pending-изменения: копирует новые данные в основные поля."""
    repo = TrackedInnRepository(session)
    tracked = await repo.get_by_inn(inn, user_id=user_id)
    if not tracked:
        raise OrganizationNotFoundError(f"ИНН {inn} не найден в списке отслеживания")
    await repo.confirm_pending(tracked)


async def check_all_tracked_inns(session: AsyncSession, redis: aioredis.Redis) -> None:
    """Проверяет все активные ИНН. Запускается планировщиком."""
    repo = TrackedInnRepository(session)
    active = await repo.get_list(only_active=True)

    logger.info("Daily check started: %d active INNs", len(active))
    errors = 0
    for tracked in active:
        try:
            await check_inn(tracked.inn, session, redis, force_refresh=True, user_id=tracked.user_id)
        except OrganizationNotFoundError:
            logger.warning("Daily check: INN %s not found in EGRUL", tracked.inn)
            errors += 1
        except EgrulAPIError as exc:
            logger.error("Daily check: EGRUL API error for INN %s: %s", tracked.inn, exc)
            errors += 1

    logger.info("Daily check finished: %d processed, %d errors", len(active), errors)
