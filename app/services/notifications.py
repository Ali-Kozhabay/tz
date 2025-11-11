from __future__ import annotations

import asyncio
import logging

from app.models import User
from app.tasks.notifications import mail_queue

logger = logging.getLogger(__name__)


async def _enqueue(job: str, *args) -> None:
    try:
        await asyncio.to_thread(mail_queue.enqueue, job, *args)
    except Exception as exc:  # noqa: BLE001
        logger.warning("notifications.enqueue_failed", extra={"job": job, "error": str(exc)})


async def enqueue_welcome(user: User) -> None:
    locale = user.profile.locale if user.profile else "en"
    name = user.profile.name if user.profile else None
    await _enqueue("app.tasks.notifications.send_welcome_email", user.email, name, locale)


async def enqueue_invite_redeemed(user: User) -> None:
    locale = user.profile.locale if user.profile else "en"
    await _enqueue("app.tasks.notifications.send_invite_redeemed_email", user.email, locale, user.role.value)


async def enqueue_weekly_digest(user: User, summary: str) -> None:
    locale = user.profile.locale if user.profile else "en"
    await _enqueue("app.tasks.notifications.send_weekly_digest", user.email, locale, summary)
