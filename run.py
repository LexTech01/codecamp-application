"""Entry point for Cellusys CodeCamp Recruitment Platform.

Debug mode is opt-in via FLASK_DEBUG=1 (set in the local .env), so this
entry point is safe even if accidentally invoked outside local development.
"""
import os
from app import create_app, db, seed_database

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        from flask_migrate import upgrade
        upgrade()
        seed_database()
    app.run(
        debug=os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes"),
        host=os.environ.get("FLASK_HOST", "0.0.0.0"),
        port=int(os.environ.get("FLASK_PORT", 5555)),
    )
