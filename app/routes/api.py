"""JSON API endpoints for AJAX interactions."""
import json
from datetime import datetime, timedelta, timezone
from flask import Blueprint, request, jsonify, url_for
from flask_login import login_required, current_user
from sqlalchemy.orm.exc import StaleDataError
from app import db, limiter
from app.models.application import Application
from app.pipeline import pipeline
from app.models.assessment import Assessment, Question, TestAttempt
from app.models.interview import InterviewSlot, InterviewBooking
from app.models.announcement import AnnouncementRead
from app.models.notification import Notification
from app.utils.helpers import log_activity, create_notification, send_mail

api_bp = Blueprint("api", __name__)


def _interviewee_can_book():
    """Return True if the current student may book/reschedule an interview."""
    app_record = Application.query.filter_by(user_id=current_user.id).first()
    if not app_record:
        return False
    if app_record.pipeline_stage == "interview_scheduled":
        return True
    if app_record.pipeline_stage == "test_completed":
        last_attempt = TestAttempt.query.filter_by(user_id=current_user.id).order_by(
            TestAttempt.completed_at.desc()
        ).first()
        return bool(last_attempt and last_attempt.passed)
    return False


def _local_now():
    """Current wall-clock time (slots are stored in the app's local time — UTC)."""
    now = datetime.now(timezone.utc)
    return now.date(), now.time().replace(tzinfo=None)


@api_bp.route("/notifications")
@login_required
def get_notifications():
    notifs = Notification.query.filter_by(user_id=current_user.id).order_by(
        Notification.created_at.desc()
    ).limit(20).all()
    return jsonify([
        {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "link": n.link,
            "is_read": n.is_read,
            "created_at": n.created_at.strftime("%b %d, %Y %I:%M %p"),
        }
        for n in notifs
    ])


@api_bp.route("/notifications/<int:notif_id>/read", methods=["POST"])
@login_required
def mark_notification_read(notif_id):
    notif = Notification.query.filter_by(id=notif_id, user_id=current_user.id).first_or_404()
    notif.is_read = True
    db.session.commit()
    return jsonify({"success": True})


@api_bp.route("/notifications/read-all", methods=["POST"])
@login_required
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify({"success": True})


@api_bp.route("/assessment/<int:assessment_id>/submit", methods=["POST"])
@login_required
def submit_assessment(assessment_id):
    data = request.get_json() or {}
    answers = data.get("answers", {})
    time_taken = data.get("time_taken", 0)
    assessment = Assessment.query.get_or_404(assessment_id)

    # Reject resubmission only after a passed attempt — prevents score overwrite.
    # A failed attempt allows retakes (mirrors take_assessment's retake logic).
    last_completed = TestAttempt.query.filter_by(
        user_id=current_user.id, assessment_id=assessment_id
    ).filter(TestAttempt.completed_at.isnot(None)).order_by(
        TestAttempt.completed_at.desc()
    ).first()
    if last_completed and last_completed.passed:
        return jsonify({"error": "Assessment already submitted"}), 400

    attempt = TestAttempt.query.filter_by(
        user_id=current_user.id, assessment_id=assessment_id
    ).filter(TestAttempt.completed_at.is_(None)).first()
    if not attempt:
        attempt = TestAttempt(user_id=current_user.id, assessment_id=assessment_id)
        db.session.add(attempt)
    questions = Question.query.filter_by(assessment_id=assessment_id).all()
    earned = 0
    total = 0
    for q in questions:
        total += q.points
        selected = answers.get(str(q.id))
        if selected is not None and int(selected) == q.correct_answer:
            earned += q.points
    score = round((earned / total * 100) if total else 0, 1)
    attempt.answers = json.dumps(answers)
    attempt.earned_points = earned
    attempt.total_points = total
    attempt.score = score
    attempt.passed = score >= assessment.pass_score
    attempt.completed_at = datetime.now(timezone.utc)
    attempt.time_taken_seconds = time_taken
    app_record = Application.query.filter_by(user_id=current_user.id).first()
    if app_record:
        app_record.test_score = score
        app_record.test_attempts = (app_record.test_attempts or 0) + 1
        app_record.last_test_attempt_date = datetime.now(timezone.utc)

        if attempt.passed:
            app_record.pipeline_stage = "test_completed"
            app_record.status = "test_completed"
            create_notification(
                current_user.id,
                "Test Passed!",
                f"You scored {score}%. Interview scheduling is now available.",
                url_for("student.interview_schedule"),
            )
        else:
            app_record.pipeline_stage = "test_completed"
            app_record.status = "test_completed"
            create_notification(
                current_user.id,
                "Test Completed",
                f"You scored {score}%. Minimum pass score is {assessment.pass_score}%. You can retake the test.",
                url_for("student.assessment_list"),
            )
    log_activity(current_user.id, "test_completed", f"Score: {score}% (Attempt {app_record.test_attempts if app_record else 1})")
    db.session.commit()
    return jsonify({
        "success": True,
        "score": score,
        "passed": attempt.passed,
        "attempt_id": attempt.id,
    })


