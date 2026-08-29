"""rename plan_expiration to plan_expires_at

Revision ID: 40eaec4a804d
Revises: 5f12877b8946
Create Date: 2026-08-29 01:46:18.196016

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '40eaec4a804d'
down_revision: Union[str, Sequence[str], None] = '5f12877b8946'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('users', 'plan_expiration', new_column_name='plan_expires_at')
    pass


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('users', 'plan_expires_at', new_column_name='plan_expiration')
    pass
