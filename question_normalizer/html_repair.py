"""Stage 1 — Structural pre-clean.

This stage runs BEFORE any HTML parser. Parsers silently drop the artifacts
we need to fix (duplicate `style` attrs in particular), so the duplicate
merge has to be a string/regex pre-pass.

Order:
  1. Merge duplicate `style` attributes on a tag (last-wins on conflicts).
  2. De-duplicate other repeated attributes (first wins).
  3. Tag balance/close via a forgiving parser (lxml or html5lib).
  4. Collapse insignificant whitespace between block tags.
"""

from __future__ import annotations

import re
from typing import Iterable

# A tag opener with at least one attribute. Captures the opening, attr
# block, and self-close/close marker. Single quotes also accepted.
_TAG_RE = re.compile(
    r"""
    (<                               # opening bracket
      \s*([a-zA-Z][a-zA-Z0-9-]*)     # group(2): tag name
      \b                              # word boundary
      ([^>]*?)                        # group(3): attribute soup
      (/?)>                           # group(4): optional self-close
    )
    """,
    re.VERBOSE | re.DOTALL,
)

# Single attribute: name = "value" | 'value' | bareword | name-with-no-value.
_ATTR_RE = re.compile(
    r"""
    \s*([a-zA-Z_:][-a-zA-Z0-9_:.]*)   # group(1): attribute name
    (?:                                # optional value
      \s*=\s*
      (?:
        "([^"]*)"                      # group(2): dq value
        |
        '([^']*)'                      # group(3): sq value
        |
        ([^\s"'=<>`]+)                 # group(4): unquoted value
      )
    )?
    """,
    re.VERBOSE,
)


def _parse_attrs(attr_blob: str) -> list[tuple[str, str | None]]:
    """Return [(name, value_or_None), ...] preserving source order."""
    out: list[tuple[str, str | None]] = []
    pos = 0
    while pos < len(attr_blob):
        m = _ATTR_RE.match(attr_blob, pos)
        if not m or m.end() == pos:
            pos += 1
            continue
        name = m.group(1).lower()
        value = m.group(2) if m.group(2) is not None else m.group(3) if m.group(3) is not None else m.group(4)
        out.append((name, value))
        pos = m.end()
    return out


def _merge_style_declarations(values: Iterable[str]) -> str:
    """Merge multiple ``style`` attribute values into one string.

    Declarations are concatenated with ``; ``. Identical declarations are
    de-duplicated; when two declarations target the SAME CSS property,
    last-wins (matching what a single style="" with two properties would
    do, and avoiding the browser's first-wins-then-drop behaviour for
    duplicate ATTRIBUTES).
    """
    by_prop: dict[str, str] = {}
    order: list[str] = []
    for raw in values:
        for decl in raw.split(";"):
            decl = decl.strip()
            if not decl or ":" not in decl:
                continue
            prop, _, val = decl.partition(":")
            prop = prop.strip().lower()
            val = val.strip()
            if prop not in by_prop:
                order.append(prop)
            by_prop[prop] = val
    return "; ".join(f"{p}:{by_prop[p]}" for p in order)


def _serialize_attrs(attrs: list[tuple[str, str | None]]) -> str:
    parts: list[str] = []
    for name, value in attrs:
        if value is None:
            parts.append(name)
        else:
            # Escape any double-quote in value to keep the wrapping valid.
            safe = value.replace('"', "&quot;")
            parts.append(f'{name}="{safe}"')
    return " ".join(parts)


def merge_duplicate_attributes(html: str) -> str:
    """Stage 1.1 + 1.2 — collapse duplicate attributes inside each tag."""

    def _rewrite(m: re.Match[str]) -> str:
        tag_name = m.group(2)
        attr_blob = m.group(3)
        self_close = m.group(4)
        attrs = _parse_attrs(attr_blob)
        if not attrs:
            return m.group(0)

        # Bucket by name; for `style` we merge, for others we keep-first.
        seen: dict[str, str | None] = {}
        order: list[str] = []
        style_values: list[str] = []
        for name, value in attrs:
            if name == "style":
                if value is not None:
                    style_values.append(value)
                if name not in seen:
                    order.append(name)
                    seen[name] = None  # placeholder; final value set below
            else:
                if name not in seen:
                    order.append(name)
                    seen[name] = value

        if style_values:
            seen["style"] = _merge_style_declarations(style_values)

        rebuilt = _serialize_attrs([(n, seen[n]) for n in order])
        prefix = "<" + tag_name + (" " + rebuilt if rebuilt else "")
        return prefix + ("/" if self_close else "") + ">"

    return _TAG_RE.sub(_rewrite, html)


def balance_tags(html: str) -> str:
    """Stage 1.3 — feed through a forgiving parser to close stray tags.

    Returns a fragment (no <html>/<body> wrappers).
    """
    if not html.strip():
        return html
    try:
        # Local import so the module loads even if lxml is missing at
        # import time (tests using pure-python paths still work).
        from lxml import html as lxml_html  # type: ignore

        # `fragments_fromstring` keeps fragment semantics. We wrap to guarantee
        # a single root for serialization, then strip the wrapper back out.
        wrapper = lxml_html.fragment_fromstring(html, create_parent="qn-wrap")
        rendered = lxml_html.tostring(wrapper, encoding="unicode")
        # Strip the synthetic wrapper tags.
        inner = re.sub(r"^<qn-wrap[^>]*>|</qn-wrap>$", "", rendered.strip())
        return inner
    except Exception:
        # Fallback: hand back the input unchanged. Stage 2 will sanitize.
        return html


_BLOCK_WS_RE = re.compile(r">\s+<")


def collapse_block_whitespace(html: str) -> str:
    """Stage 1.4 — collapse whitespace between adjacent tags only."""
    return _BLOCK_WS_RE.sub("><", html)


def repair(html: str) -> str:
    """Apply all Stage 1 transforms in order. Pure function."""
    if not html:
        return html
    html = merge_duplicate_attributes(html)
    html = balance_tags(html)
    html = collapse_block_whitespace(html)
    return html
