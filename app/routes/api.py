"""JSON API endpoints for AJAX interactions."""
import json
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.application import Application, KANBAN_COLUMNS, VALID_TRANSITIONS, can_advance_to
from app.models.assessment import Assessment, Question, TestAttempt
from app.models.interview import InterviewSlot, InterviewBooking
from app.models.announcement import AnnouncementRead
from app.models.notification import Notification
from app.utils.helpers import log_activity, create_notification

api_bp = Blueprint("api", __name__)


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
    attempt.completed_at = datetime.utcnow()
    attempt.time_taken_seconds = time_taken
    app_record = Application.query.filter_by(user_id=current_user.id).first()
    if app_record:
        app_record.test_score = score
        app_record.test_attempts = (app_record.test_attempts or 0) + 1
        app_record.last_test_attempt_date = datetime.utcnow()
        
        if attempt.passed:
            app_record.pipeline_stage = "test_completed"
            app_record.status = "test_completed"
            create_notification(
                current_user.id,
                "Test Passed!",
                f"You scored {score}%. Interview scheduling is now available.",
                "/student/interview",
            )
        else:
            app_record.pipeline_stage = "test_completed"
            app_record.status = "test_completed"
            create_notification(
                current_user.id,
                "Test Completed",
                f"You scored {score}%. Minimum pass score is {assessment.pass_score}%. You can retake the test.",
                "/student/assessment",
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
def available_dates():
    today = datetime.utcnow().date()
    end = today + timedelta(days=30)
    slots = InterviewSlot.query.filter(
        InterviewSlot.slot_date >= today,
        InterviewSlot.slot_date <= end,
        InterviewSlot.is_available == True,
    ).all()
    dates = sorted(set(s.slot_date.isoformat() for s in slots if not s.booking))
    return jsonify({"dates": dates})


@api_bp.route("/interview/slots/<date_str>")
@login_required
def slots_for_date(date_str):
    slot_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    slots = InterviewSlot.query.filter_by(slot_date=slot_date, is_available=True).all()
    available = []
    for s in slots:
        if not s.booking:
            available.append({
                "id": s.id,
                "start": s.start_time.strftime("%H:%M"),
                "end": s.end_time.strftime("%H:%M"),
                "label": s.formatted_time,
            })
    return jsonify({"slots": available})


@api_bp.route("/interview/book", methods=["POST"])
@login_required
def book_interview():
    data = request.get_json() or {}
    slot_id = data.get("slot_id")
    slot = InterviewSlot.query.get_or_404(slot_id)
    if slot.booking:
        return jsonify({"error": "Slot no longer available"}), 400
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
        app_record.updated_at = datetime.utcnow()
    create_notification(
        current_user.id,
        "Interview Scheduled",
        f"Your interview is booked for {slot.formatted_date} at {slot.formatted_time}.",
    )
    log_activity(current_user.id, "interview_booked", f"Slot {slot_id}")
    db.session.commit()
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
    db.session.commit()
    return jsonify({"success": True})


@api_bp.route("/pipeline/move", methods=["POST"])
@login_required
def move_pipeline_card():
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403
    data = request.get_json() or {}
    app_id = data.get("application_id")
    column = data.get("column")
    stage_map = {
        "new": "submitted",
        "review": "under_review",
        "test": "test_invited",
        "interview": "interview_scheduled",
        "accepted": "accepted",
        "rejected": "rejected",
    }
    new_stage = stage_map.get(column, "submitted")
    app_record = Application.query.get_or_404(app_id)
    
    if new_stage not in VALID_TRANSITIONS.get(app_record.pipeline_stage, []):
        return jsonify({"error": f"Cannot transition from {app_record.pipeline_stage} to {new_stage}"}), 400
    
    app_record.pipeline_stage = new_stage
    app_record.status = new_stage
    app_record.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"success": True, "stage": new_stage})


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
