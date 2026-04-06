import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.request_history import RequestHistory, RequestStatus


class RequestHistoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        inn: str,
        status: RequestStatus,
        org_name: str | None = None,
        error_message: str | None = None,
        raw_response: dict | None = None,
        user_id: uuid.UUID | None = None,
    ) -> RequestHistory:
        record = RequestHistory(
            inn=inn,
            user_id=user_id,
            org_name=org_name,
            status=status,
            error_message=error_message,
            raw_response=raw_response,
        )
        self._session.add(record)
        await self._session.commit()
        await self._session.refresh(record)
        return record

    async def get_list(
        self,
        offset: int = 0,
        limit: int = 20,
        user_id: uuid.UUID | None = None,
    ) -> tuple[list[RequestHistory], int]:
        base_q = select(RequestHistory)
        if user_id is not None:
            base_q = base_q.where(RequestHistory.user_id == user_id)

        count_q = select(func.count()).select_from(base_q.subquery())
        total = (await self._session.execute(count_q)).scalar_one()

        items_q = (
            base_q
            .order_by(RequestHistory.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list((await self._session.execute(items_q)).scalars().all())
        return items, total

    async def get_by_id(self, record_id: uuid.UUID) -> RequestHistory | None:
        q = select(RequestHistory).where(RequestHistory.id == record_id)
        return (await self._session.execute(q)).scalar_one_or_none()
