from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Channel, Message, User, UserRole
from app.schemas import ChatMessagePayload


redis_client = Redis.from_url(settings.redis_url, decode_responses=True)

DEFAULT_CHANNELS = [
    {"slug": "hq", "is_readonly": False},
    {"slug": "announcements", "is_readonly": True},
]


class ChatService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.redis: Redis = redis_client

    async def _get_channel(self, slug: str) -> Channel:
        channel = await self.session.scalar(select(Channel).where(Channel.slug == slug))
        if not channel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found"
            )
        return channel

    async def get_channel(self, slug: str) -> Channel:
        return await self._get_channel(slug)

    async def fetch_recent(
        self, channel: Channel, limit: int = 50
    ) -> list[dict[str, Any]]:
        result = await self.session.execute(
            select(Message)
            .where(Message.channel_id == channel.id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        messages = result.scalars().all()
        return [self.serialize_message(message) for message in reversed(messages)]

    def serialize_message(self, message: Message) -> dict[str, Any]:
        return {
            "id": message.id,
            "channel_id": message.channel_id,
            "user_id": message.user_id,
            "parent_id": message.parent_id,
            "text": message.text,
            "attachments": message.attachments or [],
            "pinned": message.pinned,
            "deleted_at": message.deleted_at.isoformat()
            if message.deleted_at
            else None,
            "created_at": message.created_at.isoformat(),
        }

    async def create_message(
        self, slug: str, user: User, payload: ChatMessagePayload
    ) -> dict[str, Any]:
        await self._enforce_rate_limit(user)
        channel = await self._get_channel(slug)
        if channel.is_readonly and user.role not in (UserRole.admin,):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Channel is read-only"
            )
        message = Message(
            channel_id=channel.id,
            user_id=user.id,
            parent_id=payload.parent_id,
            text=payload.text,
            attachments=payload.attachments,
        )
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        data = self.serialize_message(message)
        await self.broadcast(slug, "message.created", data)
        return data

    async def delete_message(
        self, slug: str, message_id: int, user: User
    ) -> dict[str, Any]:
        message = await self.session.scalar(
            select(Message)
            .where(Message.id == message_id)
            .options(joinedload(Message.channel))
        )
        if not message or message.channel.slug != slug:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Message not found"
            )
        if message.user_id != user.id and user.role != UserRole.admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed"
            )
        message.deleted_at = datetime.now(UTC)
        await self.session.commit()
        payload = {"id": message.id}
        await self.broadcast(slug, "message.deleted", payload)
        return payload

    async def pin_message(
        self, slug: str, message_id: int, user: User
    ) -> dict[str, Any]:
        if user.role != UserRole.admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Requires admin"
            )
        message = await self.session.scalar(
            select(Message)
            .where(Message.id == message_id)
            .options(joinedload(Message.channel))
        )
        if not message or message.channel.slug != slug:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Message not found"
            )
        message.pinned = True
        await self.session.commit()
        payload = self.serialize_message(message)
        await self.broadcast(slug, "message.pinned", payload)
        return payload

    async def broadcast(
        self, slug: str, event_type: str, payload: dict[str, Any]
    ) -> None:
        message = json.dumps({"type": event_type, "payload": payload})
        await self.redis.publish(self._channel_key(slug), message)

    def _channel_key(self, slug: str) -> str:
        return f"ws:channel:{slug}"

    async def subscribe(self, slug: str):
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(self._channel_key(slug))
        return pubsub

    async def _enforce_rate_limit(self, user: User) -> None:
        key = f"chat:rate:{user.id}"
        count = await self.redis.incr(key)
        if count == 1:
            await self.redis.expire(key, 60)
        if count > settings.rate_limit_chat_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Chat rate limit exceeded",
            )


async def ensure_default_channels(session: AsyncSession) -> None:
    result = await session.execute(select(Channel.slug))
    existing = set(result.scalars().all())
    created = False
    for channel in DEFAULT_CHANNELS:
        if channel["slug"] not in existing:
            session.add(Channel(**channel))
            created = True
    if created:
        await session.commit()
