"""Google Sheets sync for applicants who pass the aptitude test.

Best-effort by design: a Sheets outage or misconfiguration must never break
the assessment flow. The row is built synchronously (pure Python, no I/O) and
pushed in a daemon thread, so the API response is not delayed by the network.

Row semantics: one row per applicant, keyed by Email. Existing rows are
updated in place, missing rows are appended. Headers are written automatically
when the sheet is empty.
"""
import json
import logging
import os
import threading
from datetime import datetime, timezone

from flask import current_app

log = logging.getLogger("cellusys.sheets")

SHEET_HEADERS = [
    "User ID",
    "Email",
    "First name",
    "Last name",
    "Phone / WhatsApp",
    "Date of birth",
    "Gender",
    "Applicant location",
    "Campus location",
    "Course applying for",
    "Referral code",
    "Education level",
    "Institution",
    "Motivation",
    "Pipeline stage",
    "Test score",
    "Passed",
    "Submitted at",
    "Updated at",
    "Last synced",
]
EMAIL_HEADER = "Email"
_EMAIL_COL_INDEX = SHEET_HEADERS.index(EMAIL_HEADER)
_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

_client = None
_client_lock = threading.Lock()


def _fmt_dt(value):
    """Format a datetime as a UTC string for the sheet ('' when unset)."""
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _load_credentials_info():
    """Return the service-account JSON as a dict from env/file config."""
    raw = current_app.config.get("GOOGLE_SHEETS_CREDENTIALS_JSON", "")
    if raw:
        try:
            return json.loads(raw)
        except (TypeError, ValueError) as exc:
            log.error("GOOGLE_SHEETS_CREDENTIALS_JSON is not valid JSON: %s", exc)
            return None
    path = current_app.config.get("GOOGLE_SHEETS_CREDENTIALS_FILE", "")
    if path and os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError) as exc:
            log.error("Could not read service account file %s: %s", path, exc)
            return None
    log.error("No Google Sheets credentials configured (JSON or file).")
    return None


def _get_client():
    """Lazily create (once) a thread-safe gspread client with sane timeouts."""
    global _client
    if _client is not None:
        return _client
    with _client_lock:
        if _client is not None:
            return _client
        try:
            from google.oauth2.service_account import Credentials
            import gspread
            import requests

            info = _load_credentials_info()
            if not info:
                return None
            scoped = Credentials.from_service_account_info(info, scopes=_SCOPES)
            session = requests.Session()
            session.mount(
                "https://",
                requests.adapters.HTTPAdapter(
                    pool_connections=4,
                    pool_maxsize=8,
                    max_retries=requests.adapters.Retry(
                        total=3,
                        backoff_factor=0.5,
                        status_forcelist=[429, 500, 502, 503, 504],
                    ),
                ),
            )
            _client = gspread.Client(auth=scoped, session=session)
            log.info("Google Sheets client initialized")
        except Exception as exc:
            log.error("Failed to initialize Google Sheets client: %s", exc)
            _client = None
    return _client


def _get_worksheet():
    """Open the configured spreadsheet and return the target worksheet."""
    client = _get_client()
    if client is None:
        return None
    spreadsheet_id = current_app.config.get("GOOGLE_SHEETS_SPREADSHEET_ID", "")
    if not spreadsheet_id:
        log.error("GOOGLE_SHEETS_SPREADSHEET_ID is not configured.")
        return None
    sh = client.open_by_key(spreadsheet_id)
    tab_name = current_app.config.get("GOOGLE_SHEETS_TAB", "")
    if tab_name:
        return sh.worksheet(tab_name)
    return sh.sheet1


def _ensure_header(tab, header_cells):
    """Write headers when the sheet is empty or misaligned.

    Returns (header list, wrote_header) where wrote_header is True only when
    the headers were just written (meaning the batch-read email column from
    before is stale and must not be used for the row lookup).
    """
    header = [str(c).strip() for c in (header_cells[0] if header_cells else [])]
    if not header or header[0] != SHEET_HEADERS[0]:
        tab.update("A1", [SHEET_HEADERS], value_input_option="RAW")
        return SHEET_HEADERS, True
    return header, False


def _upsert(tab, row):
    """Update the applicant's row (matched by Email) or append a new one."""
    email = row[_EMAIL_COL_INDEX]
    if not email:
        log.warning("Skipping Google Sheets sync: applicant has no email.")
        return

    values = tab.batch_get(["1:1", "B:B"])
    header_cells = values[0] if values else []
    header, header_written = _ensure_header(tab, header_cells)

    email_col = _EMAIL_COL_INDEX + 1
    if EMAIL_HEADER in header:
        email_col = header.index(EMAIL_HEADER) + 1

    if header_written:
        email_values = [SHEET_HEADERS[email_col - 1]]
    else:
        email_rows = values[1] if len(values) > 1 else []
        email_values = [r[0] if r else "" for r in email_rows]

    row_idx = None
    for idx, value in enumerate(email_values, start=1):
        if value == email:
            row_idx = idx
            break

    if row_idx is not None:
        tab.update(f"A{row_idx}", [row], value_input_option="RAW")
        log.info("Updated Google Sheets row %s for %s", row_idx, email)
    else:
        tab.append_row(row, value_input_option="RAW")
        log.info("Appended Google Sheets row for %s", email)


def _push_row(app, row):
    """Run inside the app context in a background thread."""
    with app.app_context():
        try:
            tab = _get_worksheet()
            if tab is None:
                return
            _upsert(tab, row)
        except Exception as exc:
            log.error("Google Sheets sync failed: %s", exc)


def sync_passed_applicant(app_record, user, passed=True):
    """Queue a best-effort background sync of a passed applicant's row.

    Must be called inside a request/app context. Never raises.
    """
    if not current_app.config.get("GOOGLE_SHEETS_ENABLED"):
        return
    if not current_app.config.get("GOOGLE_SHEETS_SPREADSHEET_ID"):
        log.debug("Google Sheets sync skipped: spreadsheet ID not configured.")
        return
    try:
        row = [
            app_record.user_id,
            user.email or "",
            user.first_name or "",
            user.last_name or "",
            user.phone or "",
            app_record.date_of_birth or "",
            app_record.gender or "",
            app_record.applicant_location or "",
            app_record.campus_location or "",
            app_record.field_of_study or "",
            app_record.referral_code or "",
            app_record.education_level or "",
            app_record.institution or "",
            app_record.motivation or "",
            app_record.pipeline_stage or "",
            app_record.test_score if app_record.test_score is not None else "",
            "TRUE" if passed else "FALSE",
            _fmt_dt(app_record.submitted_at),
            _fmt_dt(app_record.updated_at),
            _fmt_dt(datetime.now(timezone.utc)),
        ]
    except Exception as exc:
        log.error(
            "Failed to build Google Sheets row for user %s: %s",
            getattr(user, "id", "?"), exc,
        )
        return
    app = current_app._get_current_object()
    threading.Thread(
        target=_push_row, args=(app, row), name="sheets-sync", daemon=True
    ).start()
    log.debug("Queued Google Sheets sync for %s", user.email)
