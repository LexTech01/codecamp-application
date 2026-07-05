"""Application model for bootcamp recruitment pipeline."""
from datetime import datetime
from app import db

# Recruitment pipeline stages
PIPELINE_STAGES = [
    "submitted",
    "under_review",
    "test_invited",
    "test_completed",
    "interview_scheduled",
    "interview_completed",
    "accepted",
    "rejected",
    "waitlisted",
    "onboarding",
    "enrolled",
]

KANBAN_COLUMNS = {
    "new": ["submitted"],
    "test": ["test_invited", "test_completed"],
    "interview": ["interview_scheduled", "interview_completed"],
    "accepted": ["accepted", "onboarding", "enrolled"],
    "rejected": ["rejected", "waitlisted"],
}


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
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def status_label(self):
        labels = {
            "draft": "Draft",
            "submitted": "Submitted",
            "under_review": "Under Review",
            "test_invited": "Test Invited",
            "test_completed": "Test Completed",
            "interview_scheduled": "Interview Scheduled",
            "interview_completed": "Interview Completed",
            "accepted": "Accepted",
            "rejected": "Rejected",
            "waitlisted": "Waitlisted",
            "onboarding": "Onboarding",
            "enrolled": "Enrolled",
        }
        return labels.get(self.pipeline_stage, self.pipeline_stage.replace("_", " ").title())

    @property
    def progress_percent(self):
        stages = [
            "submitted", "test_invited", "test_completed",
            "interview_scheduled", "interview_completed", "accepted",
        ]
        if self.pipeline_stage in ("rejected", "waitlisted"):
            return 100
        if self.pipeline_stage in ("onboarding", "enrolled"):
            return 100
        try:
            idx = stages.index(self.pipeline_stage)
            return int((idx + 1) / len(stages) * 100)
        except ValueError:
            return 10 if self.is_submitted else 0

    def advance_stage(self, new_stage):
        self.pipeline_stage = new_stage
        self.status = new_stage
        self.updated_at = datetime.utcnow()


VALID_TRANSITIONS = {
    "draft": ["submitted"],
    "submitted": ["under_review", "test_invited", "rejected"],
    "under_review": ["test_invited", "rejected", "waitlisted"],
    "test_invited": ["test_completed", "rejected"],
    "test_completed": ["interview_scheduled", "accepted", "rejected"],
    "interview_scheduled": ["interview_completed", "rejected", "no_show"],
    "interview_completed": ["accepted", "rejected", "waitlisted"],
    "rejected": ["waitlisted"],
    "waitlisted": ["test_invited"],
    "accepted": ["onboarding"],
    "onboarding": ["enrolled"],
    "enrolled": ["enrolled"],
}

ADMIN_DECISION_TRANSITIONS = {
    "submitted": ["under_review", "test_invited", "rejected"],
    "under_review": ["test_invited", "rejected", "waitlisted"],
    "test_invited": ["test_completed", "rejected"],
    "test_completed": ["interview_scheduled", "accepted", "rejected", "waitlisted"],
    "interview_scheduled": ["rejected"],
    "interview_completed": ["accepted", "rejected", "waitlisted"],
    "accepted": ["onboarding"],
    "onboarding": ["enrolled"],
    "rejected": ["test_invited"],
    "waitlisted": ["test_invited"],
}


def can_advance_to(current_stage, target_stage):
    """Check if stage transition is valid."""
    return target_stage in VALID_TRANSITIONS.get(current_stage, [])
