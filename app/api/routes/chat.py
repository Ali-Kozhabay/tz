from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.models.chat import Channel
from app.schemas.chat import ChatChannelRead

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.get(
    "/channels", response_model=list[ChatChannelRead], summary="List chat channels"
)
async def list_channels(session: AsyncSession = Depends(get_db_session)):
    result = await session.execute(select(Channel.slug, Channel.is_readonly))
    return [
        ChatChannelRead(slug=slug, is_readonly=is_readonly)
        for slug, is_readonly in result.all()
    ]


@router.get(
    "/docs",
    summary="How to use WebSocket chat",
    response_model=dict,
    description=(
        "Explains how to connect to the WebSocket chat API. "
        "Use `ws://host/ws/channels/{slug}` with an access JWT passed either as "
        "`Authorization: Bearer <token>` or via `?token=` query. "
        "Client messages are JSON with types `message.create`, "
        "`message.delete`, `message.pin`."
    ),
)
async def chat_docs():
    return {
        "ws_url": "/ws/channels/{slug}",
        "auth": "Authorization: Bearer <access token> or ?token=<token>",
        "events": {
            "message.create": {
                "payload": {"text": "your text", "parent_id": "optional"}
            },
            "message.delete": {"payload": {"id": "message id"}},
            "message.pin": {"payload": {"id": "message id", "note": "admin only"}},
        },
        "broadcasts": [
            "message.history",
            "message.created",
            "message.deleted",
            "message.pinned",
        ],
    }
