"""drop interview rating columns

Revision ID: f1b2c3d4e5a6
Revises: f0a1b2c3d4e5
Create Date: 2026-09-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = 'f1b2c3d4e5a6'
down_revision = 'f0a1b2c3d4e5'
branch_labels = None
depends_on = None


def upgrade():
    # The interview workflow no longer uses star ratings — decisions are
    # pass / fail / waitlist only.
    op.drop_column('interview_bookings', 'rating')
    op.drop_column('applications', 'interview_rating')


def downgrade():
    op.add_column('applications', sa.Column('interview_rating', sa.Integer(), nullable=True))
    op.add_column('interview_bookings', sa.Column('rating', sa.Integer(), nullable=True))