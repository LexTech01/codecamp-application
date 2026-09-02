"""Flask application factory."""
import logging
import os
import secrets
import sentry_sdk
from flask import Flask, jsonify
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from flask_mail import Mail
from flask_session import Session as FlaskSession
from flask_caching import Cache
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config


db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"
limiter = Limiter(key_func=get_remote_address)
csrf = CSRFProtect()
mail = Mail()
flask_session = FlaskSession()
cache = Cache()


def create_app(config_class=Config, config_override=None):
    app = Flask(__name__)
    app.config.from_object(config_class)
    if config_override:
        app.config.update(config_override)

    # ── Production safety guards ────────────────────────────────────────
    # Fail loudly instead of running with a forgeable secret key or an
    # ephemeral SQLite database on disk (data would be lost on redeploy).
    _secret = app.config.get("SECRET_KEY")
    if not _secret:
        if app.debug or app.testing:
            # Ephemeral dev key — sessions reset on every restart, which is
            # acceptable for local development but must never happen in prod.
            app.config["SECRET_KEY"] = secrets.token_hex(32)
        else:
            raise RuntimeError(
                "SECRET_KEY must be set to a random value in production "
                "(e.g. via the SECRET_KEY environment variable)."
            )

    if (
        not app.debug
        and not app.testing
        and str(app.config.get("SQLALCHEMY_DATABASE_URI", "")).startswith("sqlite")
    ):
        raise RuntimeError(
            "DATABASE_URL must be set to a PostgreSQL database in production; "
            "the SQLite fallback is only allowed in debug/testing mode."
        )

    # Never run the Werkzeug interactive debugger against a production DB: it
    # exposes a remote-code-execution console.
    if (
        app.debug
        and not app.testing
        and (
            os.environ.get("FLASK_ENV") == "production"
            or str(app.config.get("SQLALCHEMY_DATABASE_URI", "")).startswith("postgresql")
        )
    ):
        raise RuntimeError(
            "Debug mode must not be enabled against a production/PostgreSQL database."
        )

    # Rate limiting is effectively useless (and bypassable per worker) without
    # a shared storage backend. Require Redis in production.
    if (
        not app.debug
        and not app.testing
        and str(app.config.get("RATELIMIT_STORAGE_URL", "")).startswith("memory")
    ):
        raise RuntimeError(
            "RATELIMIT_STORAGE_URL must be set to a shared backend (e.g. Redis) "
            "in production; the in-memory limiter does not work across workers."
        )

    # ── Logging ─────────────────────────────────────────────────────
    log_level = logging.DEBUG if app.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    app.logger.setLevel(log_level)
    app.logger.info("Application starting")

    # ── ProxyFix — trust nginx forwarding headers ─────────────────────
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # ── Sentry ──────────────────────────────────────────────────────
    sentry_dsn = os.environ.get("SENTRY_DSN")
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            traces_sample_rate=0.1,
            profiles_sample_rate=0.05,
            enable_tracing=True,
        )
        app.logger.info("Sentry initialized")
    else:
        app.logger.debug("SENTRY_DSN not set — error tracking disabled")

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(os.path.join(app.root_path, "..", "instance"), exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    limiter.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    flask_session.init_app(app)
    cache.init_app(app)

    from app.models.user import User
    from flask import session

    @login_manager.user_loader
    def load_user(user_id):
        user = User.query.get(int(user_id))
        if user is None:
            return None
        # Invalidate sessions after a password reset (session_version bump).
        if session.get("_sess_v") != user.session_version:
            return None
        # Reject deactivated accounts (see admin user management).
        if not user.is_active:
            return None
        return user

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
            _uid = current_user.id
            _key = f"sidebar:{_uid}"
            _data = cache.get(_key)
            if _data is None:
                unread = Notification.query.filter_by(user_id=_uid, is_read=False).count()
                notifications = Notification.query.filter_by(user_id=_uid).order_by(Notification.created_at.desc()).limit(5).all()
                activities = ActivityLog.query.filter_by(user_id=_uid).order_by(ActivityLog.created_at.desc()).limit(5).all()
                cache.set(_key, (unread, notifications, activities), timeout=15)
            else:
                unread, notifications, activities = _data
        return dict(
            unread_notifications=unread,
            sidebar_notifications=notifications,
            sidebar_activities=activities
        )

    @app.after_request
    def add_security_headers(response):
        from flask import request
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com "
            "https://unpkg.com https://fonts.googleapis.com; "
            "font-src 'self' data: https://cdnjs.cloudflare.com https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "frame-src https://www.google.com; "
            "connect-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none'"
        )
        if request.is_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    @app.before_request
    def log_request_start():
        from flask import request
        if request.path.startswith("/static/"):
            return
        app.logger.debug("%s %s", request.method, request.path)

    @app.after_request
    def log_request_end(response):
        from flask import request
        if request.path.startswith("/static/"):
            return response
        app.logger.debug("%s %s → %s", request.method, request.path, response.status_code)
        return response

    @app.errorhandler(500)
    def handle_500(e):
        from flask import request, render_template
        app.logger.error("Internal server error: %s", e)
        if request.path.startswith("/api/"):
            return jsonify({"error": "Internal server error"}), 500
        return render_template(
            "errors/error.html", code=500, title="Something went wrong",
            message="An unexpected error occurred. Please try again later.",
        ), 500

    @app.errorhandler(404)
    def handle_404(e):
        from flask import request, render_template
        if request.path.startswith("/api/"):
            return jsonify({"error": "Not found"}), 404
        return render_template(
            "errors/error.html", code=404, title="Page Not Found",
            message="The page you are looking for does not exist.",
        ), 404

    @app.errorhandler(429)
    def handle_429(e):
        from flask import request
        if request.path.startswith("/api/"):
            return jsonify({"error": "Too many attempts. Please slow down and try again later."}), 429
        return jsonify({"error": "Too many attempts. Please try again later."}), 429

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    return app


