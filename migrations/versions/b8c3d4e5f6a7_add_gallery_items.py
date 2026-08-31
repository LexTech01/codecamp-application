"""add gallery items table

Revision ID: b8c3d4e5f6a7
Revises: a7b2c9d1e3f4
Create Date: 2026-08-31 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b8c3d4e5f6a7'
down_revision = 'a7b2c9d1e3f4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'gallery_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('alt', sa.String(length=200), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('gallery_items')
