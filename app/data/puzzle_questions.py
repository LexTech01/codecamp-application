"""Seed data for the Cellusys CodeCamp Puzzles Challenge assessment.

Extracted from the public Google Form
"Cellusys CodeCamp – Puzzles Challenge Assessment".

Images live directly in ``app/static/images/assessment/`` and are referenced
by their local filename (e.g. ``q1_opt0_potato.jpg``, ``q3_question.jpg``).
A question/option without an image uses ``None``.

Correct answers (0-based index into ``options``) are set.
"""

PUZZLE_ASSESSMENT = {
    "title": "Cellusys Aptitude Assessment",
    "description": (
        "Puzzles Challenge – logical reasoning, problem-solving and "
        "attention-to-detail questions. Required for scholarship consideration."
    ),
    "duration_minutes": 15,
    "pass_score": 70,
}

# Each question: text, options (list), question_image (local filename or None),
# option_images (list aligned with options, local filename or None), correct_answer.
PUZZLE_QUESTIONS = [
    {
        "text": "Which one is different from the others?",
        "options": ["Potato", "Pot", "Tomato", "Green Pepper"],
        "question_image": None,
        "option_images": [
            "q1_opt0_potato.jpg",
            "q1_opt1_pot.jpg",
            "q1_opt2_tomato.jpg",
            "q1_opt3_green_pepper.jpg",
        ],
        "correct_answer": 1,
    },
    {
        "text": "Which one is different?",
        "options": ["Steel", "Copper", "Wood", "Aluminium"],
        "question_image": None,
        "option_images": [
            "q2_opt0_steel.jpg",
            "q2_opt1_copper.jpg",
            "q2_opt2_wood.jpg",
            "q2_opt3_aluminium.jpg",
        ],
        "correct_answer": 2,
    },
    {
        "text": "1. What is shown in the image?",
        "options": ["Line Graph", "Bar Chart", "Pie Chart", "Histogram"],
        "question_image": "q3_question.jpg",
        "option_images": [None, None, None, None],
        "correct_answer": 2,
    },
    {
        "text": "2. What is shown in the image?",
        "options": ["Algorithm", "Flowchart", "Pie Chart", "Table"],
        "question_image": "q4_question.jpg",
        "option_images": [None, None, None, None],
        "correct_answer": 1,
    },
    {
        "text": (
            "What mistake in logic was made in the following reasoning?\n"
            "All animals walk on legs. Snakes are animals. Therefore, snakes "
            "walk on legs. Later, it was discovered that snakes do not walk "
            "on legs. Where was the error?"
        ),
        "options": ["Invalid conclusion", "Incorrect second premise", "False generalization", "Wrong reasoning method"],
        "question_image": "q5_question.jpg",
        "option_images": [None, None, None, None],
        "correct_answer": 2,
    },
    {
        "text": (
            "Study the instructions below and follow them carefully:\n"
            "\u2013 Start from 1\n"
            "\u2013 Go down 2 steps\n"
            "\u2013 Go down 1 step and right 1 step\n"
            "\u2013 Add 3 and move to the resulting number\n"
            "\u2013 Go down 2 steps\n"
            "\u2013 Subtract 1\n"
            "What number have you reached?"
        ),
        "options": ["6", "7", "8", "9"],
        "question_image": "q6_question.jpg",
        "option_images": [None, None, None, None],
        "correct_answer": 2,
    },
    {
        "text": "Choose the piece that matches perfectly the combination of the two given pieces.",
        "options": ["A", "B", "C", "D", "E", "F"],
        "question_image": "q7_question.jpg",
        "option_images": [None, None, None, None, None, None],
        "correct_answer": 1,
    },
    {
        "text": "Which piece is missing from the pattern?",
        "options": ["A", "B", "C", "D"],
        "question_image": "q8_question.jpg",
        "option_images": [
            "q8_opt0_A.jpg",
            "q8_opt1_B.jpg",
            "q8_opt2_C.jpg",
            "q8_opt3_D.jpg",
        ],
        "correct_answer": 0,
    },
    {
        "text": "Choose the option to fit the final space.",
        "options": ["A", "B", "C", "D"],
        "question_image": "q9_question.jpg",
        "option_images": [
            "q9_opt0_A.jpg",
            "q9_opt1_B.jpg",
            "q9_opt2_C.jpg",
            "q9_opt3_D.jpg",
        ],
        "correct_answer": 1,
    },
    {
        "text": "Study the pattern below and determine the missing letter:\nWhat letter should replace the question mark (?)",
        "options": ["B", "L", "J", "K"],
        "question_image": "q10_question.jpg",
        "option_images": [None, None, None, None],
        "correct_answer": 3,
    },
    {
        "text": "A farmer owns 13 sheep. All but 8 are eaten by a wolf. How many sheep does the farmer have left?",
        "options": ["5", "8", "13", "0"],
        "question_image": "q11_question.jpg",
        "option_images": [None, None, None, None],
        "correct_answer": 1,
    },
    {
        "text": "What is the result of the expression below?\n6 + ((5 \u00d7 4) \u00f7 2)",
        "options": ["14", "16", "18", "20"],
        "question_image": "q12_question.jpg",
        "option_images": [None, None, None, None],
        "correct_answer": 1,
    },
    {
        "text": "What is the remainder of the following division:\n14 \u00f7 3",
        "options": ["0", "7", "2", "4.667"],
        "question_image": None,
        "option_images": [None, None, None, None],
        "correct_answer": 2,
    },
    {
        "text": "What is the sum of the angles of this triangle?",
        "options": ["90\u00b0", "360\u00b0", "270\u00b0", "180\u00b0"],
        "question_image": "q14_question.jpg",
        "option_images": [None, None, None, None],
        "correct_answer": 3,
    },
    {
        "text": "Which one of these shapes has the largest area?",
        "options": ["Square", "Circle", "Triangle", "Cannot be determined"],
        "question_image": "q15_question.jpg",
        "option_images": [None, None, None, None],
        "correct_answer": 0,
    },
    {
        "text": "Which one of these shapes has the longest perimeter (length of the boundary of the shape)?",
        "options": ["Square", "Circle", "Triangle", "Cannot be determined"],
        "question_image": "q16_question.jpg",
        "option_images": [None, None, None, None],
        "correct_answer": 0,
    },
    {
        "text": "Dip into each of these jars with a blindfold on and pick one ball. Which container gives you a higher probability of picking a red ball?",
        "options": ["A", "B", "All have equal probability", "None"],
        "question_image": "q17_question.jpg",
        "option_images": [None, None, None, None],
        "correct_answer": 0,
    },
    {
        "text": "If we roll a fair six-sided die once, what is the probability of getting side 4?",
        "options": ["1/2", "1/3", "1/4", "1/6"],
        "question_image": "q18_question.jpg",
        "option_images": [None, None, None, None],
        "correct_answer": 3,
    },
    {
        "text": "How many eggs are in this pyramid?",
        "options": ["10", "15", "50", "30"],
        "question_image": "q19_question.jpg",
        "option_images": [None, None, None, None],
        "correct_answer": 3,
    },
    {
        "text": "Focusing: How many digits do you see?",
        "options": ["10", "4", "6", "9"],
        "question_image": "q20_question.jpg",
        "option_images": [None, None, None, None],
        "correct_answer": 2,
    },
    {
        "text": "Based on the summations of rows and columns, calculate the value of the summation of the circle and triangle.",
        "options": ["11", "18", "12", "13"],
        "question_image": "q21_question.jpg",
        "option_images": [None, None, None, None],
        "correct_answer": 0,
    },
    {
        "text": "3D Awareness: Which top view is correct?",
        "options": ["A", "B", "C", "D"],
        "question_image": "q22_question.jpg",
        "option_images": [
            "q22_opt0_A.jpg",
            "q22_opt1_B.jpg",
            "q22_opt2_C.jpg",
            "q22_opt3_D.jpg",
        ],
        "correct_answer": 2,
    },
]
