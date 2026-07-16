"""version transcript parser and normalization provenance

Revision ID: d31f6c8a92b7
Revises: c9d82a7e41f0
Create Date: 2026-07-16
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "d31f6c8a92b7"
down_revision: str | Sequence[str] | None = "c9d82a7e41f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("transcripts") as batch_op:
        batch_op.drop_constraint("uq_transcripts_video_provider_hash", type_="unique")
        batch_op.add_column(
            sa.Column(
                "quality_diagnostics",
                sa.JSON(),
                server_default=sa.text("'{}'"),
                nullable=False,
            )
        )
        batch_op.create_unique_constraint(
            "uq_transcripts_video_provider_hash_version",
            ["video_id", "provider", "content_hash", "parser_version", "normalizer_version"],
        )


def downgrade() -> None:
    with op.batch_alter_table("transcripts") as batch_op:
        batch_op.drop_constraint("uq_transcripts_video_provider_hash_version", type_="unique")
        batch_op.create_unique_constraint(
            "uq_transcripts_video_provider_hash",
            ["video_id", "provider", "content_hash"],
        )
        batch_op.drop_column("quality_diagnostics")
