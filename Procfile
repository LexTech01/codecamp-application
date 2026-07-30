web: gunicorn wsgi:app \
    --bind 0.0.0.0:$PORT \
    --workers 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info

worker: celery -A app.celery_app.celery worker --loglevel=info --concurrency=2