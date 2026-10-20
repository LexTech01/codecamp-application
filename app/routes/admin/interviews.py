"""Interview management routes."""
from datetime import datetime, date, timedelta, timezone
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.exc import StaleDataError
from app import db
from app.models.application import Application
from app.models.interview import InterviewSlot, InterviewBooking
from app.models.user import User
from app.routes.admin import admin_bp
from app.routes.admin.applicants import _apply_stage_change
from app.utils.decorators import admin_required
from app.utils import outbox


def _add_slot(interviewer_id, slot_date, start, end):
    """Create a slot unless it overlaps an existing slot on the same date."""
    if start >= end:
        return False
    for existing in InterviewSlot.query.filter_by(slot_date=slot_date).all():
        if start < existing.end_time and end > existing.start_time:
            return False
    db.session.add(
        InterviewSlot(
            interviewer_id=interviewer_id,
            slot_date=slot_date,
            start_time=start,
            end_time=end,
        )
    )
    return True


def _parse_time_range(value):
    if "-" not in value:
        return None, None
    start_str, end_str = value.split("-", 1)
    try:
        start = datetime.strptime(start_str.strip(), "%H:%M").time()
        end = datetime.strptime(end_str.strip(), "%H:%M").time()
    except ValueError:
        return None, None
    return start, end


def _parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


MAX_SLOTS_PER_DAY = 4


@admin_bp.route("/interviews")
@login_required
@admin_required
def interviews():
    slots = InterviewSlot.query.order_by(InterviewSlot.slot_date.desc()).limit(50).all()
    page = request.args.get("page", 1, type=int)
    bookings_pagination = (
        InterviewBooking.query
        .options(
            joinedload(InterviewBooking.candidate).joinedload(User.application),
            joinedload(InterviewBooking.slot),
        )
        .order_by(InterviewBooking.created_at.desc())
        .paginate(page=page, per_page=20, error_out=False)
    )
    return render_template(
        "admin/interviews.html",
        slots=slots,
        bookings=bookings_pagination.items,
        pagination=bookings_pagination,
    )


@admin_bp.route("/interviews/slots", methods=["POST"])
@login_required
@admin_required
def create_slots():
    """Create interview slots for a single date or as a weekly recurrence."""
    mode = request.form.get("mode", "single")
    times = request.form.getlist("times")
    if not times:
        flash("Select at least one time slot.", "error")
        return redirect(url_for("admin.interviews"))

    created = 0
    if mode == "recurring":
        start_str = request.form.get("start_date")
        if not start_str:
            flash("Start date is required for recurring slots.", "error")
            return redirect(url_for("admin.interviews"))
        start_date = _parse_date(start_str)
        if start_date is None or start_date <= date.today():
            flash("Start date must be in the future.", "error")
            return redirect(url_for("admin.interviews"))

        try:
            weeks = int(request.form.get("weeks", 4))
        except (TypeError, ValueError):
            weeks = 4
        weeks = max(1, min(weeks, 12))

        weekday_set = set()
        for wd in request.form.getlist("weekdays"):
            try:
                day = int(wd)
            except (TypeError, ValueError):
                continue
            if 0 <= day <= 6:
                weekday_set.add(day)
        if not weekday_set:
            flash("Select at least one weekday.", "error")
            return redirect(url_for("admin.interviews"))

        monday = start_date - timedelta(days=start_date.weekday())
        today = date.today()
        created_by_day = {}
        for w in range(weeks):
            for day in weekday_set:
                slot_day = monday + timedelta(weeks=w, days=day)
                if slot_day <= today:
                    continue
                existing_count = InterviewSlot.query.filter_by(slot_date=slot_day).count()
                for t in times:
                    if existing_count + created_by_day.get(slot_day, 0) >= MAX_SLOTS_PER_DAY:
                        break
                    start, end = _parse_time_range(t)
                    if start is None:
                        continue
                    if _add_slot(current_user.id, slot_day, start, end):
                        created += 1
                        created_by_day[slot_day] = created_by_day.get(slot_day, 0) + 1
        db.session.commit()
        if created:
            flash(f"{created} recurring time slot(s) created.", "success")
        else:
            flash("No slots were created. Check for duplicates, overlaps, past dates, or the 3-per-day limit.", "warning")
        return redirect(url_for("admin.interviews"))

    slot_date_str = request.form.get("slot_date")
    if not slot_date_str:
        flash("Date is required.", "error")
        return redirect(url_for("admin.interviews"))
    slot_date = _parse_date(slot_date_str)
    if slot_date is None or slot_date <= date.today():
        flash("Slot date must be in the future.", "error")
        return redirect(url_for("admin.interviews"))

    existing_count = InterviewSlot.query.filter_by(slot_date=slot_date).count()
    for t in times:
        if existing_count >= MAX_SLOTS_PER_DAY:
            break
        start, end = _parse_time_range(t)
        if start is None:
            continue
        existing = InterviewSlot.query.filter_by(
            slot_date=slot_date, start_time=start, end_time=end
        ).first()
        if existing:
            continue
        if _add_slot(current_user.id, slot_date, start, end):
            created += 1
            existing_count += 1
    db.session.commit()
    if created:
        flash(f"{created} time slot(s) created.", "success")
    else:
        flash("No slots were created. Check for duplicates, invalid times, or the 3-per-day limit.", "warning")
    return redirect(url_for("admin.interviews"))


