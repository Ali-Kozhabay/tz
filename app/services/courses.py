from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models import ContentVisibility, Course, Lesson, LessonStatus, Progress, User, UserRole
from app.schemas import CourseCreate, LessonCreate, ProgressMarkRequest


class CourseService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_courses(
        self,
        role: UserRole,
        visibility: ContentVisibility | None,
        limit: int,
        cursor: int | None,
    ) -> tuple[list[Course], Sequence[tuple[int, int]], int | None]:
        statement: Select[Any] = (
            select(Course, func.count(Lesson.id).label("lessons_count"))
            .outerjoin(Lesson, Lesson.course_id == Course.id)
            .group_by(Course.id)
            .order_by(Course.id.asc())
            .limit(limit + 1)
        )

        allowed_visibility = {ContentVisibility.public}
        if role in (UserRole.member, UserRole.admin):
            allowed_visibility.add(ContentVisibility.member)

        if visibility:
            if visibility not in allowed_visibility:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Visibility denied")
            statement = statement.where(Course.visibility == visibility)
        else:
            statement = statement.where(Course.visibility.in_(allowed_visibility))

        if cursor:
            statement = statement.where(Course.id > cursor)

        result = await self.session.execute(statement)
        rows = result.all()
        next_cursor = None
        if len(rows) > limit:
            next_cursor = rows[-1][0].id
            rows = rows[:limit]

        courses = [row[0] for row in rows]
        counts = [(row[0].id, row[1]) for row in rows]
        return courses, counts, next_cursor

    async def get_course(self, slug: str, role: UserRole) -> Course:
        course = await self.session.scalar(
            select(Course).where(Course.slug == slug).options(joinedload(Course.lessons))
        )
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
        if course.visibility == ContentVisibility.member and role not in (UserRole.member, UserRole.admin):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Members only")
        return course

    async def create_course(self, payload: CourseCreate) -> Course:
        course = Course(**payload.model_dump())
        self.session.add(course)
        await self.session.commit()
        await self.session.refresh(course)
        return course

    async def create_lesson(self, payload: LessonCreate) -> Lesson:
        lesson = Lesson(**payload.model_dump())
        self.session.add(lesson)
        await self.session.commit()
        await self.session.refresh(lesson)
        return lesson

    async def published_lessons(self, course: Course) -> list[Lesson]:
        return [lesson for lesson in course.lessons if lesson.published]

    async def upsert_progress(self, user: User, payload: ProgressMarkRequest) -> Progress:
        lesson = await self.session.get(Lesson, payload.lesson_id)
        if not lesson:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
        course = await self.session.get(Course, lesson.course_id)
        if course and course.visibility == ContentVisibility.member and user.role not in (
            UserRole.member,
            UserRole.admin,
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Members only lesson")

        progress = await self.session.scalar(
            select(Progress).where(
                Progress.user_id == user.id,
                Progress.lesson_id == payload.lesson_id,
            )
        )
        if not progress:
            progress = Progress(
                user_id=user.id,
                lesson_id=payload.lesson_id,
                status=payload.status,
                percent=payload.percent,
            )
            self.session.add(progress)
        else:
            progress.status = payload.status
            progress.percent = payload.percent

        await self.session.commit()
        await self.session.refresh(progress)
        return progress

    async def load_progress_for_course(self, user: User, course: Course) -> dict[str, Any] | None:
        if not user:
            return None
        lesson_ids = [lesson.id for lesson in course.lessons if lesson.published]
        if not lesson_ids:
            return None
        result = await self.session.execute(
            select(
                func.avg(Progress.percent).label("percent"),
                func.count().label("lessons_done"),
            ).where(
                Progress.user_id == user.id,
                Progress.lesson_id.in_(lesson_ids),
                Progress.status == LessonStatus.done,
            )
        )
        row = result.first()
        if not row:
            return {"percent": 0, "lessons_done": 0}
        percent_value, lessons_done = row
        percent = int(percent_value) if percent_value is not None else 0
        return {"percent": percent, "lessons_done": int(lessons_done or 0)}
