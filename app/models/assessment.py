"""Assessment and test attempt models."""
from datetime import datetime, timezone
from app import db

MAX_TEST_ATTEMPTS = 3


class Assessment(db.Model):
    __tablename__ = "assessments"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    duration_minutes = db.Column(db.Integer, default=45)
    pass_score = db.Column(db.Float, default=70.0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    questions = db.relationship("Question", backref="assessment", lazy="dynamic", cascade="all, delete-orphan")
    attempts = db.relationship("TestAttempt", backref="assessment", lazy="dynamic")


class Question(db.Model):
    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey("assessments.id"), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    # Legacy fixed 4-option columns. New questions should use ``options`` (JSON).
    option_a = db.Column(db.String(500))  # made nullable; legacy questions only
    option_b = db.Column(db.String(500))
    option_c = db.Column(db.String(500))
    option_d = db.Column(db.String(500))
    # Variable-length options and images (JSON). When ``options`` is set it wins.
    options = db.Column(db.JSON)          # [str, ...]
    option_images = db.Column(db.JSON)    # [str|None, ...], aligned with options
    # Question-level image filename (relative to static/images/assessment/).
    question_image = db.Column(db.String(300))
    # 0-based index into ``options``/options_list(); NULL means unscored (answer not set).
    correct_answer = db.Column(db.Integer, nullable=True)
    points = db.Column(db.Integer, default=10)
    order_num = db.Column(db.Integer, default=0)

    def options_list(self):
        if self.options:
            return list(self.options)
        return [self.option_a, self.option_b, self.option_c, self.option_d]

    def option_images_list(self):
        if self.option_images:
            return list(self.option_images)
        return [None] * len(self.options_list())

    def to_dict(self):
        return {
            "id": self.id,
            "text": self.question_text,
            "options": self.options_list(),
            "image": self.question_image,
            "option_images": self.option_images_list(),
            "points": self.points,
        }


class TestAttempt(db.Model):
    __tablename__ = "test_attempts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    assessment_id = db.Column(db.Integer, db.ForeignKey("assessments.id"), nullable=False)
    answers = db.Column(db.Text)  # JSON: {question_id: selected_index}
    score = db.Column(db.Float, default=0)
    total_points = db.Column(db.Integer, default=0)
    earned_points = db.Column(db.Integer, default=0)
    passed = db.Column(db.Boolean, default=False)
    started_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime)
    time_taken_seconds = db.Column(db.Integer)

    def __repr__(self):
        return f"<TestAttempt user={self.user_id} score={self.score}>"
