"""Scheduled email reminders (Celery beat).

A single sweep task handles three time-based rules:

* **interview reminders** — 24h and 2h before a scheduled interview
* **draft application nudges** — account created, application never submitted
* **test-not-taken reminders** — invited to the aptitude test, no attempt yet

Every send goes through :mod:`app.utils.messaging`, whose ``dedupe_key`` makes
the sweep idempotent: a reminder is never emailed twice, no matter how often
(or how many times) the task runs.

Interview slots are stored as naive local date/time. Ghana (Africa/Accra) is
UTC+0 year-round, so naive slot values are compared directly against naive UTC.
"""
import logging
from datetime import datetime, timedelta, timezone

from flask import current_app

from app import db
from app.celery_app import celery
from app.models.application import Application
from app.models.interview import InterviewSlot
from app.models.user import User
from app.utils.messaging import claim_outbound_message, deliver_outbound_message

log = logging.getLogger("cellusys.reminders")

LOCATION = "Cellusys Academy, Kwabenya Musuku Roundabout, Accra, Ghana"


def _now_utc():
    """Naive UTC — matches how DB datetimes are stored/compared."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _naive(value):
    if value is None:
        return None
    return value.replace(tzinfo=None) if value.tzinfo else value


def _send(user, kind, dedupe_key, subject, text_body, html_body):
    """Claim + deliver one email. Returns True when actually sent."""
    msg = claim_outbound_message(
        user_id=user.id,
        recipient=user.email,
        kind=kind,
        dedupe_key=dedupe_key,
        subject=subject,
        body=text_body,
    )
    if msg is None:
        return False
    return deliver_outbound_message(msg, text_body, html_body)


# ── Interview reminders ─────────────────────────────────────────────────

def _send_interview_reminder(user, slot, window):
    kind = f"interview_reminder_{window}"
    dedupe_key = f"{kind}:{slot.booking.id}"
    when = f"{slot.formatted_date} at {slot.formatted_time}"

    if window == "24h":
        subject = "Cellusys CodeCamp — Interview Reminder"
        lead = f"This is a reminder that your interview is scheduled for {when}."
    else:
        subject = "Cellusys CodeCamp — Interview Starting Soon"
        lead = f"Your interview starts in about 2 hours: {when}."

    text_body = (
        f"Hi {user.first_name},\n\n"
        f"{lead}\n"
        f"Location: {LOCATION}.\n"
        f"Log in to your dashboard if you need to reschedule or cancel.\n\n"
        f"Cellusys CodeCamp"
    )
    html_body = (
        f"<h2>Interview Reminder</h2>"
        f"<p>Hi {user.first_name},</p>"
        f"<p>{lead}</p>"
        f"<p>Location: <strong>{LOCATION}</strong>.</p>"
        f"<p>Log in to your dashboard if you need to reschedule or cancel.</p>"
    )
    return _send(user, kind, dedupe_key, subject, text_body, html_body)


def _send_interview_reminders(now):
    """Send 24h and 2h reminders. Returns (count_24h, count_2h)."""
    sent_24 = sent_2 = 0
    today = now.date()
    horizon = (now + timedelta(hours=26)).date()

    slots = InterviewSlot.query.filter(
        InterviewSlot.slot_date >= today,
        InterviewSlot.slot_date <= horizon,
    ).all()

    for slot in slots:
        booking = slot.booking
        if booking is None or booking.status != "scheduled":
            continue
        user = db.session.get(User, booking.user_id)
        if user is None or not user.is_active or not user.email:
            continue

        remaining = datetime.combine(slot.slot_date, slot.start_time) - now
        if remaining <= timedelta(0):
            continue
        if timedelta(hours=3) < remaining <= timedelta(hours=26):
            if _send_interview_reminder(user, slot, "24h"):
                sent_24 += 1
        elif timedelta(minutes=20) <= remaining <= timedelta(hours=3):
            if _send_interview_reminder(user, slot, "2h"):
                sent_2 += 1

    return sent_24, sent_2


# ── Application reminders ───────────────────────────────────────────────

def _send_draft_nudge(user, app_record):
    kind = "draft_nudge"
    subject = "Cellusys CodeCamp — Finish Your Application"
    text_body = (
        f"Hi {user.first_name},\n\n"
        f"You started a Cellusys CodeCamp application but haven't submitted it "
        f"yet. Complete it to be considered for the aptitude test and interview.\n\n"
        f"Log in to your dashboard to pick up where you left off.\n\n"
        f"Cellusys CodeCamp"
    )
    html_body = (
        f"<h2>Your application is waiting</h2>"
        f"<p>Hi {user.first_name},</p>"
        f"<p>You started a Cellusys CodeCamp application but haven't submitted "
        f"it yet. Complete it to be considered for the aptitude test and interview.</p>"
        f"<p>Log in to your dashboard to pick up where you left off.</p>"
    )
    return _send(user, kind, f"{kind}:{app_record.id}", subject, text_body, html_body)


def _send_draft_nudges(now):
    cutoff = now - timedelta(days=current_app.config.get("REMINDER_DAYS_DRAFT", 3))
    count = 0
    for app_record in Application.query.filter(Application.is_submitted.is_(False)).all():
        created = _naive(app_record.created_at)
        user = app_record.user
        if created is None or created > cutoff:
            continue
        if user is None or not user.is_active or user.role != "student" or not user.email:
            continue
        if _send_draft_nudge(user, app_record):
            count += 1
    return count


def _send_test_reminder(user, app_record):
    kind = "test_reminder"
    subject = "Cellusys CodeCamp — Take Your Aptitude Test"
    text_body = (
        f"Hi {user.first_name},\n\n"
        f"You've been invited to take the Cellusys CodeCamp aptitude test, "
        f"which is the next step in your application.\n\n"
        f"Log in to your dashboard to start the test when you're ready "
        f"(find a quiet place and a stable internet connection).\n\n"
        f"Cellusys CodeCamp"
    )
    html_body = (
        f"<h2>Your aptitude test is ready</h2>"
        f"<p>Hi {user.first_name},</p>"
        f"<p>You've been invited to take the Cellusys CodeCamp aptitude test, "
        f"which is the next step in your application.</p>"
        f"<p>Log in to your dashboard to start the test when you're ready "
        f"(find a quiet place and a stable internet connection).</p>"
    )
    return _send(user, kind, f"{kind}:{app_record.id}", subject, text_body, html_body)


def _send_test_reminders(now):
    cutoff = now - timedelta(days=current_app.config.get("REMINDER_DAYS_TEST", 3))
    count = 0
    apps = Application.query.filter(
        Application.pipeline_stage == "test_invited",
        Application.is_submitted.is_(True),
    ).all()
    for app_record in apps:
        if (app_record.test_attempts or 0) > 0:
            continue
        submitted = _naive(app_record.submitted_at)
        user = app_record.user
        if submitted is None or submitted > cutoff:
            continue
        if user is None or not user.is_active or user.role != "student" or not user.email:
            continue
        if _send_test_reminder(user, app_record):
            count += 1
    return count


# ── Sweep ───────────────────────────────────────────────────────────────

@celery.task(name="app.tasks.reminders.run_due_reminders")
def run_due_reminders():
    """Send every reminder whose time window has opened (idempotent)."""
    if not current_app.config.get("REMINDER_ENABLED"):
        return {"skipped": "disabled"}

    now = _now_utc()
    sent_24, sent_2 = _send_interview_reminders(now)
    report = {
        "interview_reminder_24h": sent_24,
        "interview_reminder_2h": sent_2,
        "draft_nudge": _send_draft_nudges(now),
        "test_reminder": _send_test_reminders(now),
    }
    if any(report.values()):
        log.info("Reminders sent: %s", report)
    return report
