"""initial

Hand-authored (no live Postgres instance was reachable in this environment to
run `alembic revision --autogenerate`; DEVOPS-AGENT's docker-compose Postgres
was not up yet). This mirrors the SQLAlchemy models in backend/app/models/
exactly. Verify with `alembic upgrade head` once Postgres is running.

Revision ID: f34629ab1df4
Revises:
Create Date: 2026-08-31 21:43:09.662124

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f34629ab1df4'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Enum types (kept as module-level objects so create/drop calls can reuse them).
video_source_type_enum = sa.Enum("url", "upload", name="videosourcetype")
video_job_status_enum = sa.Enum(
    "pending",
    "transcribing",
    "analyzing",
    "rendering",
    "completed",
    "partial",
    "failed",
    name="videojobstatus",
)
short_clip_category_enum = sa.Enum(
    "viral",
    "educational",
    "emotional",
    "surprising",
    "story",
    "other",
    name="shortclipcategory",
)
short_clip_status_enum = sa.Enum(
    "scored", "rendering", "ready", "failed", name="shortclipstatus"
)
broll_visual_type_enum = sa.Enum(
    "stock_footage",
    "image",
    "screenshot",
    "screen_recording",
    "chart",
    "animation",
    name="brollvisualtype",
)

_SCORE_COLUMNS = (
    "hook_strength",
    "standalone_value",
    "engagement",
    "retention",
    "payoff",
    "clarity",
    "shareability",
    "viral_potential",
    "b_roll_quality",
)


def upgrade() -> None:
    """Upgrade schema."""
    # NOTE: each sa.Enum below is only referenced once (one column each), so
    # SQLAlchemy's postgresql dialect emits `CREATE TYPE ... (checkfirst)`
    # automatically as part of the owning create_table() call - no separate
    # explicit `.create()` step is needed (and would double-create).

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "video_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("source_type", video_source_type_enum, nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("file_path", sa.String(length=1000), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column(
            "status",
            video_job_status_enum,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_video_jobs_id", "video_jobs", ["id"])
    op.create_index("ix_video_jobs_user_id", "video_jobs", ["user_id"])
    op.create_index(
        "ix_video_jobs_user_status", "video_jobs", ["user_id", "status"]
    )

    op.create_table(
        "short_clips",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("video_job_id", sa.Integer(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("category", short_clip_category_enum, nullable=False),
        sa.Column("start_time", sa.Float(), nullable=False),
        sa.Column("end_time", sa.Float(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("transcript_excerpt", sa.Text(), nullable=False),
        sa.Column("hook_strength", sa.Integer(), nullable=False),
        sa.Column("standalone_value", sa.Integer(), nullable=False),
        sa.Column("engagement", sa.Integer(), nullable=False),
        sa.Column("retention", sa.Integer(), nullable=False),
        sa.Column("payoff", sa.Integer(), nullable=False),
        sa.Column("clarity", sa.Integer(), nullable=False),
        sa.Column("shareability", sa.Integer(), nullable=False),
        sa.Column("viral_potential", sa.Integer(), nullable=False),
        sa.Column("b_roll_quality", sa.Integer(), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column(
            "status",
            short_clip_status_enum,
            nullable=False,
            server_default="scored",
        ),
        sa.Column("file_path", sa.String(length=1000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["video_job_id"], ["video_jobs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        *(
            sa.CheckConstraint(
                f"{col} >= 1 AND {col} <= 10", name=f"ck_short_clips_{col}_1_to_10"
            )
            for col in _SCORE_COLUMNS
        ),
    )
    op.create_index("ix_short_clips_id", "short_clips", ["id"])
    op.create_index("ix_short_clips_video_job_id", "short_clips", ["video_job_id"])
    op.create_index(
        "ix_short_clips_video_job_rank", "short_clips", ["video_job_id", "rank"]
    )

    op.create_table(
        "broll_suggestions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("short_clip_id", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Float(), nullable=False),
        sa.Column("end_time", sa.Float(), nullable=False),
        sa.Column("visual_type", broll_visual_type_enum, nullable=False),
        sa.Column("search_keywords", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("stock_asset_url", sa.String(length=1000), nullable=True),
        sa.ForeignKeyConstraint(
            ["short_clip_id"], ["short_clips.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_broll_suggestions_id", "broll_suggestions", ["id"])
    op.create_index(
        "ix_broll_suggestions_short_clip_id", "broll_suggestions", ["short_clip_id"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("broll_suggestions")
    op.drop_table("short_clips")
    op.drop_table("video_jobs")
    op.drop_table("users")

    bind = op.get_bind()
    broll_visual_type_enum.drop(bind, checkfirst=True)
    short_clip_status_enum.drop(bind, checkfirst=True)
    short_clip_category_enum.drop(bind, checkfirst=True)
    video_job_status_enum.drop(bind, checkfirst=True)
    video_source_type_enum.drop(bind, checkfirst=True)
