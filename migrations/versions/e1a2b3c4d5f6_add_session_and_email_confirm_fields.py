"""add session version and email confirmation fields

Revision ID: e1a2b3c4d5f6
Revises: b7e1a2f4c0d9
Create Date: 2026-08-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e1a2b3c4d5f6'
down_revision = 'b7e1a2f4c0d9'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('session_version', sa.Integer(), nullable=False, server_default='1')
        )
        batch_op.add_column(sa.Column('pending_email', sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column('email_confirm_token_hash', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('email_confirm_expires_at', sa.DateTime(), nullable=True))
        batch_op.create_index('ix_users_email_confirm_token_hash', ['email_confirm_token_hash'])


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index('ix_users_email_confirm_token_hash')
        batch_op.drop_column('email_confirm_expires_at')
        batch_op.drop_column('email_confirm_token_hash')
        batch_op.drop_column('pending_email')
        batch_op.drop_column('session_version')
