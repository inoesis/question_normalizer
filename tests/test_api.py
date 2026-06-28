"""Integration tests — full ``normalize_questions`` pipeline."""

import pytest

from question_normalizer import normalize_questions


def test_six_samples_round_trip(sample_questions):
    assert len(sample_questions) == 6
    out = normalize_questions(sample_questions)
    assert len(out) == 6
    for original, normalized in zip(sample_questions, out):
        # The three guaranteed output keys exist with the right shape.
        assert isinstance(normalized["question"], str)
        assert isinstance(normalized["answers"], list)
        assert isinstance(normalized["correct_answers"], list)
        # Same number of answers in the same order.
        assert len(normalized["answers"]) == len(original["answers"])


def test_render_type_preserved(sample_questions):
    out = normalize_questions(sample_questions)
    # Each sample has render_type nested inside `question.render_type`.
    types_in = [q["question"]["render_type"] for q in sample_questions]
    types_out = [q.get("render_type") for q in out]
    assert types_out == types_in


def test_qb_id_and_tags_preserved(sample_questions):
    out = normalize_questions(sample_questions)
    for original, normalized in zip(sample_questions, out):
        assert normalized.get("QB_id") == original.get("QB_id")
        assert normalized.get("quiz_question_tags") == original.get("quiz_question_tags")


def test_assertion_reason_block_structure_preserved(sample_questions):
    ar = next(q for q in normalize_questions(sample_questions) if q.get("render_type") == "assertion_reason")
    body = ar["question"].lower()
    assert "assertion" in body
    assert "reason" in body
    # The colored left-border styling must survive sanitization
    assert "border-left" in body


def test_match_columns_table_preserved(sample_questions):
    m = next(q for q in normalize_questions(sample_questions) if q.get("render_type") == "match_columns")
    assert "<table" in m["question"]
    assert "<td" in m["question"]


def test_figure_img_preserved_with_alt_and_loading(sample_questions):
    fig = next(q for q in normalize_questions(sample_questions) if q.get("render_type") == "figure")
    html = fig["question"]
    assert "<img" in html
    assert 'alt=' in html
    assert 'loading="lazy"' in html


def test_math_options_normalized(sample_questions):
    # Sample 3 has options like ${\rm{A - Q, S, T; B - P, R}}$ which should
    # be normalized to \mathrm form.
    out = normalize_questions(sample_questions)
    for q in out:
        for ans in q["answers"]:
            assert "\\rm{" not in ans


def test_idempotent_over_corpus(sample_questions):
    once = normalize_questions(sample_questions)
    twice = normalize_questions(once)
    # The whole batch round-trips byte-identical.
    assert once == twice


def test_correct_answers_validated(sample_questions):
    out = normalize_questions(sample_questions)
    for q in out:
        n = len(q["answers"])
        for idx in q["correct_answers"]:
            assert 0 <= idx < n
        # Sorted ascending, no duplicates
        assert q["correct_answers"] == sorted(set(q["correct_answers"]))


def test_xss_payload_stripped():
    qs = [
        {
            "question": '<div>safe<script>alert(1)</script></div><img src="x" onerror="alert(2)">',
            "answers": ['<b onclick="alert(3)">opt</b>'],
            "correct_answers": [0],
        }
    ]
    out = normalize_questions(qs)
    body = out[0]["question"].lower()
    assert "<script" not in body
    assert "onerror" not in body
    assert "onclick" not in out[0]["answers"][0].lower()


def test_fault_isolation_keeps_batch_length():
    # Mix valid + malformed. ``None`` and a non-dict member.
    qs = [
        {"question": "hi", "answers": ["a", "b"], "correct_answers": [0]},
        "not a dict",
        {"question": {"text": "yo"}, "answers": [], "correct_answers": []},
    ]
    out = normalize_questions(qs)
    assert len(out) == 3
    assert out[0]["question"]
    assert out[1].get("_normalize_error")  # fallback record


def test_input_shape_tolerance():
    flat = [{"question": "<div>x</div>", "answers": ["a"], "correct_answers": [0]}]
    nested = [
        {
            "question": {"text": "<div>x</div>", "render_type": "mcq"},
            "answers": ["a"],
            "correct_answers": [0],
        }
    ]
    out_flat = normalize_questions(flat)
    out_nested = normalize_questions(nested)
    # The HTML body should normalize identically; nested keeps render_type.
    assert out_flat[0]["question"] == out_nested[0]["question"]
    assert out_nested[0]["render_type"] == "mcq"


def test_hard_failure_on_non_list():
    with pytest.raises(TypeError):
        normalize_questions({"not": "a list"})  # type: ignore[arg-type]
