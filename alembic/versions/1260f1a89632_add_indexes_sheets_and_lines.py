"""add_indexes_sheets_and_lines

Revision ID: 1260f1a89632
Revises: d03831f8b7e8
Create Date: 2026-06-21 02:07:21.008602

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1260f1a89632'
down_revision: Union[str, Sequence[str], None] = 'd03831f8b7e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index("ix_sheets_owner_id", "sheets", ["owner_id"])
    op.create_index("ix_sheets_owner_deleted", "sheets", ["owner_id", "is_deleted"])
    op.create_index("ix_sheet_lines_sheet_id", "sheet_lines", ["sheet_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_sheets_owner_id", "sheets")
    op.drop_index("ix_sheets_owner_deleted", "sheets")
    op.drop_index("ix_sheet_lines_sheet_id", "sheet_lines")
