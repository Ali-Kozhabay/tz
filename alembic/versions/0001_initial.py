"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2024-06-04 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    user_role = sa.Enum("guest", "user", "member", "admin", name="user_role")
    invite_role = sa.Enum("guest", "user", "member", "admin", name="invite_role")
    visibility_enum = sa.Enum("public", "member", name="course_visibility")
    progress_status = sa.Enum("in_progress", "done", name="progress_status")

    bind = op.get_bind()
    user_role.create(bind, checkfirst=True)
    invite_role.create(bind, checkfirst=True)
    visibility_enum.create(bind, checkfirst=True)
    progress_status.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, nullable=False, server_default="guest"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "profiles",
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("avatar_url", sa.String(length=512), nullable=True),
        sa.Column("locale", sa.String(length=10), nullable=False, server_default="en"),
        sa.Column(
            "settings", sa.JSON(), nullable=False, server_default=sa.text("'{}'")
        ),
    )

    op.create_table(
        "invites",
        sa.Column("code", sa.String(length=64), primary_key=True),
        sa.Column("role_to_grant", invite_role, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("used_by_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("used_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "courses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column(
            "visibility", visibility_enum, nullable=False, server_default="public"
        ),
        sa.Column("cover_url", sa.String(length=512)),
        sa.Column("description", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "channels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column(
            "is_readonly", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )
    op.create_index("ix_channels_slug", "channels", ["slug"], unique=True)

    op.create_table(
        "lessons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "course_id", sa.Integer(), sa.ForeignKey("courses.id", ondelete="CASCADE")
        ),
        sa.Column("index", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content_url", sa.String(length=512), nullable=False),
        sa.Column("duration_sec", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "published", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.UniqueConstraint("course_id", "index", name="uq_lessons_course_idx"),
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "channel_id", sa.Integer(), sa.ForeignKey("channels.id", ondelete="CASCADE")
        ),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE")
        ),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("messages.id")),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("attachments", sa.JSON(), server_default=sa.text("'[]'")),
        sa.Column(
            "pinned", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "lesson_id",
            sa.Integer(),
            sa.ForeignKey("lessons.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status", progress_status, nullable=False, server_default="in_progress"
        ),
        sa.Column("percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "lesson_id", name="uq_progress_user_lesson"),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("entity", sa.String(length=128), nullable=False),
        sa.Column("entity_id", sa.String(length=128), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("progress")
    op.drop_table("messages")
    op.drop_table("lessons")
    op.drop_index("ix_channels_slug", table_name="channels")
    op.drop_table("channels")
    op.drop_table("courses")
    op.drop_table("invites")
    op.drop_table("profiles")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    sa.Enum(name="progress_status").drop(bind, checkfirst=True)
    sa.Enum(name="course_visibility").drop(bind, checkfirst=True)
    sa.Enum(name="invite_role").drop(bind, checkfirst=True)
    sa.Enum(name="user_role").drop(bind, checkfirst=True)
