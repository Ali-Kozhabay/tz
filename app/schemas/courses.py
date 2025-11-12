from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, conint

from app.models.enums import ContentVisibility, LessonStatus


class CourseCreate(BaseModel):
    title: str
    slug: str
    visibility: ContentVisibility = ContentVisibility.public
    cover_url: str | None = None
    description: str | None = None


class LessonCreate(BaseModel):
    course_id: int
    index: int
    title: str
    content_url: str
    duration_sec: int = 0
    published: bool = False


class LessonRead(BaseModel):
    id: int
    index: int
    title: str
    content_url: str
    duration_sec: int
    published: bool

    model_config = {"from_attributes": True}


class CourseRead(BaseModel):
    id: int
    title: str
    slug: str
    visibility: ContentVisibility
    cover_url: str | None
    description: str | None
    lessons_count: int | None = None

    model_config = {"from_attributes": True}


class CourseDetail(BaseModel):
    course: CourseRead
    lessons: list[LessonRead]
    progress: dict[str, Any] | None = None


class PaginatedCourses(BaseModel):
    items: list[CourseRead]
    next_cursor: str | None = None


class ProgressMarkRequest(BaseModel):
    lesson_id: int
    status: LessonStatus = LessonStatus.in_progress
    percent: int = Field(ge=0, le=100)


class ProgressMarkResponse(BaseModel):
    ok: bool = True
