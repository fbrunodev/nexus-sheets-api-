"""add_name_to_users

Revision ID: 34f21cc032c4
Revises: 1260f1a89632
Create Date: 2026-06-21 02:49:50.125916

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '34f21cc032c4'
down_revision: Union[str, Sequence[str], None] = '1260f1a89632'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('name', sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'name')
