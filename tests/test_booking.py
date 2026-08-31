"""Integration tests for interview booking lifecycle."""
from datetime import datetime, date, timedelta, timezone
from app import db
from app.models.user import User
from app.models.application import Application
from app.models.assessment import Assessment, TestAttempt
from app.models.interview import InterviewSlot, InterviewBooking


def _login(client, user_id):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True
        sess["_sess_v"] = 1


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


def test_book_requires_passed_test(client, app):
    with app.app_context():
        admin = User(email="admin-gate@test.com", first_name="A", last_name="G", role="admin")
        admin.set_password("p")
        student = User(email="stu-gate@test.com", first_name="S", last_name="G", role="student")
        student.set_password("p")
        db.session.add_all([admin, student])
        db.session.commit()
        admin_id = admin.id
        student_id = student.id
        assessment = Assessment(title="Gate Test", pass_score=70.0)
        db.session.add(assessment)
        slot = InterviewSlot(
            interviewer_id=admin_id,
            slot_date=date.today() + timedelta(days=3),
            start_time=datetime.strptime("10:00", "%H:%M").time(),
            end_time=datetime.strptime("10:30", "%H:%M").time(),
        )
        db.session.add(slot)
        db.session.commit()
        slot_id = slot.id
        assessment_id = assessment.id

    _login(client, student_id)

    resp = client.get("/api/interview/available-dates")
    assert resp.status_code == 403

    resp = client.post("/api/interview/book", json={"slot_id": slot_id})
    assert resp.status_code == 403

    with app.app_context():
        app_record = Application(user_id=student_id, pipeline_stage="test_completed", is_submitted=True)
        attempt = TestAttempt(
            user_id=student_id, assessment_id=assessment_id,
            passed=True, score=80.0,
            completed_at=datetime.now(timezone.utc),
        )
        db.session.add_all([app_record, attempt])
        db.session.commit()

    resp = client.post("/api/interview/book", json={"slot_id": slot_id})
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True


def test_elapsed_slot_hidden(client, app):
    with app.app_context():
        admin = User(email="admin-elapsed@test.com", first_name="E", last_name="G", role="admin")
        admin.set_password("p")
        student = User(email="stu-elapsed@test.com", first_name="E", last_name="G", role="student")
        student.set_password("p")
        db.session.add_all([admin, student])
        db.session.commit()
        admin_id = admin.id
        student_id = student.id
        app_record = Application(user_id=student_id, pipeline_stage="interview_scheduled", is_submitted=True)
        past_slot = InterviewSlot(
            interviewer_id=admin_id,
            slot_date=date.today(),
            start_time=datetime.strptime("00:01", "%H:%M").time(),
            end_time=datetime.strptime("00:31", "%H:%M").time(),
        )
        db.session.add_all([app_record, past_slot])
        db.session.commit()

    _login(client, student_id)
    resp = client.get(f"/api/interview/slots/{date.today().isoformat()}")
    assert resp.status_code == 200
    assert resp.get_json()["slots"] == []

    resp = client.get("/api/interview/available-dates")
    assert resp.status_code == 200
    assert date.today().isoformat() not in resp.get_json()["dates"]


def test_create_slot_rejects_overlap(client, app):
    with app.app_context():
        admin = User(email="admin-overlap@test.com", first_name="O", last_name="V", role="admin")
        admin.set_password("p")
        db.session.add(admin)
        db.session.commit()
        admin_id = admin.id
        slot = InterviewSlot(
            interviewer_id=admin_id,
            slot_date=date.today() + timedelta(days=9),
            start_time=datetime.strptime("09:00", "%H:%M").time(),
            end_time=datetime.strptime("10:00", "%H:%M").time(),
        )
        db.session.add(slot)
        db.session.commit()

    _login(client, admin_id)
    resp = client.post("/admin/interviews/slots", data={
        "slot_date": (date.today() + timedelta(days=9)).isoformat(),
        "times": ["09:30-10:30"],
    })
    assert resp.status_code == 302

    with app.app_context():
        assert InterviewSlot.query.count() == 1  # overlapping slot not created


