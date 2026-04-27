"""student_profile: multi desired directions/specializations

Revision ID: h1i2j3k4l5m6
Revises: g7h8i9j0k1l2
Create Date: 2026-04-27

"""
from alembic import op
import sqlalchemy as sa


revision = 'h1i2j3k4l5m6'
down_revision = 'g7h8i9j0k1l2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'student_profile_desired_directions',
        sa.Column('student_profile_id', sa.Integer(), nullable=False),
        sa.Column('study_direction_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ['student_profile_id'],
            ['student_profile.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['study_direction_id'],
            ['study_direction.id'],
            ondelete='CASCADE',
        ),
        sa.UniqueConstraint(
            'student_profile_id',
            'study_direction_id',
            name='uq_student_profile_desired_direction',
        ),
    )
    op.create_index(
        'ix_student_profile_desired_directions_student_profile_id',
        'student_profile_desired_directions',
        ['student_profile_id'],
    )
    op.create_index(
        'ix_student_profile_desired_directions_study_direction_id',
        'student_profile_desired_directions',
        ['study_direction_id'],
    )

    op.create_table(
        'student_profile_desired_specializations',
        sa.Column('student_profile_id', sa.Integer(), nullable=False),
        sa.Column('specialization_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ['student_profile_id'],
            ['student_profile.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['specialization_id'],
            ['specialization.id'],
            ondelete='CASCADE',
        ),
        sa.UniqueConstraint(
            'student_profile_id',
            'specialization_id',
            name='uq_student_profile_desired_specialization',
        ),
    )
    op.create_index(
        'ix_student_profile_desired_specializations_student_profile_id',
        'student_profile_desired_specializations',
        ['student_profile_id'],
    )
    op.create_index(
        'ix_student_profile_desired_specializations_specialization_id',
        'student_profile_desired_specializations',
        ['specialization_id'],
    )


def downgrade():
    op.drop_index('ix_student_profile_desired_specializations_specialization_id', table_name='student_profile_desired_specializations')
    op.drop_index('ix_student_profile_desired_specializations_student_profile_id', table_name='student_profile_desired_specializations')
    op.drop_table('student_profile_desired_specializations')

    op.drop_index('ix_student_profile_desired_directions_study_direction_id', table_name='student_profile_desired_directions')
    op.drop_index('ix_student_profile_desired_directions_student_profile_id', table_name='student_profile_desired_directions')
    op.drop_table('student_profile_desired_directions')

