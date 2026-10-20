"""Email delivery through the Resend API — the app's one true remote seam.

``send_mail`` hides a tiny transport seam with two real adapters:

* :class:`ResendTransport` — production HTTPS delivery via api.resend.com
* :class:`NullTransport` — no-op success (TESTING and keyless local dev)

Scheduled sends go through :mod:`app.utils.messaging`, which wraps
``send_mail`` in an idempotent, auditable claim; routes call ``send_mail``
directly after the owning transaction commits.
"""
import logging

RESEND_API_URL = "https://api.resend.com/emails"


class ResendTransport:
    """HTTPS delivery through Resend (works where outbound SMTP is blocked)."""

    def send(self, *, recipient, subject, text_body, html_body=None):
        import requests
        from flask import current_app

        logger = logging.getLogger(__name__)
        api_key = current_app.config.get("RESEND_API_KEY")
        if not api_key:
            logger.error("RESEND_API_KEY is not set — cannot send email to %s", recipient)
            return False

        payload = {
            "from": current_app.config["EMAIL_FROM"],
            "to": [recipient],
            "subject": subject,
            "text": text_body,
        }
        if html_body:
            payload["html"] = html_body

        try:
            resp = requests.post(
                RESEND_API_URL,
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10,
            )
            if resp.status_code >= 400:
                logger.error(
                    "Resend API error %s for %s: %s",
                    resp.status_code, recipient, resp.text[:500],
                )
                return False
            return True
        except Exception:
            logger.exception("Failed to send email to %s via Resend", recipient)
            return False


class NullTransport:
    """Swallows messages and reports success (used under TESTING)."""

    def send(self, *, recipient, subject, text_body, html_body=None):
        return True


def send_mail(recipient, subject, text_body, html_body=None):
    """Send an email, reporting success without raising.

    Returns True when the message was accepted by Resend, False otherwise.
    Under TESTING the call is suppressed (no network) and reports success.
    """
    from flask import current_app

    if current_app.config.get("TESTING"):
        logging.getLogger(__name__).debug("TESTING: suppressed email to %s", recipient)
        return NullTransport().send(
            recipient=recipient, subject=subject, text_body=text_body, html_body=html_body
        )
    return ResendTransport().send(
        recipient=recipient, subject=subject, text_body=text_body, html_body=html_body
    )