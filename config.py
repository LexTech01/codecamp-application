"""Cellusys — Application configuration."""
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "lisms-dev-secret-key-change-in-prod")

    # Database — set DATABASE_URL for PostgreSQL in production
    # Falls back to SQLite at instance/cellusys.db for local dev
    _db_url = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(BASE_DIR, "instance", "cellusys.db"),
    )
    if _db_url.startswith("postgresql://") and "sslmode=" not in _db_url:
        sep = "&" if "?" in _db_url else "?"
        _db_url += f"{sep}sslmode=require"
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flask-Migrate
    FLASK_MIGRATE_LOCK_PATH = os.path.join(BASE_DIR, "instance", "migrate.lock")

    # Upload
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "app", "static", "uploads")
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf", "doc", "docx", "xlsx", "csv", "mp4"}

    # Cloudinary (optional — configure when uploads use it)
    CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
    CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY", "")
    CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "")

    # Mail
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@cellusys.com")

    # Redis
    _redis_url = os.environ.get("REDIS_URL")
    REDIS_URL = _redis_url or "redis://localhost:6379/0"

    # Celery (disabled by default — requires REDIS_URL)
    CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", _redis_url or "")
    CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", _redis_url or "")
    RATELIMIT_ENABLED = os.environ.get("RATELIMIT_ENABLED", "true").lower() == "true"
    RATELIMIT_DEFAULT = "200 per day; 50 per hour"
    RATELIMIT_STORAGE_URL = os.environ.get("RATELIMIT_STORAGE_URL", "memory://")

    # Flask-Caching
    CACHE_TYPE = os.environ.get("CACHE_TYPE", "RedisCache" if _redis_url else "NullCache")
    CACHE_REDIS_URL = os.environ.get("CACHE_REDIS_URL", _redis_url or "redis://localhost:6379/2")
    CACHE_DEFAULT_TIMEOUT = 60

    # Flask-Session
    SESSION_TYPE = os.environ.get("SESSION_TYPE", "redis" if _redis_url else "filesystem")
    SESSION_REDIS_URL = os.environ.get("SESSION_REDIS_URL", _redis_url or "redis://localhost:6379/1")
    SESSION_PERMANENT = True
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = "cellusys:session:"

    # Session
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "true").lower() == "true"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 86400
