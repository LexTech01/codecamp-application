"""Tests for security hardening: rate limits, open redirects, hashed tokens."""
import pytest
from datetime import datetime, timezone
from app import create_app, db, seed_database
from app.models.user import User, find_user_by_reset_token
from app.models.assessment import Assessment


def _login(client, app, user_id):
    with app.app_context():
        email = User.query.get(user_id).email
    resp = client.post("/auth/login", data={
        "email": email, "password": "password123",
    })
    assert resp.status_code == 302


def _make_user(app, email, role="student"):
    with app.app_context():
        u = User(email=email, first_name="T", last_name="U", role=role)
        u.set_password("password123")
        db.session.add(u)
        db.session.commit()
        return u.id


def test_login_redirects_safely_on_external_next(client, app):
    uid = _make_user(app, "redirect@test.com")
    resp = client.post("/auth/login", data={
        "email": "redirect@test.com",
        "password": "password123",
    })
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/student/dashboard")

    resp = client.post("/auth/login?next=https://evil.com", data={
        "email": "redirect@test.com",
        "password": "password123",
    })
    assert resp.status_code == 302
    location = resp.headers["Location"]
    assert location.startswith("/student/dashboard")


def test_login_allows_local_next(client, app):
    _make_user(app, "local@test.com")
    resp = client.post("/auth/login?next=/student/announcements", data={
        "email": "local@test.com",
        "password": "password123",
    })
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/student/announcements")


def test_login_rate_limited(client, app):
    _make_user(app, "rate@test.com")
    statuses = []
    for _ in range(7):
        resp = client.post("/auth/login", data={
            "email": "rate@test.com",
            "password": "wrong-password",
        })
        statuses.append(resp.status_code)
    assert 429 in statuses


def test_reset_token_stored_hashed(client, app):
    with app.app_context():
        uid = _make_user(app, "token@test.com")
        user = User.query.get(uid)
        raw = user.generate_reset_token()
        db.session.commit()
        stored = User.query.get(uid).reset_token_hash
        assert raw != stored
        assert stored is not None and len(stored) == 64
        assert find_user_by_reset_token(raw).id == uid

        # An expired token lookup returns the user but reset_token_valid is False
        user.reset_token_expires_at = datetime(2000, 1, 1, tzinfo=timezone.utc)
        db.session.commit()
        found = find_user_by_reset_token(raw)
        assert found is not None
        assert found.reset_token_valid is False


def test_booking_api_emails_under_testing(client, app):
    from app.models.application import Application
    from app.models.interview import InterviewSlot
    from datetime import date, timedelta
    with app.app_context():
        admin_id = _make_user(app, "admin-mail@test.com", role="admin")
        student_id = _make_user(app, "stu-mail@test.com")
        slot = InterviewSlot(
            interviewer_id=admin_id,
            slot_date=date.today() + timedelta(days=4),
            start_time=__import__("datetime").time(10, 0),
            end_time=__import__("datetime").time(10, 30),
        )
        db.session.add_all([slot, Application(user_id=student_id, pipeline_stage="test_completed", is_submitted=True)])
        db.session.commit()
        slot_id = slot.id
    with app.app_context():
        from app.models.assessment import Assessment, TestAttempt
        assessment = Assessment(title="Mail Test", pass_score=70.0)
        db.session.add(assessment)
        db.session.flush()
        db.session.add(TestAttempt(
            user_id=student_id, assessment_id=assessment.id, passed=True,
            score=80.0, completed_at=datetime.now(timezone.utc),
        ))
        db.session.commit()
    _login(client, app, student_id)
    resp = client.post("/api/interview/book", json={"slot_id": slot_id})
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True


def test_debug_rejected_against_postgres():
    """Werkzeug debugger (RCE) must never run against a production DB."""
    with pytest.raises(RuntimeError):
        create_app(config_override={
            "DEBUG": True,
            "TESTING": False,
            "SECRET_KEY": "strong-secret",
            "SQLALCHEMY_DATABASE_URI": "postgresql://u:p@localhost/mydb",
            "RATELIMIT_STORAGE_URL": "redis://localhost:6379/0",
        })


