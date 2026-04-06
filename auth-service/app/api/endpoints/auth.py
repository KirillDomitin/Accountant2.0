import redis.asyncio as aioredis
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_admin
from app.core.exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    RateLimitError,
    UserAlreadyExistsError,
)
from app.db.redis import get_redis
from app.db.session import get_db
from app.repositories.user import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse, UserStatusRequest
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])

_COOKIE = "refresh_token"
_COOKIE_TTL = 30 * 24 * 3600


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=_COOKIE,
        value=token,
        httponly=True,
        secure=False,   # поменять на True при HTTPS
        samesite="strict",
        max_age=_COOKIE_TTL,
        path="/auth/refresh",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=_COOKIE, path="/auth/refresh")


# ── Публичные эндпоинты ──────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> TokenResponse:
    client_ip = request.client.host if request.client else "unknown"
    try:
        access_token, refresh_token = await auth_service.login(
            body.email, body.password, session, redis, client_ip
        )
    except InvalidCredentialsError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный email или пароль")
    except RateLimitError:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Слишком много попыток входа")

    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(access_token=access_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=_COOKIE),
    redis: aioredis.Redis = Depends(get_redis),
) -> TokenResponse:
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Отсутствует refresh-токен")
    try:
        new_access, new_refresh = await auth_service.refresh_tokens(refresh_token, redis)
    except InvalidTokenError:
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный refresh-токен")

    _set_refresh_cookie(response, new_refresh)
    return TokenResponse(access_token=new_access)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=_COOKIE),
    redis: aioredis.Redis = Depends(get_redis),
) -> None:
    if refresh_token:
        await auth_service.logout(refresh_token, redis)
    _clear_refresh_cookie(response)


@router.get("/validate", status_code=status.HTTP_200_OK)
async def validate(
    response: Response,
    request: Request,
) -> dict:
    """Внутренний эндпоинт для nginx auth_request."""
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    try:
        payload = auth_service.validate_token(authorization.removeprefix("Bearer "))
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    response.headers["X-User-Id"] = payload["sub"]
    response.headers["X-User-Role"] = payload["role"]
    return {}


# ── Admin-only эндпоинты ─────────────────────────────────────────────────────

@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
) -> UserResponse:
    try:
        user = await auth_service.register(body.email, body.password, body.role, session)
    except UserAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return UserResponse.model_validate(user)


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
) -> list[UserResponse]:
    repo = UserRepository(session)
    users = await repo.get_all()
    return [UserResponse.model_validate(u) for u in users]


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user_status(
    user_id: str,
    body: UserStatusRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
) -> UserResponse:
    import uuid as _uuid
    repo = UserRepository(session)
    user = await repo.get_by_id(_uuid.UUID(user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    user = await repo.set_active(user, body.is_active)
    return UserResponse.model_validate(user)
