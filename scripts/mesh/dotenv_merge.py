"""Integrative dotenv harmonization — fill missing/empty keys only; never delete or replace."""

from __future__ import annotations

import os
import re
from pathlib import Path

_KEY_LINE_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")


def _is_empty_value(raw: str) -> bool:
    value = raw.strip()
    if not value:
        return True
    if value.startswith(('"', "'")) and value.endswith(('"', "'")) and len(value) >= 2:
        return not value[1:-1].strip()
    return False


def harmonize_dotenv_keys(
    path: Path,
    values: dict[str, str],
    *,
    managed_keys: frozenset[str] | None = None,
    header_comment: str | None = None,
) -> list[str]:
    """Merge managed keys into a dotenv file without removing comments or existing values.

    - Preserves every existing line (comments, blanks, ordering).
    - Updates a managed key only when its current value is empty.
    - Appends keys that are absent (additive).
    - Never overwrites a non-empty operator value.
    """
    keys = managed_keys if managed_keys is not None else frozenset(values)
    pending = {k: v for k, v in values.items() if k in keys and v}
    touched: list[str] = []

    if not path.is_file():
        lines: list[str] = []
        if header_comment:
            lines.extend(header_comment.splitlines())
            if lines and lines[-1] != "":
                lines.append("")
        for key in sorted(pending):
            lines.append(f"{key}={pending.pop(key)}")
            touched.append(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        return touched

    original = path.read_text(encoding="utf-8")
    lines = original.splitlines()
    seen: set[str] = set()
    out: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            out.append(line)
            continue
        match = _KEY_LINE_RE.match(line)
        if not match:
            out.append(line)
            continue
        key, raw_value = match.group(1), match.group(2)
        if key not in keys:
            out.append(line)
            continue
        seen.add(key)
        if key in pending and _is_empty_value(raw_value):
            out.append(f"{key}={pending.pop(key)}")
            touched.append(key)
        else:
            out.append(line)

    if pending:
        if out and out[-1] != "":
            out.append("")
        if header_comment and not any(header_comment.splitlines()[0] in ln for ln in out):
            out.extend(header_comment.splitlines())
        for key in sorted(pending):
            out.append(f"{key}={pending[key]}")
            touched.append(key)

    new_text = "\n".join(out) + ("\n" if out else "")
    if new_text != original:
        path.write_text(new_text, encoding="utf-8")
    return touched
