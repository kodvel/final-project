"""add decision brief fields

Revision ID: 0002_add_decision_brief_fields
Revises: 0001_add_message_source_citation_chunk_id
Create Date: 2026-05-13
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_add_decision_brief_fields"
down_revision: str | None = "0001_add_message_source_citation_chunk_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    if not _has_column("decision_brief", "sequence_number"):
        op.add_column("decision_brief", sa.Column("sequence_number", sa.Integer(), nullable=False, server_default="1"))
    if not _has_column("decision_brief", "objective"):
        op.add_column("decision_brief", sa.Column("objective", sa.String(), nullable=True))
    if not _has_column("decision_brief", "context_cutoff_message_id"):
        op.add_column("decision_brief", sa.Column("context_cutoff_message_id", sa.Integer(), nullable=True))
    if not _has_column("decision_brief", "status_updated_at"):
        op.add_column("decision_brief", sa.Column("status_updated_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("decision_brief", "status_updated_at")
    op.drop_column("decision_brief", "context_cutoff_message_id")
    op.drop_column("decision_brief", "objective")
    op.drop_column("decision_brief", "sequence_number")
