import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator, model_validator
import re


class TrackingAddRequest(BaseModel):
    inn: str

    @field_validator("inn")
    @classmethod
    def validate_inn(cls, v: str) -> str:
        v = v.strip()
        if not re.fullmatch(r"\d{10}|\d{12}", v):
            raise ValueError("ИНН должен содержать 10 (ЮЛ) или 12 (ИП) цифр")
        return v


class TrackingChangeResponse(BaseModel):
    id: uuid.UUID
    change_description: dict
    detected_at: datetime

    model_config = {"from_attributes": True}


class TrackedInnResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None = None
    inn: str
    org_name: str | None
    is_active: bool
    last_checked_at: datetime | None
    created_at: datetime
    pending_data_hash: str | None = None
    pending_changed_fields: list[dict] | None = None
    has_pending_changes: bool = False

    @model_validator(mode="after")
    def compute_has_pending(self) -> "TrackedInnResponse":
        self.has_pending_changes = self.pending_data_hash is not None
        if self.pending_changed_fields is None:
            self.pending_changed_fields = []
        return self

    model_config = {"from_attributes": True}


class TrackedInnDetailResponse(TrackedInnResponse):
    changes: list[TrackingChangeResponse]


class CheckResultResponse(BaseModel):
    inn: str
    org_name: str | None
    changed: bool
    changed_fields: list[dict]
    message: str


class TrackingBulkAddRequest(BaseModel):
    inns: list[str]

    @field_validator("inns")
    @classmethod
    def validate_inns(cls, v: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for raw in v:
            inn = raw.strip()
            if not re.fullmatch(r"\d{10}|\d{12}", inn):
                raise ValueError(f"Некорректный ИНН: «{inn}» — должен содержать 10 или 12 цифр")
            if inn not in seen:
                seen.add(inn)
                result.append(inn)
        if not result:
            raise ValueError("Список ИНН не может быть пустым")
        return result


class TrackingBulkAddItemResult(BaseModel):
    inn: str
    success: bool
    org_name: str | None = None
    error: str | None = None


class TrackingBulkAddResponse(BaseModel):
    results: list[TrackingBulkAddItemResult]
    added: int
    skipped: int
    failed: int
