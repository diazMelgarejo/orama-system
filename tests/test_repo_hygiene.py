from __future__ import annotations

import importlib.util
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


def test_identity_check_script_is_shell_valid():
    subprocess.check_call(["bash", "-n", "scripts/git/check_identity.sh"], cwd=ROOT)
