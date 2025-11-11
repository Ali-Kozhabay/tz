from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session, require_role
from app.models import UserRole
from app.schemas import InviteCreateRequest, InviteRead, InviteRedeemRequest
from app.services.invites import InviteService
from app.services.notifications import enqueue_invite_redeemed

router = APIRouter(tags=["Invites"])


@router.post("/admin/invites", response_model=InviteRead, status_code=status.HTTP_201_CREATED)
async def create_invite(
    payload: InviteCreateRequest,
    session:AsyncSession=Depends(get_db_session),
    user=Depends(require_role(UserRole.admin)),
):
    service = InviteService(session)
    invite = await service.create(user, payload)
    return InviteRead.model_validate(invite, from_attributes=True)


@router.post("/invites/redeem", response_model=InviteRead)
async def redeem_invite(
    payload: InviteRedeemRequest,
    session:AsyncSession=Depends(get_db_session),
    user=Depends(get_current_user),
):
    service = InviteService(session)
    invite = await service.redeem(payload.code, user)
    await enqueue_invite_redeemed(user)
    return InviteRead.model_validate(invite, from_attributes=True)
