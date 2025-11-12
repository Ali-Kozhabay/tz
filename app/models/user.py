from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import UserRole

if TYPE_CHECKING:  # pragma: no cover
    from app.models.invite import Invite
    from app.models.course import Progress
    from app.models.chat import Message


class User(Base):
    __tablename__ = "users"
    __table_args__ = (Index("ix_users_email", "email", unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole),
        nullable=False,
        default=UserRole.guest,
        server_default=UserRole.guest.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    profile: Mapped["Profile"] = relationship(back_populates="user", uselist=False)
    invites: Mapped[list["Invite"]] = relationship(
        back_populates="used_by", foreign_keys="Invite.used_by_id"
    )
    progress_entries: Mapped[list["Progress"]] = relationship(back_populates="user")
    messages: Mapped[list["Message"]] = relationship(back_populates="user")


class Profile(Base):
    __tablename__ = "profiles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(String(512))
    locale: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    settings: Mapped[dict[str, object]] = mapped_column(
        JSON, default=dict, server_default="{}"
    )

    user: Mapped[User] = relationship(back_populates="profile")
