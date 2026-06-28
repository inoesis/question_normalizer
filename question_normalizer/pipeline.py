"""Ordered stage runner for a single question.

Composes the per-stage transforms in the order mandated by the spec:
  1. html_repair       — structural pre-clean (must run before any parser)
  2. sanitizer         — allowlist tag/attr/CSS sanitization
  3. layout            — light layout-preservation guarantees
  4. math_tex          — KaTeX-compatible LaTeX source normalization
  5. (answer pass)     — apply 1+2+4 to each answer string
  6. validation        — clean correct_answers
"""

from __future__ import annotations

from typing import Any

from . import html_repair, layout, math_tex, sanitizer, validation


def _normalize_html_text(text: str, render_type: str | None) -> str:
    text = html_repair.repair(text)
    text = sanitizer.sanitize(text)
    text = layout.preserve(text, render_type=render_type)
    text = math_tex.normalize(text)
    return text


def _normalize_answer(text: str) -> str:
    # Answers go through 1+2+4 but skip the layout stage — they aren't
    # block-level question bodies. Stage 2 still permits inline tags
    # commonly used in answer markup (b, sub, sup, etc).
    text = html_repair.repair(text)
    text = sanitizer.sanitize(text)
    text = math_tex.normalize(text)
    return text


def _extract_question_html(raw: Any) -> tuple[str, dict]:
    """Accept both flat-string and nested-dict input shapes.

    Returns ``(html, passthrough_metadata)``. Passthrough metadata contains
    any sibling keys that should appear in the output dict unchanged
    (`render_type`, `explanation`, …) for the dict-shape input.
    """
    if isinstance(raw, str):
        return raw, {}
    if isinstance(raw, dict):
        html = raw.get("text") or ""
        metadata = {k: v for k, v in raw.items() if k != "text"}
        return html, metadata
    # Anything else: coerce to str. Don't raise; the per-question try/except
    # in api.py would catch it but we want to be tolerant here.
    return str(raw), {}


def run_one(question: dict) -> dict:
    """Run the full pipeline on one question dict. Pure, no I/O.

    The caller is responsible for try/except — fault isolation lives in
    :mod:`question_normalizer.api`.
    """
    qid = question.get("QB_id") or question.get("id")

    raw_question = question.get("question", "")
    html, meta = _extract_question_html(raw_question)
    normalized_html = _normalize_html_text(html, meta.get("render_type"))

    raw_answers = question.get("answers") or []
    normalized_answers = [_normalize_answer(str(a)) for a in raw_answers]

    valid_correct = validation.validate(
        question.get("correct_answers") or [],
        n_answers=len(normalized_answers),
        qid=str(qid) if qid is not None else None,
    )

    # Output: the three guaranteed keys plus everything else preserved
    # verbatim. Sibling metadata from the dict-shape question (e.g.
    # render_type) lifts to the top level so renderers can read it.
    out: dict = {}
    # Preserve every non-normalized input key first…
    for k, v in question.items():
        if k in {"question", "answers", "correct_answers"}:
            continue
        out[k] = v
    # …then meta from nested-dict question shape (last-wins ensures the
    # explicit nested keys override silently-empty top-level ones).
    for k, v in meta.items():
        if k == "text":
            continue
        out[k] = v

    out["question"] = normalized_html
    out["answers"] = normalized_answers
    out["correct_answers"] = valid_correct
    return out


def fallback_one(question: dict, cause: str) -> dict:
    """Minimal-safe output for a question that failed mid-pipeline.

    HTML is sanitized to plain text; answers are sanitized best-effort.
    """
    raw_question = question.get("question", "")
    if isinstance(raw_question, dict):
        raw_text = raw_question.get("text") or ""
    else:
        raw_text = str(raw_question)
    safe_text = sanitizer.sanitize(raw_text)

    safe_answers: list[str] = []
    for a in question.get("answers") or []:
        try:
            safe_answers.append(sanitizer.sanitize(str(a)))
        except Exception:
            # Last-resort: escape angle brackets to keep it visible-but-safe.
            safe_answers.append(str(a).replace("<", "&lt;").replace(">", "&gt;"))

    valid_correct = validation.validate(
        question.get("correct_answers") or [],
        n_answers=len(safe_answers),
        qid=str(question.get("QB_id") or question.get("id") or ""),
    )

    out: dict = {}
    for k, v in question.items():
        if k in {"question", "answers", "correct_answers"}:
            continue
        out[k] = v
    out["question"] = safe_text
    out["answers"] = safe_answers
    out["correct_answers"] = valid_correct
    out["_normalize_error"] = cause
    return out
