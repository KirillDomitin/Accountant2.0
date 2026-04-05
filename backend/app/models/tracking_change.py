import uuid

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TrackingChange(Base):
    __tablename__ = "tracking_changes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tracked_inn_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tracked_inns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    change_description: Mapped[dict] = mapped_column(JSON, nullable=False)
    detected_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    tracked_inn: Mapped["TrackedInn"] = relationship(  # noqa: F821
        "TrackedInn", back_populates="changes"
    )