def seed_database(force=False):
    """Populate database with demo content on first run.

    Core content (assessment, questions, announcements, cohorts) is seeded
    once, in any environment. Demo user accounts (admin@cellusys.com) and
    their interview slots are only created in debug mode or when SEED_DEMO=1,
    so a production database never gets publicly-documented credentials.
    """
    from flask import current_app
    from app.models.user import User
    from app.data.puzzle_questions import PUZZLE_ASSESSMENT, PUZZLE_QUESTIONS
    from app.models.assessment import Assessment, Question
    from app.models.announcement import Announcement
    from app.models.interview import InterviewerProfile
    from werkzeug.security import generate_password_hash
    from datetime import date, datetime, timedelta, timezone

    create_demo_users = (
        force
        or current_app.debug
        or os.environ.get("SEED_DEMO", "").lower() in ("1", "true", "yes")
    )
    # Never seed publicly-documented demo accounts in a production deployment,
    # even if SEED_DEMO=1 is accidentally set.
    if os.environ.get("FLASK_ENV") == "production":
        create_demo_users = False

    # Seed gallery images (idempotent — only when the table is empty).
    from app.models.gallery import GalleryItem
    GALLERY_SEED = [
        # (filename, alt, category) in display order, newest first
        ("254096ab354947609897dbd30930edfc_joseph-enninful.jpg", "Mr. Joseph ( Networking and telecom trainer", "programs"),
        ("hero-img4.jpeg", "Campus Life 2", "campus"),
        ("image1.jpeg", "Students Collaborating", "campus"),
        ("image3.jpeg", "Graduation Ceremony", "campus"),
        ("telecom.jpeg", "Networking & Telecom Lab", "programs"),
        ("hero-img3.JPG", "Campus Life 1", "campus"),
        ("IMG_8393.JPG", "CodeCamp Event 6", "events"),
        ("software.jpeg", "Software Engineering Class", "programs"),
        ("IMG_8388.JPG", "CodeCamp Event 4", "events"),
        ("img5.JPG", "CodeCamp Event 5", "events"),
        ("IMG_8387.JPG", "CodeCamp Event 3", "events"),
        ("IMG_8386.JPG", "CodeCamp Event 2", "events"),
        ("IMG_8385.JPG", "CodeCamp Event 1", "events"),
    ]
    if GalleryItem.query.first() is None:
        _gallery_now = datetime.now(timezone.utc)
        db.session.add_all([
            GalleryItem(
                filename=f,
                alt=a,
                category=c,
                created_at=_gallery_now - timedelta(minutes=i),
            )
            for i, (f, a, c) in enumerate(GALLERY_SEED)
        ])
        db.session.commit()

    if Assessment.query.first() is not None or Announcement.query.first() is not None:
        # Content already seeded — only (optionally) add the demo accounts.
        if not create_demo_users or User.query.filter_by(email="admin@cellusys.com").first():
            return
        db.session.add_all([
            User(
                email="admin@cellusys.com",
                password_hash=generate_password_hash("admin123", method="pbkdf2:sha256"),
                first_name="Alexander",
                last_name="Winfred",
                role="admin",
                phone="+233 24 123 4567",
                bio="Lead Recruitment Officer at Cellusys CodeCamp, Musuku Roundabout Accra, Ghana",
            ),
            User(
                email="student@cellusys.com",
                password_hash=generate_password_hash("student123", method="pbkdf2:sha256"),
                first_name="Jordan",
                last_name="Lee",
                role="student",
                phone="+233 24 123 4567",
            ),
        ])
        db.session.commit()
        return

    demo_admin_id = None
    if create_demo_users:
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
        demo_admin_id = admin.id

        interviewer_profile = InterviewerProfile(
            user_id=admin.id,
            title="Senior Technical Interviewer",
            bio="In-person interviews at Musuku Roundabout, Accra, Ghana. Software Engineering and Networking & Telecom tracks.",
            timezone="Africa/Accra",
        )
        db.session.add(interviewer_profile)

    assessment = Assessment(
        title=PUZZLE_ASSESSMENT["title"],
        description=PUZZLE_ASSESSMENT["description"],
        duration_minutes=PUZZLE_ASSESSMENT["duration_minutes"],
        pass_score=PUZZLE_ASSESSMENT["pass_score"],
        is_active=True,
    )
    db.session.add(assessment)
    db.session.flush()

    for idx, q in enumerate(PUZZLE_QUESTIONS, start=1):
        options = q["options"]
        correct = q.get("correct_answer")
        oimages = q.get("option_images") or [None] * len(options)
        q_obj = Question(
            assessment_id=assessment.id,
            question_text=q["text"],
            options=list(options),
            option_a=options[0] if len(options) >= 1 else None,
            option_b=options[1] if len(options) >= 2 else None,
            option_c=options[2] if len(options) >= 3 else None,
            option_d=options[3] if len(options) >= 4 else None,
            option_images=oimages,
            question_image=q.get("question_image"),
            correct_answer=correct,
            points=10,
            order_num=idx,
        )
        db.session.add(q_obj)

    announcements = [
        Announcement(
            title="Welcome to Cellusys CodeCamp",
            content="Cellusys CodeCamp offers 100% scholarships for talented young adults at Musuku Roundabout, Accra, Ghana. Complete your application to join Software Engineering or Networking and Telecom tracks.",
            is_pinned=True,
            author_id=demo_admin_id,
        ),
        Announcement(
            title="Program Duration & Attendance",
            content="The program lasts 9 months for coding (3 months for networking/telecom track). Selected students attend in-person classes three times per week.",
            is_pinned=False,
            author_id=demo_admin_id,
        ),
        Announcement(
            title="Aptitude Test Guidelines",
            content="Ensure stable internet, quiet environment, and 45 minutes uninterrupted time for your assessment. Pass the test and interview to receive your scholarship.",
            is_pinned=False,
            author_id=demo_admin_id,
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

    # Create interview slots for the next 14 days (demo interviewer only)
    if create_demo_users:
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
                            interviewer_id=demo_admin_id,
                            slot_date=slot_day,
                            start_time=start,
                            end_time=end,
                        )
                    )

    db.session.commit()
