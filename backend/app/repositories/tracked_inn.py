import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.tracked_inn import TrackedInn


class TrackedInnRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_inn(self, inn: str, user_id: uuid.UUID | None = None) -> TrackedInn | None:
        q = select(TrackedInn).where(TrackedInn.inn == inn)
        if user_id is not None:
            q = q.where(TrackedInn.user_id == user_id)
        return (await self._session.execute(q)).scalar_one_or_none()

    async def get_list(
        self,
        only_active: bool = False,
        user_id: uuid.UUID | None = None,
    ) -> list[TrackedInn]:
        q = select(TrackedInn)
        if only_active:
            q = q.where(TrackedInn.is_active == True)  # noqa: E712
        if user_id is not None:
            q = q.where(TrackedInn.user_id == user_id)
        q = q.order_by(TrackedInn.created_at.desc())
        return list((await self._session.execute(q)).scalars().all())

    async def get_detail(self, inn: str, user_id: uuid.UUID | None = None) -> TrackedInn | None:
        q = (
            select(TrackedInn)
            .where(TrackedInn.inn == inn)
            .options(selectinload(TrackedInn.changes))
        )
        if user_id is not None:
            q = q.where(TrackedInn.user_id == user_id)
        return (await self._session.execute(q)).scalar_one_or_none()

    async def create(
        self,
        inn: str,
        org_name: str | None,
        data_hash: str,
        raw_response: dict | None = None,
        user_id: uuid.UUID | None = None,
    ) -> TrackedInn:
        record = TrackedInn(
            inn=inn,
            user_id=user_id,
            org_name=org_name,
            last_data_hash=data_hash,
            last_raw_response=raw_response,
            last_checked_at=datetime.now(timezone.utc),
        )
        self._session.add(record)
        await self._session.commit()
        await self._session.refresh(record)
        return record

    async def update_last_checked(
        self,
        tracked: TrackedInn,
        org_name: str | None = None,
    ) -> TrackedInn:
        tracked.last_checked_at = datetime.now(timezone.utc)
        if org_name:
            tracked.org_name = org_name
        await self._session.commit()
        await self._session.refresh(tracked)
        return tracked

    async def set_pending(
        self,
        tracked: TrackedInn,
        new_hash: str,
        new_raw: dict,
        changed_fields: list[str],
    ) -> TrackedInn:
        tracked.pending_data_hash = new_hash
        tracked.pending_raw_response = new_raw
        tracked.pending_changed_fields = changed_fields
        await self._session.commit()
        await self._session.refresh(tracked)
        return tracked

    async def confirm_pending(self, tracked: TrackedInn) -> TrackedInn:
        if tracked.pending_data_hash is not None:
            tracked.last_data_hash = tracked.pending_data_hash
            tracked.last_raw_response = tracked.pending_raw_response
            tracked.pending_data_hash = None
            tracked.pending_raw_response = None
            tracked.pending_changed_fields = None
        await self._session.commit()
        await self._session.refresh(tracked)
        return tracked

    async def deactivate(self, tracked: TrackedInn) -> TrackedInn:
        tracked.is_active = False
        await self._session.commit()
        await self._session.refresh(tracked)
        return tracked

    async def update_check(
        self,
        tracked: TrackedInn,
        data_hash: str,
        org_name: str | None = None,
        raw_response: dict | None = None,
    ) -> TrackedInn:
        tracked.last_data_hash = data_hash
        tracked.last_checked_at = datetime.now(timezone.utc)
        if org_name:
            tracked.org_name = org_name
        if raw_response is not None:
            tracked.last_raw_response = raw_response
        await self._session.commit()
        await self._session.refresh(tracked)
        return tracked
