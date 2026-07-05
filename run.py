"""Entry point for Cellusys CodeCamp Recruitment Platform."""
from app import create_app, db, seed_database

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_database()
    app.run(debug=True, host="0.0.0.0", port=5555)
