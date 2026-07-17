"""persist complete embedding identity config

Revision ID: e72b8d91ac44
Revises: d31f6c8a92b7
Create Date: 2026-07-17
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "e72b8d91ac44"
down_revision: str | Sequence[str] | None = "d31f6c8a92b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("index_versions") as batch_op:
        batch_op.add_column(sa.Column("embedding_config", sa.JSON(), server_default=sa.text("'{}'"), nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("index_versions") as batch_op:
        batch_op.drop_column("embedding_config")
