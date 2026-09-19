"""Outbound messaging helpers.

Wraps :func:`app.utils.helpers.send_mail` with an auditable, idempotent claim
step backed by :class:`app.models.outbound_message.OutboundMessage`. Callers
(reminder tasks) can therefore be retried safely without spamming users.
"""
import logging
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError

from app import db
from app.models.outbound_message import OutboundMessage

log = logging.getLogger("cellusys.messaging")


def claim_outbound_message(user_id, recipient, kind, dedupe_key, subject, body, channel="email"):
    """Claim the right to send one message.

    Returns a pending :class:`OutboundMessage` (committed, so the claim survives
    a crash) or ``None`` when the same ``dedupe_key`` has already been sent or
    is in flight. A previously *failed* message may be reclaimed for retry.
    """
    if not recipient:
        log.warning("Skipping outbound message %s: no recipient.", kind)
        return None

    existing = OutboundMessage.query.filter_by(dedupe_key=dedupe_key).first()
    if existing is not None:
        if existing.status != "failed":
            return None
        existing.status = "pending"
        existing.error = None
        existing.recipient = recipient
        db.session.commit()
        return existing

    msg = OutboundMessage(
        user_id=user_id,
        recipient=recipient,
        channel=channel,
        kind=kind,
        subject=subject,
        body=body,
        dedupe_key=dedupe_key,
        status="pending",
    )
    db.session.add(msg)
    try:
        db.session.commit()
    except IntegrityError:
        # Another process claimed it first — treat as already handled.
        db.session.rollback()
        return None
    return msg


def deliver_outbound_message(msg, text_body, html_body=None):
    """Send a claimed message and record the outcome. Never raises."""
    from app.utils.helpers import send_mail

    ok = send_mail(
        recipient=msg.recipient,
        subject=msg.subject,
        text_body=text_body,
        html_body=html_body,
    )
    if ok:
        msg.status = "sent"
        msg.sent_at = datetime.now(timezone.utc)
        msg.error = None
    else:
        msg.status = "failed"
        msg.error = "mail backend error"
    db.session.commit()
    return ok