def test_missing_secret_key_rejected_in_prod():
    with pytest.raises(RuntimeError):
        create_app(config_override={
            "TESTING": False,
            "SECRET_KEY": "",
            "SQLALCHEMY_DATABASE_URI": "postgresql://u:p@localhost/mydb",
            "RATELIMIT_STORAGE_URL": "redis://localhost:6379/0",
        })


def test_ratelimit_requires_shared_backend_in_prod():
    with pytest.raises(RuntimeError):
        create_app(config_override={
            "TESTING": False,
            "SECRET_KEY": "strong-secret",
            "SQLALCHEMY_DATABASE_URI": "postgresql://u:p@localhost/mydb",
            "RATELIMIT_STORAGE_URL": "memory://",
        })


def test_seed_demo_skipped_in_production(client, app, monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "production")
    with app.app_context():
        seed_database(force=True)
        # Demo accounts must NOT exist in production.
        assert User.query.filter_by(email="admin@cellusys.com").first() is None
        assert User.query.filter_by(email="student@cellusys.com").first() is None
        # Core content is still seeded.
        assert Assessment.query.first() is not None


def test_reset_password_invalidates_session(client, app):
    uid = _make_user(app, "reset-sess@test.com")
    # Log in through the real route so the session version is recorded.
    resp = client.post("/auth/login", data={
        "email": "reset-sess@test.com", "password": "password123",
    })
    assert resp.status_code == 302

    # Trigger a password reset.
    with app.app_context():
        user = User.query.get(uid)
        token = user.generate_reset_token()
        db.session.commit()
    resp = client.post(f"/auth/reset-password/{token}", data={
        "password": "newpass123", "confirm_password": "newpass123",
    })
    assert resp.status_code == 302

    # The previous session must now be rejected (token version bumped).
    resp = client.get("/student/dashboard")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_profile_requires_current_password(client, app):
    uid = _make_user(app, "profile-reauth@test.com")
    _login(client, app, uid)
    resp = client.post("/student/profile", data={
        "first_name": "Changed", "last_name": "User",
        "email": "profile-reauth@test.com",
        "phone": "+233 24 000 0000", "current_password": "wrong",
    })
    assert resp.status_code == 302
    with app.app_context():
        assert User.query.get(uid).first_name == "T"  # unchanged


def test_profile_email_change_requires_confirmation(client, app):
    uid = _make_user(app, "profile-email@test.com")
    _login(client, app, uid)
    resp = client.post("/student/profile", data={
        "first_name": "Te", "last_name": "User",
        "email": "newaddr@example.com",
        "phone": "+233 24 000 0000", "current_password": "password123",
    })
    assert resp.status_code == 302
    with app.app_context():
        user = User.query.get(uid)
        assert user.email == "profile-email@test.com"  # not applied yet
        assert user.pending_email == "newaddr@example.com"
        assert user.email_confirm_token_hash is not None

    # Confirm via the token link (generate a fresh raw token for the test).
    with app.app_context():
        user = User.query.get(uid)
        raw = user.generate_email_confirm_token()
        db.session.commit()
    resp = client.get(f"/student/confirm-email/{raw}")
    assert resp.status_code == 302
    with app.app_context():
        user = User.query.get(uid)
        assert user.email == "newaddr@example.com"
        assert user.pending_email is None
        assert user.email_confirm_token_hash is None


def test_confirm_email_rejects_bad_token(client, app):
    uid = _make_user(app, "confirm-bad@test.com")
    _login(client, app, uid)
    resp = client.get("/student/confirm-email/not-a-real-token")
    assert resp.status_code == 302
    with app.app_context():
        assert User.query.get(uid).email == "confirm-bad@test.com"
