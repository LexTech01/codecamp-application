"""Cellusys — Application configuration."""
import json
import logging
import os
import re
import socket
import time
import urllib.request
from ipaddress import ip_address, IPv6Network
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
_log = logging.getLogger("cellusys.config")

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

_SUPABASE_DIRECT_RE = re.compile(
    r"^postgresql://(?P<user>[^:]+):(?P<password>[^@]+)@db\.(?P<ref>[^.]+)\.supabase\.co:5432/(?P<db>[^?]+)(?P<query>\?.*)?$"
)
_AWS_RANGES_URL = "https://ip-ranges.amazonaws.com/ip-ranges.json"
_AWS_RANGES_CACHE = os.path.join(BASE_DIR, "instance", "aws-ip-ranges.json")
_AWS_RANGES_TTL = 7 * 86400


def _aws_region_for_ipv6(addr):
    """Map an IPv6 address to its AWS region using ip-ranges.json (cached locally)."""
    try:
        if not os.path.exists(_AWS_RANGES_CACHE) or time.time() - os.path.getmtime(_AWS_RANGES_CACHE) > _AWS_RANGES_TTL:
            with urllib.request.urlopen(_AWS_RANGES_URL, timeout=10) as resp:
                data = json.load(resp)
            os.makedirs(os.path.dirname(_AWS_RANGES_CACHE), exist_ok=True)
            with open(_AWS_RANGES_CACHE, "w") as fh:
                json.dump(data, fh)
        else:
            with open(_AWS_RANGES_CACHE) as fh:
                data = json.load(fh)
        ip = ip_address(addr)
        for prefix in data.get("ipv6_prefixes", []):
            if ip in IPv6Network(prefix["ipv6_prefix"]):
                return prefix["region"]
    except Exception:
        pass
    return None


def _resolve_ipv6(host):
    """Resolve a host to an IPv6 address.

    Tries dnspython first (direct DNS query — works even where the system
    resolver mishandles AAAA records), then getaddrinfo as a fallback.
    """
    try:
        import dns.resolver

        answer = dns.resolver.resolve(host, "AAAA")
        if answer:
            return str(answer[0])
    except Exception:
        pass
    try:
        return socket.getaddrinfo(host, 5432, socket.AF_INET6)[0][4][0]
    except Exception:
        return None


def _pooler_host_that_resolves(region):
    for idx in range(4):
        host = f"aws-{idx}-{region}.pooler.supabase.com"
        try:
            socket.getaddrinfo(host, 5432)
            return host
        except Exception:
            continue
    return None


def rewrite_supabase_direct_url(url):
    """Convert a Supabase direct (IPv6-only) URI to the IPv4-compatible shared pooler.

    Supabase free-tier direct connections resolve only to IPv6, which is
    unreachable from Render. The pooler uses postgres.<ref> as username and an
    aws-<n>-<region> host; the region is derived from the project's own IPv6
    address. If anything fails, the original URL is returned untouched.
    """
    match = _SUPABASE_DIRECT_RE.match(url)
    if not match or match.group("user") != "postgres":
        return url
    ipv6 = _resolve_ipv6(f"db.{match.group('ref')}.supabase.co")
    region = _aws_region_for_ipv6(ipv6) if ipv6 else None
    if not region:
        return url
    host = _pooler_host_that_resolves(region)
    if not host:
        return url
    return (
        f"postgresql://postgres.{match.group('ref')}:{match.group('password')}"
        f"@{host}:5432/{match.group('db')}{match.group('query') or ''}"
    )


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "lisms-dev-secret-key-change-in-prod")

    # Database — set DATABASE_URL for PostgreSQL in production
    # Falls back to SQLite at instance/cellusys.db for local dev
    _db_url = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(BASE_DIR, "instance", "cellusys.db"),
    )
    # Supabase current format (2026):
    #   Direct:      postgresql://postgres:[PASS]@db.[REF].supabase.co:5432/postgres (IPv6 only)
    #   Shared pooler (IPv4 — use this on Render):
    #                 postgresql://postgres.[REF]:[PASS]@aws-[REGION].pooler.supabase.com:5432/postgres
    # Note: the old "db.[REF].pooler.supabase.com" hostname is retired — it will not resolve.
    if _db_url.startswith("postgresql://") and "sslmode=" not in _db_url:
        sep = "&" if "?" in _db_url else "?"
        _db_url += f"{sep}sslmode=require"
    _rewritten = rewrite_supabase_direct_url(_db_url)
    if _rewritten != _db_url:
        _log.info("Rewrote Supabase direct URI (IPv6-only) to IPv4 shared pooler host")
        _db_url = _rewritten
        if "sslmode=" not in _db_url:
            _db_url += "?sslmode=require"
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": int(os.environ.get("DB_POOL_SIZE", 5)),
        "max_overflow": int(os.environ.get("DB_MAX_OVERFLOW", 3)),
        "pool_pre_ping": True,
        "pool_recycle": int(os.environ.get("DB_POOL_RECYCLE", 300)),
    }

    # Flask-Migrate
    FLASK_MIGRATE_LOCK_PATH = os.path.join(BASE_DIR, "instance", "migrate.lock")

    # Google Sheets sync (optional — passed applicants are mirrored to a sheet)
    GOOGLE_SHEETS_ENABLED = os.environ.get(
        "GOOGLE_SHEETS_ENABLED", "false"
    ).lower() in ("1", "true", "yes")
    GOOGLE_SHEETS_SPREADSHEET_ID = os.environ.get("GOOGLE_SHEETS_SPREADSHEET_ID", "")
    GOOGLE_SHEETS_TAB = os.environ.get("GOOGLE_SHEETS_TAB", "")
    GOOGLE_SHEETS_CREDENTIALS_JSON = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_JSON", "")
    GOOGLE_SHEETS_CREDENTIALS_FILE = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_FILE", "")

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
    RATELIMIT_STORAGE_URL = os.environ.get("RATELIMIT_STORAGE_URL", _redis_url or "memory://")

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
