"""Cohort management routes."""
import os
from datetime import datetime, timezone
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.application import Application
from app.models.cohort import Cohort
from app.models.notification import Notification
from app.routes.admin import admin_bp
from app.utils.decorators import admin_required
from app.utils.helpers import create_notification


@admin_bp.route("/cohorts")
@login_required
@admin_required
def cohorts():
    cohorts = Cohort.query.order_by(Cohort.start_date.desc(), Cohort.name).all()
    unassigned = Application.query.filter(
        Application.pipeline_stage.in_(["accepted", "onboarding", "enrolled"]),
        Application.cohort_name.is_(None),
    ).order_by(Application.updated_at.desc()).all()

    # Single query for all cohort members — replaces per-cohort N+1
    cohort_names = [c.name for c in cohorts]
    all_members = (
        Application.query
        .filter(Application.cohort_name.in_(cohort_names))
        .order_by(Application.updated_at.desc())
        .all()
    ) if cohort_names else []
    members_by_cohort = {}
    for m in all_members:
        members_by_cohort.setdefault(m.cohort_name, []).append(m)

    grouped = {}
    for c in cohorts:
        grouped[c.name] = {"cohort": c, "members": members_by_cohort.get(c.name, [])}
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
            app_record.cohort_assigned_at = datetime.now(timezone.utc)
            if app_record.pipeline_stage == "accepted":
                app_record.pipeline_stage = "onboarding"
                app_record.status = "onboarding"
            app_record.updated_at = datetime.now(timezone.utc)
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
    from flask import make_response, current_app
    from weasyprint import HTML

    cohort = Cohort.query.get_or_404(cohort_id)
    members = Application.query.filter_by(cohort_name=cohort.name).order_by(
        Application.updated_at.desc()
    ).all()
    html = render_template(
        "admin/cohort_pdf.html",
        cohort=cohort,
        members=members,
        today=datetime.now(timezone.utc),
    )

    broker = current_app.config.get("CELERY_BROKER_URL", "")
    if broker and broker != "memory://":
        from app.tasks.pdf_tasks import generate_cohort_pdf
        task = generate_cohort_pdf.delay(cohort_id)
        return redirect(url_for("admin.task_status", task_id=task.id))
    pdf = HTML(string=html).write_pdf()
    resp = make_response(pdf)
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["Content-Disposition"] = f'attachment; filename="{cohort.name.replace(" ", "_")}_roster.pdf"'
    return resp


@admin_bp.route("/task-status/<task_id>")
@login_required
@admin_required
def task_status(task_id):
    from celery.result import AsyncResult
    from app.celery_app import celery

    result = AsyncResult(task_id, app=celery)
    if result.state == "SUCCESS":
        return redirect(url_for("admin.download_pdf", filename=result.result["file"]))
    return render_template("admin/task_pending.html", task_id=task_id, state=result.state)


@admin_bp.route("/task-status/<task_id>/raw")
@login_required
@admin_required
def task_status_raw(task_id):
    from celery.result import AsyncResult
    from app.celery_app import celery
    from flask import jsonify

    result = AsyncResult(task_id, app=celery)
    resp = {"state": result.state}
    if result.state == "SUCCESS":
        resp["redirect"] = url_for("admin.download_pdf", filename=result.result["file"])
    return jsonify(resp)


@admin_bp.route("/download-pdf/<filename>")
@login_required
@admin_required
def download_pdf(filename):
    from flask import send_from_directory, current_app
    pdf_dir = current_app.config.get("PDF_EXPORT_DIR", os.path.join(current_app.root_path, "static", "exports"))
    return send_from_directory(pdf_dir, filename, as_attachment=True)
