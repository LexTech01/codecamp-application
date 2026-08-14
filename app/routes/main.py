"""Public routes: landing page and blog."""
import math
import os
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from app import db, limiter
from app.models.announcement import Announcement
from app.models.contact import ContactMessage

main_bp = Blueprint("main", __name__)


def _validate_image_filename(post):
    """Nullify image_filename when the file is missing on disk."""
    if post.image_filename:
        path = os.path.join(current_app.config["UPLOAD_FOLDER"], post.image_filename)
        if not os.path.exists(path):
            post.image_filename = None
    return post


@main_bp.route("/")
def index():
    blog_posts = Announcement.query.order_by(Announcement.is_pinned.desc(), Announcement.created_at.desc()).limit(3).all()
    for p in blog_posts:
        _validate_image_filename(p)
    from app.models.user import User
    from app.models.application import Application
    total_applicants = User.query.filter_by(role="student").count()
    accepted = Application.query.filter(
        Application.pipeline_stage.in_(["accepted", "onboarding", "enrolled"])
    ).count()
    stats = {
        "applicants": total_applicants or 1247,
        "acceptance_rate": 18,
        "placement_rate": 94,
        "cohorts": 12,
    }
    return render_template("landing.html", blog_posts=blog_posts, stats=stats)


@main_bp.route("/blog/<int:id>")
def blog_detail(id):
    post = Announcement.query.get_or_404(id)
    _validate_image_filename(post)
    all_posts = (
        Announcement.query
        .filter(Announcement.id != id)
        .order_by(Announcement.created_at.desc())
        .all()
    )
    for p in all_posts:
        _validate_image_filename(p)
    read_time = max(1, math.ceil(len(post.content.split()) / 200))
    return render_template("blog/detail.html", post=post, all_posts=all_posts, read_time=read_time)


@main_bp.route("/gallery")
def gallery():
    images = [
        {"file": "images/IMG_8385.JPG", "alt": "CodeCamp Event 1", "category": "events"},
        {"file": "images/IMG_8386.JPG", "alt": "CodeCamp Event 2", "category": "events"},
        {"file": "images/IMG_8387.JPG", "alt": "CodeCamp Event 3", "category": "events"},
        {"file": "images/IMG_8388.JPG", "alt": "CodeCamp Event 4", "category": "events"},
        {"file": "images/img5.JPG", "alt": "CodeCamp Event 5", "category": "events"},
        {"file": "images/IMG_8393.JPG", "alt": "CodeCamp Event 6", "category": "events"},
        {"file": "images/software.jpeg", "alt": "Software Engineering Class", "category": "programs"},
        {"file": "images/telecom.jpeg", "alt": "Networking & Telecom Lab", "category": "programs"},
        {"file": "images/hero-img3.JPG", "alt": "Campus Life 1", "category": "campus"},
        {"file": "images/hero-img4.jpeg", "alt": "Campus Life 2", "category": "campus"},
        {"file": "images/image1.jpeg", "alt": "Students Collaborating", "category": "campus"},
        {"file": "images/image3.jpeg", "alt": "Graduation Ceremony", "category": "campus"},
    ]
    return render_template("gallery.html", images=images)


@main_bp.route("/contact", methods=["POST"])
@limiter.limit("6 per minute; 60 per hour")
def contact():
    if request.form.get("type") == "newsletter":
        email = request.form.get("email", "").strip()
        if not email:
            flash("Please enter your email.", "error")
            return redirect(url_for("main.index") + "#newsletter")
        msg = ContactMessage(name="Newsletter Subscriber", email=email, message="Newsletter signup")
        db.session.add(msg)
        db.session.commit()
        flash("Thank you for subscribing!", "success")
        return redirect(url_for("main.index") + "#newsletter")
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
