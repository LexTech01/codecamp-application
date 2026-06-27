"""Student dashboard and feature routes."""
import json
from datetime import datetime
from flask import (
    Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app,
)
from flask_login import login_required, current_user
from app import db
from app.forms.auth_forms import ProfileForm
from app.models.user import User
from app.models.application import Application, PIPELINE_STAGES, VALID_TRANSITIONS, can_advance_to
from app.models.assessment import Assessment, Question, TestAttempt
from app.models.interview import InterviewSlot, InterviewBooking, InterviewerProfile
from app.models.announcement import Announcement, AnnouncementRead
from app.models.notification import Notification
from app.models.activity import ActivityLog
from app.utils.decorators import student_required
from app.utils.helpers import save_upload, log_activity, create_notification, parse_json_safe

student_bp = Blueprint("student", __name__)

# Main progression stages (in order)
STAGE_PROGRESSION = [
    "draft",
    "submitted",
    "under_review",
    "test_invited",
    "test_completed",
    "interview_scheduled",
    "interview_completed",
    "accepted",
    "onboarding",
    "enrolled",
]


def check_stage_access(allowed_stages):
    """Decorator to restrict route access based on application stage.
    Allows access to current stage and any completed stages."""
    def decorator(f):
        def wrapper(*args, **kwargs):
            app_record = Application.query.filter_by(user_id=current_user.id).first()
            current_stage = app_record.pipeline_stage if app_record else None
            
            # Allow access if current stage is in allowed stages
            if current_stage in allowed_stages:
                return f(*args, **kwargs)
            
            # Allow access if current stage is past all allowed stages
            if current_stage in STAGE_PROGRESSION and any(s in STAGE_PROGRESSION for s in allowed_stages):
                current_idx = STAGE_PROGRESSION.index(current_stage)
                max_allowed_idx = max(
                    STAGE_PROGRESSION.index(s) for s in allowed_stages if s in STAGE_PROGRESSION
                )
                if current_idx > max_allowed_idx:
                    # User has passed this stage, allow review access
                    return f(*args, **kwargs)
            
            flash(f"This feature is not available at your current stage ({current_stage}).", "warning")
            return redirect(url_for("student.dashboard"))
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator


@student_bp.route("/dashboard")
@login_required
@student_required
def dashboard():
    app_record = Application.query.filter_by(user_id=current_user.id).first()
    booking = InterviewBooking.query.filter_by(user_id=current_user.id).filter(
        InterviewBooking.status.in_(["scheduled"])
    ).first()
    test_attempt = TestAttempt.query.filter_by(user_id=current_user.id).order_by(
        TestAttempt.started_at.desc()
    ).first()
    announcements = Announcement.query.order_by(
        Announcement.is_pinned.desc(), Announcement.created_at.desc()
    ).limit(3).all()
    return render_template(
        "dashboard/student.html",
        application=app_record,
        booking=booking,
        test_attempt=test_attempt,
        announcements=announcements,
        pipeline_stages=PIPELINE_STAGES[:9],
    )


@student_bp.route("/application", methods=["GET", "POST"])
@login_required
@student_required
@check_stage_access(["draft", "submitted", "under_review", "test_invited"])
def application():
    app_record = Application.query.filter_by(user_id=current_user.id).first()
    if not app_record:
        app_record = Application(user_id=current_user.id)
        db.session.add(app_record)
        db.session.commit()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "save_draft":
            _save_application_draft(app_record, request.form)
            flash("Draft saved successfully.", "success")
            return redirect(url_for("student.application", step=app_record.current_step))
        if action == "submit":
            _save_application_draft(app_record, request.form)
            app_record.is_submitted = True
            app_record.pipeline_stage = "test_invited"
            app_record.status = "test_invited"
            app_record.submitted_at = datetime.utcnow()
            app_record.current_step = 2
            log_activity(current_user.id, "application_submitted")
            create_notification(
                current_user.id,
                "Application Submitted",
                "Your application has been received. You can now take the aptitude test.",
                url_for("student.assessment_list"),
            )
            db.session.commit()
            flash("Application submitted successfully! You can now take the aptitude test.", "success")
            return redirect(url_for("student.dashboard"))
    step = request.args.get("step", app_record.current_step or 1, type=int)
    if step not in (1, 2):
        step = 1
    draft = parse_json_safe(app_record.draft_data)
    return render_template("dashboard/application.html", application=app_record, step=step, draft=draft)


def _save_application_draft(app_record, form):
    fields = ["date_of_birth", "gender", "applicant_location", "campus_location", "field_of_study", "referral_code"]
    if "first_name" in form:
        current_user.first_name = form.get("first_name", "").strip()
    if "last_name" in form:
        current_user.last_name = form.get("last_name", "").strip()
    if "email" in form:
        email = form.get("email", "").lower().strip()
        existing = User.query.filter(User.email == email, User.id != current_user.id).first() if email else None
        if email and not existing:
            current_user.email = email
    if "whatsapp" in form:
        current_user.phone = form.get("whatsapp", "").strip()
    for f in fields:
        if f in form:
            setattr(app_record, f, form.get(f))
    app_record.current_step = int(form.get("current_step", app_record.current_step or 1))
    app_record.draft_data = json.dumps({
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "email": current_user.email,
        "whatsapp": current_user.phone,
        **{f: getattr(app_record, f) for f in fields},
    })
    db.session.commit()


