"""Replace the built-in aptitude quiz with the Puzzles Challenge questions.

Run from the project root (inside the app context):

    python -m scripts.import_puzzles

This deletes existing questions on the "Cellusys Aptitude Assessment" (or a
replacement assessment found by title in app/data/puzzle_questions.py) 

Image files live directly in ``app/static/images/assessment/`` and are
referenced by local filename (e.g. ``q3_question.jpg``) in
``app/data/puzzle_questions.py``. Missing images are stored as NULL and
simply don't render.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.assessment import Assessment, Question
from app.data.puzzle_questions import PUZZLE_ASSESSMENT, PUZZLE_QUESTIONS


def main():
    app = create_app()
    with app.app_context():
        assessment = Assessment.query.filter_by(title=PUZZLE_ASSESSMENT["title"]).first()
        if assessment is None:
            assessment = Assessment(title=PUZZLE_ASSESSMENT["title"])
            db.session.add(assessment)
            db.session.flush()
        else:
            assessment.title = PUZZLE_ASSESSMENT["title"]
            assessment.description = PUZZLE_ASSESSMENT["description"]
            assessment.duration_minutes = PUZZLE_ASSESSMENT["duration_minutes"]
            assessment.pass_score = PUZZLE_ASSESSMENT["pass_score"]
            assessment.is_active = True
            # Drop existing questions so a re-run is idempotent.
            existing = Question.query.filter_by(assessment_id=assessment.id).all()
            for q in existing:
                db.session.delete(q)
            db.session.flush()

        seeded = 0
        for idx, item in enumerate(PUZZLE_QUESTIONS, start=1):
            options = item["options"]
            qobj = Question(
                assessment_id=assessment.id,
                question_text=item["text"],
                options=list(options),
                option_a=options[0] if len(options) >= 1 else None,
                option_b=options[1] if len(options) >= 2 else None,
                option_c=options[2] if len(options) >= 3 else None,
                option_d=options[3] if len(options) >= 4 else None,
                correct_answer=item.get("correct_answer"),
                # Store the raw local filename (e.g. "q3_question.jpg");
                # it is resolved to a URL at request time in student.py.
                question_image=item.get("question_image"),
                option_images=item.get("option_images") or [None] * len(options),
                points=10,
                order_num=idx,
            )
            db.session.add(qobj)
            seeded += 1

        db.session.commit()
        print(f"Seeded {seeded} questions into assessment #{assessment.id} "
              f"({assessment.title}).")
        print("Image references, durations and correct answers stored for all questions.")


if __name__ == "__main__":
    main()
