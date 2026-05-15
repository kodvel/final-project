"""add message source citation chunk id

Revision ID: 0001_add_message_source_citation_chunk_id
Revises:
Create Date: 2026-05-12
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = "0000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    if not _has_column("message_source_citation", "chunk_id"):
        op.add_column("message_source_citation", sa.Column("chunk_id", sa.String(), nullable=True))


def downgrade() -> None:
    if _has_column("message_source_citation", "chunk_id"):
        op.drop_column("message_source_citation", "chunk_id")
