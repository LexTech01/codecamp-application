"""Celery app factory for background tasks."""
from celery import Celery

_app = None


def _get_app():
    """Lazily build (once) the Flask app used to give tasks an app context."""
    global _app
    if _app is None:
        from app import create_app

        _app = create_app()
    return _app


def make_celery(app_name=__name__):
    from config import Config

    celery = Celery(
        app_name,
        broker=Config.CELERY_BROKER_URL or "memory://",
        backend=Config.CELERY_RESULT_BACKEND or "memory://",
        include=["app.tasks.reminders"],
    )
    celery.conf.update(
        timezone="UTC",
        enable_utc=True,
        beat_schedule={
            "run-due-reminders": {
                "task": "app.tasks.reminders.run_due_reminders",
                "schedule": float(Config.REMINDER_SWEEP_SECONDS),
            },
        },
    )

    class ContextTask(celery.Task):
        """Run every task inside a Flask application context."""

        abstract = True

        def __call__(self, *args, **kwargs):
            with _get_app().app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


celery = make_celery()
