"""Shared helper utilities."""
import json
import logging
import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import current_app
from app import db
from app.models.activity import ActivityLog
from app.models.notification import Notification


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]


def save_upload(file, subfolder=""):
    if not file or file.filename == "":
        return None
    if not allowed_file(file.filename):
        return None
    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], subfolder)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, filename)
    file.save(path)
    return f"uploads/{subfolder}/{filename}" if subfolder else f"uploads/{filename}"


def log_activity(user_id, action, details=None):
    entry = ActivityLog(user_id=user_id, action=action, details=details)
    db.session.add(entry)


def create_notification(user_id, title, message, link=None):
    notif = Notification(user_id=user_id, title=title, message=message, link=link)
    db.session.add(notif)
    return notif


def send_mail(recipient, subject, text_body, html_body=None):
    """Send an email, logging failures without raising.

    Under TESTING Flask-Mail appends to ``mail.outbox`` instead of sending.
    """
    from flask_mail import Message
    from app import mail

    try:
        msg = Message(subject=subject, recipients=[recipient])
        msg.body = text_body
        if html_body:
            msg.html = html_body
        mail.send(msg)
    except Exception:
        logging.getLogger(__name__).exception("Failed to send email to %s", recipient)


def parse_json_safe(data, default=None):
    if default is None:
        default = {}
    try:
        return json.loads(data) if data else default
    except (json.JSONDecodeError, TypeError):
        return default


def dumps_json(data):
    return json.dumps(data)
