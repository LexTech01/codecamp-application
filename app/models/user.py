"""User model with authentication support."""
from datetime import datetime
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
    role = db.Column(db.String(20), default="student")  # admin | student
    phone = db.Column(db.String(30))
    avatar = db.Column(db.String(255), default="default-avatar.svg")
    bio = db.Column(db.Text)
    theme = db.Column(db.String(10), default="dark")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    application = db.relationship("Application", backref="user", uselist=False, lazy=True)
    notifications = db.relationship("Notification", backref="user", lazy="dynamic")
    test_attempts = db.relationship("TestAttempt", backref="user", lazy="dynamic")
    interview_bookings = db.relationship("InterviewBooking", backref="candidate", lazy="dynamic")
    interviewer_profile = db.relationship("InterviewerProfile", backref="user", uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256")

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def is_admin(self):
        return self.role == "admin"

    def __repr__(self):
        return f"<User {self.email}>"
