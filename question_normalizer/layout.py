"""Stage 3 — Layout preservation guarantees.

Detection-only where possible. Never invents or restructures content.
The five spec types each carry their layout in the markup the sanitizer
already permits; this stage just enforces small idempotent guarantees
(e.g. ``alt`` and ``loading`` on figure ``<img>``) and never adds content.
"""

from __future__ import annotations

import re

# Inject loading="lazy" + a default alt="" on any <img> that's missing them.
_IMG_TAG_RE = re.compile(r"<img\b([^>]*?)/?>", re.IGNORECASE)
_HAS_ALT_RE = re.compile(r"\balt\s*=", re.IGNORECASE)
_HAS_LOADING_RE = re.compile(r"\bloading\s*=", re.IGNORECASE)


def _augment_img(match: re.Match[str]) -> str:
    attrs = match.group(1)
    additions = []
    if not _HAS_ALT_RE.search(attrs):
        additions.append('alt=""')
    if not _HAS_LOADING_RE.search(attrs):
        additions.append('loading="lazy"')
    if not additions:
        return match.group(0)
    sep = "" if attrs.endswith(" ") or not attrs else " "
    return f"<img{attrs}{sep}{' '.join(additions)}>"


def ensure_image_attributes(html: str) -> str:
    """Idempotent: <img> gets alt="" and loading="lazy" if missing."""
    if "<img" not in html.lower():
        return html
    return _IMG_TAG_RE.sub(_augment_img, html)


def preserve(html: str, render_type: str | None = None) -> str:
    """Apply layout guarantees. ``render_type`` is advisory; if unknown we
    infer conservatively from structure but never rewrite layout.
    """
    if not html:
        return html
    # Figure: keep <img>'s alt + loading. The other types carry layout in
    # tags/styles that survive sanitization untouched, so no further
    # rewrites are needed.
    html = ensure_image_attributes(html)
    return html
