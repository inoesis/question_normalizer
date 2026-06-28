"""Shared fixtures — the six observed scraped question samples."""

from __future__ import annotations

import json
import os

import pytest

_SAMPLE_PATH = os.environ.get(
    "QUESTION_SAMPLES_JSON",
    os.path.join(os.path.dirname(__file__), "fixtures", "questions_1.json"),
)


@pytest.fixture(scope="session")
def sample_questions() -> list[dict]:
    """The six scraped samples (mcq, assertion_reason, match_columns,
    statement, multi_statement, figure) as plain Python dicts.

    The fixtures file mirrors ``issues/v1/questions_1.json`` from the
    parent project so the tests stay self-contained.
    """
    with open(_SAMPLE_PATH, encoding="utf-8") as fh:
        return json.load(fh)["questions"]
