import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser, get_current_user
from app.core.exceptions import EgrulAPIError, OrganizationNotFoundError
from app.db.redis import get_redis
from app.db.session import get_db
from app.repositories.tracked_inn import TrackedInnRepository
from app.repositories.tracking_change import TrackingChangeRepository
from app.schemas.tracking import (
    CheckResultResponse,
    TrackedInnDetailResponse,
    TrackedInnResponse,
    TrackingAddRequest,
    TrackingBulkAddItemResult,
    TrackingBulkAddRequest,
    TrackingBulkAddResponse,
    TrackingChangeResponse,
)
from app.services.tracking_service import add_tracked_inn, check_inn, confirm_tracked_inn

router = APIRouter(prefix="/tracking", tags=["Tracking"])


@router.post("", response_model=TrackedInnResponse, status_code=status.HTTP_201_CREATED)
async def add_tracking(
    body: TrackingAddRequest,
    session: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
    current_user: CurrentUser = Depends(get_current_user),
) -> TrackedInnResponse:
    try:
        await add_tracked_inn(body.inn, session, redis, user_id=current_user.id)
    except OrganizationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except EgrulAPIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    repo = TrackedInnRepository(session)
    tracked = await repo.get_by_inn(body.inn, user_id=current_user.id)
    return TrackedInnResponse.model_validate(tracked)


@router.post("/bulk", response_model=TrackingBulkAddResponse, status_code=status.HTTP_200_OK)
async def add_tracking_bulk(
    body: TrackingBulkAddRequest,
    session: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
    current_user: CurrentUser = Depends(get_current_user),
) -> TrackingBulkAddResponse:
    results: list[TrackingBulkAddItemResult] = []
    added = skipped = failed = 0

    repo = TrackedInnRepository(session)

    for inn in body.inns:
        existing = await repo.get_by_inn(inn, user_id=current_user.id)
        if existing and existing.is_active:
            results.append(TrackingBulkAddItemResult(
                inn=inn,
                success=False,
                org_name=existing.org_name,
                error="Уже отслеживается",
            ))
            skipped += 1
            continue

        try:
            org = await add_tracked_inn(inn, session, redis, user_id=current_user.id)
            org_name = org.short_name or org.full_name
            results.append(TrackingBulkAddItemResult(inn=inn, success=True, org_name=org_name))
            added += 1
        except OrganizationNotFoundError:
            results.append(TrackingBulkAddItemResult(inn=inn, success=False, error="Организация не найдена"))
            failed += 1
        except EgrulAPIError:
            results.append(TrackingBulkAddItemResult(inn=inn, success=False, error="Ошибка запроса к ЕГРЮЛ"))
            failed += 1

    return TrackingBulkAddResponse(results=results, added=added, skipped=skipped, failed=failed)


@router.get("", response_model=list[TrackedInnResponse])
async def list_tracking(
    session: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[TrackedInnResponse]:
    repo = TrackedInnRepository(session)
    user_id = None if current_user.is_admin else current_user.id
    items = await repo.get_list(only_active=True, user_id=user_id)
    return [TrackedInnResponse.model_validate(i) for i in items]


@router.get("/{inn}", response_model=TrackedInnDetailResponse)
async def get_tracking(
    inn: str,
    session: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> TrackedInnDetailResponse:
    repo = TrackedInnRepository(session)
    user_id = None if current_user.is_admin else current_user.id
    tracked = await repo.get_detail(inn, user_id=user_id)
    if not tracked:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ИНН не найден")

    change_repo = TrackingChangeRepository(session)
    changes = await change_repo.get_by_tracked_inn(tracked.id)

    return TrackedInnDetailResponse(
        **TrackedInnResponse.model_validate(tracked).model_dump(),
        changes=[TrackingChangeResponse.model_validate(c) for c in changes],
    )


@router.delete("/{inn}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tracking(
    inn: str,
    session: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> None:
    repo = TrackedInnRepository(session)
    user_id = None if current_user.is_admin else current_user.id
    tracked = await repo.get_by_inn(inn, user_id=user_id)
    if not tracked:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ИНН не найден")
    await repo.deactivate(tracked)


@router.post("/{inn}/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def confirm_tracking(
    inn: str,
    session: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> None:
    user_id = None if current_user.is_admin else current_user.id
    try:
        await confirm_tracked_inn(inn, session, user_id=user_id)
    except OrganizationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/{inn}/check", response_model=CheckResultResponse)
async def manual_check(
    inn: str,
    session: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
    current_user: CurrentUser = Depends(get_current_user),
) -> CheckResultResponse:
    user_id = None if current_user.is_admin else current_user.id
    try:
        result = await check_inn(inn, session, redis, force_refresh=True, user_id=user_id)
    except OrganizationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except EgrulAPIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    if result["changed"]:
        parts = [c["field"] for c in result["changed_fields"]]
        msg = f"Обнаружены изменения: {', '.join(parts)}"
    else:
        msg = "Изменений не обнаружено"

    return CheckResultResponse(
        inn=inn,
        org_name=result["org_name"],
        changed=result["changed"],
        changed_fields=result["changed_fields"],
        message=msg,
    )
