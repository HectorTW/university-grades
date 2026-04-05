"""email verification and login OTP tables

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-04-05

"""
from alembic import op
import sqlalchemy as sa


revision = 'c3d4e5f6a7b8'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'pending_registration',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=36), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('username', sa.String(length=80), nullable=False),
        sa.Column('password_hash', sa.String(length=120), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('code_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('token'),
    )
    op.create_index(op.f('ix_pending_registration_email'), 'pending_registration', ['email'], unique=False)
    op.create_index(op.f('ix_pending_registration_token'), 'pending_registration', ['token'], unique=False)

    op.create_table(
        'email_login_code',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('code_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_email_login_code_user_id'), 'email_login_code', ['user_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_email_login_code_user_id'), table_name='email_login_code')
    op.drop_table('email_login_code')
    op.drop_index(op.f('ix_pending_registration_token'), table_name='pending_registration')
    op.drop_index(op.f('ix_pending_registration_email'), table_name='pending_registration')
    op.drop_table('pending_registration')
