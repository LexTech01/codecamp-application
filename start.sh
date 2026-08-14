#!/usr/bin/env bash
set -e
PORT="${PORT:-8000}"

gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 \
    --timeout 120 --access-logfile - --error-logfile - --log-level info &
GUNICORN_PID=$!

set +e
flask db upgrade && python3 -c 'from app import create_app, seed_database; app = create_app(); app.app_context().push(); seed_database()'
BOOT_STATUS=$?
set -e

if [ "$BOOT_STATUS" -ne 0 ]; then
    echo "[boot] Database migration/seed FAILED - shutting down"
    kill "$GUNICORN_PID"
    wait "$GUNICORN_PID" 2>/dev/null
    exit 1
fi
wait "$GUNICORN_PID"
