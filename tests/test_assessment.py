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
        sess["_sess_v"] = 1


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


def test_submit_blocked_after_max_failed_attempts(client, app):
    """The retry cap must be enforced on the submit endpoint, not only the GET route."""
    from app.models.assessment import MAX_TEST_ATTEMPTS

    uid = _make_student(app)
    aid = _make_assessment(app)
    _login(client, uid)

    for _ in range(MAX_TEST_ATTEMPTS):
        resp = _submit(client, uid, aid, {"1": 1})  # wrong answer -> failed attempt
        assert resp.status_code == 200

    resp = _submit(client, uid, aid, {"1": 0})
    assert resp.status_code == 403


def _make_image_assessment(app):
    """Assessment with a variable-option (8) question and an image-backed 4-option question."""
    with app.app_context():
        a = Assessment(title="Img Test", duration_minutes=20, pass_score=50.0,
                       is_active=True)
        db.session.add(a)
        db.session.flush()
        q1 = Question(assessment_id=a.id, order_num=1, points=10,
                      question_text="Var?", options=["A", "B", "C", "D", "E", "F", "G", "H"],
                      option_images=["/static/q_a.png"] + [None] * 7,
                      correct_answer=None)
        q2 = Question(assessment_id=a.id, order_num=2, points=10,
                      question_text="Img?", options=["X", "Y"],
                      question_image="/static/q_img.png", correct_answer=0)
        db.session.add_all([q1, q2])
        db.session.commit()
        return a.id, q1.id, q2.id


def test_take_page_renders_images_and_variable_options(client, app):
    uid = _make_student(app)
    aid, _, _ = _make_image_assessment(app)
    _login(client, uid)

    resp = client.get(f"/student/assessment/{aid}/take")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Var?" in html
    assert "option_images" in html
    assert "questionImageWrap" in html


def test_nullable_correct_answer_excluded_from_scoring(client, app):
    """Questions without a keyed answer (correct_answer None) don't count in the total."""
    uid = _make_student(app)
    aid, q1_id, q2_id = _make_image_assessment(app)
    _login(client, uid)

    # Only q2 is scored (correct_answer=0); q1 has None so it's excluded.
    resp = _submit(client, uid, aid, {str(q1_id): 0, str(q2_id): 0})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["score"] == 100.0  # 1 of 1 scored question correct
