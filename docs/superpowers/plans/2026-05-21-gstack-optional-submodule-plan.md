> ⤵️ **SUPERSEDED 2026-06-14** — submodule approach dropped for copy+auto-resync (install-skills.sh); gstack is a synced global skill, not a git submodule.

# gstack Optional Git Submodule — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Register gstack as an optional git submodule under `tools/gstack/` in orama-system v1. Idempotent detection at every entry point. Users who already have gstack/gbrain installed are not interrupted. New users can opt in via CLI or portal.

**Architecture:** gstack is a sidecar, never a hard dependency. Detection runs silently; install is always manual opt-in. The system works identically with or without gstack — the only difference is whether `GbrainSearchTool` returns semantic results or empty list.

**Tech Stack:** `git submodule`, bash, Python stdlib (`subprocess`, `shutil`, `pathlib`), FastAPI

**Repo:** `<workspace>/orama-system`

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `.gitmodules` | Create | Declare `tools/gstack` submodule pointer |
| `tools/gstack/` | Submodule init | gstack repo at tools/gstack (sparse, no auto-init) |
| `install-gstack.sh` | Create | Manual opt-in install script — idempotent |
| `scripts/tool_status.py` | Create | Detection logic used by install.sh + portal |
| `install.sh` | Modify | Add idempotent gstack detection block at start |
| `portal_server.py` | Modify | Add `GET /api/tools/status` endpoint |
| `tests/test_tool_status.py` | Create | 5 tests for detection logic |
| `docs/v2/19-gstack-optional-integration.md` | Create | v2 forward-plan doc |

---

### Task 1 — Detection logic (scripts/tool_status.py)

**Files:** `scripts/tool_status.py` (create), `tests/test_tool_status.py` (create)

- [ ] **Step 1: Write failing tests**

Create `tests/test_tool_status.py`:

```python
import sys
import os
import pathlib
import pytest
from unittest.mock import patch, MagicMock


def _import_fresh():
    """Re-import tool_status to avoid module caching between tests."""
    if "scripts.tool_status" in sys.modules:
        del sys.modules["scripts.tool_status"]
    import importlib
    import scripts.tool_status as m
    return m


def test_detect_gstack_gbrain_on_path():
    """When gbrain is on PATH, available=True, source='path'."""
    with patch("shutil.which", return_value="/usr/local/bin/gbrain"), \
         patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="gbrain v1.2.3\n")
        m = _import_fresh()
        result = m.detect_gstack()
    assert result["available"] is True
    assert result["source"] == "path"
    assert result["version"] == "gbrain v1.2.3"


def test_detect_gstack_skill_installed(tmp_path, monkeypatch):
    """When ~/.claude/skills/gstack exists but no PATH, available=True, source='skill'."""
    # Build a real fake home so Path.exists checks pass without monkeypatching it
    fake_skill = tmp_path / ".claude" / "skills" / "gstack"
    fake_skill.mkdir(parents=True)
    with patch("shutil.which", return_value=None), \
         patch("pathlib.Path.home", return_value=tmp_path):
        m = _import_fresh()
        result = m.detect_gstack()
    # With real fake dir present, detection must report available + source='skill'
    assert result["available"] is True
    assert result["source"] == "skill"


def test_detect_gstack_nothing_installed():
    """Nothing available → available=False, source=None."""
    with patch("shutil.which", return_value=None), \
         patch("pathlib.Path.exists", return_value=False):
        m = _import_fresh()
        result = m.detect_gstack()
    assert result["available"] is False
    assert result["source"] is None


def test_detect_gstack_never_raises():
    """detect_gstack() must never raise regardless of environment."""
    with patch("shutil.which", side_effect=Exception("env broken")):
        m = _import_fresh()
        try:
            result = m.detect_gstack()
            assert isinstance(result, dict)
        except Exception as exc:
            pytest.fail(f"detect_gstack() raised: {exc}")


def test_detect_gstack_returns_required_keys():
    """Result dict must always contain all required keys."""
    with patch("shutil.which", return_value=None), \
         patch("pathlib.Path.exists", return_value=False):
        m = _import_fresh()
        result = m.detect_gstack()
    for key in ("available", "source", "version", "gbrain_on_path",
                "skill_installed", "submodule_present"):
        assert key in result, f"Missing key: {key}"


def test_detect_gstack_submodule_binary_without_path(tmp_path, monkeypatch):
    """Regression test for Codex P2 #3288118303.

    Scenario: gstack is installed as a submodule at tools/gstack/, the
    submodule-local gbrain binary at tools/gstack/bin/gbrain exists and
    runs, but gbrain is NOT on PATH and ~/.claude/skills/gstack is
    absent. detect_gstack() must invoke the submodule binary directly
    and report source='submodule' with the version it prints.

    Bug class this guards: step 3 of detect_gstack() must NOT re-probe
    PATH via shutil.which("gbrain"), because step 1 already returned
    None — the path was disproven seconds ago. The correct probe is
    `[str(tools/gstack/bin/gbrain), "--version"]`.
    """
    # Build a fake repo with submodule binary present and runnable.
    repo = tmp_path
    gbrain = repo / "tools" / "gstack" / "bin" / "gbrain"
    gbrain.parent.mkdir(parents=True)
    gbrain.write_text("#!/usr/bin/env bash\necho 'gbrain v1.2.3'\n")
    gbrain.chmod(0o755)

    monkeypatch.chdir(repo)

    fake_home = tmp_path / "home"
    fake_home.mkdir()

    with patch("shutil.which", return_value=None), \
         patch("pathlib.Path.home", return_value=fake_home):
        m = _import_fresh()
        result = m.detect_gstack()

    assert result["submodule_present"] is True, \
        "submodule dir present should set submodule_present=True"
    assert result["available"] is True, \
        "runnable submodule-local gbrain should set available=True"
    assert result["source"] == "submodule", \
        f"expected source='submodule', got {result['source']!r}"
    assert result["version"] == "gbrain v1.2.3", \
        f"expected version captured from submodule binary, got {result['version']!r}"
```

