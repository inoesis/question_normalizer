"""Public batch entry point.

The only supported public symbol is :func:`normalize_questions`. The
batch loop is responsible for per-question fault isolation; the pipeline
itself is allowed to raise.
"""

from __future__ import annotations

import logging
from typing import Any

from . import config
from .pipeline import fallback_one, run_one

_log = logging.getLogger(config.LOGGER_NAME)


def normalize_questions(questions: list[dict]) -> list[dict]:
    """Normalize a batch of raw question dicts into LMS-ready dicts.

    - Pure: no I/O, no global state.
    - Idempotent: ``normalize_questions(normalize_questions(x)) == normalize_questions(x)``.
    - Fault-tolerant: per-question try/except keeps batch size stable.

    Hard failures (non-list input) raise ``TypeError`` immediately.
    """
    if not isinstance(questions, list):
        raise TypeError(
            f"normalize_questions expects a list of dicts, got {type(questions).__name__}"
        )

    out: list[dict] = []
    for idx, q in enumerate(questions):
        if not isinstance(q, dict):
            # Coerce silently to a fallback record so batch length stays stable.
            _log.warning("normalize.skip non-dict at index %d: %r", idx, type(q).__name__)
            out.append(
                fallback_one(
                    {"question": "", "answers": [], "correct_answers": []},
                    cause=f"not_a_dict:{type(q).__name__}",
                )
            )
            continue

        try:
            out.append(run_one(q))
        except Exception as exc:  # noqa: BLE001 — per-question isolation
            qid = q.get("QB_id") or q.get("id") or f"#{idx}"
            _log.warning(
                "normalize.failed qid=%s stage=pipeline cause=%s",
                qid,
                exc.__class__.__name__,
                exc_info=True,
            )
            out.append(fallback_one(q, cause=f"{exc.__class__.__name__}:{exc}"))

    return out
