#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import os
import re
import subprocess
import sys
from pathlib import Path


APPROVED_IDENTITIES = {
    ("cyre", "Lawrence@cyre.me"),
    ("cyre", "diazMelgarejo@gmail.com"),
    ("Codex", "codex@openai.com"),
}
FORBIDDEN_TOKENS = (
    "Lawrence " + "Melgarejo",
    "Lawrence" + "@bettermind.ph",
)
IDENTITY_DOC_EXCEPTIONS = {
    ".mailmap",
    "docs/wiki/08-git-hygiene-and-branching.md",
    # v2 spec doc — quotes forbidden tokens as YAML config examples, not leaks
    "docs/v2/11-idempotency-and-guard-patterns.md",
}
# Personal-path leak protection (OpSec) — block any tracked file from containing
# an absolute path under /Users/<anything>/ or /home/<anything>/. Developer
# workstation paths in public docs are a dox risk and hurt portability.
# Pattern intentionally matches the username segment so the check fails even
# if someone copies a teammate's path. Use ~, $REPO_ROOT, or <workspace> instead.
PERSONAL_PATH_PATTERN = re.compile(r"(/Users/|/home/)([A-Za-z][A-Za-z0-9._-]+)/")
# Username segments that are documentation placeholders, not real leaks.
# These appear in .paths.example, skill protocol docs, etc., and should be
# allowed so example commands stay readable. A real workstation username
# like "lawrencecyremelgarejo" will not match this set.
PERSONAL_PATH_PLACEHOLDERS = frozenset({
    "you", "user", "example", "username", "name", "youruser", "yourname",
    "<user>", "<username>", "USERNAME", "USER",
})
PERSONAL_PATH_EXCEPTIONS = {
    # The script itself names the pattern in source as documentation.
    "scripts/review/repo_hygiene.py",
    # Hygiene test asserts the rule against fixture content — must contain
    # a sample personal path to verify detection.
    "tests/test_repo_hygiene.py",
}
# Machine-specific OpenClaw workstation layout — never commit; use $OPENCLAW_ROOT,
# detect_openclaw_root(), or ~-relative placeholders in docs.
OPENCLAW_WORKSTATION_LAYOUT = re.compile(
    r"(?:\$\{HOME\}|\$HOME|~)?/?Documents/Terminal\s+xCode/claude/OpenClaw"
)
OPENCLAW_WORKSTATION_EXCEPTIONS = {
    "scripts/review/repo_hygiene.py",
    "tests/test_repo_hygiene.py",
}
# Hidden / bidirectional Unicode controls — these can hide malicious code in
# diffs (Trojan-Source style). Block in all tracked files except the hygiene
# script and its tests, which name the codepoints for documentation.
BIDI_CONTROL_CHARS = {
    "‪": "LRE", "‫": "RLE", "‬": "PDF",
    "‭": "LRO", "‮": "RLO",
    "⁦": "LRI", "⁧": "RLI", "⁨": "FSI", "⁩": "PDI",
}
BIDI_CONTROL_EXCEPTIONS = {
    "scripts/review/repo_hygiene.py",
    "tests/test_repo_hygiene.py",
}
PRIVATE_GENERATED_TRACKED = {".env", ".env.local", ".paths"}
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
NEW_MARKDOWN_LINE_WARN = 200
EXISTING_MARKDOWN_LINE_WARN = 500
GENERATED_ARTIFACT_PATTERNS = (
    ".DS_Store",
    "*/.DS_Store",
    "._*",
    "*/._*",
    "__pycache__/*",
    "*/__pycache__/*",
    "*.pyc",
    "*.pyo",
    ".pytest_cache/*",
    "*/.pytest_cache/*",
    ".mypy_cache/*",
    "*/.mypy_cache/*",
    "dist/*",
    "*/dist/*",
    "build/*",
    "*/build/*",
    "DerivedData/*",
    "*/DerivedData/*",
    "*.egg-info/*",
    "*.whl",
    "*.tar.gz",
    "*.xcuserstate",
    "*.xcscmblueprint",
    "*.xcodeproj/xcuserdata/*",
    "*.xcworkspace/xcuserdata/*",
    "*.xcuserdatad/*",
)
WORKFLOW_WRITE_MARKERS = (
    "softprops/action-gh-release",
    "peter-evans/create-pull-request",
    "gh pr",
    "gh release",
    "git push",
)
LEGACY_NAME = "ultrathink-system"
STALE_SKILL_REF_TOKENS = (
    "bin/" + "skills",
    "bin" + ".skills",
)
HISTORICAL_HINTS = (
    "previous identity",
    "renamed",
    "historical",
    "archive",
    "migration",
    "provenance",
    "carried over",
)
# High-confidence secret patterns — block literals in tracked files (pre-commit + CI).
# Placeholders like ${env:VAR} and documentation examples are allowed.
SECRET_PATTERN_EXCEPTIONS = {
    "scripts/review/repo_hygiene.py",
    "tests/test_repo_hygiene.py",
}
SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "google_api_key",
        re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
        "Google API key (AIza...)",
    ),
    (
        "telegram_bot_token",
        re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{30,}\b"),
        "Telegram bot token (bot_id:secret)",
    ),
    (
        "github_pat",
        re.compile(r"\bghp_[0-9A-Za-z]{20,}\b"),
        "GitHub personal access token",
    ),
    (
        "openai_api_key",
        re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
        "OpenAI API key",
    ),
    (
        "anthropic_api_key",
        re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b"),
        "Anthropic API key",
    ),
)
SECRET_PLACEHOLDER_MARKERS = (
    "${env:",
    "${ENV:",
    "<YOUR_",
    "<your_",
    "REPLACE_ME",
    "CHANGEME",
    "xxx",
)


