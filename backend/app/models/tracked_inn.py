import uuid

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TrackedInn(Base):
    __tablename__ = "tracked_inns"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    inn: Mapped[str] = mapped_column(String(12), nullable=False, unique=True, index=True)
    org_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_checked_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_data_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_raw_response: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    pending_data_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pending_raw_response: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    pending_changed_fields: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    changes: Mapped[list["TrackingChange"]] = relationship(  # noqa: F821
        "TrackingChange", back_populates="tracked_inn", lazy="select"
    )
