"""MCP filesystem path boundary — approved repo roots only (security fix 4).

Used by orama MCP servers and hygiene tooling. Mirrors Perpetua-Tools
``packages/local-agents/src/path-boundary.js`` policy.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

_REDACTED = "[REDACTED]"
_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{30,}\b"),
    re.compile(r"\bghp_[0-9A-Za-z]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._-]{20,}\b", re.IGNORECASE),
)
_EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_ENV_ASSIGNMENT = re.compile(
    r"^(\s*(?:SETUP_PASSWORD|API_KEY|TOKEN|SECRET|PASSWORD)\s*=\s*).+$",
    re.IGNORECASE | re.MULTILINE,
)

_ROOT_ENV_KEYS = (
    "MCP_APPROVED_ROOTS",
    "ALPHACLAW_ROOT",
    "PERPETUA_TOOLS_ROOT",
    "ORAMA_SYSTEM_ROOT",
    "OPENCLAW_ROOT",
)


def _split_env_roots(value: str | None) -> list[Path]:
    if not value:
        return []
    parts = []
    for chunk in value.split(os.pathsep):
        chunk = chunk.strip()
        if chunk:
            parts.append(Path(chunk).expanduser().resolve())
    return parts


def get_approved_roots(*extra: str | Path) -> list[Path]:
    """Return deduplicated absolute roots for MCP file/log reads."""
    roots: list[Path] = []
    for key in _ROOT_ENV_KEYS:
        roots.extend(_split_env_roots(os.environ.get(key)))
    for item in extra:
        if item:
            roots.append(Path(item).expanduser().resolve())
    if not roots:
        # orama-system repo root (utils/..)
        roots.append(Path(__file__).resolve().parents[1])
    seen: set[Path] = set()
    out: list[Path] = []
    for root in roots:
        if root not in seen:
            seen.add(root)
            out.append(root)
    return out


def _realpath_safe(target: Path) -> Path:
    try:
        return target.resolve(strict=True) if target.exists() else target.resolve()
    except OSError:
        return target.resolve()


def _is_under_root(resolved: Path, root: Path) -> bool:
    try:
        _realpath_safe(resolved).relative_to(_realpath_safe(root))
        return True
    except ValueError:
        return False


def resolve_allowed_path(
    input_path: str | Path,
    *,
    roots: list[Path] | None = None,
    must_exist: bool = True,
    base_for_relative: Path | None = None,
) -> tuple[bool, Path | None, str | None]:
    """Resolve path; return (ok, absolute_path, error_message)."""
    if input_path is None or (isinstance(input_path, str) and not input_path.strip()):
        return False, None, "path required"
    raw = str(input_path)
    if "\0" in raw:
        return False, None, "invalid path"

    approved = roots if roots is not None else get_approved_roots()
    if not approved:
        return False, None, "no approved MCP roots configured"

    base = base_for_relative or approved[0]
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = (base / candidate).resolve()
    else:
        candidate = candidate.resolve()

    matched: Path | None = None
    for root in approved:
        if _is_under_root(candidate, root):
            matched = root
            break
    if matched is None:
        return False, None, f"path outside approved MCP roots: {candidate}"

    if not must_exist:
        return True, candidate, None

    if not candidate.exists():
        return False, None, f"path not found: {candidate}"

    try:
        real = candidate.resolve(strict=True)
    except OSError as exc:
        return False, None, str(exc)

    if not _is_under_root(real, matched):
        return False, None, "path escapes approved root via symlink"

    return True, real, None


def redact_log_text(text: str) -> str:
    """Redact secrets and emails from log/file text before MCP exposure."""
    if not text:
        return text
    out = text
    for pattern in _SECRET_PATTERNS:
        out = pattern.sub(_REDACTED, out)
    out = _EMAIL_PATTERN.sub(_REDACTED, out)
    out = _ENV_ASSIGNMENT.sub(rf"\1{_REDACTED}", out)
    return out
