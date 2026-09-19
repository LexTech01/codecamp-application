"""Shared helper utilities."""
import json
import logging
import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import current_app, url_for
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


RESEND_API_URL = "https://api.resend.com/emails"


def _send_via_resend(recipient, subject, text_body, html_body):
    """HTTPS delivery through Resend (works where outbound SMTP is blocked)."""
    import requests

    logger = logging.getLogger(__name__)
    api_key = current_app.config.get("RESEND_API_KEY")
    if not api_key:
        logger.error("RESEND_API_KEY is not set — cannot send email to %s", recipient)
        return False

    payload = {
        "from": current_app.config["EMAIL_FROM"],
        "to": [recipient],
        "subject": subject,
        "text": text_body,
    }
    if html_body:
        payload["html"] = html_body

    try:
        resp = requests.post(
            RESEND_API_URL,
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        if resp.status_code >= 400:
            logger.error("Resend API error %s for %s: %s", resp.status_code, recipient, resp.text[:500])
            return False
        return True
    except Exception:
        logger.exception("Failed to send email to %s via Resend", recipient)
        return False


def send_mail(recipient, subject, text_body, html_body=None):
    """Send an email via Resend, logging failures without raising.

    Returns True when the message was accepted by Resend, False otherwise.
    Under TESTING the call is suppressed (no network) and reports success.
    """
    if current_app.config.get("TESTING"):
        logging.getLogger(__name__).debug("TESTING: suppressed email to %s", recipient)
        return True
    return _send_via_resend(recipient, subject, text_body, html_body)


def resolve_assessment_image(filename):
    """Resolve a local assessment image filename to a static URL.

    Images live in ``app/static/images/assessment/`` (e.g.
    ``q3_question.jpg``, ``q1_opt0_potato.jpg``). Returns the URL path
    (``static/images/assessment/<filename>``) if the file exists, else ``None``.

    Idempotent: if ``filename`` is already a URL path (starts with ``/``) it is
    returned unchanged, so values stored in the DB can be passed through again.
    """
    if not filename:
        return None
    if isinstance(filename, str) and filename.startswith("/"):
        return filename
    folder = os.path.join(
        current_app.root_path, "static", "images", "assessment"
    )
    if not os.path.isfile(os.path.join(folder, filename)):
        return None
    return url_for("static", filename=f"images/assessment/{filename}")


def question_image_url(filename):
    return resolve_assessment_image(filename)


def calculate_score(earned, total, pass_score=70.0):
    """Compute percentage score and pass/fail against the threshold."""
    score = round((earned / total * 100) if total else 0, 1)
    passed = score >= pass_score
    return score, passed


def parse_json_safe(data, default=None):
    if default is None:
        default = {}
    try:
        return json.loads(data) if data else default
    except (json.JSONDecodeError, TypeError):
        return default


def dumps_json(data):
    return json.dumps(data)
