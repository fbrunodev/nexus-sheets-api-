"""add_cooperation_type_to_sheets

Revision ID: 5f12877b8946
Revises: dada5ee85603
Create Date: 2026-07-01 20:02:20.849526

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5f12877b8946'
down_revision: Union[str, Sequence[str], None] = 'dada5ee85603'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE TYPE cooperationtype AS ENUM ('META', 'BAU', 'RECARGA')")
    op.add_column('sheets', sa.Column(
        'cooperation_type',
        sa.Enum('META', 'BAU', 'RECARGA', name='cooperationtype', create_type=False),
        server_default='META',
        nullable=False,
    ))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('sheets', 'cooperation_type')
    op.execute("DROP TYPE cooperationtype")
