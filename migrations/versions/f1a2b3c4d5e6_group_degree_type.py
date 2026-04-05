"""group: degree_type (bachelor / master)

Revision ID: f1a2b3c4d5e6
Revises: d4e5f6a7b8c9
Create Date: 2026-04-05

"""
from alembic import op
import sqlalchemy as sa


revision = 'f1a2b3c4d5e6'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('group', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'degree_type',
                sa.String(length=20),
                nullable=False,
                server_default='bachelor',
            )
        )


def downgrade():
    with op.batch_alter_table('group', schema=None) as batch_op:
        batch_op.drop_column('degree_type')
