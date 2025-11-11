from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatMessagePayload(BaseModel):
    text: str
    parent_id: int | None = None
    attachments: list[dict[str, Any]] = Field(default_factory=list)


class WebsocketMessage(BaseModel):
    type: str
    payload: dict[str, Any]


class ChatChannelRead(BaseModel):
    slug: str
    is_readonly: bool
