from __future__ import annotations

from enum import Enum


class UserRole(str, Enum):
    guest = "guest"
    user = "user"
    member = "member"
    admin = "admin"


class ContentVisibility(str, Enum):
    public = "public"
    member = "member"


class LessonStatus(str, Enum):
    in_progress = "in_progress"
    done = "done"
