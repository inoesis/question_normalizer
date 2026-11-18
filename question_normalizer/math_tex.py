"""Stage 4 — KaTeX-compatibility normalization for LaTeX spans.

The library normalizes LaTeX source only; rendering stays in the client.

Order:
  1. Detect math spans (delimiters $...$, $$...$$, \\(\\), \\[\\]).
  2. Normalize delimiters to $...$ / $$...$$.
  3. Map \\rm{...} → \\mathrm{...} (very common scraped variant).
  4. Clean malformed sequences inside math spans (stray ", ;" → ";", etc).
  5. Balance check: if unbalanced, leave the original string unchanged.
"""

from __future__ import annotations

import logging
import re
from typing import Callable

from . import config

_log = logging.getLogger(config.LOGGER_NAME)

# Delimiter pairs in priority order (longest first to avoid $$ being
# eaten by single-$ matching).
_DELIMS: tuple[tuple[str, str, bool], ...] = (
    ("$$", "$$", True),
    (r"\[", r"\]", True),
    (r"\(", r"\)", False),
    ("$", "$", False),
)


def _find_next_span(text: str, start: int) -> tuple[int, int, str, bool] | None:
    """Return (open_start, close_end_exclusive, inner, is_display) or None.

    Picks the earliest opening delimiter; for tie at the same index we
    prefer the longer delimiter.
    """
    best: tuple[int, int, str, bool] | None = None
    for left, right, display in _DELIMS:
        pos = text.find(left, start)
        if pos == -1:
            continue
        # For single-$, skip if part of a $$ run (already covered above).
        if left == "$":
            if pos > 0 and text[pos - 1] == "$":
                continue
            if pos + 1 < len(text) and text[pos + 1] == "$":
                continue
        end = text.find(right, pos + len(left))
        if end == -1:
            continue
        if left == "$" and end + 1 < len(text) and text[end + 1] == "$":
            continue
        candidate = (pos, end + len(right), text[pos + len(left) : end], display)
        if best is None or candidate[0] < best[0] or (
            candidate[0] == best[0] and len(left) > (best[1] - best[0] - len(text[best[0] : best[0] + 2]))
        ):
            # The tie-break above prefers a longer left delimiter at the
            # same index. In practice $$ always wins over $ this way.
            best = candidate
    return best


# QUIC-209: math spans are set aside while the HTML stages run, so a "<"
# inside them ("0<x") is never read as the start of a tag. The placeholder
# uses Private Use Area characters, which no question legitimately contains.
_PH_OPEN, _PH_CLOSE = "\ue000", "\ue001"
_PLACEHOLDER_RE = re.compile(f"{_PH_OPEN}(\\d+){_PH_CLOSE}")


# A real tag (or comment) written out in full. "0<x \\leq 2" has no closing
# ">" so it is not one; "<b>", "</sup>", "<br/>" are.
# "<\s*" because html_repair turns "< img ...>" into a real <img> tag.
_MARKUP_RE = re.compile(r"<\s*(?:/?[a-zA-Z][a-zA-Z0-9-]*(?:[\s/][^<>]*)?/?>|!--)")
# Text ending inside an open tag, e.g. '<img alt="' - a "$" there belongs to
# an attribute, not to math.
_OPEN_TAG_AT_END_RE = re.compile(r"<\s*[a-zA-Z/!][^>]*$")


