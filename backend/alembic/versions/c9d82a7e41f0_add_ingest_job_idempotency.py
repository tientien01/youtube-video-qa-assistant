"""add ingest job idempotency and active-target guards

Revision ID: c9d82a7e41f0
Revises: a424b0f1c95b
Create Date: 2026-07-16
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "c9d82a7e41f0"
down_revision: str | Sequence[str] | None = "a424b0f1c95b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ACTIVE_JOB_PREDICATE = "status IN ('pending', 'running', 'retry_wait')"


def upgrade() -> None:
    with op.batch_alter_table("ingest_jobs") as batch_op:
        batch_op.add_column(sa.Column("idempotency_key", sa.String(length=64), nullable=True))
        batch_op.create_index("uq_ingest_jobs_idempotency_key", ["idempotency_key"], unique=True)

    op.create_index(
        "uq_ingest_jobs_active_target",
        "ingest_jobs",
        ["video_id", "target_fingerprint"],
        unique=True,
        sqlite_where=sa.text(ACTIVE_JOB_PREDICATE),
        postgresql_where=sa.text(ACTIVE_JOB_PREDICATE),
    )


def downgrade() -> None:
    op.drop_index("uq_ingest_jobs_active_target", table_name="ingest_jobs")
    with op.batch_alter_table("ingest_jobs") as batch_op:
        batch_op.drop_index("uq_ingest_jobs_idempotency_key")
        batch_op.drop_column("idempotency_key")
