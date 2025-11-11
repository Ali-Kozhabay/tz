from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException, status
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 - ensure models register with metadata
from app.db import Base
from app.models import AuditLog, Invite, User, UserRole
from app.services.invites import InviteService


@pytest_asyncio.fixture()
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_invite_redeem_promotes_user_and_logs(session: AsyncSession):
    user = User(email="member@example.com", password_hash="hash", role=UserRole.user)
    invite = Invite(
        code="code-123",
        role_to_grant=UserRole.member,
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    session.add_all([user, invite])
    await session.commit()
    await session.refresh(user)

    service = InviteService(session)
    redeemed = await service.redeem(invite.code, user)

    assert redeemed.used_by_id == user.id
    assert redeemed.used_at is not None
    await session.refresh(user)
    assert user.role == UserRole.member

    audit_rows = (await session.execute(select(AuditLog))).scalars().all()
    assert len(audit_rows) == 1
    assert audit_rows[0].action == "invite.redeem"
    assert audit_rows[0].meta["granted_role"] == "member"


@pytest.mark.asyncio
async def test_invite_redeem_rejects_expired_codes(session: AsyncSession):
    user = User(email="expired@example.com", password_hash="hash", role=UserRole.user)
    invite = Invite(
        code="expired-code",
        role_to_grant=UserRole.member,
        expires_at=datetime.now(UTC) - timedelta(hours=1),
    )
    session.add_all([user, invite])
    await session.commit()

    service = InviteService(session)

    with pytest.raises(HTTPException) as excinfo:
        await service.redeem(invite.code, user)

    assert excinfo.value.status_code == status.HTTP_410_GONE