def test_recurring_slots(client, app):
    with app.app_context():
        admin = User(email="admin-recur@test.com", first_name="R", last_name="C", role="admin")
        admin.set_password("p")
        db.session.add(admin)
        db.session.commit()
        admin_id = admin.id

    _login(client, admin_id)
    start = date.today() + timedelta(days=7)
    while start.weekday() != 0:  # land on a Monday
        start += timedelta(days=1)
    resp = client.post("/admin/interviews/recurring", data={
        "start_date": start.isoformat(),
        "weeks": "2",
        "weekdays": ["0", "3"],  # Mon, Thu
        "times": ["09:00-09:30", "10:00-10:30"],
    })
    assert resp.status_code == 302

    with app.app_context():
        slots = InterviewSlot.query.all()
        assert len(slots) == 2 * 2 * 2  # weeks x weekdays x times


def test_cancel_completed_reverts_stage(client, app):
    with app.app_context():
        admin = User(email="admin-cmp@test.com", first_name="C", last_name="M",
                     role="admin")
        admin.set_password("p")
        student = User(email="stu-cmp@test.com", first_name="C2", last_name="M2",
                       role="student")
        student.set_password("p")
        db.session.add_all([admin, student])
        db.session.commit()
        admin_id = admin.id
        student_id = student.id

        app_record = Application(
            user_id=student_id, pipeline_stage="interview_completed", is_submitted=True,
        )
        slot = InterviewSlot(
            interviewer_id=admin_id, slot_date=date.today() + timedelta(days=2),
            start_time=datetime.strptime("15:00", "%H:%M").time(),
            end_time=datetime.strptime("16:00", "%H:%M").time(),
        )
        db.session.add_all([app_record, slot])
        db.session.commit()
        slot_id = slot.id

        booking = InterviewBooking(
            user_id=student_id, slot_id=slot_id, status="completed",
        )
        db.session.add(booking)
        db.session.commit()
        booking_id = booking.id

    _login(client, admin_id)
    resp = client.post(f"/admin/interviews/booking/{booking_id}/update",
                       data={"status": "cancelled"})
    assert resp.status_code == 302

    with app.app_context():
        app_record = Application.query.filter_by(user_id=student_id).first()
        assert app_record.pipeline_stage == "test_completed"


def test_rebook_after_cancel(client, app):
    """Regression: after cancelling, the same slot must be bookable again.

    Previously the UNIQUE slot_id constraint on interview_bookings caused a
    new booking row to raise IntegrityError → HTTP 500.
    """
    with app.app_context():
        admin = User(email="admin-rebook@test.com", first_name="R", last_name="B", role="admin")
        admin.set_password("p")
        student = User(email="stu-rebook@test.com", first_name="S", last_name="R", role="student")
        student.set_password("p")
        db.session.add_all([admin, student])
        db.session.commit()
        admin_id = admin.id
        student_id = student.id

        assessment = Assessment(title="Rebook Test", pass_score=70.0)
        app_record = Application(user_id=student_id, pipeline_stage="test_completed", is_submitted=True)
        slot = InterviewSlot(
            interviewer_id=admin_id,
            slot_date=date.today() + timedelta(days=4),
            start_time=datetime.strptime("13:00", "%H:%M").time(),
            end_time=datetime.strptime("13:30", "%H:%M").time(),
        )
        db.session.add_all([assessment, app_record, slot])
        db.session.commit()
        slot_id = slot.id
        assessment_id = assessment.id

        attempt = TestAttempt(
            user_id=student_id, assessment_id=assessment_id,
            passed=True, score=80.0, completed_at=datetime.now(timezone.utc),
        )
        db.session.add(attempt)
        db.session.commit()

    _login(client, student_id)

    resp = client.post("/api/interview/book", json={"slot_id": slot_id})
    assert resp.status_code == 200
    booking_id = resp.get_json()["booking_id"]

    resp = client.post(f"/api/interview/cancel/{booking_id}")
    assert resp.status_code == 200

    # Re-booking the now-freed slot must succeed, not 500.
    resp = client.post("/api/interview/book", json={"slot_id": slot_id})
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True

    with app.app_context():
        # Exactly one booking row for the slot, now scheduled again.
        bookings = InterviewBooking.query.filter_by(slot_id=slot_id).all()
        assert len(bookings) == 1
        assert bookings[0].status == "scheduled"
