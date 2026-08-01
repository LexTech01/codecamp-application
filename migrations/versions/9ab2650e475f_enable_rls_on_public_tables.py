"""enable rls on public tables

Revision ID: 9ab2650e475f
Revises: d33b37f095ad
Create Date: 2026-08-01 13:31:36.530501

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9ab2650e475f'
down_revision = 'd33b37f095ad'
branch_labels = None
depends_on = None


def _public_tables():
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT tablename FROM pg_tables "
            "WHERE schemaname = 'public' "
            "ORDER BY tablename"
        )
    )
    return [row[0] for row in rows]


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for table in _public_tables():
        bind.execute(sa.text(f'ALTER TABLE "public"."{table}" ENABLE ROW LEVEL SECURITY'))


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for table in _public_tables():
        bind.execute(sa.text(f'ALTER TABLE "public"."{table}" DISABLE ROW LEVEL SECURITY'))
