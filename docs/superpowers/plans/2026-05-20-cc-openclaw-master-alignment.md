> ✅ **RESOLVED 2026-06-14** — Sub-D landed: `windows_coder_pool` (contracts) + `_try_skill_envelope` dispatch (supervisor) present at repo HEAD. All sub-tracks complete.

# cc-openclaw Master Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the remaining gaps in the cc-openclaw master alignment — fix 4 non-standard SKILL.md files, implement the Windows coder pool dispatch step that is currently stubbed, add test coverage for the new dispatch gate and contracts field, then commit and open the PR.

**Architecture:** Sub-A/B/C are already landed in commit `7ee2819`. This plan covers only what is missing: 4 SKILL.md compliance fixes (Sub-B remainder), the Windows coder pool probe+dispatch implementation in `supervisor._dispatch()` (Sub-D critical gap), and tests for `_try_skill_envelope()` and the coder pool. All changes continue on branch `feat/openclaw-skills-submodule`.

**Tech Stack:** Python 3.11+, pytest-asyncio, Pydantic V2, `connectivity.check_lm_studio()`, bash (SKILL.md edits)

**Repos involved:**
- `orama-system` — branch `feat/openclaw-skills-submodule` (primary)
- `Perpetua-Tools` — same branch name (lockstep: contracts.py + supervisor.py + tests)

---

## Shipped State (do not re-implement)

Already in commit `7ee2819` on both repos:
- Sub-A: submodule, install script, start.sh, master SKILL.md attribution ✅
- Sub-B: all 9 subskill SKILL.md files compliant ✅
- Sub-B: AlphaClaw/SKILL.md, .agents/skills/{agent-failure-postmortem,codex-mcp-debugging} ✅
- Sub-C: CLAUDE.md pointers, bin/orama-system/SKILL.md sections, universal-skill-protocol.md ✅
- Sub-D: contracts.py `windows_coder_pool`, supervisor `_try_skill_envelope` + dispatch step 1 ✅

---

## Task 1 — Fix remaining Sub-B SKILL.md compliance (4 files, docs only)

**Repos:** AlphaClaw (inside `orama-system` submodule path) + `.agents/skills/`

**Files:**
- Modify: `AlphaClaw/.claude/skills/cherry-pick-down/SKILL.md`
- Modify: `AlphaClaw/.claude/skills/macos-port-status/SKILL.md`
- Modify: `.agents/skills/supabase/SKILL.md`
- Modify: `.agents/skills/supabase-postgres-best-practices/SKILL.md`

### Sub-task 1a — cherry-pick-down/SKILL.md

- [ ] **Step 1: Read current file**

```bash
cat "<workspace>/AlphaClaw/.claude/skills/cherry-pick-down/SKILL.md" | head -12
```

Expected: shows `name`, `description`, `disable-model-invocation`, `version`, `layer` but NO `agent_compatibility`.

- [ ] **Step 2: Add `agent_compatibility` to frontmatter**

Open the file and insert after `layer: "agent-local"`:

```yaml
agent_compatibility:
  - Claude
  - Codex
```

Full updated frontmatter block:
```yaml
---
name: cherry-pick-down
description: Safely cherry-pick a commit from feature/MacOS-post-install down to pr-4-macos with upstream-compat check
disable-model-invocation: true
version: "1.0"
layer: "agent-local"
agent_compatibility:
  - Claude
  - Codex
---
```

- [ ] **Step 3: Verify**

```bash
grep -A 4 "agent_compatibility" \
  "<workspace>/AlphaClaw/.claude/skills/cherry-pick-down/SKILL.md"
```

Expected output:
```
agent_compatibility:
  - Claude
  - Codex
```

### Sub-task 1b — macos-port-status/SKILL.md

- [ ] **Step 4: Add `agent_compatibility` to frontmatter**

Open `<workspace>/AlphaClaw/.claude/skills/macos-port-status/SKILL.md` and add after `layer: "agent-local"`:

```yaml
agent_compatibility:
  - Claude
  - Codex
```

- [ ] **Step 5: Verify**

```bash
grep -A 4 "agent_compatibility" \
  "<workspace>/AlphaClaw/.claude/skills/macos-port-status/SKILL.md"
```

