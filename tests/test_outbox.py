"""Tests for app.utils.outbox: audit-log rows and notifications are appended
to the session, never committed by the helpers themselves."""
from app import db
from app.models.activity import ActivityLog
from app.models.notification import Notification
from app.models.user import User
from app.utils import outbox


def _make_user(app):
    user = User(email="u@example.com", first_name="A", last_name="B", role="student")
    user.set_password("pw")
    db.session.add(user)
    db.session.flush()
    return user


def test_log_appends_activity_log(app):
    with app.app_context():
        user = _make_user(app)
        outbox.log(user.id, "login", "User u@example.com logged in")
        entries = ActivityLog.query.filter_by(user_id=user.id).all()
        assert len(entries) == 1
        assert entries[0].action == "login"
        assert entries[0].details == "User u@example.com logged in"


def test_log_does_not_commit(app):
    with app.app_context():
        user = _make_user(app)
        outbox.log(user.id, "logout")
        db.session.rollback()
        assert ActivityLog.query.filter_by(user_id=user.id).count() == 0


def test_notify_appends_notification_and_returns_row(app):
    with app.app_context():
        user = _make_user(app)
        notif = outbox.notify(user.id, "Hi", "Hello", "/dashboard")
        assert isinstance(notif, Notification)
        rows = Notification.query.filter_by(user_id=user.id).all()
        assert len(rows) == 1
        assert rows[0].title == "Hi"
        assert rows[0].message == "Hello"
        assert rows[0].link == "/dashboard"


def test_transition_logs_and_notifies_together(app):
    with app.app_context():
        user = _make_user(app)
        outbox.transition(
            user.id,
            action="application_submitted",
            title="Application Submitted",
            message="You can now take the test.",
            link="/assessment",
        )
        assert ActivityLog.query.filter_by(user_id=user.id, action="application_submitted").count() == 1
        assert Notification.query.filter_by(user_id=user.id, title="Application Submitted").count() == 1


def test_transition_logs_only_when_no_notice(app):
    with app.app_context():
        user = _make_user(app)
        outbox.transition(user.id, action="logout")
        assert ActivityLog.query.filter_by(user_id=user.id, action="logout").count() == 1
        assert Notification.query.filter_by(user_id=user.id).count() == 0