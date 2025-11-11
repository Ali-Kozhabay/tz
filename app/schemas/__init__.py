"""Expose schema namespaces."""

from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenPair
from app.schemas.chat import ChatMessagePayload, WebsocketMessage
from app.schemas.common import Message, UserRead
from app.schemas.courses import (
    CourseCreate,
    CourseDetail,
    CourseRead,
    LessonCreate,
    LessonRead,
    PaginatedCourses,
    ProgressMarkRequest,
    ProgressMarkResponse,
)
from app.schemas.invites import InviteCreateRequest, InviteRead, InviteRedeemRequest
from app.schemas.storage import StorageSignRequest, StorageSignResponse

__all__ = [
    "LoginRequest",
    "RefreshRequest",
    "RegisterRequest",
    "TokenPair",
    "ChatMessagePayload",
    "WebsocketMessage",
    "Message",
    "UserRead",
    "CourseCreate",
    "CourseDetail",
    "CourseRead",
    "LessonCreate",
    "LessonRead",
    "PaginatedCourses",
    "ProgressMarkRequest",
    "ProgressMarkResponse",
    "InviteCreateRequest",
    "InviteRead",
    "InviteRedeemRequest",
    "StorageSignRequest",
    "StorageSignResponse",
]
