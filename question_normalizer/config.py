"""Allowlists and constants shared by the pipeline stages.

These are data, not code. Extending the allowed markup is a config change.
"""

from __future__ import annotations

# ── Stage 2: tag allowlist ──────────────────────────────────────────────────
ALLOWED_TAGS: frozenset[str] = frozenset(
    {
        "div",
        "span",
        "p",
        "br",
        "b",
        "strong",
        "i",
        "em",
        "u",
        "sub",
        "sup",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
        "ul",
        "ol",
        "li",
        "img",
    }
)

# Per-tag attribute allowlist. The implicit global allow is `style` (handled
# below). Tags not listed here get no attributes beyond `style`.
ALLOWED_ATTRIBUTES: dict[str, list[str]] = {
    "*": ["style"],
    "img": ["src", "alt", "loading", "width", "height", "style"],
    "th": ["colspan", "rowspan", "style"],
    "td": ["colspan", "rowspan", "style"],
}

# Allowed schemes for any URL-bearing attribute (notably img.src). data:image
# is permitted so base64 placeholders survive sanitization.
ALLOWED_URL_SCHEMES: frozenset[str] = frozenset({"http", "https", "data"})

# Allowed CSS properties for inline style attributes. Anything outside this
# list is dropped at sanitization time (Stage 2).
ALLOWED_CSS_PROPERTIES: frozenset[str] = frozenset(
    {
        "color",
        "background",
        "background-color",
        "border",
        "border-left",
        "border-right",
        "border-top",
        "border-bottom",
        "border-radius",
        "border-collapse",
        "padding",
        "padding-left",
        "padding-right",
        "padding-top",
        "padding-bottom",
        "margin",
        "margin-left",
        "margin-right",
        "margin-top",
        "margin-bottom",
        "font-size",
        "font-weight",
        "font-style",
        "font-family",
        "line-height",
        "letter-spacing",
        "text-align",
        "vertical-align",
        "width",
        "max-width",
        "min-width",
        "height",
        "max-height",
        "display",
        "white-space",
    }
)

# Always stripped tags. Bleach removes them by virtue of not being in
# ALLOWED_TAGS, but we list these to keep intent visible.
ALWAYS_STRIPPED_TAGS: frozenset[str] = frozenset({"script", "style", "iframe", "object", "embed"})

# Event-handler attribute prefix (any `on*` attribute is dropped).
EVENT_HANDLER_PREFIX = "on"

# Strict 3-key output. The spec flags this as up-for-review; default is
# False (preserve metadata like `render_type`, `QB_id`).
STRICT_OUTPUT_KEYS: bool = False

# Library logger name. Per spec the library never configures handlers.
LOGGER_NAME = "question_normalizer"
