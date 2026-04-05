"""employer profile: ogrn, responsible_position

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-05

"""
from alembic import op
import sqlalchemy as sa


revision = 'd4e5f6a7b8c9'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('employer_profile', schema=None) as batch_op:
        batch_op.add_column(sa.Column('ogrn', sa.String(length=15), nullable=True))
        batch_op.add_column(sa.Column('responsible_position', sa.String(length=150), nullable=True))


def downgrade():
    with op.batch_alter_table('employer_profile', schema=None) as batch_op:
        batch_op.drop_column('responsible_position')
        batch_op.drop_column('ogrn')
