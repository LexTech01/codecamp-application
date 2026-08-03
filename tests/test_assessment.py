"""Regression tests for assessment submission and retake flow."""
from datetime import datetime, timezone
from app import db
from app.models.user import User
from app.models.application import Application
from app.models.assessment import Assessment, Question, TestAttempt


def _make_student(app):
    with app.app_context():
        student = User(email="asub@test.com", first_name="A", last_name="B",
                       role="student")
        student.set_password("p")
        db.session.add(student)
        db.session.flush()
        db.session.add(Application(
            user_id=student.id, pipeline_stage="test_invited",
            status="test_invited", is_submitted=True,
        ))
        db.session.commit()
        return student.id


def _make_assessment(app):
    with app.app_context():
        a = Assessment(title="Test", duration_minutes=20, pass_score=50.0,
                       is_active=True)
        db.session.add(a)
        db.session.flush()
        q = Question(assessment_id=a.id, order_num=1, points=10,
                     question_text="Q1?", option_a="A", option_b="B",
                     option_c="C", option_d="D", correct_answer=0)
        db.session.add(q)
        db.session.commit()
        return a.id


def _login(client, user_id):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True


def _submit(client, user_id, assessment_id, answers, time_taken=60):
    return client.post(f"/api/assessment/{assessment_id}/submit",
                       json={"answers": answers, "time_taken": time_taken})


def _complete_attempt(app, user_id, assessment_id, passed, score):
    with app.app_context():
        t = TestAttempt(
            user_id=user_id, assessment_id=assessment_id, score=score,
            earned_points=10 if passed else 0, total_points=10,
            passed=passed, answers="{}", time_taken_seconds=60,
            completed_at=datetime.now(timezone.utc),
        )
        db.session.add(t)
        db.session.commit()
        return t.id


def test_submit_after_failed_attempt_is_allowed(client, app):
    uid = _make_student(app)
    aid = _make_assessment(app)
    _complete_attempt(app, uid, aid, passed=False, score=10.0)
    _login(client, uid)

    resp = _submit(client, uid, aid, {"1": 0})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["passed"] is True
    assert body["score"] == 100.0


def test_submit_after_passed_attempt_is_rejected(client, app):
    uid = _make_student(app)
    aid = _make_assessment(app)
    _complete_attempt(app, uid, aid, passed=True, score=100.0)
    _login(client, uid)

    resp = _submit(client, uid, aid, {"1": 0})
    assert resp.status_code == 400
    assert "already submitted" in resp.get_json()["error"]


def test_first_submit_creates_and_completes_attempt(client, app):
    uid = _make_student(app)
    aid = _make_assessment(app)
    _login(client, uid)

    resp = _submit(client, uid, aid, {"1": 0})
    assert resp.status_code == 200

    with app.app_context():
        attempts = TestAttempt.query.filter_by(user_id=uid, assessment_id=aid).all()
        assert len(attempts) == 1
        assert attempts[0].completed_at is not None
        assert attempts[0].passed is True
