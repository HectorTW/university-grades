"""student profile: ready_for_business_trips

Revision ID: a1b2c3d4e5f6
Revises: 5f8479ef9e61
Create Date: 2026-03-26

"""
from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3d4e5f6'
down_revision = '5f8479ef9e61'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('student_profile', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'ready_for_business_trips',
                sa.Boolean(),
                nullable=False,
                server_default=sa.text('0'),
            )
        )


def downgrade():
    with op.batch_alter_table('student_profile', schema=None) as batch_op:
        batch_op.drop_column('ready_for_business_trips')
