from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Profile, User, UserRole
from app.schemas import LoginRequest, RegisterRequest
from app.utils.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def register(self, payload: RegisterRequest) -> User:
        existing = await self.session.scalar(select(User).where(User.email == payload.email))
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

        user = User(email=str(payload.email), password_hash=hash_password(payload.password))
        self.session.add(user)
        await self.session.flush()
        profile = Profile(user_id=user.id, name=None)
        self.session.add(profile)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def authenticate(self, payload: LoginRequest|str) -> User:
        user = await self.session.scalar(select(User).where(User.email == payload.email))
        if not user or not verify_password(payload.password, str(user.password_hash)):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        return user

    async def build_tokens(self, user: User) -> dict[str, str]:
        return {
            "access": create_access_token(user.id, user.role.value),
            "refresh": create_refresh_token(user.id, user.role.value),
        }

    async def refresh(self, refresh_token: str) -> dict[str, str]:
        try:
            payload = decode_token(refresh_token)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not a refresh token")

        user = await self.session.get(User, int(payload["sub"]))
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        return {
            "access": create_access_token(user.id, user.role.value),
            "refresh": refresh_token,
        }


def ensure_role(user: User, required: UserRole) -> None:
    order = {UserRole.guest: 0, UserRole.user: 1, UserRole.member: 2, UserRole.admin: 3}
    if order[user.role] < order[required]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
