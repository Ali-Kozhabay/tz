from fastapi import APIRouter, Depends, Query, Request

from app.api.deps import get_current_user, require_role
from app.models import UserRole
from app.schemas import StorageSignRequest, StorageSignResponse
from app.services.storage import StorageService
from app.utils.rate_limit import limiter

router = APIRouter(prefix="/storage", tags=["Storage"])


@router.get("/sign", response_model=StorageSignResponse)
@limiter.limit("60/minute")
async def sign_download(
    request: Request,
    key: str = Query(),
    _: object = Depends(get_current_user),
):
    service = StorageService()
    payload = StorageSignRequest(key=key, method="get")
    return service.sign(payload)


@router.get("/sign-upload", response_model=StorageSignResponse)
@limiter.limit("5/minute")
async def sign_upload(
    request: Request,
    key: str = Query(),
    _: object = Depends(require_role(UserRole.admin)),
):
    service = StorageService()
    payload = StorageSignRequest(key=key, method="put")
    return service.sign(payload)
