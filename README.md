# Cellusys CodeCamp Recruitment Platform

A Flask recruitment platform for **Cellusys CodeCamp** — 100% scholarships for talented young adults in Accra, Ghana.

## Quick Start

```bash
cd ~/Desktop/cellusys-application
pip install -r requirements.txt
python3 run.py
```

Open http://localhost:5555

The local `.env` already sets `FLASK_DEBUG=1`, so `run.py` runs in debug mode locally.

## Demo Accounts (local development only)

Demo accounts are seeded **only** in debug mode or when `SEED_DEMO=1`. They are
never created on a production database, so the credentials below are safe to
publish.

| Role    | Email               | Password   |
|---------|---------------------|------------|
| Admin   | admin@cellusys.com  | admin123   |
| Student | student@cellusys.com| student123 |

## Production requirements

Production (Render/Gunicorn) fails fast at startup if any of these are missing,
instead of silently degrading:

- `SECRET_KEY` — random value (forgeable sessions otherwise)
- `DATABASE_URL` — PostgreSQL/Supabase URL (SQLite fallback is disabled outside debug)

## Reseed Database (optional)

Core content (assessment, questions, announcements, cohorts) is seeded on the
first boot in any environment. Demo users and interview slots are added only
when running in debug mode or with `SEED_DEMO=1`. To refresh everything after
theme updates:

```bash
rm instance/cellusys.db
python3 run.py
```

## Location & Contact

- **CodeCamp GH:** Musuku Roundabout, Accra, Ghana
- **Head Office:** Cellusys Ltd, 7 Bachelors Walk, Dublin D01NH93, Ireland
- **Phone:** +233 24 123 4567
- **Web:** https://www.cellusys.com

## Programs

- Software Engineering (9 months)
- Networking and Telecom (3 months track)

## Assets

Images and video are sourced from the original Cellusys CodeCamp startup site (`codecamp-application/assets`).

## Stack

Flask, Jinja2, SQLAlchemy, Flask-Login, SQLite, Vanilla JS, Custom CSS (Poppins / Inter / Share Tech, Cellusys blue `#004AAD`)
