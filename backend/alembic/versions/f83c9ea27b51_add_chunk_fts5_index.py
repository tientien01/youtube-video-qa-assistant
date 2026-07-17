"""add derived FTS5 index for canonical child chunks

Revision ID: f83c9ea27b51
Revises: e72b8d91ac44
Create Date: 2026-07-17
"""

from collections.abc import Sequence

from alembic import op


revision: str = "f83c9ea27b51"
down_revision: str | Sequence[str] | None = "e72b8d91ac44"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE VIRTUAL TABLE chunk_fts USING fts5(
            chunk_id UNINDEXED,
            video_id UNINDEXED,
            index_version_id UNINDEXED,
            text,
            tokenize = 'unicode61 remove_diacritics 2'
        )
        """
    )
    op.execute(
        """
        INSERT INTO chunk_fts(rowid, chunk_id, video_id, index_version_id, text)
        SELECT rowid, id, video_id, index_version_id, text
        FROM chunks
        WHERE chunk_type = 'child'
        """
    )
    op.execute(
        """
        CREATE TRIGGER chunks_fts_insert AFTER INSERT ON chunks
        WHEN new.chunk_type = 'child'
        BEGIN
            INSERT INTO chunk_fts(rowid, chunk_id, video_id, index_version_id, text)
            VALUES (new.rowid, new.id, new.video_id, new.index_version_id, new.text);
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER chunks_fts_delete AFTER DELETE ON chunks
        WHEN old.chunk_type = 'child'
        BEGIN
            DELETE FROM chunk_fts WHERE rowid = old.rowid;
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER chunks_fts_update AFTER UPDATE OF text, chunk_type, video_id, index_version_id ON chunks
        BEGIN
            DELETE FROM chunk_fts WHERE rowid = old.rowid;
            INSERT INTO chunk_fts(rowid, chunk_id, video_id, index_version_id, text)
            SELECT new.rowid, new.id, new.video_id, new.index_version_id, new.text
            WHERE new.chunk_type = 'child';
        END
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS chunks_fts_update")
    op.execute("DROP TRIGGER IF EXISTS chunks_fts_delete")
    op.execute("DROP TRIGGER IF EXISTS chunks_fts_insert")
    op.execute("DROP TABLE IF EXISTS chunk_fts")
