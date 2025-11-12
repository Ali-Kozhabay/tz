from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_db_session,
    get_optional_user,
    require_role,
)
from app.models import ContentVisibility, UserRole
from app.schemas import (
    CourseCreate,
    CourseDetail,
    CourseRead,
    LessonCreate,
    LessonRead,
    PaginatedCourses,
    ProgressMarkRequest,
    ProgressMarkResponse,
    StorageSignRequest,
)
from app.services.courses import CourseService
from app.services.storage import StorageService
from app.utils.rate_limit import limiter

router = APIRouter(tags=["Courses"])


@router.get("/courses", response_model=PaginatedCourses)
async def list_courses(
    visibility: ContentVisibility | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=100),
    cursor: int | None = Query(default=None, description="Opaque cursor (course id)"),
    session: AsyncSession = Depends(get_db_session),
    user=Depends(get_optional_user),
):
    service = CourseService(session)
    role = user.role if user else UserRole.guest
    courses, counts, next_cursor = await service.list_courses(
        role, visibility, limit, cursor
    )
    counts_map = {course_id: total for course_id, total in counts}
    items = [
        CourseRead(
            id=course.id,
            title=course.title,
            slug=course.slug,
            visibility=course.visibility,
            cover_url=course.cover_url,
            description=course.description,
            lessons_count=counts_map.get(course.id, 0),
        )
        for course in courses
    ]
    return PaginatedCourses(
        items=items, next_cursor=str(next_cursor) if next_cursor else None
    )


@router.get("/courses/{slug}", response_model=CourseDetail)
async def get_course(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
    user=Depends(get_optional_user),
):
    service = CourseService(session)
    storage = StorageService()
    role = user.role if user else UserRole.guest
    course = await service.get_course(slug, role)
    lessons = await service.published_lessons(course)
    lessons_payload: list[LessonRead] = []
    for lesson in lessons:
        signed = storage.sign(StorageSignRequest(key=lesson.content_url, method="get"))
        lessons_payload.append(
            LessonRead(
                id=lesson.id,
                index=lesson.index,
                title=lesson.title,
                content_url=signed.url,
                duration_sec=lesson.duration_sec,
                published=lesson.published,
            )
        )
    progress = await service.load_progress_for_course(user, course) if user else None
    course_read = CourseRead(
        id=course.id,
        title=course.title,
        slug=course.slug,
        visibility=course.visibility,
        cover_url=course.cover_url,
        description=course.description,
        lessons_count=len(lessons_payload),
    )
    return CourseDetail(course=course_read, lessons=lessons_payload, progress=progress)


@router.post(
    "/admin/courses",
    response_model=CourseRead,
    dependencies=[Depends(require_role(UserRole.admin))],
)
async def create_course(
    payload: CourseCreate, session: AsyncSession = Depends(get_db_session)
):
    service = CourseService(session)
    course = await service.create_course(payload)
    return CourseRead.model_validate(course, from_attributes=True)


@router.post(
    "/admin/lessons",
    response_model=LessonRead,
    dependencies=[Depends(require_role(UserRole.admin))],
)
async def create_lesson(
    payload: LessonCreate, session: AsyncSession = Depends(get_db_session)
):
    service = CourseService(session)
    lesson = await service.create_lesson(payload)
    return LessonRead.model_validate(lesson, from_attributes=True)


@router.post("/progress/mark", response_model=ProgressMarkResponse)
@limiter.limit("20/minute")
async def mark_progress(
    request: Request,
    payload: ProgressMarkRequest,
    session: AsyncSession = Depends(get_db_session),
    user=Depends(get_current_user),
):
    service = CourseService(session)
    await service.upsert_progress(user, payload)
    return ProgressMarkResponse(ok=True)
