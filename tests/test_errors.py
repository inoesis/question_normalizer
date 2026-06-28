"""Coverage for errors module."""

from question_normalizer.errors import (
    MathWarning,
    NormalizationError,
    QuestionError,
    ValidationWarning,
)


def test_warning_classes_extend_base():
    assert issubclass(MathWarning, NormalizationError)
    assert issubclass(ValidationWarning, NormalizationError)


def test_question_error_record():
    err = QuestionError(qid="Q1", stage="sanitize", cause="ValueError", message="bad style")
    d = err.as_dict()
    assert d["qid"] == "Q1"
    assert d["stage"] == "sanitize"
    assert d["cause"] == "ValueError"
    assert d["message"] == "bad style"
