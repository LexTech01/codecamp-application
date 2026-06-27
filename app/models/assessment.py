"""Assessment and test attempt models."""
from datetime import datetime
from app import db


class Assessment(db.Model):
    __tablename__ = "assessments"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    duration_minutes = db.Column(db.Integer, default=45)
    pass_score = db.Column(db.Float, default=70.0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    questions = db.relationship("Question", backref="assessment", lazy="dynamic", cascade="all, delete-orphan")
    attempts = db.relationship("TestAttempt", backref="assessment", lazy="dynamic")


class Question(db.Model):
    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey("assessments.id"), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(500), nullable=False)
    option_b = db.Column(db.String(500), nullable=False)
    option_c = db.Column(db.String(500), nullable=False)
    option_d = db.Column(db.String(500), nullable=False)
    correct_answer = db.Column(db.Integer, nullable=False)  # 0-3 index
    points = db.Column(db.Integer, default=10)
    order_num = db.Column(db.Integer, default=0)

    def options_list(self):
        return [self.option_a, self.option_b, self.option_c, self.option_d]

    def to_dict(self):
        return {
            "id": self.id,
            "text": self.question_text,
            "options": self.options_list(),
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
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    time_taken_seconds = db.Column(db.Integer)

    def __repr__(self):
        return f"<TestAttempt user={self.user_id} score={self.score}>"
