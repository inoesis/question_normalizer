"""Stage 1 — html_repair."""

from question_normalizer.html_repair import merge_duplicate_attributes, repair


def test_duplicate_style_merge_keeps_both_properties():
    src = '<div style="font-size:15px;" style="margin-bottom:8px;">x</div>'
    out = merge_duplicate_attributes(src)
    assert 'style="font-size:15px; margin-bottom:8px"' in out


def test_duplicate_style_conflicting_property_last_wins():
    src = '<div style="color:red;" style="color:blue;">x</div>'
    out = merge_duplicate_attributes(src)
    assert "color:blue" in out
    assert out.count("color") == 1  # not both


def test_non_style_duplicate_keeps_first():
    src = '<div class="a" class="b">x</div>'
    out = merge_duplicate_attributes(src)
    # Bleach would lose 'class' later in Stage 2, but Stage 1 must
    # keep first for any duplicate attr.
    assert 'class="a"' in out
    assert 'class="b"' not in out


def test_repair_is_noop_on_already_clean():
    src = '<div style="color:red"><p>hi</p></div>'
    out = repair(src)
    # Idempotency at Stage 1 — running twice equals running once.
    assert repair(out) == out
