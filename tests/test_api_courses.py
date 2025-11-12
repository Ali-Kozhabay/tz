from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, AsyncIterator, Callable

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import deps as deps_module
from app.api.routes import courses as courses_routes
from app.models import ContentVisibility, UserRole
from app.schemas import StorageSignResponse
from app.services import courses as courses_service
from app.utils.rate_limit import limiter


class DummyUser:
    def __init__(self, role: UserRole):
        self.id = 1
        self.role = role


class DummyLesson:
    def __init__(
        self,
        lesson_id: int,
        *,
        index: int,
        title: str,
        content_url: str,
        duration_sec: int,
        published: bool,
    ):
        self.id = lesson_id
        self.index = index
        self.title = title
        self.content_url = content_url
        self.duration_sec = duration_sec
        self.published = published


class DummyCourse:
    def __init__(
        self,
        course_id: int,
        *,
        title: str,
        slug: str,
        visibility: ContentVisibility,
        cover_url: str | None,
        description: str | None,
        lessons: list[DummyLesson] | None = None,
    ):
        self.id = course_id
        self.title = title
        self.slug = slug
        self.visibility = visibility
        self.cover_url = cover_url
        self.description = description
        self.lessons = lessons or []


async def _session_override() -> AsyncIterator[object]:
    yield object()


def _build_client(
    overrides: dict[Callable[..., Any], Callable[..., Any]] | None = None,
) -> TestClient:
    app = FastAPI()
    app.include_router(courses_routes.router)
    app.state.limiter = limiter
    app.dependency_overrides[deps_module.get_db_session] = _session_override
    if overrides:
        for dependency, override in overrides.items():
            app.dependency_overrides[dependency] = override
    return TestClient(app)


@pytest.fixture()
def member_user():
    return DummyUser(UserRole.member)


def test_list_courses_returns_expected_payload(monkeypatch, member_user):
    course = DummyCourse(
        10,
        title="Intro to Testing",
        slug="intro-testing",
        visibility=ContentVisibility.public,
        cover_url="https://img.example/cover.png",
        description="Basics",
    )

    async def fake_list_courses(self, role, visibility, limit, cursor):  # noqa: ARG001
        assert role == UserRole.member
        assert limit == 3
        assert cursor is None
        return [course], [(course.id, 5)], 42

    async def optional_user_override():
        return member_user

    monkeypatch.setattr(
        courses_service.CourseService, "list_courses", fake_list_courses
    )
    client = _build_client({deps_module.get_optional_user: optional_user_override})

    response = client.get("/courses?limit=3")
    assert response.status_code == 200
    payload = response.json()
    assert payload["next_cursor"] == "42"
    assert payload["items"] == [
        {
            "id": 10,
            "title": "Intro to Testing",
            "slug": "intro-testing",
            "visibility": "public",
            "cover_url": "https://img.example/cover.png",
            "description": "Basics",
            "lessons_count": 5,
        }
    ]


def test_get_course_includes_lessons_and_progress(monkeypatch, member_user):
    lessons = [
        DummyLesson(
            1,
            index=1,
            title="Warm up",
            content_url="videos/1.mp4",
            duration_sec=90,
            published=True,
        )
    ]
    course = DummyCourse(
        55,
        title="Advanced Testing",
        slug="advanced-testing",
        visibility=ContentVisibility.member,
        cover_url=None,
        description="Deep dive",
        lessons=lessons,
    )

    async def fake_get_course(self, slug, role):  # noqa: ARG002
        assert slug == "advanced-testing"
        assert role == UserRole.member
        return course

    async def fake_published_lessons(self, course_obj):
        assert course_obj is course
        return lessons

    async def fake_load_progress(self, user, course_obj):  # noqa: ARG002
        return {"percent": 80, "lessons_done": 1}

    class DummyStorageService:
        def sign(self, payload):
            expires = datetime.now(UTC) + timedelta(minutes=5)
            return StorageSignResponse(
                url=f"https://cdn/{payload.key}", expires_at=expires
            )

    async def optional_user_override():
        return member_user

    monkeypatch.setattr(courses_service.CourseService, "get_course", fake_get_course)
    monkeypatch.setattr(
        courses_service.CourseService, "published_lessons", fake_published_lessons
    )
    monkeypatch.setattr(
        courses_service.CourseService, "load_progress_for_course", fake_load_progress
    )
    monkeypatch.setattr(courses_routes, "StorageService", DummyStorageService)

    client = _build_client({deps_module.get_optional_user: optional_user_override})

    response = client.get("/courses/advanced-testing")
    assert response.status_code == 200
    payload = response.json()
    assert payload["course"]["id"] == 55
    assert payload["course"]["lessons_count"] == 1
    assert payload["lessons"][0]["content_url"].startswith("https://cdn/videos/1.mp4")
    assert payload["progress"] == {"percent": 80, "lessons_done": 1}


def test_admin_create_course_returns_read_model(monkeypatch):
    course = DummyCourse(
        77,
        title="Authoring APIs",
        slug="authoring-apis",
        visibility=ContentVisibility.member,
        cover_url=None,
        description=None,
    )

    async def fake_create_course(self, payload):
        assert payload.title == "Authoring APIs"
        assert payload.visibility == ContentVisibility.member
        return course

    async def current_user_override():
        return DummyUser(UserRole.admin)

    monkeypatch.setattr(
        courses_service.CourseService, "create_course", fake_create_course
    )
    client = _build_client({deps_module.get_current_user: current_user_override})

    response = client.post(
        "/admin/courses",
        json={
            "title": "Authoring APIs",
            "slug": "authoring-apis",
            "visibility": "member",
            "cover_url": None,
            "description": None,
        },
    )
    assert response.status_code == 200
    assert response.json() == {
        "id": 77,
        "title": "Authoring APIs",
        "slug": "authoring-apis",
        "visibility": "member",
        "cover_url": None,
        "description": None,
        "lessons_count": None,
    }
