"""Student dashboard and feature routes."""
import json
from datetime import date, datetime, timezone
from email_validator import EmailNotValidError, validate_email
from flask import (
    Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app,
)
from flask_login import login_required, current_user
from app import db
from app.forms.auth_forms import ProfileForm
from app.models.user import User, find_user_by_email_confirm_token
from app.models.application import Application
from app.models.assessment import Assessment, Question, TestAttempt, MAX_TEST_ATTEMPTS
from app.models.interview import InterviewSlot, InterviewBooking, InterviewerProfile
from app.models.announcement import Announcement, AnnouncementRead
from app.models.notification import Notification
from app.models.activity import ActivityLog
from app.utils.decorators import student_required
from app.utils import outbox
from app.utils.helpers import parse_json_safe, resolve_assessment_image
from app.utils.email import send_mail
from app.pipeline import pipeline

student_bp = Blueprint("student", __name__)


def check_stage_access(allowed_stages):
    """Decorator to restrict route access based on application stage.
    Allows access to current stage and any completed stages."""
    def decorator(f):
        def wrapper(*args, **kwargs):
            app_record = Application.query.filter_by(user_id=current_user.id).first()
            current_stage = app_record.pipeline_stage if app_record else None

            if current_stage in allowed_stages:
                return f(*args, **kwargs)

            if current_stage and pipeline.check_access(current_stage, allowed_stages):
                return f(*args, **kwargs)

            flash(f"This feature is not available at your current stage.", "warning")
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
    )


@student_bp.route("/application", methods=["GET", "POST"])
@login_required
@student_required
@check_stage_access(["submitted", "under_review", "test_invited"])
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
            if app_record.is_submitted:
                flash("Your application has already been submitted.", "info")
                return redirect(url_for("student.dashboard"))
            errors = _application_submission_errors(request.form)
            if errors:
                flash("Please correct the following: " + " ".join(errors), "error")
                error_text = " ".join(errors).lower()
                step = 1 if any(
                    field in error_text
                    for field in ("name", "email", "whatsapp", "birth", "gender", "city")
                ) else 2 if any(
                    field in error_text for field in ("campus", "select a valid course")
                ) else 3
                return render_template(
                    "dashboard/application.html",
                    application=app_record,
                    step=step,
                    draft=parse_json_safe(app_record.draft_data),
                    form_data=request.form,
                )
            _save_application_draft(app_record, request.form)
            app_record.is_submitted = True
            app_record.pipeline_stage = "test_invited"
            app_record.status = "test_invited"
            app_record.submitted_at = datetime.now(timezone.utc)
            app_record.current_step = 2
            outbox.transition(
                current_user.id,
                action="application_submitted",
                title="Application Submitted",
                message="Your application has been received. You can now take the aptitude test.",
                link=url_for("student.assessment_list"),
            )
            db.session.commit()
            flash("Application submitted successfully! You can now take the aptitude test.", "success")
            return redirect(url_for("student.dashboard"))
    step = request.args.get("step", app_record.current_step or 1, type=int)
    if step not in (1, 2, 3):
        step = 1
    draft = parse_json_safe(app_record.draft_data)
    return render_template(
        "dashboard/application.html",
        application=app_record,
        step=step,
        draft=draft,
        form_data={},
    )


