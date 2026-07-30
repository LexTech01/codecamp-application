"""Interview scheduling models."""
from datetime import datetime, date, time, timezone
from app import db


class InterviewerProfile(db.Model):
    __tablename__ = "interviewer_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    title = db.Column(db.String(120))
    bio = db.Column(db.Text)
    timezone = db.Column(db.String(60), default="UTC")
    meeting_link = db.Column(db.String(255))


class InterviewSlot(db.Model):
    __tablename__ = "interview_slots"

    id = db.Column(db.Integer, primary_key=True)
    interviewer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    slot_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    interviewer = db.relationship("User", foreign_keys=[interviewer_id])
    booking = db.relationship("InterviewBooking", backref="slot", uselist=False)

    @property
    def formatted_time(self):
        return f"{self.start_time.strftime('%I:%M %p')} - {self.end_time.strftime('%I:%M %p')}"

    @property
    def formatted_date(self):
        return self.slot_date.strftime("%A, %B %d, %Y")


class InterviewBooking(db.Model):
    __tablename__ = "interview_bookings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    slot_id = db.Column(db.Integer, db.ForeignKey("interview_slots.id"), unique=True, nullable=False)
    status = db.Column(db.String(30), default="scheduled")  # scheduled, completed, cancelled, no_show
    notes = db.Column(db.Text)
    admin_notes = db.Column(db.Text)
    rating = db.Column(db.Integer)  # 1-5
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
