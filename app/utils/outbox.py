"""Outbound pipeline effects: audit-log rows and notifications.

These helpers append model rows to the current session (``ActivityLog`` and
``Notification``). They never commit — the caller owns the commit and the
``StaleDataError`` retry around it. This keeps the commit boundary inside the
routes and lets several side effects share one transaction.

Email is a separate concern: see :mod:`app.utils.email` (the single remote
seam) and :mod:`app.utils.messaging` (idempotent claims for scheduled sends).
"""
from app import db
from app.models.activity import ActivityLog
from app.models.notification import Notification


def log(user_id, action, details=None):
    """Append an audit-log entry to the session."""
    db.session.add(ActivityLog(user_id=user_id, action=action, details=details))


def notify(user_id, title, message, link=None):
    """Append a notification row to the session."""
    notif = Notification(user_id=user_id, title=title, message=message, link=link)
    db.session.add(notif)
    return notif


def transition(user_id, *, action, details=None, title=None, message=None, link=None):
    """Record one pipeline transition: an audit entry plus an optional notice.

    Appends the audit log for ``action`` and, when ``title``/``message`` are
    given, also appends a notification for ``user_id``. Nothing is committed.
    """
    log(user_id, action, details)
    if title or message:
        notify(user_id, title, message, link)