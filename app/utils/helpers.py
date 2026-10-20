"""Pure helper utilities (no session or I/O side effects).

Outbound pipeline effects (audit logs, notifications) live in
:mod:`app.utils.outbox`; email goes through :mod:`app.utils.email` and
:mod:`app.utils.messaging`. This module keeps only deterministic leaves.
"""
import json
import os
from flask import current_app, url_for


def calculate_score(earned, total, pass_score=70.0):
    """Compute percentage score and pass/fail against the threshold."""
    score = round((earned / total * 100) if total else 0, 1)
    passed = score >= pass_score
    return score, passed


def parse_json_safe(data, default=None):
    if default is None:
        default = {}
    try:
        return json.loads(data) if data else default
    except (json.JSONDecodeError, TypeError):
        return default


def resolve_assessment_image(filename):
    """Resolve a local assessment image filename to a static URL.

    Images live in ``app/static/images/assessment/`` (e.g.
    ``q3_question.jpg``, ``q1_opt0_potato.jpg``). Returns the URL path
    (``static/images/assessment/<filename>``) if the file exists, else ``None``.

    Idempotent: if ``filename`` is already a URL path (starts with ``/``) it is
    returned unchanged, so values stored in the DB can be passed through again.
    """
    if not filename:
        return None
    if isinstance(filename, str) and filename.startswith("/"):
        return filename
    folder = os.path.join(
        current_app.root_path, "static", "images", "assessment"
    )
    if not os.path.isfile(os.path.join(folder, filename)):
        return None
    return url_for("static", filename=f"images/assessment/{filename}")