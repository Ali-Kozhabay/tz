from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.schemas import LoginRequest, RefreshRequest, RegisterRequest, TokenPair
from app.services.auth import AuthService
from app.services.notifications import enqueue_welcome
from app.utils.rate_limit import limiter

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(
    request: Request,
    payload: RegisterRequest,
    session: AsyncSession = Depends(get_db_session),
):
    service = AuthService(session)
    user = await service.register(payload)
    await enqueue_welcome(user)
    return await service.build_tokens(user)


@router.post("/login", response_model=TokenPair)
@limiter.limit("10/minute")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db_session),
):
    service = AuthService(session)
    credentials = LoginRequest(email=form_data.username, password=form_data.password)
    user = await service.authenticate(credentials)
    return await service.build_tokens(user)


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, session: AsyncSession = Depends(get_db_session)):
    service = AuthService(session)
    return await service.refresh(payload.refresh)
