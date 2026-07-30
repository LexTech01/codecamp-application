web: flask db upgrade && python3 -c 'from app import create_app, seed_database; app = create_app(); app.app_context().push(); seed_database()' && gunicorn wsgi:app \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info

worker: celery -A app.celery_app.celery worker --loglevel=info --concurrency=2