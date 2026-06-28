"""Stage 6 — correct_answers validation.

Drops out-of-range and duplicate indices, sorts ascending. An empty
result is retained (the question stays in the batch) and a warning is
logged. Never raises.
"""

from __future__ import annotations

import logging
from typing import Iterable

from . import config

_log = logging.getLogger(config.LOGGER_NAME)


def validate(correct_answers: Iterable, n_answers: int, qid: str | None = None) -> list[int]:
    """Return a clean, sorted, de-duplicated list of valid 0-based indices."""
    seen: set[int] = set()
    cleaned: list[int] = []
    dropped: list = []
    for raw in correct_answers or []:
        try:
            idx = int(raw)
        except (TypeError, ValueError):
            dropped.append(raw)
            continue
        if idx < 0 or idx >= n_answers:
            dropped.append(raw)
            continue
        if idx in seen:
            continue
        seen.add(idx)
        cleaned.append(idx)
    cleaned.sort()
    if dropped:
        _log.info("validation.dropped qid=%s dropped=%s", qid, dropped)
    if not cleaned:
        _log.info("validation.no_valid_correct_answer qid=%s", qid)
    return cleaned