- [ ] **Step 2: Run tests — verify 6 fail**

```bash
cd "$REPO_ROOT"
.venv/bin/python3 -m pytest tests/test_tool_status.py -v
```

- [ ] **Step 3: Create `scripts/__init__.py`** (empty, if not exists)

- [ ] **Step 4: Create `scripts/tool_status.py`**

```python
"""Tool status detection for gstack/gbrain and other optional sidecars.

All functions are fail-safe: they never raise, never write to disk,
and never block on network calls. Idempotent to run at any frequency.
"""
import json
import pathlib
import shutil
import subprocess


def detect_gstack() -> dict:
    """Detect gstack / gbrain availability on this machine.

    Detection order (first hit wins):
    1. `gbrain` on PATH — user installed via any method
    2. `~/.claude/skills/gstack` exists — installed as Claude skill
    3. `tools/gstack/` present in repo — registered submodule

    Returns a dict with keys:
      available, source, version, gbrain_on_path, skill_installed, submodule_present
    """
    result = {
        "available": False,
        "source": None,
        "version": None,
        "gbrain_on_path": False,
        "skill_installed": False,
        "submodule_present": False,
    }

    try:
        # 1. gbrain on PATH
        if shutil.which("gbrain"):
            result["gbrain_on_path"] = True
            try:
                v = subprocess.run(
                    ["gbrain", "--version"],
                    capture_output=True, text=True, timeout=5,
                )
                result["version"] = v.stdout.strip() if v.returncode == 0 else None
            except Exception:
                pass
            result["available"] = True
            result["source"] = "path"
            return result

        # 2. ~/.claude/skills/gstack
        skill_path = pathlib.Path.home() / ".claude" / "skills" / "gstack"
        if skill_path.exists():
            result["skill_installed"] = True
            result["available"] = True
            result["source"] = "skill"
            return result

        # 3. tools/gstack submodule present — invoke binary FROM submodule, not PATH
        # PATH was already checked in step 1 and found empty; using shutil.which here
        # again would always fail. Probe the submodule-local binary instead.
        submodule_path = pathlib.Path("tools") / "gstack"
        if submodule_path.exists():
            result["submodule_present"] = True
            gbrain_bin = submodule_path / "bin" / "gbrain"
            if gbrain_bin.exists():
                try:
                    v = subprocess.run(
                        [str(gbrain_bin), "--version"],
                        capture_output=True, text=True, timeout=5,
                    )
                    if v.returncode == 0:
                        result["version"] = v.stdout.strip() or None
                        result["available"] = True
                        result["source"] = "submodule"
                        return result
                except Exception:
                    pass
            # Submodule dir found but binary not present or not runnable

    except Exception:
        pass  # Never raise — return partial result

    return result


def status_all() -> dict:
    """Return status of all optional tools. Extend here for new tools."""
    return {
        "gstack": detect_gstack(),
    }
```