Expected: same output as Step 3.

### Sub-task 1c — supabase/SKILL.md

The current frontmatter uses `metadata.version` instead of top-level `version` and is missing `layer`.

- [ ] **Step 6: Read current frontmatter**

```bash
head -15 "<workspace>/.agents/skills/supabase/SKILL.md"
```

- [ ] **Step 7: Add missing `layer` field**

Insert `layer: "agent-local"` after `agent_compatibility` block. The `metadata.version` can stay as-is (it's authoritative for the Supabase-provided versioning). Only add the missing field:

After the closing `---` of the `agent_compatibility` block, insert:
```yaml
layer: "agent-local"
```

Updated frontmatter:
```yaml
---
name: supabase
description: "Use when doing ANY task involving Supabase. Triggers: Supabase products (Database, Auth, Edge Functions, Realtime, Storage, Vectors, Cron, Queues); client libraries and SSR integrations (supabase-js, @supabase/ssr) in Next.js, React, SvelteKit, Astro, Remix; auth issues (login, logout, sessions, JWT, cookies, getSession, getUser, getClaims, RLS); Supabase CLI or MCP server; schema changes, migrations, security audits, Postgres extensions (pg_graphql, pg_cron, pg_vector)."
metadata:
  author: supabase
  version: "0.1.2"
layer: "agent-local"
agent_compatibility:
  - Claude
  - Codex
  - Gemini
  - Hermes
---
```

- [ ] **Step 8: Verify**

```bash
grep "layer:" \
  "<workspace>/.agents/skills/supabase/SKILL.md"
```

Expected: `layer: "agent-local"`

### Sub-task 1d — supabase-postgres-best-practices/SKILL.md

- [ ] **Step 9: Add `layer` and expand `agent_compatibility`**

Current file has only `Claude` in `agent_compatibility` and no `layer`. Update:

```yaml
---
name: supabase-postgres-best-practices
description: Postgres performance optimization and best practices from Supabase. Use this skill when writing, reviewing, or optimizing Postgres queries, schema designs, or database configurations.
license: MIT
metadata:
  author: supabase
  version: "1.1.1"
  organization: Supabase
  date: January 2026
  abstract: Comprehensive Postgres performance optimization guide for developers using Supabase and Postgres. Contains performance rules across 8 categories, prioritized by impact from critical (query performance, connection management) to incremental (advanced features). Each rule includes detailed explanations, incorrect vs. correct SQL examples, query plan analysis, and specific performance metrics to guide automated optimization and code generation.
layer: "agent-local"
agent_compatibility:
  - Claude
  - Codex
  - Gemini
  - Hermes
---
```

- [ ] **Step 10: Verify both fields**

```bash
grep -E "^layer:|agent_compatibility:" \
  "<workspace>/.agents/skills/supabase-postgres-best-practices/SKILL.md"
```

Expected:
```
layer: "agent-local"
agent_compatibility:
```

- [ ] **Step 11: Commit Task 1**

```bash
cd "<workspace>"
# AlphaClaw skills are inside the AlphaClaw submodule — commit there first
cd AlphaClaw
git add .claude/skills/cherry-pick-down/SKILL.md .claude/skills/macos-port-status/SKILL.md
git commit -m "fix(skills): add agent_compatibility to cherry-pick-down and macos-port-status

Both skills had proper layer+version but were missing agent_compatibility.
Adds Claude + Codex as these are repo-local coding agent skills.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"

# Then commit the .agents skills
cd "<workspace>"
git add .agents/skills/supabase/SKILL.md .agents/skills/supabase-postgres-best-practices/SKILL.md
git commit -m "fix(skills): add layer field and normalize agent_compatibility for supabase skills

supabase and supabase-postgres-best-practices were missing layer: agent-local.
supabase-postgres-best-practices was also missing Codex/Gemini/Hermes compat.
Upstream metadata.version preserved unchanged.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 2 — Implement Windows coder pool dispatch in supervisor._dispatch() [CRITICAL]

**Repo:** `Perpetua-Tools` — branch `feat/openclaw-skills-submodule`

**Files:**
- Modify: `orchestrator/supervisor.py` — implement step 2 in `_dispatch()`

**Context:** `_dispatch()` currently has step 1 (skill gate, ✅ done) and step 3 (normal backend routing). Step 2 is in the docstring but the code falls straight through to step 3. `connectivity.check_lm_studio(host)` already exists and returns `{"ok": True/False, ...}`. `spec.windows_coder_pool` is populated from `$WIN_CODER_ENDPOINTS` env var via the `OrchestrationSession.windows_coder_pool` field, but `JobSpec` doesn't carry it directly — we need to read from the session or the env var.

- [ ] **Step 1: Write the failing test first**

Create/open `tests/test_supervisor_smoke.py` and add at the end:

```python
# ── Windows coder pool dispatch ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dispatch_prefers_windows_coder_when_reachable(tmp_path, monkeypatch):
    """When a Windows coder endpoint is reachable, _dispatch routes to it before Mac-local."""
    import orchestrator.connectivity as conn_mod

    # Simulate one reachable Windows coder
    def fake_check_lm_studio(host: str = "http://127.0.0.1:1234"):
        if "192.168.254.103" in host:
            return {"ok": True, "backend": "lmstudio-win", "host": host}
        return {"ok": False}

    monkeypatch.setattr(conn_mod, "check_lm_studio", fake_check_lm_studio)
    monkeypatch.setenv("WIN_CODER_ENDPOINTS", "http://192.168.254.103:1234")

    sup = _make_sup(tmp_path)
    spec = JobSpec(
        job_id=_new_id(),
        intent="code review",
        prompt="review this file",
        backend_hint="lmstudio-mac",  # would normally go to Mac
    )
    result = await sup._dispatch(spec)
    assert result.get("routed_to_windows") is True, (
        f"Expected Windows coder routing but got: {result}"
    )


@pytest.mark.asyncio
async def test_dispatch_skips_windows_coder_when_unreachable(tmp_path, monkeypatch):
    """When Windows coder is unreachable, _dispatch falls through to normal routing."""
    import orchestrator.connectivity as conn_mod

    monkeypatch.setattr(
        conn_mod, "check_lm_studio", lambda host="http://127.0.0.1:1234": {"ok": False}
    )
    monkeypatch.setenv("WIN_CODER_ENDPOINTS", "http://192.168.254.103:1234")

    sup = _make_sup(tmp_path)
    spec = _echo_spec("fallthrough test")
    result = await sup._dispatch(spec)
    # Falls through to echo backend — no crash, no routing to Windows
    assert result.get("routed_to_windows") is not True
    assert "echo" in str(result).lower() or result.get("status") == "ok"


@pytest.mark.asyncio
async def test_dispatch_skips_windows_coder_when_pool_empty(tmp_path, monkeypatch):
    """When WIN_CODER_ENDPOINTS is empty, _dispatch proceeds to normal routing."""
    monkeypatch.setenv("WIN_CODER_ENDPOINTS", "")

    sup = _make_sup(tmp_path)
    spec = _echo_spec("empty pool test")
    result = await sup._dispatch(spec)
    assert result.get("routed_to_windows") is not True
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd "<workspace>/Perpetua-Tools"
python -m pytest tests/test_supervisor_smoke.py::test_dispatch_prefers_windows_coder_when_reachable -v
```

Expected: FAIL with `AssertionError: Expected Windows coder routing but got: ...` (because step 2 is not yet implemented).

- [ ] **Step 3: Implement `_get_reachable_windows_coder()` helper**

In `orchestrator/supervisor.py`, add this static method to `OrchestrationSupervisor` (after `_try_skill_envelope`, before `_append_event`):

```python
@staticmethod
def _get_reachable_windows_coder() -> str | None:
    """Return the first reachable Windows coder URL from WIN_CODER_ENDPOINTS, or None.

    Probes each endpoint synchronously (fast 2.5s timeout via connectivity.check_lm_studio).
    Skips silently if pool is empty or all endpoints are unreachable.
    """
    import os
    from orchestrator.connectivity import check_lm_studio

    raw = os.environ.get("WIN_CODER_ENDPOINTS", "")
    pool = [url.strip() for url in raw.split(",") if url.strip()]
    if not pool:
        return None

    log = __import__("logging").getLogger(__name__)
    for url in pool:
        try:
            result = check_lm_studio(host=url)
            if result.get("ok"):
                log.info("windows_coder_pool: %s is reachable", url)
                return url
        except Exception as exc:  # noqa: BLE001
            log.warning("windows_coder_pool: probe failed for %s — %s", url, exc)
    log.warning("windows_coder_pool: no reachable Windows coder in pool %s", pool)
    return None
```

- [ ] **Step 4: Wire step 2 into `_dispatch()`**

Replace the current `_dispatch()` body (starting after the skill gate block) with:

```python
async def _dispatch(self, spec: JobSpec) -> dict:
    """Route spec to the correct backend worker and return its result dict.

    Priority:
      1. openclaw-skills primary path (deterministic, zero-LLM)
      2. Windows coder pool (always-utilized before Mac-local)
      3. Normal backend routing (resolve_backend → WORKER_REGISTRY)
    """
    # 1. Spawning gate — check if this task maps to a known openclaw-skills ID
    skill_envelope = self._try_skill_envelope(spec)
    if skill_envelope is not None:
        import logging
        logging.getLogger(__name__).info(
            "spawn_gate: routing job %s to skill %s",
            spec.job_id, skill_envelope.skill_id,
        )
        return {"status": "ok", "skill_envelope": skill_envelope.model_dump()}

    # 2. Windows coder pool — always-utilized before Mac-local dispatch
    win_url = self._get_reachable_windows_coder()
    if win_url is not None:
        import logging
        logging.getLogger(__name__).info(
            "windows_coder_pool: dispatching job %s to %s", spec.job_id, win_url
        )
        from orchestrator.worker_registry import WORKER_REGISTRY
        worker_fn = WORKER_REGISTRY.get("lmstudio-win", WORKER_REGISTRY["echo"])
        result = await worker_fn(spec)
        result["routed_to_windows"] = True
        result["windows_endpoint"] = win_url
        return result

    # 3. Normal backend routing (resolve_backend → WORKER_REGISTRY)
    from orchestrator.worker_registry import WORKER_REGISTRY, resolve_backend
    backend = resolve_backend(spec)
    worker_fn = WORKER_REGISTRY.get(backend, WORKER_REGISTRY["echo"])
    return await worker_fn(spec)
```

- [ ] **Step 5: Run the new tests**

```bash
cd "<workspace>/Perpetua-Tools"
python -m pytest tests/test_supervisor_smoke.py \
  -k "windows_coder" -v
```

Expected: all 3 new tests PASS.

- [ ] **Step 6: Run full supervisor test suite to confirm no regression**

```bash
python -m pytest tests/test_supervisor_smoke.py tests/test_supervisor_lan.py -v
```

Expected: ALL green.

---

## Task 3 — Add `_try_skill_envelope` unit tests + contracts.py pool test

**Repo:** `Perpetua-Tools`

**Files:**
- Modify: `tests/test_supervisor_smoke.py` — add skill envelope routing tests
- Modify: `tests/test_contracts.py` — add `windows_coder_pool` env var test

### Sub-task 3a — Skill envelope routing tests

- [ ] **Step 1: Write failing tests for `_try_skill_envelope`**

Add to `tests/test_supervisor_smoke.py`:

```python
# ── _try_skill_envelope dispatch gate ─────────────────────────────────────────

def test_try_skill_envelope_returns_envelope_for_known_task_type(tmp_path, monkeypatch):
    """_try_skill_envelope returns a SkillEnvelope for known task_type values."""
    from orchestrator.openclaw_skill_resolver import SkillEnvelope
    import importlib
    import orchestrator.openclaw_skill_resolver as r
    importlib.reload(r)

    # Build fake skills tree for openclaw-status
    skill_dir = (
        tmp_path / "bin" / "orama-system" / "skills" / "openclaw-skills" / "skills" / "openclaw-status"
    )
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: openclaw-status\n---\n# Status")

    fake_root = tmp_path / "bin" / "orama-system" / "skills" / "openclaw-skills"
    monkeypatch.setattr(r, "_find_skills_root", lambda: fake_root)

    spec = JobSpec(
        job_id=_new_id(),
        intent="check status",
        prompt="what is the gateway status",
        backend_hint="echo",
        task_type="status",
    )
    result = OrchestrationSupervisor._try_skill_envelope(spec)
    assert result is not None
    assert isinstance(result, SkillEnvelope)
    assert result.skill_id == "openclaw-status"


def test_try_skill_envelope_returns_none_for_unknown_task_type():
    """_try_skill_envelope returns None for task_types not in the skill map."""
    spec = JobSpec(
        job_id=_new_id(),
        intent="general coding",
        prompt="write a function",
        backend_hint="echo",
        task_type="general",   # not in SKILL_MAP
    )
    result = OrchestrationSupervisor._try_skill_envelope(spec)
    assert result is None


def test_try_skill_envelope_returns_none_when_no_task_type():
    """_try_skill_envelope returns None gracefully when task_type is absent."""
    spec = JobSpec(
        job_id=_new_id(),
        intent="echo",
        prompt="hello",
        backend_hint="echo",
    )
    # task_type defaults to None/empty — should not crash
    result = OrchestrationSupervisor._try_skill_envelope(spec)
    assert result is None
```

- [ ] **Step 2: Run to verify they fail (or skip due to missing task_type field)**

```bash
python -m pytest tests/test_supervisor_smoke.py \
  -k "try_skill_envelope" -v
```

Expected: Either FAIL with "object has no attribute 'task_type'" (if JobSpec doesn't have the field yet) or FAIL with SkillResolutionError (if skill path not found).

- [ ] **Step 3: Verify `JobSpec` has `task_type` field**

Check in `orchestrator/supervisor.py`:

```bash
grep -n "task_type" \
  "<workspace>/Perpetua-Tools/orchestrator/supervisor.py" \
  | head -5
```

If `task_type` is NOT on `JobSpec`, add it:

```python
class JobSpec(BaseModel):
    # ... existing fields ...
    task_type: str = ""  # maps to openclaw-skills SKILL_MAP keys when set
```

- [ ] **Step 4: Run tests again**

```bash
python -m pytest tests/test_supervisor_smoke.py -k "try_skill_envelope" -v
```

Expected: `test_try_skill_envelope_returns_none_for_unknown_task_type` and `test_try_skill_envelope_returns_none_when_no_task_type` PASS. `test_try_skill_envelope_returns_envelope_for_known_task_type` may still FAIL if skill path resolution doesn't find the fake root — that is expected until the monkeypatch is active at test runtime.

### Sub-task 3b — contracts.py `windows_coder_pool` test

- [ ] **Step 5: Add pool test to test_contracts.py**

Open `tests/test_contracts.py` and add:

```python
def test_windows_coder_pool_reads_from_env(monkeypatch):
    """windows_coder_pool is populated from WIN_CODER_ENDPOINTS env var."""
    from orchestrator.contracts import OrchestrationSession

    monkeypatch.setenv("WIN_CODER_ENDPOINTS", "http://192.168.254.103:1234,http://192.168.254.104:1234")
    session = OrchestrationSession(objective="test")
    assert session.windows_coder_pool == [
        "http://192.168.254.103:1234",
        "http://192.168.254.104:1234",
    ]


def test_windows_coder_pool_empty_when_env_not_set(monkeypatch):
    """windows_coder_pool is empty list when WIN_CODER_ENDPOINTS is not set."""
    from orchestrator.contracts import OrchestrationSession

    monkeypatch.delenv("WIN_CODER_ENDPOINTS", raising=False)
    session = OrchestrationSession(objective="test")
    assert session.windows_coder_pool == []


def test_windows_coder_pool_filters_empty_strings(monkeypatch):
    """windows_coder_pool skips empty entries from malformed env var."""
    from orchestrator.contracts import OrchestrationSession

    monkeypatch.setenv("WIN_CODER_ENDPOINTS", ",http://192.168.254.103:1234,,")
    session = OrchestrationSession(objective="test")
    assert session.windows_coder_pool == ["http://192.168.254.103:1234"]
```

- [ ] **Step 6: Run contracts tests**

```bash
python -m pytest tests/test_contracts.py -v
```

Expected: ALL green including the 3 new pool tests.

- [ ] **Step 7: Run full test suite**

```bash
python -m pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: All existing tests green + new tests green. Zero regressions.

- [ ] **Step 8: Commit Task 3**

```bash
cd "<workspace>/Perpetua-Tools"
git add tests/test_supervisor_smoke.py tests/test_contracts.py orchestrator/supervisor.py
git commit -m "$(cat <<'EOF'
feat(supervisor): implement Windows coder pool dispatch + test coverage

Sub-D complete:
- _dispatch() step 2: probe WIN_CODER_ENDPOINTS pool via
  check_lm_studio(); route to first reachable Windows coder
  before Mac-local dispatch; sets routed_to_windows=True in result
- Add _get_reachable_windows_coder() static helper
- Add test_dispatch_prefers_windows_coder_when_reachable
- Add test_dispatch_skips_windows_coder_when_unreachable
- Add test_dispatch_skips_windows_coder_when_pool_empty
- Add _try_skill_envelope unit tests (known / unknown / no task_type)
- Add contracts.py windows_coder_pool env var tests (3 cases)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4 — Verify spec checklist, sync both repos, open PR

**Repos:** Both `orama-system` + `Perpetua-Tools`

- [ ] **Step 1: Run the spec verification checklist**

```bash
cd "<workspace>/orama-system"

# A: Submodule
echo "=== A: Submodule ===" && git submodule status bin/orama-system/skills/openclaw-skills/cc-openclaw
bash scripts/install-openclaw-skills.sh

# B: Compliance — no subskill missing upstream:
echo "=== B: Subskill upstream: field ===" && grep -rL "upstream:" bin/orama-system/skills/openclaw-skills/skills/

# C: Search frugality present
echo "=== C: Search frugality ===" && grep -c "Search Frugality Rule" bin/orama-system/skills/openclaw-skills/SKILL.md

# C: Windows coder in CLAUDE.md
echo "=== C: Win coder in CLAUDE.md ===" && grep "WIN_CODER" CLAUDE.md

# D: contracts pool field
cd "<workspace>/Perpetua-Tools"
echo "=== D: contracts.py pool ===" && python -c "
from orchestrator.contracts import OrchestrationSession
import os; os.environ['WIN_CODER_ENDPOINTS'] = 'http://192.168.254.103:1234'
s = OrchestrationSession(objective='verify')
print('pool:', s.windows_coder_pool)
"
```

Expected for each:
- A: `553e2e9a49e4... bin/orama-system/skills/openclaw-skills/cc-openclaw (heads/main)` + "Done."
- B: empty output (all 9 have `upstream:`)
- C: `1` (rule present)
- C: line with `WIN_CODER_ENDPOINTS`
- D: `pool: ['http://192.168.254.103:1234']`

- [ ] **Step 2: Run full PT test suite one final time**

```bash
cd "<workspace>/Perpetua-Tools"
python -m pytest tests/ -v --tb=short 2>&1 | grep -E "PASSED|FAILED|ERROR|warnings" | tail -30
```

Expected: Zero FAILED, zero ERROR.

- [ ] **Step 3: Commit orama-system spec + plan**

```bash
cd "<workspace>/orama-system"
git add docs/superpowers/plans/2026-05-20-cc-openclaw-master-alignment.md
git commit -m "docs(plan): add cc-openclaw master alignment implementation plan

Records shipped vs needed diff, 4 tasks covering Sub-B SKILL.md
compliance gaps, Sub-D Windows coder pool step 2 implementation,
test coverage, and final PR gate.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

- [ ] **Step 4: Push orama-system branch**

```bash
cd "<workspace>/orama-system"
git push -u origin feat/openclaw-skills-submodule
```

- [ ] **Step 5: Push PT branch**

```bash
cd "<workspace>/Perpetua-Tools"
git push -u origin feat/openclaw-skills-submodule
```

- [ ] **Step 6: Open orama-system PR**

```bash
cd "<workspace>/orama-system"
gh pr create \
  --title "feat(openclaw-skills): cc-openclaw master alignment — submodule, compliance, search frugality, Windows coder policy" \
  --body "$(cat <<'EOF'
## Summary

- **Sub-A**: Wire `rahulsub-be/cc-openclaw` as git submodule at `bin/orama-system/skills/openclaw-skills/cc-openclaw/`; add idempotent `scripts/install-openclaw-skills.sh` called from `start.sh`; attribute upstream in master SKILL.md (Two-Layer Architecture documented)
- **Sub-B**: All 11 SKILL.md files now have `name`, `description`, `version`, `layer`, `agent_compatibility`, `upstream` (where applicable), and `## References` cross-links
- **Sub-C**: Search frugality rule (gbrain → CRG → Brave → Perplexity → Grok) + Windows coder always-utilized policy enshrined in `CLAUDE.md`, `bin/orama-system/SKILL.md`, and `universal-skill-protocol.md`
- **Sub-D**: `supervisor._dispatch()` step 2 implemented (Windows coder pool probe + dispatch); `contracts.py` `windows_coder_pool` field; `_try_skill_envelope()` gate with 9-entry SKILL_MAP

## Test plan

- [ ] `bash scripts/install-openclaw-skills.sh` → prints "Done." with no warnings
- [ ] `grep -rL "upstream:" bin/orama-system/skills/openclaw-skills/skills/` → empty
- [ ] `python -m pytest tests/test_supervisor_smoke.py tests/test_contracts.py -v` → all green (in Perpetua-Tools)
- [ ] `grep "WIN_CODER_ENDPOINTS" CLAUDE.md` → returns match

## Lockstep companion PR

Perpetua-Tools: `feat/openclaw-skills-submodule` (contracts.py + supervisor.py + tests)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 7: Open Perpetua-Tools PR**

```bash
cd "<workspace>/Perpetua-Tools"
gh pr create \
  --title "feat(supervisor): Windows coder pool dispatch + skill envelope gate + test coverage" \
  --body "$(cat <<'EOF'
## Summary

- `supervisor._dispatch()` step 2: probe `WIN_CODER_ENDPOINTS` pool via `check_lm_studio()`; route to first reachable Windows coder before Mac-local (always-utilized policy)
- `supervisor._get_reachable_windows_coder()`: new static helper
- `contracts.py`: `windows_coder_pool` field populated from `WIN_CODER_ENDPOINTS` env
- Tests: 6 new tests covering Windows coder routing (3 cases), `_try_skill_envelope` (3 cases), and `windows_coder_pool` env parsing (3 cases)

## Test plan

- [ ] `python -m pytest tests/test_supervisor_smoke.py -k "windows_coder or skill_envelope" -v` → all green
- [ ] `python -m pytest tests/test_contracts.py -v` → all green
- [ ] `python -m pytest tests/ --tb=short` → zero failures

## Lockstep companion PR

orama-system: `feat/openclaw-skills-submodule` (submodule, compliance, docs)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Self-Review

**Spec coverage check:**
- Sub-A: ✅ All landed in 7ee2819 (shipped, not in this plan)
- Sub-B (4 remaining files): ✅ Task 1 covers cherry-pick-down, macos-port-status, supabase, supabase-postgres-best-practices
- Sub-C: ✅ All landed in 7ee2819 (shipped, not in this plan)
- Sub-D Windows coder step 2: ✅ Task 2 covers `_get_reachable_windows_coder()` + `_dispatch()` wiring
- Sub-D tests: ✅ Tasks 3a + 3b cover all 9 new test cases
- Final PR: ✅ Task 4 covers both repos

**Placeholder scan:** No TBD, TODO, "implement later", or vague steps. All code is concrete.

**Type consistency:**
- `JobSpec.task_type: str = ""` — introduced in Task 3, referenced in `_try_skill_envelope()` Task 2 ✅
- `_get_reachable_windows_coder() -> str | None` — defined in Task 2 Step 3, called in Task 2 Step 4 ✅
- `routed_to_windows: True` — set in Task 2 Step 4, asserted in Task 2 Step 1 tests ✅
- `windows_coder_pool` — already in contracts.py (shipped), tested in Task 3b ✅