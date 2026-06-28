"""Exception and warning record types for the normalizer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


class NormalizationError(Exception):
    """Base class for any error raised inside the pipeline."""


class MathWarning(NormalizationError):
    """A LaTeX span was unbalanced or failed parse; passthrough recorded."""


class ValidationWarning(NormalizationError):
    """A correct_answers entry was out-of-range, duplicate, or empty."""


@dataclass(frozen=True)
class QuestionError:
    """Structured per-question failure record (logged, not raised)."""

    qid: Optional[str]
    stage: str
    cause: str
    message: str

    def as_dict(self) -> dict:
        return {
            "qid": self.qid,
            "stage": self.stage,
            "cause": self.cause,
            "message": self.message,
        }