@api_bp.route("/interview/available-dates")
@login_required
@limiter.limit("60 per minute")
def available_dates():
    if not _interviewee_can_book():
        return jsonify({"error": "Interview not available until the assessment is passed."}), 403
    today, current_time = _local_now()
    end = today + timedelta(days=30)
    slots = InterviewSlot.query.filter(
        InterviewSlot.slot_date >= today,
        InterviewSlot.slot_date <= end,
        InterviewSlot.is_available == True,
    ).all()
    dates = sorted({
        s.slot_date.isoformat()
        for s in slots
        if not s.booking and (s.slot_date != today or s.start_time > current_time)
    })
    return jsonify({"dates": dates})


@api_bp.route("/interview/slots/<date_str>")
@login_required
def slots_for_date(date_str):
    if not _interviewee_can_book():
        return jsonify({"error": "Interview not required until the assessment is passed."}), 403
    today, current_time = _local_now()
    slot_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    slots = InterviewSlot.query.filter_by(slot_date=slot_date, is_available=True).all()
    available = []
    for s in slots:
        if s.booking:
            continue
        if s.slot_date == today and s.start_time <= current_time:
            continue
        available.append({
            "id": s.id,
            "start": s.start_time.strftime("%H:%M"),
            "end": s.end_time.strftime("%H:%M"),
            "label": s.formatted_time,
        })
    return jsonify({"slots": available})


@api_bp.route("/interview/book", methods=["POST"])
@login_required
@limiter.limit("10 per hour")
def book_interview():
    if not _interviewee_can_book():
        return jsonify({"error": "You must pass the assessment before booking an interview."}), 403
    data = request.get_json() or {}
    slot_id = data.get("slot_id")
    today, current_time = _local_now()

    # Atomic check-then-set with row lock (PostgreSQL) — prevents double-booking
    # Atomic check-then-set with row lock (PostgreSQL) — prevents double-booking
    slot = InterviewSlot.query.with_for_update().get_or_404(slot_id)
    if slot.booking:
        db.session.rollback()
        return jsonify({"error": "Slot no longer available"}), 400
    if slot.slot_date < today or (slot.slot_date == today and slot.start_time <= current_time):
        db.session.rollback()
        return jsonify({"error": "This time slot has already passed."}), 400

    existing = InterviewBooking.query.filter_by(user_id=current_user.id).filter(
        InterviewBooking.status == "scheduled"
    ).first()
    if existing:
        existing.status = "cancelled"
        existing.slot.is_available = True

    booking = InterviewBooking(user_id=current_user.id, slot_id=slot.id)
    slot.is_available = False
    db.session.add(booking)

    app_record = Application.query.filter_by(user_id=current_user.id).first()
    if app_record:
        app_record.pipeline_stage = "interview_scheduled"
        app_record.status = "interview_scheduled"
        app_record.updated_at = datetime.now(timezone.utc)

    create_notification(
        current_user.id,
        "Interview Scheduled",
        f"Your interview is booked for {slot.formatted_date} at {slot.formatted_time}.",
    )
    create_notification(
        slot.interviewer_id,
        "Interview Booked",
        f"{current_user.full_name} ({current_user.email}) booked {slot.formatted_date} at {slot.formatted_time}.",
        url_for("admin.interviews"),
    )
    log_activity(current_user.id, "interview_booked", f"Slot {slot_id}")
    db.session.commit()
    send_mail(
        recipient=current_user.email,
        subject="Cellusys CodeCamp — Interview Confirmed",
        text_body=(
            f"Hi {current_user.first_name},\n\n"
            f"Your interview is confirmed for {slot.formatted_date} at {slot.formatted_time}.\n"
            f"Location: Cellusys Academy, Kwabenya Musuku Roundabout, Accra, Ghana.\n\n"
            f"Log in to your dashboard to reschedule or cancel if needed.\n\n"
            f"Cellusys CodeCamp"
        ),
        html_body=(
            f"<h2>Interview Confirmed</h2>"
            f"<p>Hi {current_user.first_name},</p>"
            f"<p>Your interview is confirmed for "
            f"<strong>{slot.formatted_date}</strong> at <strong>{slot.formatted_time}</strong>.</p>"
            f"<p>Location: <strong>Cellusys Academy, Kwabenya Musuku Roundabout, Accra, Ghana</strong>.</p>"
            f"<p>Log in to your dashboard to reschedule or cancel if needed.</p>"
        ),
    )
    return jsonify({
        "success": True,
        "date": slot.formatted_date,
        "time": slot.formatted_time,
        "booking_id": booking.id,
    })


