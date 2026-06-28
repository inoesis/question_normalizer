"""Stage 2 — Allowlist sanitization.

Delegates to ``bleach`` (and ``tinycss2`` via ``bleach.css_sanitizer``) so
the security boundary stays in a well-audited library. Configuration is
data-driven from :mod:`question_normalizer.config`.

Note: ``bleach.css_sanitizer`` enforces the property allowlist but does
not strip dangerous CSS functions inside ALLOWED values (``url(...)``,
``expression(...)``, ``@import``). We do that in a small post-pass.
"""

from __future__ import annotations

import re

import bleach
from bleach.css_sanitizer import CSSSanitizer

from . import config

# Build the CSS sanitizer once. Property allowlist is enforced here.
_css_sanitizer = CSSSanitizer(
    allowed_css_properties=tuple(sorted(config.ALLOWED_CSS_PROPERTIES)),
    allowed_svg_properties=(),
)

# Match the dangerous CSS functions/at-rules anywhere inside an inline style.
_DANGEROUS_CSS_RE = re.compile(
    r"""
    (?:url|expression)\s*\([^)]*\)   # url(...) or expression(...)
    |
    @import[^;]*;?                    # @import …;
    """,
    re.IGNORECASE | re.VERBOSE,
)
_STYLE_ATTR_RE = re.compile(
    r"""(style\s*=\s*)(?:"([^"]*)"|'([^']*)')""",
    re.IGNORECASE,
)


def _strip_dangerous_css(html: str) -> str:
    """Remove ``url(...)``, ``expression(...)``, and ``@import`` from every
    ``style="..."`` attribute. Idempotent."""

    def _rewrite(m: re.Match[str]) -> str:
        prefix = m.group(1)
        value = m.group(2) if m.group(2) is not None else m.group(3) or ""
        cleaned = _DANGEROUS_CSS_RE.sub("", value)
        # Collapse any leftover empty declarations like `background:; color:red`
        cleaned = re.sub(r"[a-zA-Z-]+\s*:\s*;", "", cleaned)
        cleaned = re.sub(r";\s*;", ";", cleaned).strip()
        # Keep the same quote style the source used (default to double).
        quote = '"' if m.group(2) is not None else "'"
        return f"{prefix}{quote}{cleaned}{quote}"

    return _STYLE_ATTR_RE.sub(_rewrite, html)


# Bleach takes attributes either as a list (global allow) or a dict keyed
# by tag. We feed the dict form because we want different allowed attrs
# per tag — `img`'s src/loading should only apply on img, etc.
_bleach_kwargs = {
    "tags": tuple(sorted(config.ALLOWED_TAGS)),
    "attributes": {k: list(v) for k, v in config.ALLOWED_ATTRIBUTES.items()},
    "protocols": tuple(sorted(config.ALLOWED_URL_SCHEMES)),
    "strip": True,           # drop disallowed tags entirely, don't escape
    "strip_comments": True,
    "css_sanitizer": _css_sanitizer,
}


def sanitize(html: str) -> str:
    """Run the allowlist sanitizer. Idempotent."""
    if not html:
        return ""
    cleaned = bleach.clean(html, **_bleach_kwargs)
    return _strip_dangerous_css(cleaned)