def protect(text: str) -> tuple[str, list[str]]:
    """Replace each math span that is plainly math with a placeholder.

    Only spans in text (not inside a tag) and with no real HTML in or across
    them are set aside: those are where a "<" ("0<x") would otherwise be read
    as a tag. Anything else - a "$" inside an attribute, currency like "$5 <b>x</b>
    $10", "$x<sup>2</sup>$" - is left for the HTML stages, as before.
    Returns ``(text_with_placeholders, spans)``. Any U+E000/U+E001 already in
    the input is dropped, so only our own placeholders reach restore().
    """
    text = text.replace(_PH_OPEN, "").replace(_PH_CLOSE, "")
    spans: list[str] = []
    parts: list[str] = []
    pos = 0
    while (span := _find_next_span(text, pos)) is not None:
        open_start, close_end, _inner, _display = span
        parts.append(text[pos:open_start])
        raw = text[open_start:close_end]
        # Skip it if it starts inside a tag, or a tag starts inside it (even
        # one that only closes after the span: "$<img alt="$...">").
        tag = _MARKUP_RE.search(text, open_start)
        if _OPEN_TAG_AT_END_RE.search("".join(parts)) or (tag and tag.start() < close_end):
            parts.append(raw)
        else:
            parts.append(f"{_PH_OPEN}{len(spans)}{_PH_CLOSE}")
            spans.append(raw)
        pos = close_end
    parts.append(text[pos:])
    return "".join(parts), spans


def restore(text: str, spans: list[str]) -> str:
    """Put the spans back. ``spans`` arrive already cleaned as text (see
    pipeline._clean_html). A placeholder can't end up inside a tag - protect()
    skips spans there - but if one ever did, its quotes are escaped too, so it
    could never close the attribute."""

    def _back(m: re.Match[str]) -> str:
        span = spans[int(m.group(1))]
        if _OPEN_TAG_AT_END_RE.search(text, 0, m.start()):
            span = span.replace('"', "&quot;")
        return span

    return _PLACEHOLDER_RE.sub(_back, text)


_RM_RE = re.compile(r"\\rm\s*\{")
_STRAY_SEP_RE = re.compile(r",\s*;")
_MULTISPACE_RE = re.compile(r"\s{2,}")


def _normalize_math_source(inner: str) -> str:
    """Apply source-level fixes inside a math span."""
    # \rm{...} → \mathrm{...}
    inner = _RM_RE.sub(r"\\mathrm{", inner)
    # stray ", ;" → ";"
    inner = _STRAY_SEP_RE.sub(";", inner)
    # Collapse runs of whitespace
    inner = _MULTISPACE_RE.sub(" ", inner)
    return inner


def _try_balanced(text: str) -> bool:
    """Cheap balance check on the four delimiter pairs.

    Returns True if every opener has a closer in a left-to-right scan.
    """
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "\\" and i + 1 < n and text[i + 1] in "([":
            close = ")" if text[i + 1] == "(" else "]"
            end = text.find("\\" + close, i + 2)
            if end == -1:
                return False
            i = end + 2
            continue
        if ch == "$":
            # Detect $$ vs $
            if i + 1 < n and text[i + 1] == "$":
                end = text.find("$$", i + 2)
                if end == -1:
                    return False
                i = end + 2
            else:
                end = text.find("$", i + 1)
                if end == -1:
                    return False
                i = end + 1
            continue
        i += 1
    return True


def is_balanced(text: str) -> bool:
    """True when every math delimiter in ``text`` is closed. A stored question
    cut short at a "<" inside math (QUIC-209) fails this check."""
    return _try_balanced(text)


def normalize(text: str, qid: str | None = None) -> str:
    """Return ``text`` with math spans normalized.

    If delimiters are unbalanced, returns the input unchanged and logs a
    MathWarning at INFO level (per spec — do not raise).
    """
    if not text:
        return text
    if not _try_balanced(text):
        _log.info("math.unbalanced qid=%s", qid)
        return text

    parts: list[str] = []
    pos = 0
    while True:
        span = _find_next_span(text, pos)
        if span is None:
            parts.append(text[pos:])
            break
        open_start, close_end, inner, is_display = span
        parts.append(text[pos:open_start])
        normalized_inner = _normalize_math_source(inner)
        wrapper_open = "$$" if is_display else "$"
        wrapper_close = "$$" if is_display else "$"
        parts.append(f"{wrapper_open}{normalized_inner}{wrapper_close}")
        pos = close_end
    return "".join(parts)
