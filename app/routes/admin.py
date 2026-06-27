"""Admin dashboard and management routes."""
from datetime import datetime, date, timedelta
from flask import (
    Blueprint, render_template, redirect, url_for, flash, request, jsonify,
)
from flask_login import login_required, current_user
from app import db
from app.models.user import User
from app.models.application import Application, KANBAN_COLUMNS, PIPELINE_STAGES, VALID_TRANSITIONS, ADMIN_DECISION_TRANSITIONS, can_advance_to
from app.models.assessment import Assessment, Question, TestAttempt
from app.models.interview import InterviewSlot, InterviewBooking, InterviewerProfile
from app.models.announcement import Announcement
import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app
from app.models.notification import Notification
from app.utils.decorators import admin_required
from app.utils.helpers import log_activity, create_notification

admin_bp = Blueprint("admin", __name__)





@admin_bp.route("/dashboard")
@login_required
@admin_required
def dashboard():
    total_applicants = Application.query.filter_by(is_submitted=True).count()
    accepted = Application.query.filter(Application.pipeline_stage.in_(["accepted", "enrolled", "onboarding"])).count()
    rejected = Application.query.filter_by(pipeline_stage="rejected").count()
    interviews = InterviewBooking.query.filter_by(status="scheduled").count()
    test_passed = TestAttempt.query.filter_by(passed=True).count()
    test_total = TestAttempt.query.filter(TestAttempt.completed_at.isnot(None)).count()
    pass_rate = round((test_passed / test_total * 100) if test_total else 0, 1)
    acceptance_rate = round((accepted / total_applicants * 100) if total_applicants else 0, 1)
    recent_apps = Application.query.filter_by(is_submitted=True).order_by(
        Application.submitted_at.desc()
    ).limit(8).all()
    return render_template(
        "admin/dashboard.html",
        stats={
            "total_applicants": total_applicants,
            "accepted": accepted,
            "rejected": rejected,
            "interviews": interviews,
            "pass_rate": pass_rate,
            "acceptance_rate": acceptance_rate,
            "conversion_rate": round((interviews / total_applicants * 100) if total_applicants else 0, 1),
        },
        recent_apps=recent_apps,
    )


