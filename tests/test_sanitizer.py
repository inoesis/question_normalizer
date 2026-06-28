"""Stage 2 — sanitizer."""

from question_normalizer.sanitizer import sanitize


def test_strip_script_tag():
    assert "<script" not in sanitize('<div>hi<script>alert(1)</script></div>').lower()


def test_strip_event_handler():
    out = sanitize('<img src="https://x/y.png" onerror="alert(1)">')
    assert "onerror" not in out.lower()
    assert "https://x/y.png" in out


def test_javascript_href_stripped():
    out = sanitize('<a href="javascript:alert(1)">click</a>')
    assert "javascript" not in out.lower()


def test_inline_style_preserved():
    out = sanitize('<div style="font-size:15px; color:#c0392b;">x</div>')
    assert "font-size" in out
    assert "color" in out


def test_css_url_function_stripped():
    out = sanitize('<div style="background: url(javascript:1)">x</div>')
    assert "url(" not in out.lower()


def test_data_image_url_allowed():
    out = sanitize('<img src="data:image/png;base64,iVBOR" alt="x">')
    assert "data:image" in out
