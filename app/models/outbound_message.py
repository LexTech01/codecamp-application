"""Outbound message log.

Records every external message (currently email reminders) sent to a user so
that delivery is auditable and idempotent. ``dedupe_key`` is unique: a given
reminder for a given subject can only ever be claimed once.
"""
from datetime import datetime, timezone
from app import db


class OutboundMessage(db.Model):
    __tablename__ = "outbound_messages"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    recipient = db.Column(db.String(255), nullable=False)
    channel = db.Column(db.String(20), default="email", nullable=False)
    kind = db.Column(db.String(50), nullable=False, index=True)
    subject = db.Column(db.String(255))
    body = db.Column(db.Text)
    # Unique per reminder (e.g. "interview_reminder_24h:7") — guarantees a
    # reminder is never emailed twice, however often the sweep task runs.
    dedupe_key = db.Column(db.String(120), unique=True, nullable=False, index=True)
    status = db.Column(db.String(20), default="pending", nullable=False)
    error = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    sent_at = db.Column(db.DateTime)

    user = db.relationship("User", backref="outbound_messages")
