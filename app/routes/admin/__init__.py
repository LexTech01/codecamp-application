"""Admin dashboard and management routes."""
from datetime import datetime, date, timedelta
from flask import (
    Blueprint, render_template, redirect, url_for, flash, request, jsonify,
)
from flask_login import login_required, current_user
from app import db
from app.models.user import User
from app.models.application import Application
from app.pipeline import pipeline
from app.models.assessment import Assessment, Question, TestAttempt
from app.models.interview import InterviewSlot, InterviewBooking, InterviewerProfile
from app.models.announcement import Announcement
from app.models.cohort import Cohort
import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app
from app.models.notification import Notification
from app.utils.decorators import admin_required
from app.utils.helpers import log_activity, create_notification

admin_bp = Blueprint("admin", __name__)

from app.routes.admin import applicants
from app.routes.admin import cohorts
from app.routes.admin import interviews
from app.routes.admin import content
from app.routes.admin import analytics
from app.routes.admin import users


@admin_bp.route("/dashboard")
@login_required
@admin_required
def dashboard():
    total_applicants = Application.query.filter_by(is_submitted=True).count()
    accepted = Application.query.filter(Application.pipeline_stage.in_(["accepted", "enrolled", "onboarding"])).count()
    rejected = Application.query.filter_by(pipeline_stage="rejected").count()
    interviews = InterviewBooking.query.filter_by(status="scheduled").count()
    test_passed = TestAttempt.query.filter_by(passed=True).count()
    test_total = TestAttempt.query.filter(TestAttempt.completed_at.isnot(None)).count()
    pass_rate = round((test_passed / test_total * 100) if test_total else 0, 1)
    acceptance_rate = round((accepted / total_applicants * 100) if total_applicants else 0, 1)
    recent_apps = Application.query.filter_by(is_submitted=True).order_by(
        Application.submitted_at.desc()
    ).limit(8).all()
    return render_template(
        "admin/dashboard.html",
        stats={
            "total_applicants": total_applicants,
            "accepted": accepted,
            "rejected": rejected,
            "interviews": interviews,
            "pass_rate": pass_rate,
            "acceptance_rate": acceptance_rate,
            "conversion_rate": round((interviews / total_applicants * 100) if total_applicants else 0, 1),
        },
        recent_apps=recent_apps,
    )
