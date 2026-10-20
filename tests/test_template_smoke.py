"""Smoke test: every template edited for CSP-safe scripts still renders."""
from app import db
from app.models.user import User
from app.models.application import Application
from app.models.assessment import Assessment, Question, TestAttempt
from app.models.announcement import Announcement
from app.models.gallery import GalleryItem
from datetime import datetime, timezone


def _user(app, role, email, app_stage=None):
    with app.app_context():
        u = User(email=email, first_name="S", last_name="X", role=role)
        u.set_password("p")
        db.session.add(u)
        db.session.flush()
        if app_stage:
            db.session.add(Application(
                user_id=u.id, pipeline_stage=app_stage, status=app_stage,
                is_submitted=True,
            ))
        db.session.commit()
        return u.id


def _login(client, user_id):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True
        sess["_sess_v"] = 1


def _make_assessment(app):
    with app.app_context():
        a = Assessment(title="T", duration_minutes=20, pass_score=50.0, is_active=True)
        db.session.add(a)
        db.session.flush()
        db.session.add(Question(assessment_id=a.id, order_num=1, points=10,
                                question_text="Q?", option_a="A", option_b="B",
                                option_c="C", option_d="D", correct_answer=0))
        db.session.commit()
        return a.id


def test_public_pages_render(client, app):
    with app.app_context():
        db.session.add(Announcement(title="Post", content="hello world"))
        db.session.add(GalleryItem(filename="g.jpg", alt="G", category="events"))
        db.session.flush()
        post_id = Announcement.query.first().id
        db.session.commit()

    for path in ["/", "/gallery", f"/blog/{post_id}", "/auth/login"]:
        resp = client.get(path)
        assert resp.status_code == 200, f"{path} -> {resp.status_code}"


def test_dashboard_take_page_render(client, app):
    uid = _user(app, "student", "smokestudent@test.com", app_stage="test_invited")
    aid = _make_assessment(app)
    _login(client, uid)

    resp = client.get(f"/student/assessment/{aid}/take")
    assert resp.status_code == 200, resp.status_code
    html = resp.get_data(as_text=True)
    assert "questionsData" in html  # not strictly required, sanity check


def test_dashboard_and_admin_pages_render(client, app):
    uid = _user(app, "student", "smokey@test.com", app_stage="test_completed")
    aid = _make_assessment(app)
    _login(client, uid)
    with app.app_context():
        db.session.add(TestAttempt(
            user_id=uid, assessment_id=aid, score=100.0, earned_points=10,
            total_points=10, passed=True, answers="{}", time_taken_seconds=60,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        ))
        db.session.commit()

    for path in ["/student/dashboard", "/student/announcements",
                 "/student/interview"]:
        resp = client.get(path)
        assert resp.status_code == 200, f"{path} -> {resp.status_code}"

    admin_id = _user(app, "admin", "smokedmin@test.com")
    _login(client, admin_id)
    for path in ["/admin/interviews", "/admin/cohorts", "/admin/pipeline",
                 "/admin/dashboard"]:
        resp = client.get(path)
        assert resp.status_code == 200, f"{path} -> {resp.status_code}"