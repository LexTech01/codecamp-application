"""Announcements and read tracking."""
from datetime import datetime, timezone
from app import db


class Announcement(db.Model):
    __tablename__ = "announcements"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_filename = db.Column(db.String(255), nullable=True)
    is_pinned = db.Column(db.Boolean, default=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    author = db.relationship("User", foreign_keys=[author_id])
    reads = db.relationship(
        "AnnouncementRead",
        backref="announcement",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )


class AnnouncementRead(db.Model):
    __tablename__ = "announcement_reads"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    announcement_id = db.Column(db.Integer, db.ForeignKey("announcements.id"), nullable=False)
    read_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (db.UniqueConstraint("user_id", "announcement_id"),)
