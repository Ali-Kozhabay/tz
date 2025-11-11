from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.enums import UserRole


class InviteCreateRequest(BaseModel):
    role_to_grant: UserRole = UserRole.member
    expires_at: datetime


class InviteRedeemRequest(BaseModel):
    code: str


class InviteRead(BaseModel):
    code: str
    role_to_grant: UserRole
    expires_at: datetime
    used_by_id: int | None = None

    model_config = {"from_attributes": True}
