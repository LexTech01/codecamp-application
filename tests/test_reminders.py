"""Tests for scheduled email reminders (Celery sweep task)."""
from datetime import datetime, timedelta, timezone

from app import db
from app.models.application import Application
from app.models.interview import InterviewSlot, InterviewBooking
from app.models.outbound_message import OutboundMessage
from app.models.user import User
from app.tasks.reminders import run_due_reminders


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _make_user(app, email, role="student", active=True):
    user = User(email=email, first_name="Test", last_name="User", role=role,
                is_active=active)
    user.set_password("password123")
    db.session.add(user)
    db.session.commit()
    return user.id


def _make_booking(admin_id, student_id, when, status="scheduled"):
    slot = InterviewSlot(
        interviewer_id=admin_id,
        slot_date=when.date(),
        start_time=when.time(),
        end_time=(when + timedelta(minutes=30)).time(),
    )
    db.session.add(slot)
    db.session.flush()
    booking = InterviewBooking(user_id=student_id, slot_id=slot.id, status=status)
    db.session.add(booking)
    db.session.commit()
    return booking.id


def _messages(kind=None):
    query = OutboundMessage.query
    if kind:
        query = query.filter_by(kind=kind)
    return query.all()


def test_interview_24h_reminder_sent_once(app):
    with app.app_context():
        admin_id = _make_user(app, "admin@rem.com", role="admin")
        student_id = _make_user(app, "stu24@rem.com")
        _make_booking(admin_id, student_id, _now() + timedelta(hours=25))

        report = run_due_reminders.run()
        assert report["interview_reminder_24h"] == 1
        msgs = _messages("interview_reminder_24h")
        assert len(msgs) == 1
        assert msgs[0].status == "sent"
        assert msgs[0].recipient == "stu24@rem.com"
        assert "Interview Reminder" in msgs[0].subject

        # Idempotent: a second sweep sends nothing new.
        second = run_due_reminders.run()
        assert second["interview_reminder_24h"] == 0
        assert len(_messages("interview_reminder_24h")) == 1


def test_interview_2h_reminder_sent(app):
    with app.app_context():
        admin_id = _make_user(app, "admin2@rem.com", role="admin")
        student_id = _make_user(app, "stu2h@rem.com")
        _make_booking(admin_id, student_id, _now() + timedelta(hours=2))

        report = run_due_reminders.run()
        assert report["interview_reminder_2h"] == 1
        assert len(_messages("interview_reminder_2h")) == 1


def test_no_reminder_for_cancelled_booking(app):
    with app.app_context():
        admin_id = _make_user(app, "admin3@rem.com", role="admin")
        student_id = _make_user(app, "stucancel@rem.com")
        _make_booking(admin_id, student_id, _now() + timedelta(hours=25), status="cancelled")

        report = run_due_reminders.run()
        assert report["interview_reminder_24h"] == 0
        assert _messages() == []


def test_draft_nudge_after_threshold(app):
    with app.app_context():
        student_id = _make_user(app, "draft@rem.com")
        db.session.add(Application(
            user_id=student_id, is_submitted=False,
            created_at=_now() - timedelta(days=4),
        ))
        db.session.commit()

        report = run_due_reminders.run()
        assert report["draft_nudge"] == 1
        msgs = _messages("draft_nudge")
        assert msgs[0].status == "sent"
        assert msgs[0].recipient == "draft@rem.com"

        assert run_due_reminders.run()["draft_nudge"] == 0
        assert len(_messages("draft_nudge")) == 1


def test_no_draft_nudge_before_threshold(app):
    with app.app_context():
        student_id = _make_user(app, "draftnew@rem.com")
        db.session.add(Application(
            user_id=student_id, is_submitted=False,
            created_at=_now() - timedelta(days=1),
        ))
        db.session.commit()
        assert run_due_reminders.run()["draft_nudge"] == 0
        assert _messages("draft_nudge") == []


def test_test_reminder_when_not_attempted(app):
    with app.app_context():
        student_id = _make_user(app, "test@rem.com")
        db.session.add(Application(
            user_id=student_id, is_submitted=True, pipeline_stage="test_invited",
            submitted_at=_now() - timedelta(days=4), test_attempts=0,
        ))
        db.session.commit()

        report = run_due_reminders.run()
        assert report["test_reminder"] == 1
        assert _messages("test_reminder")[0].status == "sent"


def test_no_test_reminder_when_attempted(app):
    with app.app_context():
        student_id = _make_user(app, "testdone@rem.com")
        db.session.add(Application(
            user_id=student_id, is_submitted=True, pipeline_stage="test_invited",
            submitted_at=_now() - timedelta(days=4), test_attempts=1,
        ))
        db.session.commit()
        assert run_due_reminders.run()["test_reminder"] == 0
        assert _messages("test_reminder") == []


def test_inactive_user_gets_no_reminder(app):
    with app.app_context():
        admin_id = _make_user(app, "admin4@rem.com", role="admin")
        student_id = _make_user(app, "inactive@rem.com", active=False)
        _make_booking(admin_id, student_id, _now() + timedelta(hours=25))
        assert run_due_reminders.run()["interview_reminder_24h"] == 0
        assert _messages() == []
