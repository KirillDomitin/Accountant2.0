import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(user_id: uuid.UUID, role: str, email: str) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "jti": str(uuid.uuid4()),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
