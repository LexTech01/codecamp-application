"""WSGI entry point for production — Gunicorn discovers `app` here."""
import os
import logging
from urllib.parse import urlsplit, urlunsplit
from dotenv import load_dotenv

load_dotenv()

from app import create_app

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def _redact_db_url(url):
    """Mask the password in a connection string before logging."""
    if "://" not in url:
        return url
    parts = urlsplit(url)
    if not parts.password:
        return url
    host = parts.hostname or ""
    if parts.port:
        host = f"{host}:{parts.port}"
    user = f"{parts.username}:" if parts.username else ""
    return urlunsplit((parts.scheme, f"{user}***@{host}", parts.path, parts.query, parts.fragment))


db_url = os.environ.get("DATABASE_URL", "(not set — using SQLite)")
logging.info("DATABASE_URL: %s", _redact_db_url(db_url) if db_url != "(not set — using SQLite)" else db_url)
if db_url != "(not set — using SQLite)" and "pooler.supabase.com" in db_url and not db_url.split("://", 1)[-1].split("@", 1)[-1].startswith("aws-"):
    logging.warning(
        "Supabase pooler hostname format is out of date. "
        "The old 'db.<ref>.pooler.supabase.com' host is retired and will NOT resolve. "
        "Use: postgresql://postgres.<PROJECT_REF>:<PASSWORD>@aws-<N>-<REGION>.pooler.supabase.com:5432/postgres"
    )

app = create_app()
