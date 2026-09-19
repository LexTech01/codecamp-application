"""add outbound messages

Revision ID: f0a1b2c3d4e5
Revises: a1b2c3d4e5f6
Create Date: 2026-09-17 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f0a1b2c3d4e5'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'outbound_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('recipient', sa.String(length=255), nullable=False),
        sa.Column('channel', sa.String(length=20), nullable=False, server_default='email'),
        sa.Column('kind', sa.String(length=50), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=True),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('dedupe_key', sa.String(length=120), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('error', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_outbound_messages_kind', 'outbound_messages', ['kind'])
    op.create_index(
        'ix_outbound_messages_dedupe_key', 'outbound_messages', ['dedupe_key'], unique=True
    )

    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        bind.execute(sa.text(
            'ALTER TABLE "public"."outbound_messages" ENABLE ROW LEVEL SECURITY'
        ))


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        bind.execute(sa.text(
            'ALTER TABLE "public"."outbound_messages" DISABLE ROW LEVEL SECURITY'
        ))
    op.drop_index('ix_outbound_messages_dedupe_key', table_name='outbound_messages')
    op.drop_index('ix_outbound_messages_kind', table_name='outbound_messages')
    op.drop_table('outbound_messages')
