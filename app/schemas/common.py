from __future__ import annotations

from pydantic import BaseModel, EmailStr

from app.models.enums import UserRole


class Message(BaseModel):
    message: str


class UserRead(BaseModel):
    id: int
    email: EmailStr
    role: UserRole

    model_config = {"from_attributes": True}