def _application_submission_errors(form):
    """Validate all application fields server-side before changing pipeline stage."""
    errors = []
    required = {
        "first_name": "First name",
        "last_name": "Last name",
        "email": "Email address",
        "whatsapp": "WhatsApp number",
        "date_of_birth": "Date of birth",
        "gender": "Gender",
        "city": "City",
        "campus_location": "Campus",
        "field_of_study": "Course",
        "previous_student": "Previous student status",
        "current_status": "Current status",
        "profession": "Field of study or profession",
        "can_commit": "Class attendance commitment",
    }
    values = {name: form.get(name, "").strip() for name in required}
    for name, label in required.items():
        if not values[name]:
            errors.append(f"{label} is required.")

    for name, label in (("first_name", "First name"), ("last_name", "Last name")):
        if values[name] and not 2 <= len(values[name]) <= 80:
            errors.append(f"{label} must be between 2 and 80 characters.")

    email = values["email"].lower()
    if email and len(email) > 120:
        errors.append("Email address must be 120 characters or fewer.")
    elif email:
        try:
            validate_email(email, check_deliverability=False)
        except EmailNotValidError:
            errors.append("Enter a valid email address.")
        if email != current_user.email:
            if User.query.filter(User.email == email, User.id != current_user.id).first():
                errors.append("That email address is already in use.")
            else:
                errors.append("To change your email, update and confirm it in your profile first.")

    if values["whatsapp"] and len(values["whatsapp"]) > 30:
        errors.append("WhatsApp number must be 30 characters or fewer.")
    if values["city"] and len(values["city"]) > 80:
        errors.append("City must be 80 characters or fewer.")
    if values["profession"] and len(values["profession"]) > 200:
        errors.append("Field of study or profession must be 200 characters or fewer.")

    birth_date = None
    if values["date_of_birth"]:
        try:
            birth_date = datetime.strptime(values["date_of_birth"], "%Y-%m-%d").date()
            if birth_date > date.today():
                errors.append("Date of birth cannot be in the future.")
        except ValueError:
            errors.append("Enter a valid date of birth.")

    choices = {
        "gender": {"Male", "Female"},
        "campus_location": {"CodeCamp Accra", "CodeCamp Cairo"},
        "field_of_study": {
            "Software Engineering",
            "Networking and Telecommunications",
        },
        "previous_student": {
            "Yes, I'm a current student at Cellusys CodeCamp",
            "Yes, I'm a graduate of Cellusys CodeCamp",
            "Yes, I dropped from Cellusys CodeCamp",
            "No, I'm new to Cellusys CodeCamp",
        },
        "current_status": {"Student", "Graduate", "Working Professional", "Other"},
        "can_commit": {"true", "false"},
    }
    labels = {
        "gender": "Gender",
        "campus_location": "Campus",
        "field_of_study": "Course",
        "previous_student": "Previous student status",
        "current_status": "Current status",
        "can_commit": "Class attendance commitment",
    }
    for field, options in choices.items():
        if values[field] and values[field] not in options:
            errors.append(f"Select a valid {labels[field].lower()}.")

    optional_choices = {
        "referral_source": {
            "Banner", "Sticker", "Church", "Facebook", "Friend", "Instagram",
            "Mosque", "Radio", "School", "Shop", "Street", "TV", "WhatsApp",
            "MOMO Vendor", "Youtube", "Bill Board", "Telegram",
        },
        "referral_code": {
            "FAYA", "PRINCE", "JUSTIN", "FRANCIS - FBB", "MIKE", "SLY",
            "RALPH", "None",
        },
        "previous_course": {"Software Engineering", "Networking and Telecommunications"},
    }
    for field, options in optional_choices.items():
        value = form.get(field, "").strip()
        if value and value not in options:
            errors.append("Select a valid " + field.replace("_", " ") + ".")

    previous_cohort = form.get("previous_cohort", "").strip()
    if len(previous_cohort) > 120:
        errors.append("Previous cohort must be 120 characters or fewer.")
    institution = form.get("institution", "").strip()
    if len(institution) > 200:
        errors.append("Institution must be 200 characters or fewer.")

    return errors


