"""Tests for security hardening: rate limits, open redirects, hashed tokens."""
from datetime import datetime, timezone
from app import db
from app.models.user import User, find_user_by_reset_token


def _login(client, user_id):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True


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
    _login(client, student_id)
    resp = client.post("/api/interview/book", json={"slot_id": slot_id})
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True
