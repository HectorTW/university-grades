"""student_profile: current_workplace, current_job_title

Revision ID: g7h8i9j0k1l2
Revises: f1a2b3c4d5e6
Create Date: 2026-04-05

"""
from alembic import op
import sqlalchemy as sa


revision = 'g7h8i9j0k1l2'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('student_profile', schema=None) as batch_op:
        batch_op.add_column(sa.Column('current_workplace', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('current_job_title', sa.String(length=150), nullable=True))


def downgrade():
    with op.batch_alter_table('student_profile', schema=None) as batch_op:
        batch_op.drop_column('current_job_title')
        batch_op.drop_column('current_workplace')