def _save_application_draft(app_record, form):
    fields = [
        "date_of_birth", "age", "gender", "city",
        "referral_source", "campus_location", "field_of_study", "referral_code",
        "previous_student", "previous_course", "previous_cohort",
        "current_status", "profession", "institution",
    ]
    if "first_name" in form:
        current_user.first_name = form.get("first_name", "").strip()
    if "last_name" in form:
        current_user.last_name = form.get("last_name", "").strip()
    if "whatsapp" in form:
        current_user.phone = form.get("whatsapp", "").strip()
    for f in fields:
        if f in form and f != "age":
            setattr(app_record, f, form.get(f))
    if "date_of_birth" in form:
        try:
            birth_date = datetime.strptime(form.get("date_of_birth", ""), "%Y-%m-%d").date()
            today = date.today()
            app_record.age = today.year - birth_date.year - (
                (today.month, today.day) < (birth_date.month, birth_date.day)
            )
        except ValueError:
            app_record.age = None
    # Derive country from campus selection (Accra → Ghana, Cairo → Egypt)
    if app_record.campus_location:
        app_record.country = "Ghana" if app_record.campus_location == "CodeCamp Accra" else "Egypt"
    # Handle boolean field
    can_commit_val = form.get("can_commit")
    if can_commit_val is not None:
        app_record.can_commit = can_commit_val == "true"
    try:
        current_step = int(form.get("current_step", app_record.current_step or 1))
    except (TypeError, ValueError):
        current_step = app_record.current_step or 1
    app_record.current_step = current_step if current_step in (1, 2, 3) else 1
    app_record.draft_data = json.dumps({
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "email": current_user.email,
        "whatsapp": current_user.phone,
        **{f: getattr(app_record, f) for f in fields},
        "country": app_record.country,
        "can_commit": app_record.can_commit,
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
    if not assessment.is_active:
        return redirect(url_for("student.assessment_list"))
    # Enforce max retry limit
    app_record = Application.query.filter_by(user_id=current_user.id).first()
    if app_record and (app_record.test_attempts or 0) >= MAX_TEST_ATTEMPTS:
        last = TestAttempt.query.filter_by(
            user_id=current_user.id, assessment_id=assessment_id
        ).filter(TestAttempt.completed_at.isnot(None)).order_by(TestAttempt.completed_at.desc()).first()
        if last and not last.passed:
            flash(f"You've used all {MAX_TEST_ATTEMPTS} attempts. Please contact support.", "warning")
            return redirect(url_for("student.dashboard"))
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
        if app_record and app_record.pipeline_stage == "test_invited":
            outbox.log(current_user.id, "test_started")
            db.session.commit()
    question_objs = Question.query.filter_by(assessment_id=assessment_id).order_by(Question.order_num, Question.id).all()
    questions = []
    for q in question_objs:
        d = q.to_dict()
        d["image"] = resolve_assessment_image(q.question_image)
        d["option_images"] = [resolve_assessment_image(i) for i in q.option_images_list()]
        questions.append(d)
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
    app_record = Application.query.filter_by(user_id=current_user.id).first()
    attempts_used = app_record.test_attempts if app_record else 0
    retries_left = max(0, MAX_TEST_ATTEMPTS - attempts_used)
    return render_template(
        "assessment/result.html",
        attempt=attempt,
        assessment=assessment,
        retries_left=retries_left,
        max_attempts=MAX_TEST_ATTEMPTS,
    )


@student_bp.route("/interview")
@login_required
@student_required
@check_stage_access(["test_completed", "interview_scheduled", "interview_completed"])
def interview_schedule():
    app_record = Application.query.filter_by(user_id=current_user.id).first()
    if app_record and app_record.pipeline_stage == "test_completed":
        last_attempt = TestAttempt.query.filter_by(user_id=current_user.id).order_by(
            TestAttempt.completed_at.desc()
        ).first()
        if not last_attempt or not last_attempt.passed:
            flash("You must pass the assessment before accessing the interview.", "warning")
            return redirect(url_for("student.dashboard"))
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
    read_ids = {
        r.announcement_id
        for r in AnnouncementRead.query.filter_by(user_id=current_user.id).all()
    }
    query = Announcement.query
    if read_ids:
        query = query.filter(~Announcement.id.in_(read_ids))
    all_announcements = query.order_by(
        Announcement.is_pinned.desc(), Announcement.created_at.desc()
    ).all()
    notifications = Notification.query.filter_by(
        user_id=current_user.id, is_read=False
    ).order_by(
        Notification.created_at.desc()
    ).all()
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
        # Re-authenticate before applying any profile change.
        if not current_user.check_password(form.current_password.data):
            flash("Current password is incorrect.", "error")
            return redirect(url_for("student.profile"))

        changed = False
        if form.first_name.data and form.first_name.data.strip() != current_user.first_name:
            current_user.first_name = form.first_name.data.strip()
            changed = True
        if form.last_name.data and form.last_name.data.strip() != current_user.last_name:
            current_user.last_name = form.last_name.data.strip()
            changed = True
        if form.phone.data.strip() != current_user.phone:
            current_user.phone = form.phone.data.strip()
            changed = True

        new_email = form.email.data.lower().strip() if form.email.data else ""
        if new_email and new_email != current_user.email and new_email != current_user.pending_email:
            # Don't apply immediately — require confirmation from the new address.
            token = current_user.generate_email_confirm_token()
            current_user.pending_email = new_email
            db.session.commit()
            confirm_url = url_for("student.confirm_email", token=token, _external=True)
            send_mail(
                recipient=new_email,
                subject="Cellusys CodeCamp — Confirm your new email",
                text_body=(
                    f"Hi {current_user.first_name},\n\n"
                    f"Confirm this email address to finish updating your account:\n{confirm_url}\n\n"
                    f"If you did not request this, you can ignore this message.\n\n"
                    f"Cellusys CodeCamp"
                ),
            )
            flash(
                "We sent a confirmation link to your new email. "
                "Your address will update once you confirm it.",
                "info",
            )
            outbox.log(current_user.id, "email_change_requested", f"Pending: {new_email}")
            return redirect(url_for("student.profile"))

        if changed:
            db.session.commit()
            flash("Profile updated successfully.", "success")
        else:
            flash("No changes were made.", "info")
        return redirect(url_for("student.profile"))
    return render_template("dashboard/profile.html", form=form, application=app_record)


@student_bp.route("/confirm-email/<token>")
@login_required
@student_required
def confirm_email(token):
    user = find_user_by_email_confirm_token(token)
    if user is None or user.id != current_user.id or not user.email_confirm_valid:
        flash("Invalid or expired confirmation link.", "error")
        return redirect(url_for("student.profile"))
    if user.pending_email and not User.query.filter(
        User.email == user.pending_email, User.id != user.id
    ).first():
        user.email = user.pending_email
        user.session_version += 1  # force re-login on other sessions
    user.clear_email_confirm_token()
    db.session.commit()
    flash("Your email address has been updated.", "success")
    return redirect(url_for("student.profile"))
