"""Celery app factory for background tasks."""
from celery import Celery


def make_celery(app_name=__name__):
    from config import Config
    return Celery(
        app_name,
        broker=Config.CELERY_BROKER_URL or "memory://",
        backend=Config.CELERY_RESULT_BACKEND or "memory://",
        include=["app.tasks.pdf_tasks"],
    )


celery = make_celery()
