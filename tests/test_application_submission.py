"""Server-side application submission validation."""
from datetime import date

from app import db
from app.models.application import Application
from app.models.user import User


def _create_student(app):
    with app.app_context():
        user = User(
            email="application@test.com",
            first_name="Ari",
            last_name="Mensah",
            role="student",
        )
        user.set_password("password")
        db.session.add(user)
        db.session.flush()
        db.session.add(Application(user_id=user.id, pipeline_stage="submitted"))
        db.session.commit()
        return user.id


def _login(client, user_id):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True
        sess["_sess_v"] = 1


def _complete_application():
    return {
        "action": "submit",
        "current_step": "3",
        "first_name": "Ama",
        "last_name": "Mensah",
        "email": "application@test.com",
        "whatsapp": "+233 20 000 0000",
        "date_of_birth": "2000-04-15",
        "age": "999",
        "gender": "Female",
        "city": "Accra",
        "campus_location": "CodeCamp Accra",
        "field_of_study": "Software Engineering",
        "previous_student": "No, I'm new to Cellusys CodeCamp",
        "current_status": "Student",
        "profession": "Computer Science",
        "can_commit": "true",
    }


def test_application_submission_requires_all_server_fields(client, app):
    user_id = _create_student(app)
    _login(client, user_id)

    response = client.post(
        "/student/application",
        data={"action": "submit", "current_step": "3"},
    )

    assert response.status_code == 200
    assert b"First name is required." in response.data
    with app.app_context():
        application = Application.query.filter_by(user_id=user_id).first()
        assert application.is_submitted is False
        assert application.pipeline_stage == "submitted"


def test_application_submission_validates_and_derives_age(client, app):
    user_id = _create_student(app)
    _login(client, user_id)

    response = client.post("/student/application", data=_complete_application())

    assert response.status_code == 302
    with app.app_context():
        application = Application.query.filter_by(user_id=user_id).first()
        user = User.query.get(user_id)
        expected_age = date.today().year - 2000 - (
            (date.today().month, date.today().day) < (4, 15)
        )
        assert application.is_submitted is True
        assert application.pipeline_stage == "test_invited"
        assert application.age == expected_age
        assert user.email == "application@test.com"


def test_application_rejects_unverified_email_change(client, app):
    user_id = _create_student(app)
    _login(client, user_id)
    data = _complete_application()
    data["email"] = "new-address@test.com"

    response = client.post("/student/application", data=data)

    assert response.status_code == 200
    assert b"update and confirm it in your profile first" in response.data
    with app.app_context():
        application = Application.query.filter_by(user_id=user_id).first()
        user = User.query.get(user_id)
        assert application.is_submitted is False
        assert user.email == "application@test.com"
