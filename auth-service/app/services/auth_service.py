"""Бизнес-логика авторизации."""
import json
import uuid

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    RateLimitError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.user import User
from app.repositories.user import UserRepository

REFRESH_TTL = 30 * 24 * 3600  # 30 дней
RATE_LIMIT_TTL = 900           # 15 минут
RATE_LIMIT_MAX = 5


async def _check_rate_limit(ip: str, redis: aioredis.Redis) -> None:
    key = f"auth:attempts:{ip}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, RATE_LIMIT_TTL)
    if count > RATE_LIMIT_MAX:
        raise RateLimitError()


async def _store_refresh_token(
    token: str, user_id: uuid.UUID, role: str, email: str, redis: aioredis.Redis
) -> None:
    token_hash = hash_token(token)
    data = json.dumps({"user_id": str(user_id), "role": role, "email": email})
    await redis.setex(f"auth:refresh:{token_hash}", REFRESH_TTL, data)


async def login(
    email: str,
    password: str,
    session: AsyncSession,
    redis: aioredis.Redis,
    client_ip: str,
) -> tuple[str, str]:
    await _check_rate_limit(client_ip, redis)

    repo = UserRepository(session)
    user = await repo.get_by_email(email)
    if not user or not user.is_active or not verify_password(password, user.hashed_password):
        raise InvalidCredentialsError()

    await redis.delete(f"auth:attempts:{client_ip}")

    access_token = create_access_token(user.id, user.role, user.email)
    refresh_token = generate_refresh_token()
    await _store_refresh_token(refresh_token, user.id, user.role, user.email, redis)

    return access_token, refresh_token


async def refresh_tokens(
    refresh_token: str,
    redis: aioredis.Redis,
) -> tuple[str, str]:
    token_hash = hash_token(refresh_token)
    # getdel: атомарно читаем и удаляем — повторное использование невозможно
    raw = await redis.getdel(f"auth:refresh:{token_hash}")
    if not raw:
        raise InvalidTokenError()

    data = json.loads(raw)
    user_id = uuid.UUID(data["user_id"])
    role = data["role"]
    email = data.get("email", "")

    new_access = create_access_token(user_id, role, email)
    new_refresh = generate_refresh_token()
    await _store_refresh_token(new_refresh, user_id, role, email, redis)

    return new_access, new_refresh


async def logout(refresh_token: str, redis: aioredis.Redis) -> None:
    token_hash = hash_token(refresh_token)
    await redis.delete(f"auth:refresh:{token_hash}")


async def register(
    email: str,
    password: str,
    role: str,
    session: AsyncSession,
) -> User:
    repo = UserRepository(session)
    if await repo.get_by_email(email):
        raise UserAlreadyExistsError(f"Пользователь {email} уже существует")
    return await repo.create(email=email, hashed_password=hash_password(password), role=role)


def validate_token(token: str) -> dict:
    """Проверяет JWT и возвращает payload. Используется nginx auth_request."""
    try:
        return decode_access_token(token)
    except Exception as exc:
        raise InvalidTokenError() from exc


async def ensure_admin_exists(session: AsyncSession) -> None:
    """При старте создаёт дефолтного admin, если пользователей нет."""
    import os

    repo = UserRepository(session)
    users = await repo.get_all()
    if users:
        return

    admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "changeme123")
    await repo.create(
        email=admin_email,
        hashed_password=hash_password(admin_password),
        role="admin",
    )
