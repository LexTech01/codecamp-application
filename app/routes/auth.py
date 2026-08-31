"""Authentication routes."""
import logging
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session
from flask_login import login_user, logout_user, current_user
from flask_mail import Message
from app import db, limiter, mail
from app.forms.auth_forms import LoginForm, SignupForm, ForgotPasswordForm
from app.models.user import User
from app.models.application import Application
from app.utils.helpers import log_activity, create_notification

logger = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__)


def _safe_next(target):
    """Return ``target`` only if it is a local path (prevents open redirects)."""
    if not target:
        return None
    if target.startswith("/") and not target.startswith("//"):
        return target
    return None


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute; 20 per hour")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard" if current_user.is_admin else "student.dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            session["_sess_v"] = user.session_version
            log_activity(user.id, "login", f"User {user.email} logged in")
            db.session.commit()
            next_page = _safe_next(request.args.get("next"))
            if user.is_admin:
                return redirect(next_page or url_for("admin.dashboard"))
            return redirect(next_page or url_for("student.dashboard"))
        flash("Invalid email or password.", "error")
    return render_template("auth/login.html", form=form)


@auth_bp.route("/signup", methods=["GET", "POST"])
@limiter.limit("10 per hour; 50 per day")
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("student.dashboard"))
    form = SignupForm()
    if form.validate_on_submit():
        try:
            user = User(
                email=form.email.data.lower().strip(),
                first_name=form.first_name.data.strip(),
                last_name=form.last_name.data.strip(),
                phone=form.phone.data,
                role="student",
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.flush()
            app_record = Application(user_id=user.id, status="draft", pipeline_stage="submitted")
            db.session.add(app_record)
            create_notification(
                user.id,
                "Welcome to Cellusys!",
                "Complete your application to begin the recruitment journey.",
                url_for("student.application"),
            )
            log_activity(user.id, "signup", f"New account: {user.email}")
            db.session.commit()
            login_user(user)
            session["_sess_v"] = user.session_version
            flash("Account created! Complete your application to get started.", "success")
            return redirect(url_for("student.application"))
        except Exception:
            db.session.rollback()
            logger.exception("Signup failed for %s", form.email.data)
            flash("An error occurred. Please try again.", "error")
    return render_template("auth/signup.html", form=form)


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("5 per hour; 20 per day")
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        user = User.query.filter_by(email=email).first()
        if user:
            token = user.generate_reset_token()
            db.session.commit()
            reset_url = url_for("auth.reset_password", token=token, _external=True)
            try:
                msg = Message(
                    subject="Cellusys CodeCamp — Password Reset",
                    recipients=[user.email],
                )
                msg.body = (
                    f"Hi {user.first_name},\n\n"
                    f"Click the link below to reset your password:\n{reset_url}\n\n"
                    f"This link expires in 1 hour.\n\n"
                    f"Cellusys CodeCamp"
                )
                msg.html = (
                    f"<h2>Password Reset</h2>"
                    f"<p>Hi {user.first_name},</p>"
                    f"<p>Click the button below to reset your password:</p>"
                    f"<a href=\"{reset_url}\" "
                    f"style=\"display:inline-block;padding:12px 24px;background:#004AAD;color:#fff;"
                    f"text-decoration:none;border-radius:6px;\">Reset Password</a>"
                    f"<p>This link expires in 1 hour.</p>"
                )
                mail.send(msg)
                logger.info("Password reset email sent to %s", user.email)
            except Exception:
                logger.exception("Failed to send password reset email to %s", user.email)
                flash("Could not send email. Please try again later.", "error")
                return redirect(url_for("auth.forgot_password"))
        else:
            logger.info("Password reset requested for unknown email: %s", email)
        flash("If that email exists, a reset link has been sent.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/forgot_password.html", form=form)


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
@limiter.limit("10 per hour")
def reset_password(token):
    from app.models.user import find_user_by_reset_token
    user = find_user_by_reset_token(token)
    if not user or not user.reset_token_valid:
        flash("Invalid or expired reset link.", "error")
        return redirect(url_for("auth.forgot_password"))

    from app.forms.auth_forms import PasswordForm
    form = PasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.clear_reset_token()
        user.session_version += 1  # invalidate all existing sessions
        db.session.commit()
        log_activity(user.id, "password_reset", "Password reset completed")
        flash("Password reset successfully. Please sign in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", form=form, token=token)


@auth_bp.route("/logout")
def logout():
    if current_user.is_authenticated:
        log_activity(current_user.id, "logout")
        db.session.commit()
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))