#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import os
import re
import subprocess
import sys
from pathlib import Path


def repo_relative(path: Path, root: Path) -> str:
    """Return repo-relative paths with POSIX separators for stable messages."""
    return path.relative_to(root).as_posix()


APPROVED_IDENTITIES = {
    ("cyre", "Lawrence@cyre.me"),
    ("cyre", "diazMelgarejo@gmail.com"),
    ("cyre", "Lawrence@bettermind.ph"),
    ("Codex", "codex@openai.com"),
    # Mainstream AI coding agents are allowed authors/committers (the hard ban is
    # the VERBOTEN pattern, not the agent identity). cursoragent@cursor.com stays
    # approved; CodeRabbit commits as a GitHub bot but is listed for parity.
    ("Cursor Agent", "cursoragent@cursor.com"),
    ("CodeRabbit", "noreply@coderabbit.ai"),
}
# Keep in sync with scripts/git/check_identity.sh (local hooks + pre-commit).
FORBIDDEN_TOKENS: tuple[()] = ()
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
    "*.db",
    "*.sqlite",
    "*.sqlite3",
    "*.duckdb",
    "*.lmdb",
    "*.mdb",
    "*.har",
    "*.webm",
    "*.mp4",
    "*.log",
    "logs/*",
    "data/*",
    "runtime/*",
    "state/*",
    "sessions/*",
    "screenshots/*",
    "captures/*",
    "ui-captures/*",
    "recordings/*",
    "playwright-report/*",
    "test-results/*",
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
    (
        "aws_access_key",
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        "AWS access key ID (AKIA...)",
    ),
    (
        "private_key",
        re.compile(r"-----BEGIN (RSA |EC |OPENSSH |PRIVATE )?PRIVATE KEY-----"),
        "Private key block",
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


# Mojibake (LINT-007) — UTF-8 text mis-decoded as cp1252/latin-1 then re-saved.
# Signature: a UTF-8 multibyte lead char (U+00C2-U+00EF) immediately followed by a
# continuation byte (U+0080-U+00BF) OR a cp1252 high-punctuation codepoint. In clean
# English/Greek UTF-8 these never co-occur; in mojibake they always do. Markers are
# written as \u escapes so this file contains no literal mojibake to self-trip on.
MOJIBAKE_RE = re.compile(
    "[\u00c2-\u00ef](?:"
    "[\u0080-\u00bf]"
    "|[\u2013\u2014\u2018-\u201e\u2020-\u2022\u2026\u2030\u2039\u203a\u20ac\u2122"
    "\u0152\u0153\u0160\u0161\u0178\u017d\u017e\u0192\u02c6\u02dc]"
    ")"
)


def scan_mojibake(root: Path, files: list[str]) -> list[str]:
    """Block UTF-8 mojibake byte pairs in tracked text (LINT-007).

    Mojibake is text written in one charset and read as another — classically
    UTF-8 bytes decoded as Windows-1252 (e.g. an em-dash U+2014 = E2 80 94 becomes
    the three chars a-circumflex + euro + quote). The most common trigger is a tool
    reading/writing a file without an explicit encoding on a cp1252-default platform
    (Windows). Root cause + repair: docs/LESSONS.md 2026-06-10.

    Describe mojibake by codepoint, never with a literal example, or this gate will
    flag your own doc — there are intentionally no content exceptions.
    """
    errors: list[str] = []
    for rel in files:
        path = root / rel
        if not path.is_file() or is_binary(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            m = MOJIBAKE_RE.search(line)
            if m:
                errors.append(
                    f"UTF-8 mojibake in tracked file: {rel}:{line_no}: "
                    f"U+{ord(m.group()[0]):04X} mis-decoded sequence "
                    f"(see docs/LESSONS.md 2026-06-10 / CIDF LINT-007)"
                )
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


MACOS_DEDUP_DIR_PATTERN = re.compile(r" [2-9]$")
MACOS_DEDUP_EXCLUDED_DIRS = frozenset({".git", ".venv", "node_modules", ".tox"})


def scan_stale_git_locks(root: Path) -> list[str]:
    """Block stale .git/*.lock files (D5) — these wedge git operations.

    Interrupted git operations or macOS Finder activity can leave .lock files
    inside the .git directory (index.lock, refs/heads/<branch>.lock, etc).
    Until removed, subsequent git commands fail with "another process holds
    the lock." Doctrine fix: `find .git -name '*.lock' -delete`.
    """
    errors: list[str] = []
    git_dir = root / ".git"
    if not git_dir.exists():
        return errors
    for dirpath, _dirnames, filenames in os.walk(git_dir):
        for name in filenames:
            if not name.endswith(".lock"):
                continue
            full = Path(dirpath) / name
            rel = repo_relative(full, root)
            errors.append(
                f"stale lock file: {rel} — fix: find .git -name '*.lock' -delete"
            )
    return errors


def scan_macos_dedup_dirs(root: Path) -> list[str]:
    """Block macOS Finder dedup directories (D6) — '<name> 2/', '<name> 3/'.

    When Finder copies into a directory that already contains a file/dir of
    the same name, it appends ' 2', ' 3', etc. These shadow real paths and
    contaminate git status / worktree state. Doctrine fix: delete the dir
    and ensure `.gitignore` contains the dedup patterns.
    """
    errors: list[str] = []
    if not root.exists():
        return errors
    for dirpath, dirnames, _filenames in os.walk(root):
        # Prune excluded directories in-place so os.walk skips them.
        dirnames[:] = [d for d in dirnames if d not in MACOS_DEDUP_EXCLUDED_DIRS]
        for d in dirnames:
            if MACOS_DEDUP_DIR_PATTERN.search(d):
                full = Path(dirpath) / d
                rel = repo_relative(full, root)
                errors.append(
                    f"macOS Finder dedup directory: {rel} — "
                    f"fix: rm -rf '{rel}' and verify .gitignore contains '*\\ <N>/' pattern"
                )
    return errors


# Pattern that matches the leading numeric prefix in docs/v2/NN-slug.md filenames.
_DOCV2_ORDINAL_PATTERN = re.compile(r"^(\d+)-")


def scan_macos_ghost_git_refs(root: Path) -> list[str]:
    """Detect macOS APFS ghost files in .git/refs/ (D10 — ghost git ref files).

    When APFS deduplication or Finder copies a git refs directory, it may
    create files like ``main 2``, ``feat/my-branch 2`` alongside the real ref
    files.  Git silently treats these as loose refs named
    ``refs/heads/main 2`` (with a literal space), which breaks
    ``git repack -Ad``, ``git gc``, and ``git fsck`` with::

        fatal: bad object refs/heads/main 2

    The fix is to delete these files — their SHA content is redundant with
    the matching loose ref or packed-refs entry, and they carry no useful
    information.
    """
    errors: list[str] = []
    git_refs = root / ".git" / "refs"
    if not git_refs.is_dir():
        return errors
    _ghost_pattern = re.compile(r".+\s+\d+$")
    for path in git_refs.rglob("*"):
        if path.is_file() and _ghost_pattern.match(path.name):
            rel = repo_relative(path, root)
            errors.append(
                f"macOS ghost git ref file: {rel} — "
                f"fix: rm '{rel}' (duplicate of '{path.parent / path.name.rsplit(' ', 1)[0]}')"
            )
    return errors


def scan_docv2_ordinal_collision(root: Path) -> list[str]:
    """Detect duplicate numeric prefixes in docs/v2/ (D7 — multi-agent collision).

    When parallel agents independently add a docs/v2/NN-*.md file, they each
    compute "the current highest number" from disk and both claim the same
    ordinal (e.g., two files named 18-*). Git silently accepts both because
    the slugs differ — no merge conflict is raised. This scanner catches the
    collision at commit time.

    Fix: rename the newer file to the next free ordinal and update all
    cross-references. Use `ls docs/v2/ | grep '^[0-9]' | sort -V | tail -1`
    to determine the highest existing number, then claim next_free = highest + 1.
    Update docs/v2/README.md "Next free slot" line accordingly.
    """
    docv2 = root / "docs" / "v2"
    if not docv2.is_dir():
        return []
    seen: dict[int, list[str]] = {}
    for p in docv2.iterdir():
        if not p.is_file() or p.suffix != ".md":
            continue
        m = _DOCV2_ORDINAL_PATTERN.match(p.name)
        if m:
            n = int(m.group(1))
            seen.setdefault(n, []).append(p.name)
    errors: list[str] = []
    for n, names in sorted(seen.items()):
        if len(names) > 1:
            colliders = ", ".join(sorted(names))
            errors.append(
                f"docs/v2 ordinal collision on prefix {n:02d}: {colliders} — "
                f"rename all but the oldest to the next free slot and update refs"
            )
    return errors


def check_git_internal_junk(root: Path) -> list[str]:
    """
    Detect macOS metadata files stored under the repository's Git refs directory.
    
    Returns:
        list[str]: A list of error messages, one for each `.DS_Store` file found under `.git/refs`, or an empty list if the refs directory does not exist.
    """
    git_dir = root / ".git"
    refs_dir = git_dir / "refs"
    if not refs_dir.exists():
        return []
    return [
        f"macOS metadata file inside git refs: {repo_relative(path, root)}"
        for path in refs_dir.rglob(".DS_Store")
    ]


def is_cursor_environment(name: str, email: str) -> bool:
    """
    Detect whether the current environment or provided identity indicates a Cursor agent commit.

    This returns true when one of the Cursor-specific environment variables is present (CURSOR_AGENT, CURSOR_TRACE_ID, CURSOR_SESSION_ID) or when the provided git identity appears Cursor-related (the name contains "cursor" or the email ends with "@cursor.com" or "@cursor.sh"). Mirrors the is_cursor_agent() gate in scripts/git/check_identity.sh — keep the two in sync.

    Detection is only a PROXY for *when* to run the attribution guard: the Cursor
    environment is the one place the VERBOTEN personal email gets auto-injected as
    a co-author, so that is where we enforce. Cursor Agent itself is an allowed
    author/co-author identity; the actual hard ban is the VERBOTEN pattern (held in
    the private pattern lib + stripped by commit-msg.strip-coauthor).

    Parameters:
        name (str): Git committer name (e.g., output of `git config user.name`).
        email (str): Git committer email (e.g., output of `git config user.email`).

    Returns:
        true if the environment or identity indicates a Cursor agent commit, false otherwise.
    """
    for var in ("CURSOR_AGENT", "CURSOR_TRACE_ID", "CURSOR_SESSION_ID"):
        if os.getenv(var):
            return True
    name_lc = name.lower()
    email_lc = email.lower()
    if "cursor" in name_lc:
        return True
    if email_lc.endswith("@cursor.com") or email_lc.endswith("@cursor.sh"):
        return True
    return False


def check_identity(root: Path) -> list[str]:
    """
    Check the repository's configured git user identity and enforce approved Cursor-agent identities.
    
    Parameters:
        root (Path): Repository root where git configuration is read.
    
    Returns:
        list[str]: A list of error messages describing identity problems; empty if the configured identity is acceptable or enforcement is not applicable.
    """
    name = run_git(root, "config", "user.name").stdout.strip()
    email = run_git(root, "config", "user.email").stdout.strip()
    if os.getenv("GITHUB_ACTIONS") == "true" and not name and not email:
        return []
    # Identity enforcement is scoped to Cursor agent commits only — Cursor is the
    # only environment that injects non-approved authors / co-author trailers.
    # Human, Codex, and Claude CLI commits pass through unchecked (mirrors
    # scripts/git/check_identity.sh). Every OTHER hygiene check in this file
    # (forbidden identity tokens, workstation paths, secrets, bidi, links)
    # stays global and unconditional.
    if not is_cursor_environment(name, email):
        return []
    if (name, email) not in APPROVED_IDENTITIES:
        expected = " or ".join(f"{n} <{e}>" for n, e in sorted(APPROVED_IDENTITIES))
        return [
            "git identity mismatch: "
            f"found {name or '<unset>'} <{email or '<unset>'}>; "
            f"expected {expected}"
        ]
    return []


CC_OPENCLAW_SUBMODULE = "bin/orama-system/skills/openclaw-skills/cc-openclaw"


def _gitlink_sha(root: Path, rel_path: str) -> str | None:
    mode_line = run_git(root, "ls-files", "-s", rel_path).stdout.strip()
    if not mode_line:
        return None
    parts = mode_line.split()
    if not parts or parts[0] != "160000":
        return None
    return parts[1] if len(parts) > 1 else None


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


def check_cc_openclaw_gitlink(root: Path) -> list[str]:
    """F8: cc-openclaw submodule must be a pinned gitlink with .gitmodules entry."""
    errors: list[str] = []
    gitmodules = root / ".gitmodules"
    if not gitmodules.exists():
        return [f"{CC_OPENCLAW_SUBMODULE} gitlink check skipped: .gitmodules missing"]

    text = gitmodules.read_text(encoding="utf-8")
    if f'path = {CC_OPENCLAW_SUBMODULE}' not in text:
        errors.append(f"{CC_OPENCLAW_SUBMODULE} missing from .gitmodules")

    pinned = _gitlink_sha(root, CC_OPENCLAW_SUBMODULE)
    if pinned is None:
        errors.append(f"{CC_OPENCLAW_SUBMODULE} is not tracked as a git submodule (mode 160000)")
        return errors

    submodule_dir = root / CC_OPENCLAW_SUBMODULE
    if submodule_dir.exists() and (submodule_dir / ".git").exists():
        head = run_git(submodule_dir, "rev-parse", "HEAD").stdout.strip()
        if head and head != pinned:
            errors.append(
                f"{CC_OPENCLAW_SUBMODULE} working tree ({head[:12]}) "
                f"does not match pinned gitlink ({pinned[:12]})"
            )
    return errors


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


def check_skill_quality(root: Path, files: list[str]) -> list[str]:
    """LINT-010/011/012 — catch three recurring silent failures in SKILL.md files.

    LINT-010: all-``1.`` numbered lists in ``## Procedure`` sections.
      Agent runtimes (Hermes, Codex, OpenCode) consume SKILL.md as raw text.
      When every step is ``1.``, step-tracking and procedure parsing break
      silently — the bug that hit 9 openclaw-skills SKILL.md files.

    LINT-011: ``(deprecated)`` inside ``trigger:`` frontmatter strings.
      Trigger strings are routing matchers; injecting ``(deprecated)`` means
      the route only fires when a user literally types that word.

    LINT-012: ``hermes -z`` in any tracked Markdown file.
      ``hermes -z`` is a retired flag (returns an error in current builds).
      Current syntax: ``hermes chat --query "..." --safe-mode --max-turns 1``.
    """
    import re

    errors: list[str] = []
    PROCEDURE_FENCE_RE = re.compile(r"```[a-z]*\n.*?```", re.DOTALL)
    ALL_ONES_RE = re.compile(r"(?m)^1\. .+\n(?:(?!^[^1]).*\n)*?1\. ")
    DEPRECATED_TRIGGER_RE = re.compile(
        r'^(\s*trigger:\s*"[^"\n]*)\(deprecated\)', re.MULTILINE
    )

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

        # LINT-011: (deprecated) in trigger strings
        if DEPRECATED_TRIGGER_RE.search(text):
            errors.append(
                f"LINT-011: (deprecated) inside trigger: string — breaks routing: {rel}"
            )

        # LINT-012: hermes -z
        # Skip files that self-document LINT-012 (<!-- lint-ignore LINT-012 -->)
        lint012_exempt = "<!-- lint-ignore LINT-012 -->" in text
        if not lint012_exempt and "hermes -z" in text:
            errors.append(
                f"LINT-012: retired 'hermes -z' flag in markdown — use 'hermes chat --query': {rel}"
            )

        # LINT-013: raw LAN IP literals in skill, plan, or reference docs.
        # IPs must come from env vars (WIN_IP, MAC_IP, LM_STUDIO_*_ENDPOINT).
        # Code-fallback defaults (in .py files) are allowed; docs are not.
        # Exempt: files that document the variable contract itself (lan-endpoint-contract.md)
        # and files with <!-- lint-ignore LINT-013 --> pragma.
        if not rel.endswith(".py") and "<!-- lint-ignore LINT-013 -->" not in text:
            _LAN_RE = re.compile(
                r"(?<!\w)(?:192\.168\.|10\.\d+\.|172\.(?:1[6-9]|2\d|31)\.)\d+\.\d+(?!\w)"
            )
            _ip_hits = [m.group() for m in _LAN_RE.finditer(text)
                        if "lan-endpoint-contract" not in rel
                        and "windows-provider-routing" not in rel]
            if _ip_hits:
                errors.append(
                    f"LINT-013: raw LAN IP literal(s) {_ip_hits[:3]} in {rel}"
                    " — use $WIN_IP/$MAC_IP/LM_STUDIO_*_ENDPOINT env vars"
                )

        # LINT-014: argv-form secret passing in skill/plan/doc files (S1).
        lint014_exempt = (
            "<!-- lint-ignore LINT-014 -->" in text
            or "lint-ignore" in text and "LINT-014" in text
        )
        if not lint014_exempt and not rel.endswith(".py"):
            _ARGV_SECRET_RE = re.compile(
                r"security\s+add-generic-password\s+.*-w\s+[\"']?\$",
                re.IGNORECASE,
            )
            if _ARGV_SECRET_RE.search(text):
                errors.append(
                    f"LINT-014: argv secret passing in {rel}"
                    " — use store_keychain_secret.sh (stdin pipe)"
                )


        # LINT-010: only scan SKILL.md ## Procedure sections
        if not path.name == "SKILL.md":
            continue
        proc_idx = text.find("## Procedure")
        if proc_idx == -1:
            continue
        proc_text = text[proc_idx:]
        # Strip code fences — numbered lists inside fences are file content
        stripped = PROCEDURE_FENCE_RE.sub("", proc_text)
        if ALL_ONES_RE.search(stripped):
            errors.append(
                f"LINT-010: all-'1.' numbered list in ## Procedure (steps not sequential): {rel}"
            )

    return errors


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
    errors.extend(scan_mojibake(root, files))
    errors.extend(scan_tracked_secrets(root, files))
    errors.extend(check_private_generated_tracking(files))
    errors.extend(check_markdown_link_hygiene(root, files))
    errors.extend(check_generated_artifact_tracking(files))
    errors.extend(check_ecc(root, files))
    errors.extend(check_cc_openclaw_gitlink(root))
    errors.extend(check_workflow_permissions(root))
    errors.extend(check_stale_skill_path_refs(root, files))
    errors.extend(check_skill_quality(root, files))
    errors.extend(check_git_internal_junk(root))
    errors.extend(scan_stale_git_locks(root))
    errors.extend(scan_macos_dedup_dirs(root))
    errors.extend(scan_macos_ghost_git_refs(root))
    errors.extend(scan_docv2_ordinal_collision(root))
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