def run_git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def tracked_files(root: Path) -> list[str]:
    proc = run_git(root, "ls-files")
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "git ls-files failed")
    return [line for line in proc.stdout.splitlines() if line]


def is_binary(path: Path) -> bool:
    try:
        chunk = path.read_bytes()[:4096]
    except OSError:
        return True
    return b"\0" in chunk


def scan_forbidden_identity(root: Path, files: list[str]) -> list[str]:
    errors: list[str] = []
    for rel in files:
        if rel in IDENTITY_DOC_EXCEPTIONS:
            continue
        path = root / rel
        if not path.is_file() or is_binary(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for token in FORBIDDEN_TOKENS:
            if token in text:
                errors.append(f"forbidden identity token in tracked file: {rel}")
                break
    return errors


def scan_openclaw_workstation_layout(root: Path, files: list[str]) -> list[str]:
    """Block committed references to the legacy machine-specific OpenClaw tree path."""
    errors: list[str] = []
    for rel in files:
        if rel in OPENCLAW_WORKSTATION_EXCEPTIONS:
            continue
        path = root / rel
        if not path.is_file() or is_binary(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            if not OPENCLAW_WORKSTATION_LAYOUT.search(line):
                continue
            errors.append(
                f"machine-specific OpenClaw path in tracked file: {rel}:{line_no} — "
                "use $OPENCLAW_ROOT, detect_openclaw_root(), or ORAMA_INSTALL_DIR"
            )
            break
    return errors


def scan_personal_paths(root: Path, files: list[str]) -> list[str]:
    """Block absolute /Users/<name>/ or /home/<name>/ paths in tracked files.

    Workstation paths in committed files are an OpSec leak (developer name,
    directory layout, sometimes machine hostname). They also break portability.
    Use ~, $REPO_ROOT, or <workspace> placeholders instead.
    """
    errors: list[str] = []
    for rel in files:
        if rel in PERSONAL_PATH_EXCEPTIONS:
            continue
        path = root / rel
        if not path.is_file() or is_binary(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            m = PERSONAL_PATH_PATTERN.search(line)
            if not m:
                continue
            # The captured username segment; allow well-known doc placeholders.
            username = m.group(2)
            if username in PERSONAL_PATH_PLACEHOLDERS:
                continue
            errors.append(
                f"personal absolute path in tracked file: {rel}:{line_no}: "
                f"matched {m.group(0)!r} — use ~, $REPO_ROOT, or <workspace>"
            )
            break
    return errors


def scan_bidi_controls(root: Path, files: list[str]) -> list[str]:
    """Block Unicode BiDi control characters (Trojan-Source defense).

    These invisible characters can reorder source code so the rendered
    text differs from the parsed AST. CVE-2021-42574. Mostly relevant
    in code, but markdown can hide them in code fences too.
    """
    errors: list[str] = []
    for rel in files:
        if rel in BIDI_CONTROL_EXCEPTIONS:
            continue
        path = root / rel
        if not path.is_file() or is_binary(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            for ch, name in BIDI_CONTROL_CHARS.items():
                if ch in line:
                    errors.append(
                        f"BiDi control char in tracked file: {rel}:{line_no}: "
                        f"U+{ord(ch):04X} ({name})"
                    )
                    break
            else:
                continue
            break
    return errors


def check_private_generated_tracking(files: list[str]) -> list[str]:
    return [
        f"private/generated config is tracked: {rel}"
        for rel in files
        if rel in PRIVATE_GENERATED_TRACKED
    ]


def check_markdown_link_hygiene(root: Path, files: list[str]) -> list[str]:
    errors: list[str] = []
    for rel in files:
        if not rel.endswith(".md"):
            continue
        path = root / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for target in MARKDOWN_LINK_PATTERN.findall(text):
            normalized = target.strip()
            if normalized.startswith("<") and normalized.endswith(">"):
                normalized = normalized[1:-1].strip()
            if normalized.startswith(("http://", "https://", "#", "mailto:")):
                continue
            if normalized.startswith("file://") or normalized.startswith("/") or re.match(r"^[A-Za-z]:[\\/]", normalized):
                errors.append(f"markdown link must be repo-relative: {rel} -> {normalized}")
    return errors


def changed_markdown_files(root: Path) -> set[str]:
    changed: set[str] = set()
    for args in (
        ("diff", "--name-only", "--diff-filter=ACMR", "HEAD", "--", "*.md"),
        ("diff", "--cached", "--name-only", "--diff-filter=ACMR", "HEAD", "--", "*.md"),
    ):
        proc = run_git(root, *args)
        if proc.returncode == 0:
            changed.update(line for line in proc.stdout.splitlines() if line.endswith(".md"))
    return changed


def exists_in_head(root: Path, rel: str) -> bool:
    proc = run_git(root, "cat-file", "-e", f"HEAD:{rel}")
    return proc.returncode == 0


def check_markdown_size_warnings(
    root: Path,
    files: list[str],
    changed: set[str] | None = None,
    existing: set[str] | None = None,
) -> list[str]:
    warnings: list[str] = []
    changed = changed_markdown_files(root) if changed is None else changed
    for rel in sorted(changed):
        if rel not in files or not rel.endswith(".md"):
            continue
        path = root / rel
        if not path.is_file():
            continue
        try:
            line_count = len(path.read_text(encoding="utf-8").splitlines())
        except UnicodeDecodeError:
            continue
        existed_before = rel in existing if existing is not None else exists_in_head(root, rel)
        if not existed_before and line_count > NEW_MARKDOWN_LINE_WARN:
            warnings.append(
                f"{rel} has {line_count} lines; new markdown files over "
                f"{NEW_MARKDOWN_LINE_WARN} lines should ask the user about offloading "
                "related content to references/ or sub-skills"
            )
        if existed_before and line_count > EXISTING_MARKDOWN_LINE_WARN:
            warnings.append(
                f"{rel} has {line_count} lines; existing markdown files over "
                f"{EXISTING_MARKDOWN_LINE_WARN} lines should ask the user about splitting "
                "or redirecting detailed content elsewhere"
            )
    return warnings


def check_generated_artifact_tracking(files: list[str]) -> list[str]:
    errors: list[str] = []
    for rel in files:
        if any(fnmatch.fnmatch(rel, pattern) for pattern in GENERATED_ARTIFACT_PATTERNS):
            errors.append(f"generated artifact is tracked: {rel}")
    return errors


def check_git_internal_junk(root: Path) -> list[str]:
    git_dir = root / ".git"
    refs_dir = git_dir / "refs"
    if not refs_dir.exists():
        return []
    return [
        f"macOS metadata file inside git refs: {path.relative_to(root)}"
        for path in refs_dir.rglob(".DS_Store")
    ]


def check_identity(root: Path) -> list[str]:
    name = run_git(root, "config", "user.name").stdout.strip()
    email = run_git(root, "config", "user.email").stdout.strip()
    if os.getenv("GITHUB_ACTIONS") == "true" and not name and not email:
        return []
    if (name, email) not in APPROVED_IDENTITIES:
        expected = " or ".join(f"{n} <{e}>" for n, e in sorted(APPROVED_IDENTITIES))
        return [
            "git identity mismatch: "
            f"found {name or '<unset>'} <{email or '<unset>'}>; "
            f"expected {expected}"
        ]
    return []


def check_ecc(root: Path, files: list[str]) -> list[str]:
    if ".ecc" not in files:
        return []
    ecc_path = root / ".ecc"
    mode = run_git(root, "ls-files", "-s", ".ecc").stdout.strip().split()
    is_gitlink = bool(mode and mode[0] == "160000")
    if is_gitlink and not (root / ".gitmodules").exists():
        return [".ecc is tracked as a gitlink but .gitmodules is absent"]
    if is_gitlink and ecc_path.is_symlink():
        return [".ecc is a gitlink in index but a symlink in the working tree"]
    return []


def check_workflow_permissions(root: Path) -> list[str]:
    errors: list[str] = []
    workflow_dir = root / ".github" / "workflows"
    if not workflow_dir.exists():
        return errors
    for path in sorted(workflow_dir.glob("*.y*ml")):
        text = path.read_text(encoding="utf-8")
        needs_write = any(marker in text for marker in WORKFLOW_WRITE_MARKERS)
        if not needs_write:
            continue
        rel = path.relative_to(root)
        if "contents: write" not in text and "pull-requests: write" not in text:
            errors.append(f"workflow may write but lacks explicit write permission: {rel}")
    return errors


def check_stale_skill_path_refs(root: Path, files: list[str]) -> list[str]:
    errors: list[str] = []
    for rel in files:
        path = root / rel
        if not path.is_file() or is_binary(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for token in STALE_SKILL_REF_TOKENS:
            if token in text:
                errors.append(f"stale skill path/module reference in tracked file: {rel} -> {token}")
                break
    return errors


def _line_has_secret_placeholder(line: str) -> bool:
    return any(marker in line for marker in SECRET_PLACEHOLDER_MARKERS)


def scan_tracked_secrets(root: Path, files: list[str]) -> list[str]:
    """Block committed API keys, bot tokens, and other high-confidence secrets."""
    errors: list[str] = []
    for rel in files:
        if rel in SECRET_PATTERN_EXCEPTIONS:
            continue
        path = root / rel
        if not path.is_file() or is_binary(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            if _line_has_secret_placeholder(line):
                continue
            for kind, pattern, label in SECRET_PATTERNS:
                if pattern.search(line):
                    errors.append(
                        f"tracked secret pattern ({kind}): {rel}:{line_no} — {label}; "
                        "use ${env:VAR} placeholders or move to .env"
                    )
                    break
            else:
                continue
            break
    return errors


def classify_legacy_name_refs(root: Path, files: list[str]) -> tuple[int, int]:
    active = 0
    historical = 0
    for rel in files:
        if rel == "scripts/review/repo_hygiene.py":
            continue
        path = root / rel
        if not path.is_file() or is_binary(path):
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line in lines:
            if LEGACY_NAME not in line:
                continue
            lower = line.lower()
            if any(hint in lower for hint in HISTORICAL_HINTS) or "docs/recovery/" in rel:
                historical += 1
            else:
                active += 1
    return active, historical


def report_status(root: Path) -> list[str]:
    warnings: list[str] = []
    status = run_git(root, "status", "--short", "--branch")
    if status.returncode != 0:
        return [f"git status failed: {status.stderr.strip()}"]
    warnings.append(status.stdout.strip())

    shallow = run_git(root, "rev-parse", "--is-shallow-repository")
    if shallow.returncode == 0:
        warnings.append(f"shallow={shallow.stdout.strip()}")
    return warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Repo hygiene guard for orama-system salvage work")
    parser.add_argument("repo", nargs="?", default=".", help="repository root")
    args = parser.parse_args()

    root = Path(args.repo).resolve()
    files = tracked_files(root)

    errors: list[str] = []
    errors.extend(check_identity(root))
    errors.extend(scan_forbidden_identity(root, files))
    errors.extend(scan_personal_paths(root, files))
    errors.extend(scan_openclaw_workstation_layout(root, files))
    errors.extend(scan_bidi_controls(root, files))
    errors.extend(scan_tracked_secrets(root, files))
    errors.extend(check_private_generated_tracking(files))
    errors.extend(check_markdown_link_hygiene(root, files))
    errors.extend(check_generated_artifact_tracking(files))
    errors.extend(check_ecc(root, files))
    errors.extend(check_workflow_permissions(root))
    errors.extend(check_stale_skill_path_refs(root, files))
    errors.extend(check_git_internal_junk(root))
    warnings = check_markdown_size_warnings(root, files)
    active_legacy, historical_legacy = classify_legacy_name_refs(root, files)

    for line in report_status(root):
        print(f"INFO: {line}")
    print(
        "INFO: legacy name references "
        f"active={active_legacy} historical_or_allowed={historical_legacy}"
    )
    for warning in warnings:
        print(f"WARNING: {warning}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("OK: repo hygiene checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
