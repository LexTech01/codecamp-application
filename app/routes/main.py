"""Public routes: landing page and blog."""
import math
import os
from flask import (
    Blueprint, render_template, request, flash, redirect, url_for,
    current_app, send_from_directory,
)
from app import db, limiter
from app.models.announcement import Announcement
from app.models.contact import ContactMessage
from app.models.gallery import GalleryItem

main_bp = Blueprint("main", __name__)


@main_bp.route("/media/uploads/<path:filename>")
def uploaded_announcement_image(filename):
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    if os.path.isfile(os.path.join(upload_folder, filename)):
        return send_from_directory(upload_folder, filename)
    return send_from_directory(
        os.path.join(current_app.static_folder, "uploads"), filename
    )


@main_bp.route("/media/gallery/<path:filename>")
def gallery_image(filename):
    upload_folder = current_app.config["GALLERY_UPLOAD_FOLDER"]
    if os.path.isfile(os.path.join(upload_folder, filename)):
        return send_from_directory(upload_folder, filename)
    return send_from_directory(
        os.path.join(current_app.static_folder, "images", "gallery"), filename
    )


def _validate_image_filename(post):
    """Nullify image_filename when the file is missing on disk."""
    if post.image_filename:
        path = os.path.join(current_app.config["UPLOAD_FOLDER"], post.image_filename)
        if not os.path.exists(path):
            path = os.path.join(current_app.static_folder, "uploads", post.image_filename)
        if not os.path.exists(path):
            post.image_filename = None
    return post


def _featured_blog_posts():
    posts = (
        Announcement.query
        .order_by(Announcement.is_pinned.desc(), Announcement.created_at.desc())
        .limit(3)
        .all()
    )
    gallery_items = GalleryItem.query.order_by(GalleryItem.created_at.desc()).all()
    gallery_filenames = []
    seen_filenames = set()
    for item in gallery_items:
        if item.filename not in seen_filenames:
            gallery_filenames.append(item.filename)
            seen_filenames.add(item.filename)
        if len(gallery_filenames) == len(posts):
            break

    for index, post in enumerate(posts):
        if index < len(gallery_filenames):
            post.blog_image_url = url_for(
                "main.gallery_image", filename=gallery_filenames[index]
            )
        elif post.image_filename:
            _validate_image_filename(post)
            post.blog_image_url = (
                url_for("main.uploaded_announcement_image", filename=post.image_filename)
                if post.image_filename else None
            )
        else:
            post.blog_image_url = None
    return posts


@main_bp.route("/")
def index():
    blog_posts = _featured_blog_posts()
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
    gallery_images = (
        GalleryItem.query.order_by(GalleryItem.created_at.desc()).limit(6).all()
    )
    gallery = [g.to_dict() for g in gallery_images]
    return render_template(
        "landing.html", blog_posts=blog_posts, stats=stats, gallery=gallery
    )


@main_bp.route("/blog/<int:id>")
def blog_detail(id):
    post = Announcement.query.get_or_404(id)
    featured_posts = _featured_blog_posts()
    featured_post = next((item for item in featured_posts if item.id == post.id), None)
    if featured_post is not None:
        post_image_url = featured_post.blog_image_url
    else:
        _validate_image_filename(post)
        post_image_url = (
            url_for("main.uploaded_announcement_image", filename=post.image_filename)
            if post.image_filename else None
        )
    all_posts = (
        Announcement.query
        .filter(Announcement.id != id)
        .order_by(Announcement.created_at.desc())
        .all()
    )
    featured_images = {item.id: item.blog_image_url for item in featured_posts}
    for p in all_posts:
        _validate_image_filename(p)
        p.blog_image_url = featured_images.get(p.id) or (
            url_for("main.uploaded_announcement_image", filename=p.image_filename)
            if p.image_filename else None
        )
    read_time = max(1, math.ceil(len(post.content.split()) / 200))
    return render_template(
        "blog/detail.html",
        post=post,
        post_image_url=post_image_url,
        all_posts=all_posts,
        read_time=read_time,
    )


@main_bp.route("/gallery")
def gallery():
    items = GalleryItem.query.order_by(GalleryItem.created_at.desc()).all()
    images = [i.to_dict() for i in items]
    return render_template("gallery.html", images=images)


@main_bp.route("/privacy")
def privacy_policy():
    return render_template("privacy.html")


@main_bp.route("/terms")
def terms_of_service():
    return render_template("terms.html")


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
