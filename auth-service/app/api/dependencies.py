from fastapi import Header, HTTPException, status

from app.core.exceptions import InvalidTokenError
from app.services.auth_service import validate_token


def _get_payload(authorization: str | None) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Не авторизован")
    try:
        return validate_token(authorization.removeprefix("Bearer "))
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный токен")


def require_admin(authorization: str | None = Header(default=None)) -> dict:
    payload = _get_payload(authorization)
    if payload.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Только для администраторов")
    return payload


def require_auth(authorization: str | None = Header(default=None)) -> dict:
    return _get_payload(authorization)
