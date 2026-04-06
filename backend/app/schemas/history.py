import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.request_history import RequestStatus


class HistoryItemResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None = None
    inn: str
    org_name: str | None
    status: RequestStatus
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class HistoryDetailResponse(HistoryItemResponse):
    raw_response: dict | None


class HistoryListResponse(BaseModel):
    items: list[HistoryItemResponse]
    total: int
    offset: int
    limit: int
