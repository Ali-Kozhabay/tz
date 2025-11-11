from __future__ import annotations

from datetime import datetime
from typing import Any, TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:  # pragma: no cover
    from app.models.user import User


class Channel(Base):
    __tablename__ = "channels"
    __table_args__ = (Index("ix_channels_slug", "slug", unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    is_readonly: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    messages: Mapped[list["Message"]] = relationship(back_populates="channel")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id"))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    attachments: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, default=list, server_default="[]")
    pinned: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    channel: Mapped[Channel] = relationship(back_populates="messages")
    user: Mapped["User"] = relationship(back_populates="messages")
    parent: Mapped["Message | None"] = relationship(remote_side="Message.id")