@admin_bp.route("/applicants")
@login_required
@admin_required
def applicants():
    q = request.args.get("q", "")
    stage = request.args.get("stage", "")
    page = request.args.get("page", 1, type=int)
    per_page = 20
    query = Application.query.filter_by(is_submitted=True)
    if q:
        query = query.join(User).filter(
            db.or_(
                User.first_name.ilike(f"%{q}%"),
                User.last_name.ilike(f"%{q}%"),
                User.email.ilike(f"%{q}%"),
            )
        )
    if stage:
        query = query.filter_by(pipeline_stage=stage)
    pagination = query.order_by(Application.updated_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return render_template(
        "admin/applicants.html",
        applications=pagination.items,
        pagination=pagination,
        pipeline_stages=PIPELINE_STAGES,
        q=q,
        stage=stage,
    )


@admin_bp.route("/applicants/<int:app_id>")
@login_required
@admin_required
def applicant_detail(app_id):
    app_record = Application.query.get_or_404(app_id)

    attempts = TestAttempt.query.filter_by(user_id=app_record.user_id).all()
    booking = InterviewBooking.query.filter_by(user_id=app_record.user_id).first()
    valid_next_stages = ADMIN_DECISION_TRANSITIONS.get(app_record.pipeline_stage, [])
    return render_template(
        "admin/applicant_detail.html",
        application=app_record,
        attempts=attempts,
        booking=booking,
        stage_options=[app_record.pipeline_stage] + valid_next_stages,
    )


@admin_bp.route("/applicants/<int:app_id>/update-stage", methods=["POST"])
@login_required
@admin_required
def update_stage(app_id):
    app_record = Application.query.get_or_404(app_id)
    new_stage = request.form.get("pipeline_stage")
    if new_stage not in PIPELINE_STAGES:
        flash("Invalid stage.", "error")
        return redirect(request.referrer or url_for("admin.applicants"))

    if new_stage == app_record.pipeline_stage:
        flash("Stage unchanged.", "info")
        return redirect(request.referrer or url_for("admin.applicants"))
    
    if not can_advance_to(app_record.pipeline_stage, new_stage):
        flash(f"Cannot transition from {app_record.pipeline_stage} to {new_stage}.", "error")
        return redirect(request.referrer or url_for("admin.applicants"))
    
    if new_stage == "rejected":
        reason = request.form.get("rejection_reason", "")
        app_record.rejection_reason = reason
        app_record.can_reapply = False
    
    if new_stage == "waitlisted":
        app_record.can_reapply = True
        app_record.reapply_at = datetime.utcnow() + timedelta(days=30)
    
    app_record.pipeline_stage = new_stage
    app_record.status = new_stage
    app_record.updated_at = datetime.utcnow()
    
    notification_title = "Application Update"
    notification_message = f"Your application status is now: {app_record.status_label}"
    if new_stage == "accepted":
        notification_title = "Application Passed"
        notification_message = "Congratulations, your application has passed. Cohort placement will follow."
    elif new_stage == "rejected":
        notification_title = "Application Rejected"
        notification_message = app_record.rejection_reason or "Your application was not selected at this time."
    elif new_stage == "waitlisted":
        notification_title = "Application Waitlisted"
        notification_message = "Your application has been waitlisted. We'll notify you when there is an update."

    create_notification(
        app_record.user_id,
        notification_title,
        notification_message,
        url_for("student.dashboard"),
    )
    log_activity(current_user.id, "stage_update", f"App {app_id} -> {new_stage}")
    db.session.commit()
    flash(f"Stage updated to {app_record.status_label}.", "success")
    return redirect(request.referrer or url_for("admin.applicants"))


@admin_bp.route("/cohorts")
@login_required
@admin_required
def cohorts():
    applications = Application.query.filter(
        Application.pipeline_stage.in_(["accepted", "onboarding", "enrolled"])
    ).order_by(Application.updated_at.desc()).all()
    return render_template("admin/cohorts.html", applications=applications)


@admin_bp.route("/cohorts/<int:app_id>/assign", methods=["POST"])
@login_required
@admin_required
def assign_cohort(app_id):
    app_record = Application.query.get_or_404(app_id)
    if app_record.pipeline_stage not in ("accepted", "onboarding", "enrolled"):
        flash("Only passed applicants can be placed into cohorts.", "error")
        return redirect(url_for("admin.cohorts"))

    cohort_name = request.form.get("cohort_name", "").strip()
    if not cohort_name:
        flash("Cohort name is required.", "error")
        return redirect(url_for("admin.cohorts"))

    app_record.cohort_name = cohort_name
    app_record.cohort_notes = request.form.get("cohort_notes", "").strip()
    app_record.cohort_assigned_at = datetime.utcnow()
    if app_record.pipeline_stage == "accepted":
        app_record.pipeline_stage = "onboarding"
        app_record.status = "onboarding"
    app_record.updated_at = datetime.utcnow()

    create_notification(
        app_record.user_id,
        "Cohort Placement",
        f"You have been placed in {cohort_name}.",
        url_for("student.announcements"),
    )
    log_activity(current_user.id, "cohort_assigned", f"App {app_id} -> {cohort_name}")
    db.session.commit()
    flash("Cohort placement saved.", "success")
    return redirect(url_for("admin.cohorts"))


@admin_bp.route("/pipeline")
@login_required
@admin_required
def pipeline():
    apps = Application.query.filter_by(is_submitted=True).all()
    columns = {k: [] for k in KANBAN_COLUMNS}
    for app in apps:
        for col, stages in KANBAN_COLUMNS.items():
            if app.pipeline_stage in stages:
                columns[col].append(app)
                break
    return render_template("admin/pipeline.html", columns=columns, kanban_keys=list(KANBAN_COLUMNS.keys()))


@admin_bp.route("/analytics")
@login_required
@admin_required
def analytics():
    total = Application.query.filter_by(is_submitted=True).count()
    stages = {}
    for stage in PIPELINE_STAGES:
        stages[stage] = Application.query.filter_by(pipeline_stage=stage, is_submitted=True).count()
    attempts = TestAttempt.query.filter(TestAttempt.completed_at.isnot(None)).all()
    scores = [a.score for a in attempts if a.score]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0
    return render_template(
        "admin/analytics.html",
        stats={"total": total, "stages": stages, "avg_score": avg_score, "attempts": len(attempts)},
    )


@admin_bp.route("/assessments")
@login_required
@admin_required
def assessments():
    assessments = Assessment.query.all()
    return render_template("admin/assessments.html", assessments=assessments)


@admin_bp.route("/assessments/create", methods=["GET", "POST"])
@login_required
@admin_required
def create_assessment():
    flash(
        "Aptitude assessments are preconfigured and cannot be created or edited from the admin panel.",
        "warning",
    )
    return redirect(url_for("admin.assessments"))


@admin_bp.route("/assessments/<int:assessment_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_assessment(assessment_id):
    flash(
        "Aptitude assessments are preconfigured and cannot be created or edited from the admin panel.",
        "warning",
    )
    return redirect(url_for("admin.assessments"))


@admin_bp.route("/interviews")
@login_required
@admin_required
def interviews():
    slots = InterviewSlot.query.order_by(InterviewSlot.slot_date.desc()).limit(50).all()
    bookings = InterviewBooking.query.order_by(InterviewBooking.created_at.desc()).all()
    return render_template("admin/interviews.html", slots=slots, bookings=bookings)


@admin_bp.route("/interviews/slots", methods=["POST"])
@login_required
@admin_required
def create_slots():
    slot_date = datetime.strptime(request.form.get("slot_date"), "%Y-%m-%d").date()
    times = request.form.getlist("times")
    for t in times:
        start_str, end_str = t.split("-")
        start = datetime.strptime(start_str.strip(), "%H:%M").time()
        end = datetime.strptime(end_str.strip(), "%H:%M").time()
        slot = InterviewSlot(
            interviewer_id=current_user.id,
            slot_date=slot_date,
            start_time=start,
            end_time=end,
        )
        db.session.add(slot)
    db.session.commit()
    flash("Time slots created.", "success")
    return redirect(url_for("admin.interviews"))


@admin_bp.route("/interviews/booking/<int:booking_id>/update", methods=["POST"])
@login_required
@admin_required
def update_booking(booking_id):
    booking = InterviewBooking.query.get_or_404(booking_id)
    new_status = request.form.get("status", booking.status)
    booking.status = new_status
    booking.admin_notes = request.form.get("admin_notes")
    booking.rating = request.form.get("rating", type=int)
    
    app_record = Application.query.filter_by(user_id=booking.user_id).first()
    
    if new_status == "completed":
        if app_record:
            app_record.pipeline_stage = "interview_completed"
            app_record.status = "interview_completed"
            if booking.rating:
                app_record.interview_rating = booking.rating
    elif new_status == "no_show":
        # Auto-reject for no-show
        if app_record:
            app_record.pipeline_stage = "rejected"
            app_record.status = "rejected"
            app_record.rejection_reason = "No-show at interview"
            create_notification(
                booking.user_id,
                "Application Rejected",
                "Your application was rejected due to not showing up for your scheduled interview.",
                url_for("student.dashboard"),
            )
    
    db.session.commit()
    flash("Booking updated.", "success")
    return redirect(url_for("admin.interviews"))


@admin_bp.route("/interviews/slot/<int:slot_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_slot(slot_id):
    slot = InterviewSlot.query.get_or_404(slot_id)
    if slot.booking:
        flash("Cannot delete a booked slot. Cancel the booking first.", "error")
        return redirect(url_for("admin.interviews"))
    db.session.delete(slot)
    db.session.commit()
    flash("Slot deleted.", "success")
    return redirect(url_for("admin.interviews"))


@admin_bp.route("/announcements", methods=["GET", "POST"])
@login_required
@admin_required
def manage_announcements():
    if request.method == "POST":
        # handle uploaded image
        image = request.files.get("image")
        filename = None
        if image and image.filename:
            allowed = set(current_app.config.get("ALLOWED_EXTENSIONS", []))
            ext = image.filename.rsplit('.', 1)[-1].lower()
            if ext in allowed:
                fname = secure_filename(image.filename)
                unique = f"{uuid.uuid4().hex}_{fname}"
                upload_path = current_app.config["UPLOAD_FOLDER"]
                os.makedirs(upload_path, exist_ok=True)
                image.save(os.path.join(upload_path, unique))
                filename = unique

        ann = Announcement(
            title=request.form.get("title"),
            content=request.form.get("content"),
            image_filename=filename,
            is_pinned=request.form.get("is_pinned") == "on",
            author_id=current_user.id,
        )
        db.session.add(ann)
        db.session.commit()

        # enforce max 6 posts: delete oldest extras and their files
        total = Announcement.query.count()
        if total > 6:
            extras = Announcement.query.order_by(Announcement.created_at.asc()).limit(total - 6).all()
            for ex in extras:
                # delete file if present
                if ex.image_filename:
                    try:
                        fp = os.path.join(current_app.config["UPLOAD_FOLDER"], ex.image_filename)
                        if os.path.exists(fp):
                            os.remove(fp)
                    except Exception:
                        pass
                db.session.delete(ex)
            db.session.commit()

        flash("Announcement published.", "success")
        return redirect(url_for("admin.manage_announcements"))
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
    return render_template("admin/announcements.html", announcements=announcements)


@admin_bp.route('/announcements/<int:ann_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_announcement(ann_id):
    ann = Announcement.query.get_or_404(ann_id)
    # remove image file if present
    if ann.image_filename:
        try:
            fp = os.path.join(current_app.config['UPLOAD_FOLDER'], ann.image_filename)
            if os.path.exists(fp):
                os.remove(fp)
        except Exception:
            pass
    db.session.delete(ann)
    db.session.commit()
    flash('Announcement deleted.', 'success')
    return redirect(url_for('admin.manage_announcements'))
