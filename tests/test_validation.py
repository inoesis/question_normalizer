"""Stage 6 — validation."""

from question_normalizer.validation import validate


def test_drops_out_of_range():
    assert validate([0, 5], n_answers=4) == [0]


def test_dedupes_and_sorts():
    assert validate([2, 0, 2, 1], n_answers=4) == [0, 1, 2]


def test_empty_result_no_exception():
    assert validate([10, 11], n_answers=4) == []


def test_handles_string_ints():
    assert validate(["1", 0], n_answers=4) == [0, 1]


def test_handles_non_int_garbage():
    assert validate(["abc", None, 1], n_answers=4) == [1]
