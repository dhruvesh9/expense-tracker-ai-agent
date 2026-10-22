"""add covering indexes for reports

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-19

With millions of expenses, every report scanned the whole table (1-2 s each). These
covering indexes let the database answer from the index alone.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_expenses_report_core", "expenses", ["currency", "expense_date", "amount_minor", "user_id"])
    op.create_index("ix_expenses_report_category", "expenses", ["currency", "expense_date", "category", "amount_minor"])
    op.create_index(
        "ix_expenses_report_merchant", "expenses",
        ["currency", "expense_date", "merchant", "payment_method", "amount_minor"],
    )


def downgrade() -> None:
    op.drop_index("ix_expenses_report_merchant", table_name="expenses")
    op.drop_index("ix_expenses_report_category", table_name="expenses")
    op.drop_index("ix_expenses_report_core", table_name="expenses")
