"""add application form fields

Revision ID: a1b2c3d4e5f6
Revises: b8c3d4e5f6a7
Create Date: 2026-09-12 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'b8c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('applications', schema=None) as batch_op:
        batch_op.add_column(sa.Column('referral_source', sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column('previous_student', sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column('previous_course', sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column('previous_cohort', sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column('current_status', sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column('profession', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('can_commit', sa.Boolean(), nullable=True))


def downgrade():
    with op.batch_alter_table('applications', schema=None) as batch_op:
        batch_op.drop_column('can_commit')
        batch_op.drop_column('profession')
        batch_op.drop_column('current_status')
        batch_op.drop_column('previous_cohort')
        batch_op.drop_column('previous_course')
        batch_op.drop_column('previous_student')
        batch_op.drop_column('referral_source')
