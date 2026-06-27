# Cellusys CodeCamp Recruitment Platform

A Flask recruitment platform for **Cellusys CodeCamp** — 100% scholarships for talented young adults in Accra, Ghana.

## Quick Start

```bash
cd ~/Desktop/cellusys
pip install -r requirements.txt
python3 run.py
```

Open http://localhost:5500

## Demo Accounts

| Role    | Email               | Password   |
|---------|---------------------|------------|
| Admin   | admin@cellusys.com  | admin123   |
| Student | student@cellusys.com| student123 |

## Reseed Database (optional)

Seed data runs only on first launch. To refresh announcements and demo content after theme updates:

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
