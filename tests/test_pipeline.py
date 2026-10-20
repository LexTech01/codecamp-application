"""Unit tests for PipelineMachine."""
import pytest


def test_can_advance_valid(pipeline):
    assert pipeline.can_advance("submitted", "under_review")
    assert pipeline.can_advance("under_review", "test_invited")
    assert pipeline.can_advance("test_invited", "test_completed")
    assert pipeline.can_advance("test_completed", "interview_scheduled")
    assert pipeline.can_advance("test_completed", "accepted")
    assert pipeline.can_advance("interview_scheduled", "interview_completed")
    assert pipeline.can_advance("interview_scheduled", "accepted")
    assert pipeline.can_advance("interview_scheduled", "accepted")
    assert not pipeline.can_advance("interview_scheduled", "waitlisted")
    assert pipeline.can_advance("interview_completed", "accepted")
    assert pipeline.can_advance("accepted", "onboarding")
    assert pipeline.can_advance("onboarding", "enrolled")
    assert pipeline.can_advance("rejected", "test_invited")


def test_can_advance_invalid(pipeline):
    assert not pipeline.can_advance("submitted", "accepted")
    assert not pipeline.can_advance("draft", "accepted")
    assert not pipeline.can_advance("test_completed", "submitted")
    assert not pipeline.can_advance("accepted", "rejected")
    assert not pipeline.can_advance("rejected", "accepted")
    assert not pipeline.can_advance("rejected", "onboarding")


def test_available_actions(pipeline):
    assert "test_invited" in pipeline.available_actions("under_review")
    assert "rejected" in pipeline.available_actions("under_review")
    assert "waitlisted" in pipeline.available_actions("under_review")
    assert "accepted" in pipeline.available_actions("interview_completed")
    assert "accepted" in pipeline.available_actions("interview_scheduled")
    assert "waitlisted" not in pipeline.available_actions("interview_scheduled")
    assert "test_invited" in pipeline.available_actions("rejected")
    assert [] == pipeline.available_actions("enrolled")


def test_status_label(pipeline):
    assert pipeline.status_label("submitted") == "Submitted"
    assert pipeline.status_label("under_review") == "Under Review"
    assert pipeline.status_label("interview_scheduled") == "Interview Scheduled"
    assert pipeline.status_label("accepted") == "Accepted"
    assert pipeline.status_label("rejected") == "Rejected"
    assert pipeline.status_label("waitlisted") == "Waitlisted"
    assert pipeline.status_label("onboarding") == "Onboarding"
    assert pipeline.status_label("enrolled") == "Enrolled"


def test_progress_percent(pipeline):
    assert pipeline.progress_percent("submitted") > 0
    assert pipeline.progress_percent("accepted") == 100
    assert pipeline.progress_percent("rejected") == 100
    assert pipeline.progress_percent("waitlisted") == 100
    assert pipeline.progress_percent("non_existent") == 0


def test_check_access_allows_current(pipeline):
    assert pipeline.check_access("test_completed", ["test_completed"])


def test_check_access_allows_past(pipeline):
    assert pipeline.check_access("interview_completed", ["interview_scheduled"])


def test_check_access_blocks_future(pipeline):
    assert not pipeline.check_access("submitted", ["interview_completed"])


def test_notify_content(pipeline):
    title, msg = pipeline.notify_content("test_completed", "accepted")
    assert "Passed" in title
    assert "passed" in msg.lower()

    title, msg = pipeline.notify_content("under_review", "rejected")
    assert "Rejected" in title

    title, msg = pipeline.notify_content("interview_completed", "waitlisted")
    assert "Waitlisted" in title

    title, msg = pipeline.notify_content("submitted", "under_review")
    assert "Update" in title


def test_all_transitions_defined(pipeline):
    for stage in pipeline.STAGES:
        assert stage in pipeline.TRANSITIONS


def test_notify_content_all_stages(pipeline):
    for from_stage, targets in pipeline.TRANSITIONS.items():
        for to_stage in targets:
            title, msg = pipeline.notify_content(from_stage, to_stage)
            assert title
            assert msg
