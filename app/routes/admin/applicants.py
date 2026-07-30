"""Applicant management routes."""
from datetime import datetime, timedelta, timezone
from flask import render_template, redirect, url_for, flash, request
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
    if new_stage not in pipeline.STAGES:
        flash("Invalid stage.", "error")
        return redirect(url_for("admin.applicant_detail", app_id=app_id))

    if new_stage == app_record.pipeline_stage:
        flash("Stage unchanged.", "info")
        return redirect(url_for("admin.applicant_detail", app_id=app_id))
    
    if not pipeline.can_advance(app_record.pipeline_stage, new_stage):
        flash(f"Cannot transition from {app_record.pipeline_stage} to {new_stage}.", "error")
        return redirect(url_for("admin.applicant_detail", app_id=app_id))
    
    old_stage = app_record.pipeline_stage

    if new_stage == "rejected":
        reason = request.form.get("rejection_reason", "")
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
    log_activity(current_user.id, "stage_update", f"App {app_id} -> {new_stage}")
    try:
        db.session.commit()
        flash(f"Stage updated to {app_record.status_label}.", "success")
    except StaleDataError:
        db.session.rollback()
        flash("Conflict: another admin modified this application. Please reload and try again.", "error")
    return redirect(url_for("admin.applicant_detail", app_id=app_id))
