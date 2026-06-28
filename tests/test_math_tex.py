"""Stage 4 — math_tex."""

from question_normalizer.math_tex import normalize


def test_rm_maps_to_mathrm():
    out = normalize("${\\rm{A - Q, S}}$")
    assert "\\mathrm{" in out
    assert "\\rm{" not in out


def test_stray_comma_semicolon_collapsed():
    out = normalize("$\\mathrm{Q}, ; \\mathrm{B}$")
    assert ", ;" not in out
    assert ";" in out


def test_inline_dollar_passthrough():
    out = normalize("text $x^2$ tail")
    assert out == "text $x^2$ tail"


def test_unbalanced_passthrough():
    src = "this has an unmatched $ dollar sign"
    assert normalize(src) == src


def test_outside_math_untouched():
    # spaces outside math spans must NOT be collapsed
    out = normalize("a  b   $x$  c")
    assert "a  b" in out


def test_idempotent():
    src = "${\\rm{A}}-{\\rm{B}}$"
    once = normalize(src)
    twice = normalize(once)
    assert once == twice


def test_display_double_dollar():
    out = normalize("text $$x^2$$ tail")
    assert "$$x^2$$" in out


def test_display_backslash_bracket():
    out = normalize("text \\[x^2\\] tail")
    # display delimiters get canonicalised to $$..$$
    assert "$$x^2$$" in out


def test_inline_backslash_paren():
    out = normalize("text \\(x^2\\) tail")
    assert "$x^2$" in out


def test_unbalanced_double_dollar_passthrough():
    src = "open $$x but no close"
    assert normalize(src) == src


def test_empty_string_safe():
    assert normalize("") == ""


def test_no_math_at_all():
    assert normalize("plain prose with no maths") == "plain prose with no maths"
