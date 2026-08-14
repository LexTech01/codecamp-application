"""Unit tests for the real scoring logic in app.utils.helpers."""

from app.utils.helpers import calculate_score


def test_all_correct():
    score, passed = calculate_score(40, 40)
    assert score == 100.0
    assert passed is True


def test_all_wrong():
    score, passed = calculate_score(0, 40)
    assert score == 0.0
    assert passed is False


def test_half_correct():
    score, passed = calculate_score(20, 40)
    assert score == 50.0
    assert passed is False


def test_just_above_pass():
    score, passed = calculate_score(28, 40)
    assert score == 70.0
    assert passed is True


def test_just_below_pass():
    score, passed = calculate_score(27, 40)
    assert score == 67.5
    assert passed is False


def test_empty_total():
    score, passed = calculate_score(0, 0)
    assert score == 0.0
    assert passed is False


def test_partial_answers():
    score, passed = calculate_score(15, 30)
    assert score == 50.0
    assert passed is False


def test_high_pass_threshold():
    score, passed = calculate_score(85, 100, pass_score=90.0)
    assert score == 85.0
    assert passed is False


def test_perfect_with_threshold():
    score, passed = calculate_score(100, 100, pass_score=50.0)
    assert score == 100.0
    assert passed is True


def test_float_precision():
    score, passed = calculate_score(1, 3)
    assert score == 33.3
    assert passed is False


def test_single_question():
    score, passed = calculate_score(1, 1)
    assert score == 100.0
    assert passed is True
