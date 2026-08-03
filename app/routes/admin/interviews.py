"""Interview management routes."""
from datetime import datetime, date, timedelta, timezone
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from app import db
from app.models.application import Application
from app.models.interview import InterviewSlot, InterviewBooking
from app.models.user import User
from app.routes.admin import admin_bp
from app.utils.decorators import admin_required
from app.utils.helpers import log_activity, create_notification


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
    db.session.commit()
    if created:
        flash(f"{created} time slot(s) created.", "success")
    else:
        flash("No slots were created. Check for duplicates or invalid times.", "warning")
    return redirect(url_for("admin.interviews"))


@admin_bp.route("/interviews/recurring", methods=["POST"])
@login_required
@admin_required
def create_recurring_slots():
    """Generate slots repeating weekly from a start date across a weekday set."""
    start_str = request.form.get("start_date")
    if not start_str:
        flash("Start date is required.", "error")
        return redirect(url_for("admin.interviews"))
    try:
        start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Invalid start date.", "error")
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

    times = request.form.getlist("times")
    if not times:
        flash("Select at least one time slot.", "error")
        return redirect(url_for("admin.interviews"))

    monday = start_date - timedelta(days=start_date.weekday())
    created = 0
    today = date.today()
    for w in range(weeks):
        for day in weekday_set:
            slot_day = monday + timedelta(weeks=w, days=day)
            if slot_day <= today:
                continue
            for t in times:
                start, end = _parse_time_range(t)
                if start is None:
                    continue
                if _add_slot(current_user.id, slot_day, start, end):
                    created += 1
    db.session.commit()
    if created:
        flash(f"{created} recurring time slot(s) created.", "success")
    else:
        flash("No slots were created. Check for duplicates, overlaps, or past dates.", "warning")
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
        if app_record and app_record.pipeline_stage in ("interview_scheduled", "interview_completed"):
            app_record.pipeline_stage = "test_completed"
            app_record.status = "test_completed"
            app_record.updated_at = datetime.now(timezone.utc)
    
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