@admin_bp.route("/interviews/booking/<int:booking_id>/update", methods=["POST"])
@login_required
@admin_required
def update_booking(booking_id):
    booking = InterviewBooking.query.get_or_404(booking_id)
    new_status = request.form.get("status", booking.status)
    result = request.form.get("result", "").strip()
    admin_notes = request.form.get("admin_notes", "").strip()

    app_record = Application.query.filter_by(user_id=booking.user_id).first()
    redirect_target = redirect(url_for("admin.interviews"))

    # ── Interview decision: passed / failed ───────────────────────────────
    decision_map = {"passed": "accepted", "failed": "rejected"}
    if result in decision_map:
        if booking.status != "approved":
            flash("Approve the interview before recording a decision.", "error")
            return redirect_target
        target = decision_map[result]
        if app_record:
            if target != app_record.pipeline_stage:
                reason = request.form.get("rejection_reason", "").strip()
                if not _apply_stage_change(app_record, target, rejection_reason=reason):
                    flash(
                        f"That outcome is not allowed for this applicant's current stage "
                        f"({app_record.status_label}).",
                        "error",
                    )
                    return redirect_target
            elif target == "rejected" and not app_record.rejection_reason:
                app_record.rejection_reason = (
                    request.form.get("rejection_reason", "").strip()
                    or "Not selected after interview"
                )
        else:
            flash("No application found for this candidate.", "error")
            return redirect_target
        booking.status = "completed"
        booking.admin_notes = admin_notes
        outbox.log(current_user.id, "booking_decision", f"Booking {booking_id} -> {result}")
        try:
            db.session.commit()
            flash(f"{booking.candidate.full_name} marked as {result}.", "success")
        except StaleDataError:
            db.session.rollback()
            flash("Conflict: another admin modified this booking. Please reload and try again.", "error")
        return redirect_target

    # ── Same-status save: notes only ───────────────────────────────────────
    if new_status == booking.status:
        booking.admin_notes = admin_notes
        db.session.commit()
        flash("Booking details updated.", "success")
        return redirect_target

    # ── Status transitions (approve / cancel) ─────────────────────────────
    valid_booked_transitions = {
        "scheduled": ["approved", "cancelled"],
        "approved": ["cancelled"],
        "completed": ["cancelled"],
        "cancelled": ["scheduled"],
    }
    if new_status not in valid_booked_transitions.get(booking.status, []):
        flash(f"Cannot change status from {booking.status} to {new_status}.", "error")
        return redirect_target

    booking.status = new_status
    booking.admin_notes = admin_notes

    if new_status == "approved":
        outbox.notify(
            booking.user_id,
            "Interview Approved",
            "Your interview has been approved by an admin.",
            url_for("student.interview_schedule"),
        )
    elif new_status == "cancelled":
        if booking.slot:
            booking.slot.is_available = True
        if app_record and app_record.pipeline_stage in ("interview_scheduled", "interview_completed"):
            _apply_stage_change(app_record, "test_completed")

    outbox.log(current_user.id, "booking_update", f"Booking {booking_id} -> {new_status}")
    try:
        db.session.commit()
        flash("Booking updated.", "success")
    except StaleDataError:
        db.session.rollback()
        flash("Conflict: another admin modified this booking. Please reload and try again.", "error")
    return redirect_target


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
