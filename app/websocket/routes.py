from __future__ import annotations

import asyncio
import contextlib

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AsyncSessionLocal
from app.models.user import User
from app.schemas.chat import ChatMessagePayload
from app.services.chat import ChatService
from app.utils.security import decode_token


async def _acquire_session() -> AsyncSession:
    return AsyncSessionLocal()


async def _auth_websocket(websocket: WebSocket, session: AsyncSession):
    token = websocket.query_params.get("token")
    auth_header = websocket.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
    if not token:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION, reason="Missing token"
        )
        raise WebSocketDisconnect(code=status.WS_1008_POLICY_VIOLATION)
    try:
        payload = decode_token(token)
    except Exception as exc:  # noqa: BLE001
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token"
        )
        raise WebSocketDisconnect(code=status.WS_1008_POLICY_VIOLATION) from exc
    if payload.get("type") != "access":
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token type"
        )
        raise WebSocketDisconnect(code=status.WS_1008_POLICY_VIOLATION)
    user = await session.get(User, int(payload["sub"]))
    if not user:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION, reason="User not found"
        )
        raise WebSocketDisconnect(code=status.WS_1008_POLICY_VIOLATION)
    return user


async def _redis_forward(pubsub, websocket: WebSocket):
    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            await websocket.send_text(message["data"])
    except asyncio.CancelledError:
        pass


async def _handle_event(
    slug: str, event: dict, chat_service: ChatService, user: User, websocket: WebSocket
):
    event_type = event.get("type")
    payload = event.get("payload", {})
    if event_type == "message.create":
        data = ChatMessagePayload(**payload)
        created = await chat_service.create_message(slug, user, data)
        await websocket.send_json(
            {"type": "message.ack", "payload": {"id": created["id"]}}
        )
    elif event_type == "message.delete":
        message_id = payload.get("id")
        if not message_id:
            await websocket.send_json(
                {"type": "error", "payload": {"message": "id required"}}
            )
            return
        await chat_service.delete_message(slug, int(message_id), user)
    elif event_type == "message.pin":
        message_id = payload.get("id")
        if not message_id:
            await websocket.send_json(
                {"type": "error", "payload": {"message": "id required"}}
            )
            return
        await chat_service.pin_message(slug, int(message_id), user)
    else:
        await websocket.send_json(
            {"type": "error", "payload": {"message": "Unknown event"}}
        )


def register_websocket(app: FastAPI) -> None:
    @app.websocket("/ws/channels/{slug}")
    async def channel_socket(websocket: WebSocket, slug: str):
        session = await _acquire_session()
        chat_service = ChatService(session)
        pubsub = None
        forward_task = None
        try:
            user = await _auth_websocket(websocket, session)
            await websocket.accept()
            channel = await chat_service.get_channel(slug)
            history = await chat_service.fetch_recent(channel)
            await websocket.send_json({"type": "message.history", "payload": history})
            pubsub = await chat_service.subscribe(slug)
            forward_task = asyncio.create_task(_redis_forward(pubsub, websocket))
            try:
                while True:
                    event = await websocket.receive_json()
                    await _handle_event(slug, event, chat_service, user, websocket)
            except WebSocketDisconnect:
                pass
            finally:
                if forward_task:
                    forward_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await forward_task
                if pubsub:
                    await pubsub.unsubscribe(chat_service._channel_key(slug))
                    close_result = pubsub.close()
                    if asyncio.iscoroutine(close_result):
                        await close_result
        finally:
            await session.close()
