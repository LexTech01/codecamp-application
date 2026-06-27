"""Public routes: landing page."""
from flask import Blueprint, render_template, request, flash, redirect, url_for
from app import db
from app.models.announcement import Announcement
from app.models.contact import ContactMessage

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    blog_posts = Announcement.query.order_by(Announcement.is_pinned.desc(), Announcement.created_at.desc()).limit(3).all()
    stats = {
        "applicants": 1247,
        "acceptance_rate": 18,
        "placement_rate": 94,
        "cohorts": 12,
    }
    return render_template("landing.html", blog_posts=blog_posts, stats=stats)


@main_bp.route("/contact", methods=["POST"])
def contact():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    message = request.form.get("message", "").strip()
    if not name or not email or not message:
        flash("Please fill in all fields.", "error")
        return redirect(url_for("main.index") + "#contact")
    msg = ContactMessage(name=name, email=email, message=message)
    db.session.add(msg)
    db.session.commit()
    flash("Thank you! We will get back to you soon.", "success")
    return redirect(url_for("main.index") + "#contact")
