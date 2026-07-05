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
from app.models.cohort import Cohort
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
    pagination = query.order_by(
        Application.field_of_study.asc(),
        Application.country.asc(),
        Application.applicant_location.asc(),
        Application.updated_at.desc(),
    ).paginate(page=page, per_page=per_page, error_out=False)

    grouped_applications = {}
    for app in pagination.items:
        program = app.field_of_study or "Unspecified"
        grouped_applications.setdefault(program, []).append(app)

    return render_template(
        "admin/applicants.html",
        applications=pagination.items,
        grouped_applications=grouped_applications,
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
        return redirect(url_for("admin.applicant_detail", app_id=app_id))

    if new_stage == app_record.pipeline_stage:
        flash("Stage unchanged.", "info")
        return redirect(url_for("admin.applicant_detail", app_id=app_id))
    
    if not can_advance_to(app_record.pipeline_stage, new_stage):
        flash(f"Cannot transition from {app_record.pipeline_stage} to {new_stage}.", "error")
        return redirect(url_for("admin.applicant_detail", app_id=app_id))
    
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
    return redirect(url_for("admin.applicant_detail", app_id=app_id))


@admin_bp.route("/cohorts")
@login_required
@admin_required
def cohorts():
    cohorts = Cohort.query.order_by(Cohort.start_date.desc(), Cohort.name).all()
    unassigned = Application.query.filter(
        Application.pipeline_stage.in_(["accepted", "onboarding", "enrolled"]),
        Application.cohort_name.is_(None),
    ).order_by(Application.updated_at.desc()).all()
    grouped = {}
    for c in cohorts:
        members = Application.query.filter_by(cohort_name=c.name).order_by(
            Application.updated_at.desc()
        ).all()
        grouped[c.name] = {"cohort": c, "members": members}
    return render_template(
        "admin/cohorts.html",
        cohorts=cohorts,
        grouped=grouped,
        unassigned=unassigned,
    )


@admin_bp.route("/cohorts/create", methods=["POST"])
@login_required
@admin_required
def create_cohort():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Cohort name is required.", "error")
        return redirect(url_for("admin.cohorts"))
    existing = Cohort.query.filter_by(name=name).first()
    if existing:
        flash("A cohort with that name already exists.", "error")
        return redirect(url_for("admin.cohorts"))
    start = request.form.get("start_date")
    end = request.form.get("end_date")
    cohort = Cohort(
        name=name,
        description=request.form.get("description", "").strip(),
        start_date=datetime.strptime(start, "%Y-%m-%d").date() if start else None,
        end_date=datetime.strptime(end, "%Y-%m-%d").date() if end else None,
    )
    db.session.add(cohort)
    db.session.commit()
    flash(f"Cohort '{name}' created.", "success")
    return redirect(url_for("admin.cohorts"))


@admin_bp.route("/cohorts/<int:cohort_id>/edit", methods=["POST"])
@login_required
@admin_required
def edit_cohort(cohort_id):
    cohort = Cohort.query.get_or_404(cohort_id)
    name = request.form.get("name", "").strip()
    if name and name != cohort.name:
        existing = Cohort.query.filter_by(name=name).first()
        if existing:
            flash("A cohort with that name already exists.", "error")
            return redirect(url_for("admin.cohorts"))
        old_name = cohort.name
        cohort.name = name
        Application.query.filter_by(cohort_name=old_name).update(
            {"cohort_name": name}, synchronize_session=False
        )
    cohort.description = request.form.get("description", "").strip()
    start = request.form.get("start_date")
    end = request.form.get("end_date")
    cohort.start_date = datetime.strptime(start, "%Y-%m-%d").date() if start else None
    cohort.end_date = datetime.strptime(end, "%Y-%m-%d").date() if end else None
    db.session.commit()
    flash("Cohort updated.", "success")
    return redirect(url_for("admin.cohorts"))


@admin_bp.route("/cohorts/<int:cohort_id>/assign", methods=["POST"])
@login_required
@admin_required
def assign_cohort(cohort_id):
    cohort = Cohort.query.get_or_404(cohort_id)
    app_ids = request.form.getlist("app_ids")
    if not app_ids:
        flash("No students selected.", "warning")
        return redirect(url_for("admin.cohorts"))
    for app_id in app_ids:
        app_record = Application.query.get(int(app_id))
        if app_record and app_record.pipeline_stage in ("accepted", "onboarding", "enrolled"):
            app_record.cohort_name = cohort.name
            app_record.cohort_notes = request.form.get("notes", "").strip()
            app_record.cohort_assigned_at = datetime.utcnow()
            if app_record.pipeline_stage == "accepted":
                app_record.pipeline_stage = "onboarding"
                app_record.status = "onboarding"
            app_record.updated_at = datetime.utcnow()
    db.session.commit()
    flash(f"{len(app_ids)} student(s) assigned to {cohort.name}.", "success")
    return redirect(url_for("admin.cohorts"))


@admin_bp.route("/cohorts/<int:cohort_id>/notify", methods=["POST"])
@login_required
@admin_required
def notify_cohort(cohort_id):
    cohort = Cohort.query.get_or_404(cohort_id)
    title = request.form.get("title", "").strip()
    message = request.form.get("message", "").strip()
    if not title or not message:
        flash("Title and message are required.", "error")
        return redirect(url_for("admin.cohorts"))
    members = Application.query.filter_by(cohort_name=cohort.name).all()
    sent = 0
    for app in members:
        create_notification(app.user_id, title, message, url_for("student.announcements"))
        sent += 1
    db.session.commit()
    flash(f"Notification sent to {sent} student(s) in {cohort.name}.", "success")
    return redirect(url_for("admin.cohorts"))


@admin_bp.route("/cohorts/<int:cohort_id>/export")
@login_required
@admin_required
def export_cohort_pdf(cohort_id):
    from flask import make_response
    from weasyprint import HTML

    cohort = Cohort.query.get_or_404(cohort_id)
    members = Application.query.filter_by(cohort_name=cohort.name).order_by(
        Application.updated_at.desc()
    ).all()
    html = render_template(
        "admin/cohort_pdf.html",
        cohort=cohort,
        members=members,
        today=datetime.utcnow(),
    )
    pdf = HTML(string=html).write_pdf()
    resp = make_response(pdf)
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["Content-Disposition"] = f'attachment; filename="{cohort.name.replace(" ", "_")}_roster.pdf"'
    return resp


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
    scores = [a.score for a in attempts if a.score is not None]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0
    score_buckets = [
        sum(1 for s in scores if 0 <= s < 20),
        sum(1 for s in scores if 20 <= s < 40),
        sum(1 for s in scores if 40 <= s < 60),
        sum(1 for s in scores if 60 <= s < 80),
        sum(1 for s in scores if 80 <= s <= 100),
    ]
    return render_template(
        "admin/analytics.html",
        stats={
            "total": total,
            "stages": stages,
            "avg_score": avg_score,
            "attempts": len(attempts),
            "score_buckets": score_buckets,
        },
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
    slot_date_str = request.form.get("slot_date")
    if not slot_date_str:
        flash("Date is required.", "error")
        return redirect(url_for("admin.interviews"))
    slot_date = datetime.strptime(slot_date_str, "%Y-%m-%d").date()
    if slot_date <= date.today():
        flash("Slot date must be in the future.", "error")
        return redirect(url_for("admin.interviews"))
    
    times = request.form.getlist("times")
    if not times:
        flash("Select at least one time slot.", "error")
        return redirect(url_for("admin.interviews"))
    
    created = 0
    for t in times:
        if "-" not in t:
            continue
        start_str, end_str = t.split("-", 1)
        start = datetime.strptime(start_str.strip(), "%H:%M").time()
        end = datetime.strptime(end_str.strip(), "%H:%M").time()
        if start >= end:
            continue
        # Check for duplicate
        existing = InterviewSlot.query.filter_by(
            slot_date=slot_date, start_time=start, end_time=end
        ).first()
        if existing:
            continue
        slot = InterviewSlot(
            interviewer_id=current_user.id,
            slot_date=slot_date,
            start_time=start,
            end_time=end,
        )
        db.session.add(slot)
        created += 1
    db.session.commit()
    if created:
        flash(f"{created} time slot(s) created.", "success")
    else:
        flash("No slots were created. Check for duplicates or invalid times.", "warning")
    return redirect(url_for("admin.interviews"))


@admin_bp.route("/interviews/booking/<int:booking_id>/update", methods=["POST"])
@login_required
@admin_required
def update_booking(booking_id):
    booking = InterviewBooking.query.get_or_404(booking_id)
    new_status = request.form.get("status", booking.status)
    
    valid_booked_transitions = {
        "scheduled": ["completed", "no_show", "cancelled"],
        "completed": ["cancelled"],
        "no_show": ["cancelled"],
        "cancelled": ["scheduled"],
    }
    if new_status not in valid_booked_transitions.get(booking.status, []):
        flash(f"Cannot change status from {booking.status} to {new_status}.", "error")
        return redirect(url_for("admin.interviews"))
    
    booking.status = new_status
    booking.admin_notes = request.form.get("admin_notes", "").strip()
    booking.rating = request.form.get("rating", type=int)
    
    app_record = Application.query.filter_by(user_id=booking.user_id).first()
    
    if new_status == "completed":
        if app_record:
            app_record.pipeline_stage = "interview_completed"
            app_record.status = "interview_completed"
            if booking.rating:
                app_record.interview_rating = booking.rating
    elif new_status == "no_show":
        if booking.slot:
            booking.slot.is_available = True
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
    elif new_status == "cancelled":
        if booking.slot:
            booking.slot.is_available = True
        if app_record and app_record.pipeline_stage == "interview_scheduled":
            app_record.pipeline_stage = "test_completed"
            app_record.status = "test_completed"
            app_record.updated_at = datetime.utcnow()
    
    log_activity(current_user.id, "booking_update", f"Booking {booking_id} -> {new_status}")
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

        # enforce max 6 posts: delete oldest non-pinned extras
        total = Announcement.query.count()
        if total > 6:
            extras = Announcement.query.filter_by(is_pinned=False).order_by(
                Announcement.created_at.asc()
            ).limit(total - 6).all()
            for ex in extras:
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
