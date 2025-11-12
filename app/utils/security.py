from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, TypedDict, cast

from jose import jwt
from passlib.context import CryptContext

from app.config import settings


pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


class TokenPayload(TypedDict, total=False):
    sub: str
    type: str
    exp: int
    iat: int
    role: str
    extra: dict[str, Any]


def _create_token(
    subject: str, ttl_seconds: int, token_type: str, **claims: Any
) -> str:
    now = datetime.now(UTC)
    payload: TokenPayload = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl_seconds)).timestamp()),
    }
    if claims:
        payload.update(claims)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_alg)


def create_access_token(user_id: int, role: str) -> str:
    return _create_token(str(user_id), settings.access_token_ttl, "access", role=role)


def create_refresh_token(user_id: int, role: str) -> str:
    return _create_token(str(user_id), settings.refresh_token_ttl, "refresh", role=role)


def decode_token(token: str) -> TokenPayload:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_alg])
    return cast(TokenPayload, payload)