- [ ] **Step 5: Run tests — verify 5 pass**

```bash
.venv/bin/python3 -m pytest tests/test_tool_status.py -v
```

- [ ] **Step 6: Run full suite — verify existing 183 tests still pass**

```bash
.venv/bin/python3 -m pytest tests/ -v
```

---

### Task 2 — install-gstack.sh (idempotent opt-in installer)

**File:** `install-gstack.sh` (create)

- [ ] **Step 1: Create `install-gstack.sh`**

```bash
#!/usr/bin/env bash
# install-gstack.sh — Optional gstack/gbrain installer for orama-system.
#
# IDEMPOTENT: safe to run multiple times. Skips if already installed.
# OPTIONAL:   system runs fine without gstack. This is pure opt-in.
#
# Usage:
#   bash install-gstack.sh               # auto-detect + install if needed
#   bash install-gstack.sh --check-only  # print status, do not install

set -euo pipefail

CHECK_ONLY=false
for arg in "$@"; do
  [[ "$arg" == "--check-only" ]] && CHECK_ONLY=true
done

echo "=== gstack/gbrain Optional Install ==="

# 1. Already on PATH?
if command -v gbrain &>/dev/null; then
  echo "✓ gbrain already available at $(command -v gbrain)"
  gbrain --version 2>/dev/null || true
  echo "  Nothing to install."
  exit 0
fi

# 2. Already installed as Claude skill?
SKILL_PATH="$HOME/.claude/skills/gstack"
if [ -d "$SKILL_PATH" ]; then
  echo "✓ gstack already installed as Claude skill at $SKILL_PATH"
  exit 0
fi

# 3. Submodule already present?
if [ -d "tools/gstack" ] && [ -f "tools/gstack/setup" ]; then
  echo "✓ gstack submodule already present at tools/gstack"
  if [ "$CHECK_ONLY" = true ]; then exit 0; fi
  echo "  Running setup..."
  bash tools/gstack/setup --team
  echo "✓ gstack setup complete."
  exit 0
fi

# Not found anywhere
if [ "$CHECK_ONLY" = true ]; then
  echo "✗ gstack not detected. Run 'bash install-gstack.sh' to install."
  exit 1
fi

echo "  gstack not detected. Installing submodule..."

# Verify we're in a git repo
if ! git rev-parse --is-inside-work-tree &>/dev/null; then
  echo "ERROR: Not inside a git repository. Cannot add submodule."
  exit 1
fi

# Add submodule (idempotent — git submodule add is a no-op if already registered)
git submodule add https://github.com/garrytan/gstack tools/gstack 2>/dev/null || {
  echo "  Submodule already registered. Updating..."
  git submodule update --init --recursive tools/gstack
}
git submodule update --init --recursive tools/gstack

if [ -f "tools/gstack/setup" ]; then
  echo "  Running gstack setup..."
  bash tools/gstack/setup --team
  echo "✓ gstack installed successfully."
  echo "  Verify with: gbrain --version"
else
  echo "WARNING: gstack submodule cloned but setup script not found."
  echo "  Manual step: cd tools/gstack && bash setup --team"
fi
```

- [ ] **Step 2: Make executable**

```bash
chmod +x install-gstack.sh
```

- [ ] **Step 3: Test --check-only mode (no install)**

```bash
bash install-gstack.sh --check-only
# Expected: prints status without installing anything
```

---

### Task 3 — Modify install.sh (idempotent guard block)

**File:** `install.sh` (modify)

- [ ] **Step 1: Read current install.sh to find injection point**

```bash
head -30 install.sh
```

- [ ] **Step 2: Add gstack detection block**

After the initial echo/header block in `install.sh`, add:

```bash
# ─── gstack / gbrain detection (OPTIONAL — never blocks install) ───────────
# One truth, one probe: install.sh uses the SAME availability rule as the
# Python detect_gstack() in scripts/tool_status.py. The submodule branch
# does NOT count as "available" until the submodule-local binary runs and
# returns 0 — exactly mirroring detect_gstack() step 3 (Codex P2 #3288118303).
_GSTACK_STATUS="not_detected"
if command -v gbrain &>/dev/null; then
  echo "✓ gbrain detected at $(command -v gbrain). gstack features enabled."
  _GSTACK_STATUS="path"
elif [ -d "$HOME/.claude/skills/gstack" ]; then
  echo "✓ gstack skill detected at ~/.claude/skills/gstack. gstack features enabled."
  _GSTACK_STATUS="skill"
elif [ -d "tools/gstack" ]; then
  echo "→ gstack submodule found. Running setup..."
  bash tools/gstack/setup --team 2>/dev/null || true
  # Same probe as scripts/tool_status.py:detect_gstack() step 3.
  # PATH was already disproven above; check the submodule-local binary.
  if [ -x "tools/gstack/bin/gbrain" ] && tools/gstack/bin/gbrain --version >/dev/null 2>&1; then
    echo "✓ tools/gstack/bin/gbrain runnable. gstack features enabled (source=submodule)."
    _GSTACK_STATUS="submodule"
  else
    echo "  ⚠ tools/gstack/ present but tools/gstack/bin/gbrain not runnable; treating as absent."
    _GSTACK_STATUS="absent"
  fi
else
  echo "  ℹ gstack not detected — running in keyword-only RAG mode."
  echo "    To enable semantic search: bash install-gstack.sh"
  _GSTACK_STATUS="absent"
fi
export GSTACK_STATUS="$_GSTACK_STATUS"
# ────────────────────────────────────────────────────────────────────────────
```

- [ ] **Step 3: Run install.sh in a test env — verify it completes without blocking**

```bash
bash install.sh 2>&1 | head -20
# Must not hang. gstack detection must print status and continue.
```

---

### Task 4 — Portal endpoint GET /api/tools/status

**File:** `portal_server.py` (modify)

- [ ] **Step 1: Read portal_server.py to find endpoint registration location**

Look for existing `@app.get` routes (around line 50-100).

- [ ] **Step 2: Add tools status endpoint**

After the `/health` endpoint, add:

```python
@app.get("/api/tools/status", tags=["tools"])
async def api_tools_status():
    """Return detection status for all optional tools (gstack, etc.)."""
    try:
        import sys
        import os
        sys.path.insert(0, os.path.dirname(__file__))
        from scripts.tool_status import status_all
        return status_all()
    except Exception as exc:
        return {"error": str(exc), "gstack": {"available": False, "source": None}}
```

- [ ] **Step 3: Test endpoint manually**

```bash
# Start portal server (in background)
python portal_server.py &
sleep 2
curl -s http://localhost:8000/api/tools/status | python3 -m json.tool
# Expected: {"gstack": {"available": true/false, "source": "path"/"skill"/null, ...}}
kill %1
```

- [ ] **Step 4: Run full orama-system test suite**

```bash
.venv/bin/python3 -m pytest tests/ -v
```

All 183+ tests must pass.

---

### Task 5 — Commit gstack optional submodule

- [ ] **Step 1: Verify no regressions**

```bash
cd "<workspace>/orama-system"
.venv/bin/python3 -m pytest tests/ -v
```

- [ ] **Step 2: Commit**

```bash
git add scripts/__init__.py \
        scripts/tool_status.py \
        install-gstack.sh \
        install.sh \
        portal_server.py \
        tests/test_tool_status.py
git commit -m "$(cat <<'EOF'
feat(gstack): optional git submodule + idempotent detection

Add gstack as optional submodule at tools/gstack/. Never blocks
existing installations — detection runs silently and skips if gbrain
is already on PATH or as Claude skill.

- scripts/tool_status.py: fail-safe detect_gstack() + status_all()
- install-gstack.sh: manual opt-in installer, idempotent
- install.sh: gstack detection guard block (never blocks install)
- portal_server.py: GET /api/tools/status returns detection state
- tests/test_tool_status.py: 5 tests, all passing

System runs identically without gstack — GbrainSearchTool returns []
(graceful fallback from perpetua-core).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Verification

```bash
# 1. Test suite passes
.venv/bin/python3 -m pytest tests/ -v | tail -5

# 2. install-gstack.sh check-only is silent
bash install-gstack.sh --check-only

# 3. Portal reports gstack status
curl -s http://localhost:8000/api/tools/status | python3 -m json.tool

# 4. install.sh does not block on gstack absent
bash install.sh 2>&1 | grep -E "gstack|gbrain|ℹ"
```
