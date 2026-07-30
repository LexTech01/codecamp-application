"""Integration tests for interview booking lifecycle."""
from datetime import datetime, date, timedelta
from app import db
from app.models.user import User
from app.models.application import Application
from app.models.interview import InterviewSlot, InterviewBooking


def _login(client, user_id):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True


def test_create_slot(client, app):
    with app.app_context():
        admin = User(email="admin@test.com", first_name="Admin", last_name="User",
                     role="admin")
        admin.set_password("pass")
        db.session.add(admin)
        db.session.commit()
        admin_id = admin.id

    _login(client, admin_id)
    resp = client.post("/admin/interviews/slots", data={
        "slot_date": (date.today() + timedelta(days=7)).isoformat(),
        "times": ["09:00-10:00", "10:00-11:00"],
    })
    assert resp.status_code == 302

    with app.app_context():
        slots = InterviewSlot.query.all()
        assert len(slots) == 2


def test_cancel_booking_frees_slot(client, app):
    with app.app_context():
        admin = User(email="admin2@test.com", first_name="A", last_name="B",
                     role="admin")
        admin.set_password("p")
        student = User(email="stu@test.com", first_name="S", last_name="T",
                       role="student")
        student.set_password("p")
        db.session.add_all([admin, student])
        db.session.commit()
        admin_id = admin.id

        slot = InterviewSlot(
            interviewer_id=admin_id, slot_date=date.today() + timedelta(days=5),
            start_time=datetime.strptime("09:00", "%H:%M").time(),
            end_time=datetime.strptime("10:00", "%H:%M").time(),
        )
        db.session.add(slot)
        db.session.commit()
        slot_id = slot.id

        booking = InterviewBooking(
            user_id=student.id, slot_id=slot_id, status="scheduled",
        )
        slot.is_available = False
        db.session.add(booking)
        db.session.commit()
        booking_id = booking.id

    _login(client, admin_id)
    resp = client.post(f"/admin/interviews/booking/{booking_id}/update",
                       data={"status": "cancelled"})
    assert resp.status_code == 302

    with app.app_context():
        updated = InterviewBooking.query.get(booking_id)
        assert updated.status == "cancelled"
        slot = InterviewSlot.query.get(slot_id)
        assert slot.is_available is True


def test_booking_no_show_rejects(client, app):
    with app.app_context():
        admin = User(email="admin3@test.com", first_name="A", last_name="C",
                     role="admin")
        admin.set_password("p")
        student = User(email="stu2@test.com", first_name="S2", last_name="T2",
                       role="student")
        student.set_password("p")
        db.session.add_all([admin, student])
        db.session.commit()
        admin_id = admin.id
        student_id = student.id

        app_record = Application(
            user_id=student_id, pipeline_stage="interview_scheduled",
            is_submitted=True,
        )
        slot = InterviewSlot(
            interviewer_id=admin_id, slot_date=date.today() + timedelta(days=3),
            start_time=datetime.strptime("11:00", "%H:%M").time(),
            end_time=datetime.strptime("12:00", "%H:%M").time(),
        )
        db.session.add_all([app_record, slot])
        db.session.commit()
        slot_id = slot.id

        booking = InterviewBooking(
            user_id=student_id, slot_id=slot_id, status="scheduled",
        )
        slot.is_available = False
        db.session.add(booking)
        db.session.commit()
        booking_id = booking.id

    _login(client, admin_id)
    resp = client.post(f"/admin/interviews/booking/{booking_id}/update",
                       data={"status": "no_show"})
    assert resp.status_code == 302

    with app.app_context():
        app_record = Application.query.filter_by(user_id=student_id).first()
        assert app_record.pipeline_stage == "rejected"
        assert app_record.rejection_reason == "No-show at interview"


def test_booking_completed_advances_stage(client, app):
    with app.app_context():
        admin = User(email="admin4@test.com", first_name="A", last_name="D",
                     role="admin")
        admin.set_password("p")
        student = User(email="stu3@test.com", first_name="S3", last_name="T3",
                       role="student")
        student.set_password("p")
        db.session.add_all([admin, student])
        db.session.commit()
        admin_id = admin.id
        student_id = student.id

        app_record = Application(
            user_id=student_id, pipeline_stage="interview_scheduled",
            is_submitted=True,
        )
        slot = InterviewSlot(
            interviewer_id=admin_id, slot_date=date.today() + timedelta(days=1),
            start_time=datetime.strptime("14:00", "%H:%M").time(),
            end_time=datetime.strptime("15:00", "%H:%M").time(),
        )
        db.session.add_all([app_record, slot])
        db.session.commit()
        slot_id = slot.id

        booking = InterviewBooking(
            user_id=student_id, slot_id=slot_id, status="scheduled",
        )
        slot.is_available = False
        db.session.add(booking)
        db.session.commit()
        booking_id = booking.id

    _login(client, admin_id)
    resp = client.post(f"/admin/interviews/booking/{booking_id}/update",
                       data={"status": "completed", "rating": 4})
    assert resp.status_code == 302

    with app.app_context():
        app_record = Application.query.filter_by(user_id=student_id).first()
        assert app_record.pipeline_stage == "interview_completed"
        assert app_record.interview_rating == 4
