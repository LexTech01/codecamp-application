"""Authentication routes."""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from app import db, limiter
from app.forms.auth_forms import LoginForm, SignupForm, ForgotPasswordForm
from app.models.user import User
from app.models.application import Application
from app.utils.helpers import log_activity, create_notification

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard" if current_user.is_admin else "student.dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            log_activity(user.id, "login", f"User {user.email} logged in")
            next_page = request.args.get("next")
            if user.is_admin:
                return redirect(next_page or url_for("admin.dashboard"))
            return redirect(next_page or url_for("student.dashboard"))
        flash("Invalid email or password.", "error")
    return render_template("auth/login.html", form=form)


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("student.dashboard"))
    form = SignupForm()
    if form.validate_on_submit():
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
        db.session.commit()
        login_user(user)
        log_activity(user.id, "signup", f"New account: {user.email}")
        flash("Account created! Complete your application to get started.", "success")
        return redirect(url_for("student.application"))
    return render_template("auth/signup.html", form=form)


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        flash("If that email exists, a reset link has been sent.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/forgot_password.html", form=form)


@auth_bp.route("/logout")
def logout():
    if current_user.is_authenticated:
        log_activity(current_user.id, "logout")
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))
