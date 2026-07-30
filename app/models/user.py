"""User model with authentication support."""
import secrets
from datetime import datetime, timezone, timedelta
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
from app import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    role = db.Column(db.String(20), default="student")
    phone = db.Column(db.String(30))
    avatar = db.Column(db.String(255), default="default-avatar.svg")
    bio = db.Column(db.Text)
    theme = db.Column(db.String(10), default="dark")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    reset_token = db.Column(db.String(128), unique=True, nullable=True)
    reset_token_expires_at = db.Column(db.DateTime, nullable=True)

    application = db.relationship("Application", backref="user", uselist=False, lazy=True)
    notifications = db.relationship("Notification", backref="user", lazy="dynamic")
    test_attempts = db.relationship("TestAttempt", backref="user", lazy="dynamic")
    interview_bookings = db.relationship("InterviewBooking", backref="candidate", lazy="dynamic")
    interviewer_profile = db.relationship("InterviewerProfile", backref="user", uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256")

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_reset_token(self):
        self.reset_token = secrets.token_urlsafe(48)
        self.reset_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        return self.reset_token

    @property
    def reset_token_valid(self):
        if not self.reset_token or not self.reset_token_expires_at:
            return False
        return datetime.now(timezone.utc) < self.reset_token_expires_at

    def clear_reset_token(self):
        self.reset_token = None
        self.reset_token_expires_at = None

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def is_admin(self):
        return self.role == "admin"

    def __repr__(self):
        return f"<User {self.email}>"
