import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tracking_change import TrackingChange


class TrackingChangeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        tracked_inn_id: uuid.UUID,
        change_description: dict,
    ) -> TrackingChange:
        record = TrackingChange(
            tracked_inn_id=tracked_inn_id,
            change_description=change_description,
        )
        self._session.add(record)
        await self._session.commit()
        await self._session.refresh(record)
        return record

    async def get_by_tracked_inn(self, tracked_inn_id: uuid.UUID) -> list[TrackingChange]:
        q = (
            select(TrackingChange)
            .where(TrackingChange.tracked_inn_id == tracked_inn_id)
            .order_by(TrackingChange.detected_at.desc())
        )
        return list((await self._session.execute(q)).scalars().all())
