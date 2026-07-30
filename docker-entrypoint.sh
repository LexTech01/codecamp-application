#!/bin/bash
set -e

# Trap SIGTERM for graceful shutdown
cleanup() {
    echo "Shutting down..."
    kill -TERM "$nginx_pid" 2>/dev/null || true
    kill -TERM "$gunicorn_pid" 2>/dev/null || true
    wait "$gunicorn_pid" 2>/dev/null || true
    echo "Shutdown complete"
}
trap cleanup SIGTERM SIGINT

# Apply database migrations
echo "Running database migrations..."
flask db upgrade

# Seed demo data (only on fresh DB)
echo "Seeding database..."
python3 -c "
from app import create_app, seed_database
app = create_app()
with app.app_context():
    seed_database()
"

# Start nginx
nginx -g "daemon off;" &
nginx_pid=$!

# Start Gunicorn
echo "Starting Gunicorn..."
gunicorn wsgi:app \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - &
gunicorn_pid=$!

# Wait for any child to exit, then forward signal
wait -n
exit $?