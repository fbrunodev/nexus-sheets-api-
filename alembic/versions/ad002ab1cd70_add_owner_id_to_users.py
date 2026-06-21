"""add_owner_id_to_users

Revision ID: ad002ab1cd70
Revises: 34f21cc032c4
Create Date: 2026-06-21 02:51:30.151881

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ad002ab1cd70'
down_revision: Union[str, Sequence[str], None] = '34f21cc032c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('owner_id', sa.String(), nullable=True))
    op.create_foreign_key('fk_users_owner_id', 'users', 'users', ['owner_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_users_owner_id', 'users', type_='foreignkey')
    op.drop_column('users', 'owner_id')
