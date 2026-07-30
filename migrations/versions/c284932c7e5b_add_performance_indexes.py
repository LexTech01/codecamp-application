"""add performance indexes

Revision ID: c284932c7e5b
Revises: c99fcbaa0494
Create Date: 2026-07-30 10:36:31.510686

"""
from alembic import op
import sqlalchemy as sa


revision = 'c284932c7e5b'
down_revision = 'c99fcbaa0494'
branch_labels = None
depends_on = None


def upgrade():
    # Foreign-key indexes for JOIN performance
    op.create_index(op.f('ix_applications_user_id'), 'applications', ['user_id'], unique=True)
    op.create_index(op.f('ix_questions_assessment_id'), 'questions', ['assessment_id'])
    op.create_index(op.f('ix_test_attempts_user_id'), 'test_attempts', ['user_id'])
    op.create_index(op.f('ix_test_attempts_assessment_id'), 'test_attempts', ['assessment_id'])
    op.create_index(op.f('ix_interviewer_profiles_user_id'), 'interviewer_profiles', ['user_id'], unique=True)
    op.create_index(op.f('ix_interview_slots_interviewer_id'), 'interview_slots', ['interviewer_id'])
    op.create_index(op.f('ix_interview_bookings_user_id'), 'interview_bookings', ['user_id'])
    op.create_index(op.f('ix_interview_bookings_slot_id'), 'interview_bookings', ['slot_id'], unique=True)
    op.create_index(op.f('ix_activity_logs_user_id'), 'activity_logs', ['user_id'])
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'])
    op.create_index(op.f('ix_announcements_author_id'), 'announcements', ['author_id'])
    op.create_index(op.f('ix_announcement_reads_user_id'), 'announcement_reads', ['user_id'])
    op.create_index(op.f('ix_announcement_reads_announcement_id'), 'announcement_reads', ['announcement_id'])

    # Filter/query performance indexes
    op.create_index(op.f('ix_applications_pipeline_stage'), 'applications', ['pipeline_stage'])
    op.create_index(op.f('ix_applications_is_submitted'), 'applications', ['is_submitted'])
    op.create_index(op.f('ix_notifications_is_read'), 'notifications', ['is_read'])
    op.create_index(op.f('ix_interview_slots_slot_date'), 'interview_slots', ['slot_date'])
    op.create_index(op.f('ix_interview_slots_is_available'), 'interview_slots', ['is_available'])
    op.create_index(op.f('ix_interview_bookings_status'), 'interview_bookings', ['status'])
    op.create_index(op.f('ix_test_attempts_completed_at'), 'test_attempts', ['completed_at'])


def downgrade():
    op.drop_index(op.f('ix_test_attempts_completed_at'), table_name='test_attempts')
    op.drop_index(op.f('ix_interview_bookings_status'), table_name='interview_bookings')
    op.drop_index(op.f('ix_interview_slots_is_available'), table_name='interview_slots')
    op.drop_index(op.f('ix_interview_slots_slot_date'), table_name='interview_slots')
    op.drop_index(op.f('ix_notifications_is_read'), table_name='notifications')
    op.drop_index(op.f('ix_applications_is_submitted'), table_name='applications')
    op.drop_index(op.f('ix_applications_pipeline_stage'), table_name='applications')
    op.drop_index(op.f('ix_announcement_reads_announcement_id'), table_name='announcement_reads')
    op.drop_index(op.f('ix_announcement_reads_user_id'), table_name='announcement_reads')
    op.drop_index(op.f('ix_announcements_author_id'), table_name='announcements')
    op.drop_index(op.f('ix_notifications_user_id'), table_name='notifications')
    op.drop_index(op.f('ix_activity_logs_user_id'), table_name='activity_logs')
    op.drop_index(op.f('ix_interview_bookings_slot_id'), table_name='interview_bookings')
    op.drop_index(op.f('ix_interview_bookings_user_id'), table_name='interview_bookings')
    op.drop_index(op.f('ix_interview_slots_interviewer_id'), table_name='interview_slots')
    op.drop_index(op.f('ix_interviewer_profiles_user_id'), table_name='interviewer_profiles')
    op.drop_index(op.f('ix_test_attempts_assessment_id'), table_name='test_attempts')
    op.drop_index(op.f('ix_test_attempts_user_id'), table_name='test_attempts')
    op.drop_index(op.f('ix_questions_assessment_id'), table_name='questions')
    op.drop_index(op.f('ix_applications_user_id'), table_name='applications')
