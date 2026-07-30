"""Content management routes: announcements and assessments."""
import os
import uuid
import logging
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models.announcement import Announcement
from app.models.assessment import Assessment
from app.routes.admin import admin_bp
from app.utils.decorators import admin_required

logger = logging.getLogger(__name__)


@admin_bp.route("/announcements", methods=["GET", "POST"])
@login_required
@admin_required
def manage_announcements():
    if request.method == "POST":
        image = request.files.get("image")
        filename = None
        if image and image.filename:
            allowed = set(current_app.config.get("ALLOWED_EXTENSIONS", []))
            ext = image.filename.rsplit('.', 1)[-1].lower()
            if ext in allowed:
                fname = secure_filename(image.filename)
                unique = f"{uuid.uuid4().hex}_{fname}"
                upload_path = current_app.config["UPLOAD_FOLDER"]
                os.makedirs(upload_path, exist_ok=True)
                image.save(os.path.join(upload_path, unique))
                filename = unique

        ann = Announcement(
            title=request.form.get("title"),
            content=request.form.get("content"),
            image_filename=filename,
            is_pinned=request.form.get("is_pinned") == "on",
            author_id=current_user.id,
        )
        db.session.add(ann)
        db.session.commit()

        total = Announcement.query.count()
        if total > 6:
            extras = Announcement.query.filter_by(is_pinned=False).order_by(
                Announcement.created_at.asc()
            ).limit(total - 6).all()
            for ex in extras:
                if ex.image_filename:
                    fp = os.path.join(current_app.config["UPLOAD_FOLDER"], ex.image_filename)
                    if os.path.exists(fp):
                        try:
                            os.remove(fp)
                        except OSError as e:
                            logger.warning("Failed to delete old announcement image %s: %s", fp, e)
                db.session.delete(ex)
            db.session.commit()

        flash("Announcement published.", "success")
        return redirect(url_for("admin.manage_announcements"))
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
    return render_template("admin/announcements.html", announcements=announcements)


@admin_bp.route('/announcements/<int:ann_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_announcement(ann_id):
    ann = Announcement.query.get_or_404(ann_id)
    if ann.image_filename:
        fp = os.path.join(current_app.config['UPLOAD_FOLDER'], ann.image_filename)
        if os.path.exists(fp):
            try:
                os.remove(fp)
            except OSError as e:
                logger.warning("Failed to delete announcement image %s: %s", fp, e)
    db.session.delete(ann)
    db.session.commit()
    flash('Announcement deleted.', 'success')
    return redirect(url_for('admin.manage_announcements'))


@admin_bp.route("/assessments")
@login_required
@admin_required
def assessments():
    assessments = Assessment.query.all()
    return render_template("admin/assessments.html", assessments=assessments)


@admin_bp.route("/assessments/create", methods=["GET", "POST"])
@login_required
@admin_required
def create_assessment():
    flash(
        "Aptitude assessments are preconfigured and cannot be created or edited from the admin panel.",
        "warning",
    )
    return redirect(url_for("admin.assessments"))


@admin_bp.route("/assessments/<int:assessment_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_assessment(assessment_id):
    flash(
        "Aptitude assessments are preconfigured and cannot be created or edited from the admin panel.",
        "warning",
    )
    return redirect(url_for("admin.assessments"))
