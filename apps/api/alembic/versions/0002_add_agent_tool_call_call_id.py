"""add agent tool call call id

Revision ID: 0002_add_agent_tool_call_call_id
Revises: 0001_add_message_source_citation_chunk_id
Create Date: 2026-05-13
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(table_name):
        return True
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _has_index(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(table_name):
        return True
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    if not _has_column("agent_tool_call", "call_id"):
        op.add_column("agent_tool_call", sa.Column("call_id", sa.String(), nullable=True))
    if not _has_index("agent_tool_call", "ix_agent_tool_call_call_id"):
        op.create_index("ix_agent_tool_call_call_id", "agent_tool_call", ["call_id"])


def downgrade() -> None:
    if _has_index("agent_tool_call", "ix_agent_tool_call_call_id"):
        op.drop_index("ix_agent_tool_call_call_id", table_name="agent_tool_call")
    if _has_column("agent_tool_call", "call_id"):
        op.drop_column("agent_tool_call", "call_id")
