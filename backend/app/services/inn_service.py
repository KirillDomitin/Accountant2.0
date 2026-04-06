"""Оркестрация: получение данных ЕГРЮЛ → генерация docx → сохранение истории."""
import io
import uuid

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EgrulAPIError, OrganizationNotFoundError
from app.models.request_history import RequestStatus
from app.repositories.request_history import RequestHistoryRepository
from app.services.docx_generator import generate_docx
from app.services.egrul_client import fetch_egrul_data
from app.services.egrul_parser import parse_egrul_response


async def lookup_inn(
    inn: str,
    session: AsyncSession,
    redis: aioredis.Redis,
    user_id: uuid.UUID | None = None,
) -> tuple[io.BytesIO, str]:
    """
    Возвращает (docx_buffer, filename).
    Сохраняет запись в request_history независимо от результата.
    """
    repo = RequestHistoryRepository(session)

    try:
        raw = await fetch_egrul_data(inn, redis)
        org = parse_egrul_response(raw)
        buf = generate_docx(org)
    except OrganizationNotFoundError as exc:
        await repo.create(inn=inn, status=RequestStatus.error, error_message=str(exc), user_id=user_id)
        raise
    except EgrulAPIError as exc:
        await repo.create(inn=inn, status=RequestStatus.error, error_message=str(exc), user_id=user_id)
        raise
    except Exception as exc:
        await repo.create(
            inn=inn,
            status=RequestStatus.error,
            error_message=f"Внутренняя ошибка: {exc}",
            user_id=user_id,
        )
        raise

    await repo.create(
        inn=inn,
        status=RequestStatus.success,
        org_name=org.short_name or org.full_name,
        raw_response=raw,
        user_id=user_id,
    )

    safe_name = (org.short_name or inn).replace('"', "").replace(" ", "_")
    filename = f"{safe_name}.docx"
    return buf, filename
