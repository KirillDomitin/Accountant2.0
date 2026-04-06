from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser, get_current_user
from app.core.exceptions import EgrulAPIError, OrganizationNotFoundError
from app.db.redis import get_redis
from app.db.session import get_db
from app.schemas.inn import InnLookupRequest
from app.services.inn_service import lookup_inn

router = APIRouter(prefix="/inn", tags=["INN"])


@router.post("/lookup")
async def lookup(
    body: InnLookupRequest,
    session: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
    current_user: CurrentUser = Depends(get_current_user),
) -> Response:
    try:
        buf, filename = await lookup_inn(body.inn, session, redis, user_id=current_user.id)
    except OrganizationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except EgrulAPIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        )

    return Response(
        content=buf.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )
