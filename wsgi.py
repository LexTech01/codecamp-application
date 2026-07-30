"""WSGI entry point for production — Gunicorn discovers `app` here."""
import os
import logging
from dotenv import load_dotenv

load_dotenv()

from app import create_app

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
db_url = os.environ.get("DATABASE_URL", "(not set — using SQLite)")
logging.info("DATABASE_URL: %s", db_url[:60] + "..." if len(db_url) > 60 else db_url)

app = create_app()