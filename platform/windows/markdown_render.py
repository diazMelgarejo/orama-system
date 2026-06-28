"""Minimal safe markdown → HTML for LAN peer inbox previews (Windows lane, no CDN)."""
from __future__ import annotations

import html
import re

_BLOCK_RE = re.compile(
    r"```(\w*)\n(.*?)```",
    re.DOTALL,
)
_HEADER_RE = [
    (re.compile(r"^###### (.+)$", re.MULTILINE), r"<h6>\1</h6>"),
    (re.compile(r"^##### (.+)$", re.MULTILINE), r"<h5>\1</h5>"),
    (re.compile(r"^#### (.+)$", re.MULTILINE), r"<h4>\1</h4>"),
    (re.compile(r"^### (.+)$", re.MULTILINE), r"<h3>\1</h3>"),
    (re.compile(r"^## (.+)$", re.MULTILINE), r"<h2>\1</h2>"),
    (re.compile(r"^# (.+)$", re.MULTILINE), r"<h1>\1</h1>"),
]
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_UL_RE = re.compile(r"^[-*] (.+)$", re.MULTILINE)


def markdown_to_html(text: str) -> str:
    """Escape-first markdown subset suitable for peer assignment previews."""
    if not text:
        return "<p><em>(empty)</em></p>"

    parts: list[str] = []
    last = 0
    for match in _BLOCK_RE.finditer(text):
        before = text[last : match.start()]
        if before:
            parts.append(_render_inline_block(before))
        code = html.escape(match.group(2).rstrip("\n"))
        parts.append(f"<pre><code>{code}</code></pre>")
        last = match.end()
    tail = text[last:]
    if tail:
        parts.append(_render_inline_block(tail))
    return "\n".join(parts) if parts else _render_inline_block(text)


def _render_inline_block(block: str) -> str:
    escaped = html.escape(block)
    for pattern, repl in _HEADER_RE:
        escaped = pattern.sub(repl, escaped)
    escaped = _UL_RE.sub(r"<li>\1</li>", escaped)
    if "<li>" in escaped:
        escaped = re.sub(
            r"(?:<li>.*?</li>\n?)+",
            lambda m: f"<ul>{m.group(0)}</ul>",
            escaped,
            flags=re.DOTALL,
        )
    escaped = _LINK_RE.sub(
        lambda m: (
            f'<a href="{html.escape(m.group(2), quote=True)}" '
            f'rel="noopener noreferrer">{m.group(1)}</a>'
        ),
        escaped,
    )
    escaped = _BOLD_RE.sub(r"<strong>\1</strong>", escaped)
    escaped = _INLINE_CODE_RE.sub(r"<code>\1</code>", escaped)
    paragraphs = [
        f"<p>{chunk.strip()}</p>"
        for chunk in re.split(r"\n\s*\n", escaped)
        if chunk.strip()
    ]
    return "\n".join(paragraphs) if paragraphs else f"<p>{escaped}</p>"
