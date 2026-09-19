"""Tests for the Resend email backend."""
from app.utils import helpers


class _FakeResponse:
    def __init__(self, status_code=200, text=""):
        self.status_code = status_code
        self.text = text


def test_send_mail_uses_resend(app, monkeypatch):
    calls = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.update(url=url, json=json, headers=headers)
        return _FakeResponse(200)

    monkeypatch.setattr("requests.post", fake_post)
    with app.app_context():
        app.config.update(
            TESTING=False,
            RESEND_API_KEY="re_test",
            EMAIL_FROM="Cellusys <noreply@cellusys.com>",
        )
        ok = helpers.send_mail("u@example.com", "Hi", "Body", "<p>Body</p>")

    assert ok is True
    assert calls["url"] == helpers.RESEND_API_URL
    assert calls["headers"]["Authorization"] == "Bearer re_test"
    assert calls["json"]["to"] == ["u@example.com"]
    assert calls["json"]["from"] == "Cellusys <noreply@cellusys.com>"
    assert calls["json"]["text"] == "Body"
    assert calls["json"]["html"] == "<p>Body</p>"


def test_send_mail_testing_never_calls_resend(app, monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("network call attempted during tests")

    monkeypatch.setattr("requests.post", boom)
    with app.app_context():
        app.config["RESEND_API_KEY"] = "re_test"
        assert helpers.send_mail("u@example.com", "Hi", "Body") is True


def test_send_via_resend_returns_false_on_api_error(app, monkeypatch):
    monkeypatch.setattr("requests.post", lambda *a, **k: _FakeResponse(422, "bad domain"))
    with app.app_context():
        app.config["RESEND_API_KEY"] = "re_test"
        assert helpers._send_via_resend("u@example.com", "s", "t", None) is False


def test_send_via_resend_returns_false_on_exception(app, monkeypatch):
    def boom(*args, **kwargs):
        raise ConnectionError("dns")

    monkeypatch.setattr("requests.post", boom)
    with app.app_context():
        app.config["RESEND_API_KEY"] = "re_test"
        assert helpers._send_via_resend("u@example.com", "s", "t", None) is False


def test_send_via_resend_requires_api_key(app):
    with app.app_context():
        app.config["RESEND_API_KEY"] = ""
        assert helpers._send_via_resend("u@example.com", "s", "t", None) is False
