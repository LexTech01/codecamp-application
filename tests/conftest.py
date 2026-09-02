import os
import tempfile
import pytest
from app import create_app, db as _db


@pytest.fixture(scope="function")
def app():
    _db_fd, db_path = tempfile.mkstemp(suffix=".db")
    app = create_app(config_override={
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
        "WTF_CSRF_ENABLED": False,
        "MAIL_SUPPRESS_SEND": True,
        "SESSION_COOKIE_SECURE": False,
    })
    with app.app_context():
        _db.create_all()
    # Note: the app context is intentionally popped here. Keeping it alive
    # across test-client requests would bind Flask's `g` (and thus
    # flask_login's cached `g._login_user`) to the persistent context,
    # which leaks authentication state between requests and breaks
    # session-version invalidation checks.
    yield app
    with app.app_context():
        _db.session.remove()
        _db.drop_all()
        _db.engine.dispose()
    os.close(_db_fd)
    try:
        os.unlink(db_path)
    except PermissionError:
        pass  # Windows may briefly hold the SQLite file handle open


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def pipeline(app):
    from app.pipeline import pipeline
    return pipeline
