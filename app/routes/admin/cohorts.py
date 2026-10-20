"""Cohort management routes."""
from datetime import datetime, timezone
from flask import render_template, redirect, url_for, flash, request, Response
from flask_login import login_required, current_user
from app import db
from app.models.application import Application
from app.models.cohort import Cohort
from app.models.notification import Notification
from app.routes.admin import admin_bp
from app.utils.decorators import admin_required
from app.utils import outbox
from app.utils.csv_export import build_export


def _parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


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
        start_date=_parse_date(start) if start else None,
        end_date=_parse_date(end) if end else None,
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
    cohort.start_date = _parse_date(start) if start else None
    cohort.end_date = _parse_date(end) if end else None
    db.session.commit()
    flash("Cohort updated.", "success")
    return redirect(url_for("admin.cohorts"))


@admin_bp.route("/cohorts/<int:cohort_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_cohort(cohort_id):
    cohort = Cohort.query.get_or_404(cohort_id)
    name = cohort.name
    members = Application.query.filter_by(cohort_name=name).all()
    for app_record in members:
        app_record.cohort_name = None
        app_record.cohort_notes = None
        app_record.cohort_assigned_at = None
        app_record.updated_at = datetime.now(timezone.utc)
    db.session.delete(cohort)
    db.session.commit()
    count = len(members)
    flash(f"Cohort '{name}' deleted. {count} student(s) unassigned.", "success")
    return redirect(url_for("admin.cohorts"))


def _assign_to_cohort(cohort, app_ids, notes):
    assigned = 0
    for app_id in app_ids:
        try:
            app_id = int(app_id)
        except (TypeError, ValueError):
            continue
        app_record = Application.query.get(app_id)
        if app_record and app_record.pipeline_stage in ("accepted", "onboarding", "enrolled"):
            app_record.cohort_name = cohort.name
            app_record.cohort_notes = notes
            app_record.cohort_assigned_at = datetime.now(timezone.utc)
            if app_record.pipeline_stage == "accepted":
                app_record.pipeline_stage = "onboarding"
                app_record.status = "onboarding"
            app_record.updated_at = datetime.now(timezone.utc)
            assigned += 1
    return assigned


@admin_bp.route("/cohorts/<int:cohort_id>/assign", methods=["POST"])
@login_required
@admin_required
def assign_cohort(cohort_id):
    cohort = Cohort.query.get_or_404(cohort_id)
    app_ids = request.form.getlist("app_ids")
    if not app_ids:
        flash("No students selected.", "warning")
        return redirect(url_for("admin.cohorts"))
    assigned = _assign_to_cohort(cohort, app_ids, request.form.get("notes", "").strip())
    db.session.commit()
    flash(f"{assigned} student(s) assigned to {cohort.name}.", "success")
    return redirect(url_for("admin.cohorts"))


@admin_bp.route("/cohorts/assign-unassigned", methods=["POST"])
@login_required
@admin_required
def assign_unassigned():
    """Assign unassigned accepted/onboarding students from one form-driven POST."""
    cohort = Cohort.query.get_or_404(int(request.form.get("cohort_id", 0)))
    app_ids = request.form.getlist("app_ids")
    if not app_ids:
        flash("No students selected.", "warning")
        return redirect(url_for("admin.cohorts"))
    assigned = _assign_to_cohort(cohort, app_ids, "")
    db.session.commit()
    flash(f"{assigned} student(s) assigned to {cohort.name}.", "success")
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
        outbox.notify(app.user_id, title, message, url_for("student.announcements"))
        sent += 1
    db.session.commit()
    flash(f"Notification sent to {sent} student(s) in {cohort.name}.", "success")
    return redirect(url_for("admin.cohorts"))


@admin_bp.route("/cohorts/<int:cohort_id>/export")
@login_required
@admin_required
def export_cohort_csv(cohort_id):
    cohort = Cohort.query.get_or_404(cohort_id)
    members = Application.query.filter_by(cohort_name=cohort.name).order_by(
        Application.updated_at.desc()
    ).all()

    invalid = '<>:"/\\|?*'
    filename = "".join(
        "_" if ch in invalid or ch in " " else ch for ch in cohort.name
    ).strip("_") or "cohort"
    data, ext, mimetype = build_export(members, sheet_title=cohort.name)
    return Response(
        data,
        mimetype=mimetype,
        headers={
            "Content-Disposition": f"attachment; filename={filename}_roster.{ext}",
        },
    )
