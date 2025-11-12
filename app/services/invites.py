from __future__ import annotations

import secrets
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, Invite, User, UserRole
from app.schemas import InviteCreateRequest


def _role_rank(role: UserRole) -> int:
    return {
        UserRole.guest: 0,
        UserRole.user: 1,
        UserRole.member: 2,
        UserRole.admin: 3,
    }[role]


class InviteService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, actor: User, payload: InviteCreateRequest) -> Invite:
        code = secrets.token_urlsafe(8)
        invite = Invite(
            code=code,
            role_to_grant=payload.role_to_grant,
            expires_at=payload.expires_at,
        )
        self.session.add(invite)
        await self.session.flush()
        self.session.add(
            AuditLog(
                actor_id=actor.id,
                action="invite.create",
                entity="invite",
                entity_id=invite.code,
                meta={"role": payload.role_to_grant.value},
            )
        )
        await self.session.commit()
        await self.session.refresh(invite)
        return invite

    async def redeem(self, code: str, user: User) -> Invite:
        invite = await self.session.scalar(select(Invite).where(Invite.code == code))
        if not invite:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found"
            )
        if invite.expires_at < datetime.now(UTC):
            raise HTTPException(
                status_code=status.HTTP_410_GONE, detail="Invite expired"
            )
        if invite.used_by_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Invite already used"
            )

        if _role_rank(invite.role_to_grant) > _role_rank(user.role):
            user.role = invite.role_to_grant

        invite.used_by_id = user.id
        invite.used_at = datetime.now(UTC)

        self.session.add(
            AuditLog(
                actor_id=user.id,
                action="invite.redeem",
                entity="invite",
                entity_id=invite.code,
                meta={"granted_role": user.role.value},
            )
        )

        await self.session.commit()
        await self.session.refresh(invite)
        return invite
