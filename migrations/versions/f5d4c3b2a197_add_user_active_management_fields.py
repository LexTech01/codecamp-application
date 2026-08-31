"""add user active management fields for admin/staff management

Revision ID: f5d4c3b2a197
Revises: e1a2b3c4d5f6
Create Date: 2026-08-29 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f5d4c3b2a197'
down_revision = 'e1a2b3c4d5f6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1')
        )
        batch_op.add_column(sa.Column('deactivated_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('deactivated_reason', sa.String(length=255), nullable=True))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('deactivated_reason')
        batch_op.drop_column('deactivated_at')
        batch_op.drop_column('is_active')
