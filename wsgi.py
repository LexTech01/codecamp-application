"""WSGI entry point for production — Gunicorn discovers `app` here."""
import os
from dotenv import load_dotenv

load_dotenv()

from app import create_app

app = create_app()