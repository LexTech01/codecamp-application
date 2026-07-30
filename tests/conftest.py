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
    })
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.close()
        _db.drop_all()
    os.close(_db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def pipeline(app):
    from app.pipeline import pipeline
    return pipeline