@api_bp.route("/interview/cancel/<int:booking_id>", methods=["POST"])
@login_required
def cancel_interview(booking_id):
    booking = InterviewBooking.query.filter_by(id=booking_id, user_id=current_user.id).first_or_404()
    booking.status = "cancelled"
    if booking.slot:
        booking.slot.is_available = True
        slot_info = (booking.slot.formatted_date, booking.slot.formatted_time)
    else:
        slot_info = None
    app_record = Application.query.filter_by(user_id=current_user.id).first()
    if app_record and app_record.pipeline_stage in ("interview_scheduled", "interview_completed"):
        app_record.pipeline_stage = "test_completed"
        app_record.status = "test_completed"
        app_record.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    if slot_info:
        send_mail(
            recipient=current_user.email,
            subject="Cellusys CodeCamp — Interview Cancelled",
            text_body=(
                f"Hi {current_user.first_name},\n\n"
                f"Your interview on {slot_info[0]} at {slot_info[1]} has been cancelled.\n"
                f"Log in to reschedule at a time that works for you.\n\n"
                f"Cellusys CodeCamp"
            ),
        )
    return jsonify({"success": True})


@api_bp.route("/pipeline/move", methods=["POST"])
@login_required
def move_pipeline_card():
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403
    data = request.get_json() or {}
    app_id = data.get("application_id")
    column = data.get("column")
    new_stage = pipeline.stage_for_kanban(column)
    app_record = Application.query.get_or_404(app_id)
    
    if not pipeline.can_advance(app_record.pipeline_stage, new_stage):
        return jsonify({"error": f"Cannot transition from {app_record.pipeline_stage} to {new_stage}"}), 400
    
    app_record.pipeline_stage = new_stage
    app_record.status = new_stage
    app_record.version += 1
    app_record.updated_at = datetime.now(timezone.utc)
    notif_title, notif_message = pipeline.notify_content(app_record.pipeline_stage, new_stage)
    create_notification(
        app_record.user_id,
        notif_title,
        notif_message,
        url_for("student.dashboard"),
    )
    log_activity(current_user.id, "pipeline_move", f"App {app_id} -> {new_stage}")
    try:
        db.session.commit()
        return jsonify({"success": True, "stage": new_stage})
    except StaleDataError:
        db.session.rollback()
        return jsonify({"error": "Conflict: another admin modified this application. Please reload."}), 409


@api_bp.route("/announcements/<int:ann_id>/read", methods=["POST"])
@login_required
def mark_announcement_read(ann_id):
    existing = AnnouncementRead.query.filter_by(
        user_id=current_user.id, announcement_id=ann_id
    ).first()
    if not existing:
        db.session.add(AnnouncementRead(user_id=current_user.id, announcement_id=ann_id))
        db.session.commit()
    return jsonify({"success": True})


@api_bp.route("/theme", methods=["POST"])
@login_required
def set_theme():
    theme = request.get_json().get("theme", "dark")
    if theme in ("dark", "light"):
        current_user.theme = theme
        db.session.commit()
    return jsonify({"success": True, "theme": current_user.theme})
