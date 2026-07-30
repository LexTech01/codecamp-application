#!/bin/bash
set -e

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

# Start Gunicorn
echo "Starting Gunicorn..."
exec gunicorn wsgi:app \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -