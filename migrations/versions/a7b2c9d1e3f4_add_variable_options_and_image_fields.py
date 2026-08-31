"""add variable options and image fields to questions

Revision ID: a7b2c9d1e3f4
Revises: f5d4c3b2a197
Create Date: 2026-08-29 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a7b2c9d1e3f4'
down_revision = 'f5d4c3b2a197'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('questions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('options', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('option_images', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('question_image', sa.String(length=300), nullable=True))
        batch_op.alter_column('option_a', existing_type=sa.String(length=500), nullable=True)
        batch_op.alter_column('option_b', existing_type=sa.String(length=500), nullable=True)
        batch_op.alter_column('option_c', existing_type=sa.String(length=500), nullable=True)
        batch_op.alter_column('option_d', existing_type=sa.String(length=500), nullable=True)
        batch_op.alter_column('correct_answer', existing_type=sa.Integer(), nullable=True)


def downgrade():
    with op.batch_alter_table('questions', schema=None) as batch_op:
        batch_op.alter_column('correct_answer', existing_type=sa.Integer(), nullable=False)
        batch_op.alter_column('option_d', existing_type=sa.String(length=500), nullable=False)
        batch_op.alter_column('option_c', existing_type=sa.String(length=500), nullable=False)
        batch_op.alter_column('option_b', existing_type=sa.String(length=500), nullable=False)
        batch_op.alter_column('option_a', existing_type=sa.String(length=500), nullable=False)
        batch_op.drop_column('question_image')
        batch_op.drop_column('option_images')
        batch_op.drop_column('options')
