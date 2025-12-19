"""Export reports table for statistical exports

Revision ID: 0004
Revises: 0003
Create Date: 2025-12-16

Creates:
- export_reports: Track generated export reports with password and TTL
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "export_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("report_id", sa.String(32), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(128), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("report_type", sa.String(20), nullable=False),  # weekly, monthly, custom
        sa.Column("file_format", sa.String(10), nullable=False),  # csv, xlsx, pdf
        sa.Column("task_filter", sa.String(20), nullable=False),  # all, created, assigned, received
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("download_count", sa.Integer(), server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_export_report_id", "export_reports", ["report_id"])
    op.create_index("idx_export_user", "export_reports", ["user_id"])
    op.create_index("idx_export_expires", "export_reports", ["expires_at"])


def downgrade() -> None:
    op.drop_index("idx_export_expires", table_name="export_reports")
    op.drop_index("idx_export_user", table_name="export_reports")
    op.drop_index("idx_export_report_id", table_name="export_reports")
    op.drop_table("export_reports")