@student_bp.route("/assessment")
@login_required
@student_required
@check_stage_access(["test_invited", "test_completed"])
def assessment_list():
    assessments = Assessment.query.filter_by(is_active=True).all()
    attempts = {a.assessment_id: a for a in TestAttempt.query.filter_by(user_id=current_user.id).all()}
    app_record = Application.query.filter_by(user_id=current_user.id).first()
    return render_template(
        "assessment/list.html",
        assessments=assessments,
        attempts=attempts,
        application=app_record,
    )


@student_bp.route("/assessment/<int:assessment_id>/take")
@login_required
@student_required
@check_stage_access(["test_invited", "test_completed"])
def take_assessment(assessment_id):
    assessment = Assessment.query.get_or_404(assessment_id)
    # Get all completed attempts for this assessment
    completed = TestAttempt.query.filter_by(
        user_id=current_user.id, assessment_id=assessment_id
    ).filter(TestAttempt.completed_at.isnot(None)).order_by(TestAttempt.completed_at.desc()).first()
    
    # If passed, redirect to results
    if completed and completed.passed:
        return redirect(url_for("student.assessment_result", attempt_id=completed.id))
    
    # If failed, allow retake by creating a new attempt
    # Check for an incomplete attempt
    attempt = TestAttempt.query.filter_by(
        user_id=current_user.id, assessment_id=assessment_id
    ).filter(TestAttempt.completed_at.is_(None)).first()
    
    if not attempt:
        attempt = TestAttempt(user_id=current_user.id, assessment_id=assessment_id)
        db.session.add(attempt)
        db.session.commit()
        app_record = Application.query.filter_by(user_id=current_user.id).first()
        if app_record and app_record.pipeline_stage == "test_invited":
            log_activity(current_user.id, "test_started")
    question_objs = Question.query.filter_by(assessment_id=assessment_id).order_by(Question.order_num, Question.id).all()
    questions = [q.to_dict() for q in question_objs]
    return render_template(
        "assessment/take.html",
        assessment=assessment,
        questions=questions,
        attempt=attempt,
    )


@student_bp.route("/assessment/result/<int:attempt_id>")
@login_required
@student_required
def assessment_result(attempt_id):
    attempt = TestAttempt.query.filter_by(id=attempt_id, user_id=current_user.id).first_or_404()
    assessment = Assessment.query.get(attempt.assessment_id)
    return render_template("assessment/result.html", attempt=attempt, assessment=assessment)


@student_bp.route("/interview")
@login_required
@student_required
@check_stage_access(["test_completed", "interview_scheduled", "interview_completed"])
def interview_schedule():
    app_record = Application.query.filter_by(user_id=current_user.id).first()
    booking = InterviewBooking.query.filter_by(user_id=current_user.id).filter(
        InterviewBooking.status.in_(["scheduled", "completed"])
    ).first()
    interviewer = User.query.filter_by(role="admin").first()
    profile = InterviewerProfile.query.first() if interviewer else None
    return render_template(
        "interview/schedule.html",
        application=app_record,
        booking=booking,
        interviewer=interviewer,
        profile=profile,
    )


@student_bp.route("/announcements")
@login_required
@student_required
def announcements():
    all_announcements = Announcement.query.order_by(
        Announcement.is_pinned.desc(), Announcement.created_at.desc()
    ).all()
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(
        Notification.created_at.desc()
    ).all()
    read_ids = {
        r.announcement_id
        for r in AnnouncementRead.query.filter_by(user_id=current_user.id).all()
    }
    return render_template(
        "dashboard/announcements.html",
        announcements=all_announcements,
        notifications=notifications,
        read_ids=read_ids,
    )


@student_bp.route("/profile", methods=["GET", "POST"])
@login_required
@student_required
def profile():
    app_record = Application.query.filter_by(user_id=current_user.id).first()
    form = ProfileForm()
    if request.method == "GET":
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.email.data = current_user.email
        form.phone.data = current_user.phone
    if form.validate_on_submit():
        changed = False
        if form.first_name.data and form.first_name.data.strip() != current_user.first_name:
            current_user.first_name = form.first_name.data.strip()
            changed = True
        if form.last_name.data and form.last_name.data.strip() != current_user.last_name:
            current_user.last_name = form.last_name.data.strip()
            changed = True
        if form.email.data and form.email.data.lower().strip() != current_user.email:
            current_user.email = form.email.data.lower().strip()
            changed = True
        if form.phone.data.strip() != current_user.phone:
            current_user.phone = form.phone.data.strip()
            changed = True
        if changed:
            db.session.commit()
            flash("Profile updated successfully.", "success")
        else:
            flash("No changes were made.", "info")
        return redirect(url_for("student.profile"))
    return render_template("dashboard/profile.html", form=form, application=app_record)
