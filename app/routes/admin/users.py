"""Admin user/staff management routes."""
from datetime import datetime, timezone
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.user import User
from app.routes.admin import admin_bp
from app.utils.decorators import admin_required
from app.utils.helpers import log_activity


@admin_bp.route("/users")
@login_required
@admin_required
def users():
    role = request.args.get("role", "")
    q = request.args.get("q", "")
    query = User.query
    if role in ("admin", "student"):
        query = query.filter_by(role=role)
    if q:
        query = query.filter(
            db.or_(
                User.first_name.ilike(f"%{q}%"),
                User.last_name.ilike(f"%{q}%"),
                User.email.ilike(f"%{q}%"),
            )
        )
    users_list = query.order_by(User.created_at.desc()).all()
    return render_template(
        "admin/users.html",
        users=users_list,
        role=role,
        q=q,
    )


@admin_bp.route("/users/<int:user_id>/role", methods=["POST"])
@login_required
@admin_required
def set_role(user_id):
    user = User.query.get_or_404(user_id)
    new_role = request.form.get("role")
    if new_role not in ("admin", "student"):
        flash("Invalid role.", "error")
        return redirect(url_for("admin.users"))
    if user.id == current_user.id and new_role != "admin":
        flash("You cannot demote your own account.", "error")
        return redirect(url_for("admin.users"))
    if user.role != new_role:
        old_role = user.role
        user.role = new_role
        log_activity(
            current_user.id, "role_change", f"User {user.id} {old_role} -> {new_role}"
        )
        db.session.commit()
        flash(f"{user.full_name} is now {'an admin' if new_role == 'admin' else 'a student'}.", "success")
    else:
        flash("Role unchanged.", "info")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/deactivate", methods=["POST"])
@login_required
@admin_required
def deactivate_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot deactivate your own account.", "error")
        return redirect(url_for("admin.users"))
    reason = request.form.get("reason", "").strip()
    if user.role == "admin":
        flash("Deactivate an admin's role to student first before deactivating the account.", "warning")
        return redirect(url_for("admin.users"))
    if user.is_active:
        user.is_active = False
        user.deactivated_at = datetime.now(timezone.utc)
        user.deactivated_reason = reason or None
        log_activity(current_user.id, "user_deactivated", f"User {user.id}: {reason or 'no reason'}")
        db.session.commit()
        flash(f"{user.full_name} has been deactivated.", "success")
    else:
        flash("Account is already deactivated.", "info")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/reactivate", methods=["POST"])
@login_required
@admin_required
def reactivate_user(user_id):
    user = User.query.get_or_404(user_id)
    if not user.is_active:
        user.is_active = True
        user.deactivated_at = None
        user.deactivated_reason = None
        log_activity(current_user.id, "user_reactivated", f"User {user.id}")
        db.session.commit()
        flash(f"{user.full_name} has been reactivated.", "success")
    else:
        flash("Account is already active.", "info")
    return redirect(url_for("admin.users"))
