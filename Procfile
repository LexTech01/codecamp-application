web: ./start.sh
worker: celery -A app.celery_app.celery worker -B --loglevel=info --concurrency=1 --max-tasks-per-child=200 --schedule=/tmp/celerybeat-schedule
