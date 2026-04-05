import enum
import uuid

from sqlalchemy import DateTime, Enum, String, Text
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RequestStatus(str, enum.Enum):
    success = "success"
    error = "error"


class RequestHistory(Base):
    __tablename__ = "request_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    inn: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    org_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[RequestStatus] = mapped_column(
        Enum(RequestStatus, name="request_status"), nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_response: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
