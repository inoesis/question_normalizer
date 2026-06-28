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
