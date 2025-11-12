from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AsyncSessionLocal
from app.models import User, UserRole
from app.services.auth import ensure_role
from app.utils.security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token"
        )
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from exc
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
        )
    user_id = payload.get("sub")
    user = await session.get(User, int(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> User | None:
    if not credentials:
        return None
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            return None
        return await session.get(User, int(payload["sub"]))
    except Exception:  # noqa: BLE001
        return None


def require_role(role: UserRole):
    async def _inner(user: User = Depends(get_current_user)) -> User:
        ensure_role(user, role)
        return user

    return _inner
