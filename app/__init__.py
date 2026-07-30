"""Flask application factory."""
import os
from flask import Flask, jsonify
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate

from config import Config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"
limiter = Limiter(key_func=get_remote_address)
csrf = CSRFProtect()


def create_app(config_class=Config, config_override=None):
    app = Flask(__name__)
    app.config.from_object(config_class)
    if config_override:
        app.config.update(config_override)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(os.path.join(app.root_path, "..", "instance"), exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    limiter.init_app(app)
    csrf.init_app(app)

    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.student import student_bp
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(student_bp, url_prefix="/student")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.context_processor
    def inject_globals():
        from flask_login import current_user
        unread = 0
        notifications = []
        activities = []
        if current_user.is_authenticated:
            from app.models.notification import Notification
            from app.models.activity import ActivityLog
            unread = Notification.query.filter_by(
                user_id=current_user.id, is_read=False
            ).count()
            notifications = Notification.query.filter_by(
                user_id=current_user.id
            ).order_by(Notification.created_at.desc()).limit(5).all()
            activities = ActivityLog.query.filter_by(
                user_id=current_user.id
            ).order_by(ActivityLog.created_at.desc()).limit(5).all()
        return dict(
            unread_notifications=unread,
            sidebar_notifications=notifications,
            sidebar_activities=activities
        )

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin"
        return response

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    return app


def seed_database():
    """Populate database with demo data on first run."""
    from app.models.user import User
    from app.models.assessment import Assessment, Question
    from app.models.announcement import Announcement
    from app.models.interview import InterviewerProfile
    from werkzeug.security import generate_password_hash
    from datetime import date, time, timedelta

    if User.query.filter_by(email="admin@cellusys.com").first():
        return

    admin = User(
        email="admin@cellusys.com",
        password_hash=generate_password_hash("admin123", method="pbkdf2:sha256"),
        first_name="Alexander",
        last_name="Winfred",
        role="admin",
        phone="+233 24 123 4567",
        bio="Lead Recruitment Officer at Cellusys CodeCamp, Musuku Roundabout Accra, Ghana",
    )
    student = User(
        email="student@cellusys.com",
        password_hash=generate_password_hash("student123", method="pbkdf2:sha256"),
        first_name="Jordan",
        last_name="Lee",
        role="student",
        phone="+233 24 123 4567",
    )
    db.session.add_all([admin, student])
    db.session.flush()

    InterviewerProfile(
        user_id=admin.id,
        title="Senior Technical Interviewer",
        bio="In-person interviews at Musuku Roundabout, Accra, Ghana. Software Engineering and Networking & Telecom tracks.",
        timezone="Africa/Accra",
    )

    assessment = Assessment(
        title="Cellusys Aptitude Assessment",
        description="Evaluate aptitude for Software Engineering and Networking & Telecom programs. Required for scholarship consideration.",
        duration_minutes=45,
        pass_score=70,
        is_active=True,
    )
    db.session.add(assessment)
    db.session.flush()

    questions_data = [
        # Logical Reasoning
        (
            "All roses are flowers. Some flowers fade quickly. Which of these is true?",
            [
                "All roses fade quickly",
                "Some roses may fade quickly",
                "No roses fade quickly",
                "Roses are not flowers",
            ],
            1,
            5,
        ),
        (
            "If you rearrange the letters 'OCDUET', you get a word that means:",
            ["A type of bird", "A place to learn", "A musical instrument", "A form of transport"],
            1,
            5,
        ),
        (
            "A farmer has 15 goats. All but 8 escape. How many does he have left?",
            ["7", "8", "15", "23"],
            1,
            5,
        ),
        (
            "Which word does NOT belong with the others?",
            ["Triangle", "Circle", "Square", "Rectangle"],
            1,
            5,
        ),
        (
            "If it takes 5 minutes to boil one egg, how many minutes does it take to boil 3 eggs together?",
            ["5", "10", "15", "20"],
            0,
            5,
        ),
        # Numerical Reasoning
        (
            "What number comes next? 2, 6, 18, 54, ?",
            ["72", "108", "162", "216"],
            2,
            5,
        ),
        (
            "A shirt costs £24 after a 20% discount. What was the original price?",
            ["£28", "£30", "£29", "£26"],
            1,
            5,
        ),
        (
            "How many sides does a hexagon have?",
            ["5", "6", "7", "8"],
            1,
            5,
        ),
        (
            "What is half of a quarter?",
            ["0.125", "0.25", "0.5", "0.75"],
            0,
            5,
        ),
        (
            "If a train leaves at 14:45 and arrives at 16:30, how many minutes is the journey?",
            ["105", "95", "115", "90"],
            0,
            5,
        ),
        # Verbal Reasoning
        (
            "Choose the word that is closest in meaning to 'BRIEF'",
            ["Short", "Long", "Bright", "Heavy"],
            0,
            5,
        ),
        (
            "Which word is the opposite of 'ANCIENT'?",
            ["Old", "Modern", "Rare", "Broken"],
            1,
            5,
        ),
        (
            "Complete the sentence: Water is to thirst as food is to ___",
            ["Drink", "Hunger", "Cook", "Plate"],
            1,
            5,
        ),
        (
            "Which of these is a proper noun?",
            ["city", "London", "river", "mountain"],
            1,
            5,
        ),
        (
            "Choose the odd one out:",
            ["Joy", "Happiness", "Sadness", "Delight"],
            2,
            5,
        ),
        # Pattern Recognition / General
        (
            "Which shape has no corners?",
            ["Square", "Triangle", "Circle", "Rectangle"],
            2,
            5,
        ),
        (
            "If you fold a piece of paper in half and then in half again, how many sections do you get?",
            ["2", "4", "6", "8"],
            1,
            5,
        ),
        (
            "How many months have 31 days?",
            ["5", "6", "7", "8"],
            2,
            5,
        ),
        (
            "Which number is the odd one out? 3, 5, 7, 8, 11",
            ["3", "5", "7", "8"],
            3,
            5,
        ),
        (
            "A clock shows 3:15. What is the angle between the hour and minute hand?",
            ["0°", "7.5°", "15°", "30°"],
            1,
            5,
        ),
    ]
    for text, options, correct, points in questions_data:
        db.session.add(
            Question(
                assessment_id=assessment.id,
                question_text=text,
                option_a=options[0],
                option_b=options[1],
                option_c=options[2],
                option_d=options[3],
                correct_answer=correct,
                points=points,
            )
        )

    announcements = [
        Announcement(
            title="Welcome to Cellusys CodeCamp",
            content="Cellusys CodeCamp offers 100% scholarships for talented young adults at Musuku Roundabout, Accra, Ghana. Complete your application to join Software Engineering or Networking and Telecom tracks.",
            is_pinned=True,
            author_id=admin.id,
        ),
        Announcement(
            title="Program Duration & Attendance",
            content="The program lasts 9 months for coding (3 months for networking/telecom track). Selected students attend in-person classes three times per week.",
            is_pinned=False,
            author_id=admin.id,
        ),
        Announcement(
            title="Aptitude Test Guidelines",
            content="Ensure stable internet, quiet environment, and 45 minutes uninterrupted time for your assessment. Pass the test and interview to receive your scholarship.",
            is_pinned=False,
            author_id=admin.id,
        ),
    ]
    db.session.add_all(announcements)

    # Seed default cohorts
    from app.models.cohort import Cohort
    base_date = date.today() + timedelta(days=60)
    db.session.add_all([
        Cohort(
            name="SE Cohort 2026",
            description="Software Engineering",
            start_date=base_date,
            end_date=base_date + timedelta(days=270),
        ),
        Cohort(
            name="NT Cohort 2026",
            description="Networking & Telecom",
            start_date=base_date,
            end_date=base_date + timedelta(days=90),
        ),
    ])

    # Create interview slots for the next 14 days
    from app.models.interview import InterviewSlot
    from datetime import time as dt_time

    time_ranges = [
        (dt_time(9, 0), dt_time(9, 30)),
        (dt_time(10, 0), dt_time(10, 30)),
        (dt_time(11, 0), dt_time(11, 30)),
        (dt_time(14, 0), dt_time(14, 30)),
        (dt_time(15, 0), dt_time(15, 30)),
        (dt_time(16, 0), dt_time(16, 30)),
    ]
    for day_offset in range(1, 15):
        slot_day = date.today() + timedelta(days=day_offset)
        if slot_day.weekday() < 5:  # weekdays only
            for start, end in time_ranges:
                db.session.add(
                    InterviewSlot(
                        interviewer_id=admin.id,
                        slot_date=slot_day,
                        start_time=start,
                        end_time=end,
                    )
                )

    db.session.commit()
