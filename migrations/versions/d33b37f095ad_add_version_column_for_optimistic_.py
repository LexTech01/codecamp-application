"""Add version column for optimistic locking

Revision ID: d33b37f095ad
Revises: c284932c7e5b
Create Date: 2026-07-30 10:54:10.124827

"""
from alembic import op
import sqlalchemy as sa


revision = 'd33b37f095ad'
down_revision = 'c284932c7e5b'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('applications', schema=None) as batch_op:
        batch_op.add_column(sa.Column('version', sa.Integer(), nullable=False, server_default='1'))


def downgrade():
    with op.batch_alter_table('applications', schema=None) as batch_op:
        batch_op.drop_column('version')
