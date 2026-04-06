import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser, get_current_user
from app.db.session import get_db
from app.repositories.request_history import RequestHistoryRepository
from app.schemas.history import HistoryDetailResponse, HistoryItemResponse, HistoryListResponse

router = APIRouter(prefix="/history", tags=["History"])


@router.get("", response_model=HistoryListResponse)
async def get_history(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> HistoryListResponse:
    repo = RequestHistoryRepository(session)
    user_id = None if current_user.is_admin else current_user.id
    items, total = await repo.get_list(offset=offset, limit=limit, user_id=user_id)
    return HistoryListResponse(
        items=[HistoryItemResponse.model_validate(i) for i in items],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{record_id}", response_model=HistoryDetailResponse)
async def get_history_item(
    record_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> HistoryDetailResponse:
    repo = RequestHistoryRepository(session)
    record = await repo.get_by_id(record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Запись не найдена")
    # Non-admin can only see their own records
    if not current_user.is_admin and record.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Запись не найдена")
    return HistoryDetailResponse.model_validate(record)
