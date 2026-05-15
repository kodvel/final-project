"""add decision_brief task 8 fields

Revision ID: 0003_decision_brief_task_8_fields
Revises: 0002_add_agent_tool_call_call_id
Create Date: 2026-05-14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    if not _has_column("decision_brief", "sequence_number"):
        op.add_column(
            "decision_brief",
            sa.Column("sequence_number", sa.Integer(), nullable=False, server_default="1"),
        )
    if not _has_column("decision_brief", "context_cutoff_message_id"):
        op.add_column(
            "decision_brief",
            sa.Column("context_cutoff_message_id", sa.Integer(), nullable=True),
        )
    if not _has_column("decision_brief", "objective"):
        op.add_column(
            "decision_brief",
            sa.Column("objective", sa.String(), nullable=True),
        )
    if not _has_column("decision_brief", "status_updated_at"):
        op.add_column(
            "decision_brief",
            sa.Column(
                "status_updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.current_timestamp(),
            ),
        )


def downgrade() -> None:
    for column in ("status_updated_at", "objective", "context_cutoff_message_id", "sequence_number"):
        if _has_column("decision_brief", column):
            op.drop_column("decision_brief", column)
