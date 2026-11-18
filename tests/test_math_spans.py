"""QUIC-209 — a "<" inside a math span is math, not the start of an HTML tag.

html_repair and the sanitizer used to read the "<x" in "$$ 0<x \\leq 2 $$"
as a tag and delete everything after it, closing $$ included.
"""

import pytest
from lxml import html as lxml_html

from question_normalizer import html_repair, layout, math_tex, normalize_questions, sanitizer
from question_normalizer.pipeline import _normalize_html_text

JEE_Q5 = (
    r"$$\text { Let } f(x)=\left\{\begin{array}{lr} -2, & -2 \leq x \leq 0 \\ "
    r"x-2, & 0<x \leq 2 \end{array}\right.$$ find"
)


def norm(text):
    return _normalize_html_text(text, None)


def _old_pipeline(text):
    """The pipeline as it was before QUIC-209 (no math spans set aside)."""
    text = html_repair.repair(text)
    text = sanitizer.sanitize(text)
    text = layout.preserve(text, render_type=None)
    return math_tex.normalize(text)


def test_the_jee_question_keeps_its_math_and_the_text_after_it():
    out = norm(JEE_Q5)
    assert r"0&lt;x \leq 2 \end{array}\right.$$ find" in out
    assert out.count("$$") == 2


@pytest.mark.parametrize(
    "text, expected",
    [
        ("If $a<b$ and $b>c$ then", "If $a&lt;b$ and $b&gt;c$ then"),
        (r"If \(a<b\) then", "If $a&lt;b$ then"),
        (r"\[x<y\] done", "$$x&lt;y$$ done"),
    ],
)
def test_every_delimiter_is_protected(text, expected):
    assert norm(text) == expected


def test_spaced_less_than_is_unchanged():
    # Already worked; the stored form must stay the same.
    assert norm(r"$$ & 0 < x \leq 2 $$ find") == r"$$ &amp; 0 &lt; x \leq 2 $$ find"


def test_real_tags_inside_math_still_go_through_the_sanitizer():
    # Not plain math, so not set aside: the sanitizer removes what it always did.
    out = norm("$<script>alert(1)</script>$ and $<b onclick=x>y</b>$")
    assert out == "$alert(1)$ and $<b>y</b>$"


@pytest.mark.parametrize(
    "text",
    [
        '<img src="x.png" alt="$" onerror="alert(1)$">',
        "<img src='x.png' alt='$' onerror='alert(1)$'>",
        '<img src="x.png" alt=$x onerror=alert(1)$>',
        '< img src="x.png" alt="$" onerror="alert(1)$">',
        '< img/src="x.png" alt="$x$">',
    ],
)
def test_a_span_inside_an_attribute_cannot_add_attributes(text):
    # The span starts inside alt="..."; its quote must not close the attribute.
    [img] = lxml_html.fragments_fromstring(norm(text))
    assert set(img.attrib) <= {"src", "alt", "loading"}
    assert "\ue000" not in img.get("alt", "")


def test_a_greater_than_later_in_the_text_does_not_stop_the_fix():
    assert norm("$0<x$ and x > 5") == "$0&lt;x$ and x &gt; 5"


def test_the_latex_prime_is_kept_as_is():
    assert norm("$f'(x)<0$") == "$f'(x)&lt;0$"


@pytest.mark.parametrize(
    "text",
    [
        "costs $5 and <b>bold</b> $10",
        "<p>Pay $5</p><p>or $10</p>",
        '<img src="https://x/?a=$1" alt=""> costs $5',
        '<img src="https://x/a.png" alt="$"> text $y$',
        "$x<sup>2</sup>$",
        "$90&deg$ and $a \\& b$",
        '$<img src="x.png" alt="$" loading="lazy">',
        "$0<x and y$ z > 1",
    ],
)
def test_html_between_dollars_is_left_to_the_html_stages_as_before(text):
    # Reviewers' cases: real markup or a "$" inside a tag - not plain math, so
    # the output must be exactly what it was before QUIC-209.
    assert norm(text) == _old_pipeline(text)


def test_tags_outside_math_are_still_sanitized():
    out = norm("<b>bold</b><script>bad()</script> and $x<y$")
    assert out == "<b>bold</b>bad() and $x&lt;y$"


def test_an_unclosed_dollar_is_left_to_the_old_path():
    # No closing $: not math, nothing set aside (same as before).
    assert "$5" in norm("costs $5 only")


def test_idempotent():
    once = norm(JEE_Q5)
    assert norm(once) == once


def test_placeholder_characters_in_the_input_are_dropped():
    # Invisible Private Use Area characters; left in, they could look like
    # our own placeholder for span 0.
    assert norm("\ue0000\ue001 then $x<y$") == "0 then $x&lt;y$"


def test_full_pipeline_through_the_public_api():
    [q] = normalize_questions(
        [{"question": JEE_Q5, "answers": ["$0<x$", "b"], "correct_answers": [0]}]
    )
    assert q["question"].endswith("$$ find")
    assert q["answers"][0] == "$0&lt;x$"


def test_is_balanced_flags_a_question_cut_short_by_the_old_bug():
    assert math_tex.is_balanced(norm(JEE_Q5))
    assert not math_tex.is_balanced(_old_pipeline(JEE_Q5))
