"""Applicant management routes."""
from io import StringIO
import csv
from datetime import datetime, timedelta, timezone
from flask import render_template, redirect, url_for, flash, request, Response
from flask_login import login_required, current_user
from sqlalchemy.orm.exc import StaleDataError
from app import db
from app.models.user import User
from app.models.application import Application
from app.pipeline import pipeline
from app.models.assessment import TestAttempt
from app.models.interview import InterviewBooking
from app.routes.admin import admin_bp
from app.utils.decorators import admin_required
from app.utils.helpers import log_activity, create_notification


def _apply_stage_change(app_record, new_stage, rejection_reason=None):
    """Transition an application to a new pipeline stage, applying side effects.

    Returns True only when the stage actually changed. Returns False when the
    transition is a no-op (same stage) or invalid. Does NOT commit — the caller
    decides when to persist.
    """
    if new_stage not in pipeline.STAGES:
        return False
    if new_stage == app_record.pipeline_stage:
        return False
    if not pipeline.can_advance(app_record.pipeline_stage, new_stage):
        return False

    old_stage = app_record.pipeline_stage

    if new_stage == "rejected":
        reason = rejection_reason or ""
        app_record.rejection_reason = reason
        app_record.can_reapply = False

    if new_stage == "waitlisted":
        app_record.can_reapply = True
        app_record.reapply_at = datetime.now(timezone.utc) + timedelta(days=30)

    app_record.pipeline_stage = new_stage
    app_record.status = new_stage
    app_record.version += 1
    app_record.updated_at = datetime.now(timezone.utc)

    notif_title, notif_message = pipeline.notify_content(old_stage, new_stage)
    if new_stage == "rejected":
        notif_message = app_record.rejection_reason or notif_message

    create_notification(
        app_record.user_id,
        notif_title,
        notif_message,
        url_for("student.dashboard"),
    )
    return True


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
        pipeline_stages=pipeline.STAGES,
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
    valid_next_stages = pipeline.available_actions(app_record.pipeline_stage)
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
    reason = request.form.get("rejection_reason", "")

    if new_stage == app_record.pipeline_stage:
        flash("Stage unchanged.", "info")
        return redirect(url_for("admin.applicant_detail", app_id=app_id))

    if new_stage not in pipeline.STAGES:
        flash("Invalid stage.", "error")
        return redirect(url_for("admin.applicant_detail", app_id=app_id))

    if not _apply_stage_change(app_record, new_stage, rejection_reason=reason):
        flash(f"Cannot transition from {app_record.pipeline_stage} to {new_stage}.", "error")
        return redirect(url_for("admin.applicant_detail", app_id=app_id))

    log_activity(current_user.id, "stage_update", f"App {app_id} -> {new_stage}")
    try:
        db.session.commit()
        flash(f"Stage updated to {app_record.status_label}.", "success")
    except StaleDataError:
        db.session.rollback()
        flash("Conflict: another admin modified this application. Please reload and try again.", "error")
    return redirect(url_for("admin.applicant_detail", app_id=app_id))


@admin_bp.route("/applicants/bulk-action", methods=["POST"])
@login_required
@admin_required
def bulk_action():
    app_ids = request.form.getlist("app_ids")
    action = request.form.get("action", "")
    redirect_args = {"q": request.form.get("q", ""), "stage": request.form.get("stage", "")}
    if not app_ids:
        flash("No applicants selected.", "warning")
        return redirect(url_for("admin.applicants", **redirect_args))

    if action.startswith("move_to_"):
        new_stage = action.replace("move_to_", "", 1)
        if new_stage not in pipeline.STAGES:
            flash("Invalid move target.", "error")
            return redirect(url_for("admin.applicants", **redirect_args))
        changed = 0
        for app_id in app_ids:
            app_record = Application.query.get(int(app_id))
            if app_record and _apply_stage_change(app_record, new_stage):
                changed += 1
        db.session.commit()
        flash(f"Moved {changed} of {len(app_ids)} applicant(s) to {pipeline.status_label(new_stage)}.", "success")
        return redirect(url_for("admin.applicants", **redirect_args))

    if action == "reject":
        reason = request.form.get("reason", "").strip()
        changed = 0
        for app_id in app_ids:
            app_record = Application.query.get(int(app_id))
            if app_record and _apply_stage_change(app_record, "rejected", rejection_reason=reason):
                changed += 1
        db.session.commit()
        flash(f"Rejected {changed} of {len(app_ids)} applicant(s).", "success")
        return redirect(url_for("admin.applicants", **redirect_args))

    flash("Unknown action.", "error")
    return redirect(url_for("admin.applicants", **redirect_args))


@admin_bp.route("/applicants/export.csv")
@login_required
@admin_required
def export_applicants():
    q = request.args.get("q", "")
    stage = request.args.get("stage", "")
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
    apps = query.order_by(Application.updated_at.desc()).all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "First Name", "Last Name", "Email", "Phone", "Program",
        "Country", "Location", "Stage", "Test Score", "Interview Rating",
        "Cohort", "Submitted At",
    ])
    for a in apps:
        writer.writerow([
            a.user.first_name,
            a.user.last_name,
            a.user.email,
            a.user.phone or "",
            a.field_of_study or "",
            a.country or "",
            a.applicant_location or "",
            a.pipeline_stage,
            a.test_score if a.test_score is not None else "",
            a.interview_rating if a.interview_rating is not None else "",
            a.cohort_name or "",
            a.submitted_at.strftime("%Y-%m-%d %H:%M:%S") if a.submitted_at else "",
        ])
    csv_bytes = output.getvalue().encode("utf-8")
    return Response(
        csv_bytes,
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=applicants.csv",
            "Content-Type": "text/csv; charset=utf-8",
        },
    )
