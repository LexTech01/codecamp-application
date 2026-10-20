#!/usr/bin/env bash
set -e
PORT="${PORT:-8000}"

CELERY_PID=""
cleanup() {
    if [ -n "$CELERY_PID" ] && kill -0 "$CELERY_PID" 2>/dev/null; then
        kill "$CELERY_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT

# Migrate and seed BEFORE accepting traffic so deploys never serve requests
# against a half-migrated database (or answer 500s while tables are created).
echo "[boot] Running database migrations + seed"
flask db upgrade
python3 -c 'from app import create_app, seed_database; app = create_app(); app.app_context().push(); seed_database()'
echo "[boot] Database migration + seed complete"

# On Render Free there is no free background-worker instance type, so the
# Celery worker + beat run inside this web process. Reminders pause whenever
# the service spins down and resume on the next request. Set
# RUN_CELERY_IN_WEB=true (see render.yaml) to enable.
if [ "${RUN_CELERY_IN_WEB,,}" = "true" ]; then
    echo "[boot] Starting Celery worker + beat (RUN_CELERY_IN_WEB=true)"
    celery -A app.celery_app.celery worker -B --loglevel=info \
        --concurrency=1 --max-tasks-per-child=200 \
        --schedule=/tmp/celerybeat-schedule &
    CELERY_PID=$!
fi

exec gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 \
    --timeout 120 --access-logfile - --error-logfile - --log-level info