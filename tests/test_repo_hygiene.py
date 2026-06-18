from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parent.parent
HYGIENE_PATH = ROOT / "scripts" / "review" / "repo_hygiene.py"


def load_repo_hygiene():
    spec = importlib.util.spec_from_file_location("repo_hygiene", HYGIENE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def find_bash() -> str:
    candidates: list[str | None] = [
        os.environ.get("HERMES_GIT_BASH_PATH"),
        shutil.which("bash"),
    ]
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidates.extend(
            str(path)
            for path in sorted(
                Path(local_app_data).glob(
                    "GitHubDesktop/app-*/resources/app/git/usr/bin/bash.exe"
                )
            )
        )
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    raise AssertionError("bash.exe not found; set HERMES_GIT_BASH_PATH or install Git Bash")


def test_private_generated_config_is_not_tracked():
    tracked = subprocess.check_output(
        ["git", "-C", str(ROOT), "ls-files"],
        text=True,
    ).splitlines()

    assert ".env" not in tracked
    assert ".env.local" not in tracked
    assert ".paths" not in tracked


def test_generated_artifact_patterns_are_blocked():
    repo_hygiene = load_repo_hygiene()
    errors = repo_hygiene.check_generated_artifact_tracking(
        [
            ".DS_Store",
            "bin/shared/__pycache__/state_manager.cpython-312.pyc",
            "dist/orama_system-0.9.9.9.whl",
            "DerivedData/Build/Intermediates.noindex/file",
            "Project.xcodeproj/xcuserdata/user.xcuserdatad/UserInterfaceState.xcuserstate",
            "README.md",
        ]
    )

    assert errors == [
        "generated artifact is tracked: .DS_Store",
        "generated artifact is tracked: bin/shared/__pycache__/state_manager.cpython-312.pyc",
        "generated artifact is tracked: dist/orama_system-0.9.9.9.whl",
        "generated artifact is tracked: DerivedData/Build/Intermediates.noindex/file",
        "generated artifact is tracked: Project.xcodeproj/xcuserdata/user.xcuserdatad/UserInterfaceState.xcuserstate",
    ]


def test_git_internal_junk_is_blocked(tmp_path):
    repo_hygiene = load_repo_hygiene()
    refs_dir = tmp_path / ".git" / "refs" / "heads"
    refs_dir.mkdir(parents=True)
    (refs_dir / ".DS_Store").write_text("", encoding="utf-8")

    assert repo_hygiene.check_git_internal_junk(tmp_path) == [
        "macOS metadata file inside git refs: .git/refs/heads/.DS_Store"
    ]


def test_scan_openclaw_workstation_layout_blocks_machine_path(tmp_path):
    repo_hygiene = load_repo_hygiene()
    docs = tmp_path / "docs"
    docs.mkdir()
    md = docs / "setup.md"
    md.write_text(
        'Clone at ${HOME}/Documents/Terminal xCode/claude/OpenClaw/orama-system\n',
        encoding="utf-8",
    )

    errors = repo_hygiene.scan_openclaw_workstation_layout(tmp_path, ["docs/setup.md"])

    assert len(errors) == 1
    assert "machine-specific OpenClaw path" in errors[0]
    assert "docs/setup.md" in errors[0]


def test_scan_tracked_secrets_blocks_google_and_telegram_tokens(tmp_path):
    repo_hygiene = load_repo_hygiene()
    cfg = tmp_path / "config"
    cfg.mkdir()
    bad = cfg / "bad.json"
    bad.write_text(
        "\n".join(
            [
                '{"apiKey": "AIzaSy0123456789012345678901234567890"}',
                '{"botToken": "1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef"}',
            ]
        ),
        encoding="utf-8",
    )
    good = cfg / "good.json"
    good.write_text(
        '{"apiKey": "${env:OPENCLAW_GEMINI_APIKEY}", "botToken": "${env:OPENCLAW_TELEGRAM_BOT_TOKEN}"}',
        encoding="utf-8",
    )

    errors = repo_hygiene.scan_tracked_secrets(
        tmp_path,
        ["config/bad.json", "config/good.json"],
    )

    assert len(errors) == 1
    assert "config/bad.json" in errors[0]
    assert "google_api_key" in errors[0]


def test_scan_personal_paths_blocks_user_home(tmp_path):
    repo_hygiene = load_repo_hygiene()
    docs = tmp_path / "docs"
    docs.mkdir()
    md = docs / "README.md"
    md.write_text(
        "Config path: /Users/janedoe/projects/orama-system/README.md\n",
        encoding="utf-8",
    )

    errors = repo_hygiene.scan_personal_paths(tmp_path, ["docs/README.md"])

    assert len(errors) == 1
    assert "personal absolute path" in errors[0]
    assert "/Users/janedoe/" in errors[0]


def test_markdown_link_hygiene_blocks_absolute_paths(tmp_path):
    repo_hygiene = load_repo_hygiene()
    docs = tmp_path / "docs"
    docs.mkdir()
    md = docs / "README.md"
    md.write_text(
        "\n".join(
            [
                "[relative](wiki/README.md)",
                "[github](https://github.com/example/repo/blob/main/docs/README.md)",
                "[absolute](</Users/example/repo/docs/wiki/README.md>)",
            ]
        ),
        encoding="utf-8",
    )

    errors = repo_hygiene.check_markdown_link_hygiene(tmp_path, ["docs/README.md"])

    assert errors == [
        "markdown link must be repo-relative: docs/README.md -> /Users/example/repo/docs/wiki/README.md"
    ]


def test_markdown_size_warnings_for_changed_files(tmp_path):
    repo_hygiene = load_repo_hygiene()
    docs = tmp_path / "docs"
    docs.mkdir()
    new_doc = docs / "new-guide.md"
    old_doc = docs / "old-guide.md"
    small_doc = docs / "small-guide.md"
    new_doc.write_text("\n".join(["line"] * 201), encoding="utf-8")
    old_doc.write_text("\n".join(["line"] * 501), encoding="utf-8")
    small_doc.write_text("short\n", encoding="utf-8")

    warnings = repo_hygiene.check_markdown_size_warnings(
        tmp_path,
        ["docs/new-guide.md", "docs/old-guide.md", "docs/small-guide.md"],
        changed={"docs/new-guide.md", "docs/old-guide.md", "docs/small-guide.md"},
        existing={"docs/old-guide.md", "docs/small-guide.md"},
    )

    assert warnings == [
        "docs/new-guide.md has 201 lines; new markdown files over 200 lines should ask the user about offloading related content to references/ or sub-skills",
        "docs/old-guide.md has 501 lines; existing markdown files over 500 lines should ask the user about splitting or redirecting detailed content elsewhere",
    ]


def test_stale_skill_path_refs_are_blocked_in_hidden_tracked_files(tmp_path):
    repo_hygiene = load_repo_hygiene()
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    workflow = workflow_dir / "ci.yml"
    stale_path = "bin/" + "skills"
    stale_module = "bin" + ".skills"
    workflow.write_text(f"grep -q Quick Start {stale_path}/SKILL.md\n", encoding="utf-8")
    package_check = tmp_path / "test-package-install.py"
    package_check.write_text(f"from {stale_module}.cidf.core import x\n", encoding="utf-8")

    errors = repo_hygiene.check_stale_skill_path_refs(
        tmp_path,
        [".github/workflows/ci.yml", "test-package-install.py"],
    )

    assert errors == [
        f"stale skill path/module reference in tracked file: .github/workflows/ci.yml -> {stale_path}",
        f"stale skill path/module reference in tracked file: test-package-install.py -> {stale_module}",
    ]


def test_scan_stale_git_locks_detects_lock_files(tmp_path):
    repo_hygiene = load_repo_hygiene()
    git_dir = tmp_path / ".git"
    (git_dir / "refs" / "heads").mkdir(parents=True)
    (git_dir / "index.lock").write_text("", encoding="utf-8")
    (git_dir / "refs" / "heads" / "main.lock").write_text("", encoding="utf-8")
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")

    errors = repo_hygiene.scan_stale_git_locks(tmp_path)

    assert len(errors) == 2
    joined = "\n".join(errors)
    assert ".git/index.lock" in joined
    assert ".git/refs/heads/main.lock" in joined
    for err in errors:
        assert "stale lock file" in err
        assert "find .git -name '*.lock' -delete" in err


def test_scan_stale_git_locks_clean_repo_returns_empty(tmp_path):
    repo_hygiene = load_repo_hygiene()
    git_dir = tmp_path / ".git" / "refs" / "heads"
    git_dir.mkdir(parents=True)
    (tmp_path / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")

    assert repo_hygiene.scan_stale_git_locks(tmp_path) == []


def test_scan_macos_dedup_dirs_detects_finder_dedup(tmp_path):
    repo_hygiene = load_repo_hygiene()
    (tmp_path / "foo 2").mkdir()
    (tmp_path / "bar 3").mkdir()
    # Negative cases — must NOT match.
    (tmp_path / "foo2").mkdir()
    (tmp_path / "foo 2.txt").write_text("not a dir", encoding="utf-8")
    # Excluded paths — dedup-like dirs inside .git / .venv must be ignored.
    (tmp_path / ".git" / "objects 2").mkdir(parents=True)
    (tmp_path / "node_modules" / "pkg 2").mkdir(parents=True)

    errors = repo_hygiene.scan_macos_dedup_dirs(tmp_path)

    assert len(errors) == 2
    joined = "\n".join(sorted(errors))
    assert "foo 2" in joined
    assert "bar 3" in joined
    assert "foo2" not in joined
    assert "objects 2" not in joined
    assert "node_modules" not in joined
    for err in errors:
        assert "macOS Finder dedup directory" in err
        assert "rm -rf" in err


def test_scan_macos_dedup_dirs_clean_tree_returns_empty(tmp_path):
    repo_hygiene = load_repo_hygiene()
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "foo2.py").write_text("x = 1\n", encoding="utf-8")

    assert repo_hygiene.scan_macos_dedup_dirs(tmp_path) == []


def test_repo_hygiene_script_runs_clean():
    result = subprocess.run(
        [sys.executable, "scripts/review/repo_hygiene.py", "."],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_scan_docv2_ordinal_collision_detects_duplicate_prefix(tmp_path):
    """Two files with the same NN- prefix should produce one error."""
    repo_hygiene = load_repo_hygiene()
    docv2 = tmp_path / "docs" / "v2"
    docv2.mkdir(parents=True)
    (docv2 / "18-master-alignment.md").write_text("# a\n", encoding="utf-8")
    (docv2 / "18-rag-and-memory.md").write_text("# b\n", encoding="utf-8")
    (docv2 / "19-gstack-optional.md").write_text("# c\n", encoding="utf-8")

    errors = repo_hygiene.scan_docv2_ordinal_collision(tmp_path)

    assert len(errors) == 1
    assert "18" in errors[0]
    assert "18-master-alignment.md" in errors[0] or "18-rag-and-memory.md" in errors[0]
    assert "ordinal collision" in errors[0]


def test_scan_docv2_ordinal_collision_three_way_collision(tmp_path):
    """Three files with the same prefix produce exactly one error (per prefix)."""
    repo_hygiene = load_repo_hygiene()
    docv2 = tmp_path / "docs" / "v2"
    docv2.mkdir(parents=True)
    for slug in ("18-a.md", "18-b.md", "18-c.md"):
        (docv2 / slug).write_text("# x\n", encoding="utf-8")

    errors = repo_hygiene.scan_docv2_ordinal_collision(tmp_path)

    assert len(errors) == 1
    assert "18" in errors[0]


def test_scan_docv2_ordinal_collision_clean_returns_empty(tmp_path):
    """Sequential prefixes 00–22 with unique slugs must be accepted."""
    repo_hygiene = load_repo_hygiene()
    docv2 = tmp_path / "docs" / "v2"
    docv2.mkdir(parents=True)
    for i, slug in enumerate(["00-context.md", "01-kernel.md", "22-worktrees.md"]):
        (docv2 / slug).write_text(f"# {i}\n", encoding="utf-8")

    assert repo_hygiene.scan_docv2_ordinal_collision(tmp_path) == []


def test_scan_docv2_ordinal_collision_no_docv2_dir(tmp_path):
    """Repos without docs/v2/ must not error."""
    repo_hygiene = load_repo_hygiene()
    assert repo_hygiene.scan_docv2_ordinal_collision(tmp_path) == []


def test_scan_macos_ghost_git_refs_detects_space_numbered_file(tmp_path):
    """Files like .git/refs/heads/main 2 must be flagged as ghost refs."""
    repo_hygiene = load_repo_hygiene()
    refs_heads = tmp_path / ".git" / "refs" / "heads"
    refs_heads.mkdir(parents=True)
    (refs_heads / "main").write_text("56f2a6d7b63e8853b814d32f970b62971dc7768c\n")
    (refs_heads / "main 2").write_text("56f2a6d7b63e8853b814d32f970b62971dc7768c\n")
    errors = repo_hygiene.scan_macos_ghost_git_refs(tmp_path)
    assert len(errors) == 1
    assert "main 2" in errors[0]
    assert "ghost git ref" in errors[0]


def test_scan_macos_ghost_git_refs_detects_branch_with_number(tmp_path):
    """Subdirectory refs like .git/refs/heads/feat/my-branch 3 are caught."""
    repo_hygiene = load_repo_hygiene()
    refs_feat = tmp_path / ".git" / "refs" / "heads" / "feat"
    refs_feat.mkdir(parents=True)
    (refs_feat / "my-branch 3").write_text("abcdef1234567890abcdef1234567890abcdef12\n")
    errors = repo_hygiene.scan_macos_ghost_git_refs(tmp_path)
    assert len(errors) == 1
    assert "my-branch 3" in errors[0]


def test_scan_macos_ghost_git_refs_clean_returns_empty(tmp_path):
    """Repos with normal ref names must not flag any errors."""
    repo_hygiene = load_repo_hygiene()
    refs_heads = tmp_path / ".git" / "refs" / "heads"
    refs_heads.mkdir(parents=True)
    (refs_heads / "main").write_text("56f2a6d7b63e8853b814d32f970b62971dc7768c\n")
    (refs_heads / "feat-my-branch").write_text("abcdef1234567890abcdef1234567890abcdef12\n")
    assert repo_hygiene.scan_macos_ghost_git_refs(tmp_path) == []


def test_scan_macos_ghost_git_refs_no_git_dir(tmp_path):
    """Repos without a .git/refs dir must not error."""
    repo_hygiene = load_repo_hygiene()
    assert repo_hygiene.scan_macos_ghost_git_refs(tmp_path) == []


def test_identity_check_script_is_shell_valid():
    subprocess.check_call([find_bash(), "-n", "scripts/git/check_identity.sh"], cwd=ROOT)


def test_identity_enforcement_is_scoped_to_cursor(monkeypatch):
    """Identity enforcement applies only to Cursor agents; humans/Codex/Claude
    pass through. Mirrors is_cursor_agent() in scripts/git/check_identity.sh."""
    repo_hygiene = load_repo_hygiene()
    for var in ("CURSOR_AGENT", "CURSOR_TRACE_ID", "CURSOR_SESSION_ID"):
        monkeypatch.delenv(var, raising=False)

    bad = ("Random Person", "random@gmail.com")
    # Non-Cursor environment: not detected as Cursor -> identity not enforced.
    assert repo_hygiene.is_cursor_environment(*bad) is False
    # Any Cursor env var present -> detected -> identity enforced.
    monkeypatch.setenv("CURSOR_AGENT", "1")
    assert repo_hygiene.is_cursor_environment(*bad) is True
    monkeypatch.delenv("CURSOR_AGENT", raising=False)
    # Cursor-flavored identity is a positive signal even without env vars.
    assert repo_hygiene.is_cursor_environment("Cursor Agent", "cursoragent@cursor.com") is True


# ── repo_relative (new helper in repo_hygiene.py) ────────────────────────────

def test_repo_relative_returns_posix_string(tmp_path):
    repo_hygiene = load_repo_hygiene()
    nested = tmp_path / "some" / "nested" / "file.txt"
    result = repo_hygiene.repo_relative(nested, tmp_path)
    assert result == "some/nested/file.txt"
    assert "\\" not in result


def test_repo_relative_direct_child(tmp_path):
    repo_hygiene = load_repo_hygiene()
    child = tmp_path / "file.txt"
    assert repo_hygiene.repo_relative(child, tmp_path) == "file.txt"


def test_repo_relative_deep_git_path(tmp_path):
    repo_hygiene = load_repo_hygiene()
    ref = tmp_path / ".git" / "refs" / "heads" / "main 2"
    result = repo_hygiene.repo_relative(ref, tmp_path)
    assert result == ".git/refs/heads/main 2"
    assert "\\" not in result


def test_scan_stale_git_locks_paths_use_posix_separators(tmp_path):
    """Regression: scan_stale_git_locks must emit forward-slash paths on all platforms."""
    repo_hygiene = load_repo_hygiene()
    lock_dir = tmp_path / ".git" / "refs" / "heads"
    lock_dir.mkdir(parents=True)
    (lock_dir / "feature.lock").write_text("", encoding="utf-8")

    errors = repo_hygiene.scan_stale_git_locks(tmp_path)

    assert len(errors) == 1
    # Path component separator must be forward slash.
    assert ".git/refs/heads/feature.lock" in errors[0]
    assert "\\" not in errors[0]


def test_scan_macos_dedup_dirs_paths_use_posix_separators(tmp_path):
    """Regression: scan_macos_dedup_dirs must emit forward-slash paths for the rel path."""
    repo_hygiene = load_repo_hygiene()
    sub = tmp_path / "src"
    sub.mkdir()
    (sub / "lib 2").mkdir()

    errors = repo_hygiene.scan_macos_dedup_dirs(tmp_path)

    assert len(errors) == 1
    # The rel path portion uses forward slashes (the message also contains a
    # literal '\' in the gitignore pattern hint, which is expected and acceptable).
    assert "src/lib 2" in errors[0]


def test_scan_macos_ghost_git_refs_paths_use_posix_separators(tmp_path):
    """Regression: scan_macos_ghost_git_refs must emit forward-slash paths."""
    repo_hygiene = load_repo_hygiene()
    refs = tmp_path / ".git" / "refs" / "heads"
    refs.mkdir(parents=True)
    (refs / "main 2").write_text("abc123\n", encoding="utf-8")

    errors = repo_hygiene.scan_macos_ghost_git_refs(tmp_path)

    assert len(errors) == 1
    assert ".git/refs/heads/main 2" in errors[0]
    assert "\\" not in errors[0]


def test_check_git_internal_junk_paths_use_posix_separators(tmp_path):
    """Regression: check_git_internal_junk must emit forward-slash paths."""
    repo_hygiene = load_repo_hygiene()
    refs_dir = tmp_path / ".git" / "refs" / "heads"
    refs_dir.mkdir(parents=True)
    (refs_dir / ".DS_Store").write_text("", encoding="utf-8")

    errors = repo_hygiene.check_git_internal_junk(tmp_path)

    assert len(errors) == 1
    assert ".git/refs/heads/.DS_Store" in errors[0]
    assert "\\" not in errors[0]


# ── find_bash (new helper in test_repo_hygiene.py) ───────────────────────────

def test_find_bash_returns_existing_file(tmp_path, monkeypatch):
    """find_bash() must return a path to an existing file.

    Uses monkeypatching so the outcome is deterministic regardless of what
    binaries happen to be installed on the executing machine -- avoiding
    cross-runner flakiness (e.g. Windows runners without Git Bash on PATH).
    """
    fake_bash = tmp_path / "bash"
    fake_bash.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")
    monkeypatch.setenv("HERMES_GIT_BASH_PATH", str(fake_bash))
    bash = find_bash()
    assert Path(bash).is_file(), f"find_bash() returned non-existent path: {bash}"


def test_find_bash_prefers_hermes_git_bash_path(tmp_path, monkeypatch):
    """When HERMES_GIT_BASH_PATH points at a real file, find_bash() returns it."""
    fake_bash = tmp_path / "bash"
    fake_bash.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")
    monkeypatch.setenv("HERMES_GIT_BASH_PATH", str(fake_bash))
    assert find_bash() == str(fake_bash)


def test_find_bash_ignores_nonexistent_hermes_git_bash_path(tmp_path, monkeypatch):
    """HERMES_GIT_BASH_PATH pointing at a missing file must be skipped.

    Monkeypatches shutil.which so the fallback returns a deterministic
    result instead of depending on machine-installed binaries.
    """
    monkeypatch.setenv("HERMES_GIT_BASH_PATH", "/no/such/bash.exe")
    # Inject a fake which()-found bash so the result is machine-independent.
    fake_bash = tmp_path / "bash_from_which"
    fake_bash.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")
    monkeypatch.setattr(shutil, "which", lambda name: str(fake_bash) if name == "bash" else None)
    result = find_bash()
    assert result == str(fake_bash)


def test_find_bash_falls_back_without_env_var(tmp_path, monkeypatch):
    """Without HERMES_GIT_BASH_PATH, find_bash() falls back to shutil.which.

    Monkeypatches shutil.which to a deterministic fake so the test passes
    on any runner (including Windows without Git Bash installed).
    """
    monkeypatch.delenv("HERMES_GIT_BASH_PATH", raising=False)
    fake_bash = tmp_path / "bash_fallback"
    fake_bash.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")
    monkeypatch.setattr(shutil, "which", lambda name: str(fake_bash) if name == "bash" else None)
    result = find_bash()
    assert result == str(fake_bash)
