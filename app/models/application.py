"""Application model for bootcamp recruitment pipeline."""
from datetime import datetime, timezone
from app import db
from app.pipeline import pipeline


class Application(db.Model):
    __tablename__ = "applications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)

    # Personal info
    date_of_birth = db.Column(db.String(20))
    age = db.Column(db.Integer)
    applicant_location = db.Column(db.String(120))
    campus_location = db.Column(db.String(120))
    referral_code = db.Column(db.String(120))
    gender = db.Column(db.String(20))
    nationality = db.Column(db.String(80))
    address = db.Column(db.Text)
    city = db.Column(db.String(80))
    country = db.Column(db.String(80))

    # Education
    education_level = db.Column(db.String(80))
    institution = db.Column(db.String(200))
    field_of_study = db.Column(db.String(120))
    graduation_year = db.Column(db.String(10))
    gpa = db.Column(db.String(10))

    # Experience & motivation
    programming_experience = db.Column(db.String(50))
    languages_known = db.Column(db.Text)
    portfolio_url = db.Column(db.String(255))
    linkedin_url = db.Column(db.String(255))
    github_url = db.Column(db.String(255))
    motivation = db.Column(db.Text)
    why_cellusys = db.Column(db.Text)
    career_goals = db.Column(db.Text)

    # Files
    resume_filename = db.Column(db.String(255))
    cover_letter_filename = db.Column(db.String(255))

    # Pipeline
    status = db.Column(db.String(30), default="draft")
    pipeline_stage = db.Column(db.String(30), default="submitted")
    admin_notes = db.Column(db.Text)
    test_score = db.Column(db.Float)
    interview_rating = db.Column(db.Integer)

    # Rejection & Appeal
    rejection_reason = db.Column(db.Text)
    can_reapply = db.Column(db.Boolean, default=False)
    reapply_at = db.Column(db.DateTime)

    # Test Retakes
    test_attempts = db.Column(db.Integer, default=0)
    last_test_attempt_date = db.Column(db.DateTime)

    # Onboarding
    onboarding_completed = db.Column(db.Boolean, default=False)
    cohort_name = db.Column(db.String(120))
    cohort_notes = db.Column(db.Text)
    cohort_assigned_at = db.Column(db.DateTime)

    # Multi-step form draft (JSON string)
    draft_data = db.Column(db.Text)
    current_step = db.Column(db.Integer, default=1)
    is_submitted = db.Column(db.Boolean, default=False)

    submitted_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    @property
    def status_label(self):
        return pipeline.status_label(self.pipeline_stage)

    @property
    def progress_percent(self):
        return pipeline.progress_percent(self.pipeline_stage)

    def advance_stage(self, new_stage):
        self.pipeline_stage = new_stage
        self.status = new_stage
        self.updated_at = datetime.now(timezone.utc)
