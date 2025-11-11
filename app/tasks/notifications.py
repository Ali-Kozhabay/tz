from __future__ import annotations

import smtplib
from email.message import EmailMessage
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from redis import Redis
from rq import Queue

from app.config import settings

templates_path = Path(__file__).resolve().parent.parent / "templates" / "emails"
env = Environment(
    loader=FileSystemLoader(templates_path),
    autoescape=select_autoescape(enabled_extensions=("txt", "html")),
)

redis_conn = Redis.from_url(settings.redis_url)
mail_queue = Queue("notifications", connection=redis_conn)


def _render(template_name: str, **context) -> str:
    template = env.get_template(template_name)
    return template.render(**context)


def _send_email(subject: str, to_email: str, body: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["To"] = to_email
    msg["From"] = settings.smtp_user or f"no-reply@{settings.base_url}"
    msg.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
        if settings.smtp_user and settings.smtp_pass:
            smtp.login(settings.smtp_user, settings.smtp_pass)
        smtp.send_message(msg)


def send_welcome_email(email: str, name: str | None, locale: str) -> None:
    body = _render("welcome.txt", name=name or "friend", locale=locale, base_url=settings.base_url)
    _send_email("Welcome to the platform", email, body)


def send_invite_redeemed_email(email: str, locale: str, role: str) -> None:
    body = _render("invite_redeemed.txt", locale=locale, role=role)
    _send_email("Invite redeemed", email, body)


def send_weekly_digest(email: str, locale: str, summary: str) -> None:
    body = _render("weekly_digest.txt", locale=locale, summary=summary)
    _send_email("Weekly digest", email, body)
