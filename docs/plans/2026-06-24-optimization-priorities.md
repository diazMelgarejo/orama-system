<!-- lint-ignore LINT-012 -->
# Optimization Priorities — Strategic Backlog (2026-06-24)

> **Date:** 2026-06-24 · **Owner:** orama-system (L3) + Perpetua-Tools (L2)
> **Status:** 🔄 ACTIVE — L1 skipped (user decision); L2-L5 ✅ shipped `890e0c8`
> **Author:** claude-sonnet-4.6 + cyre
> **Review trigger:** next substantive session start OR when perpetua-core gate clears

---

## Source context

Generated after completing:
- PR #104 + #105 nested branch merge (combine-never-replace, 11 conflicts)
- Perpetua-Tools 4-PR hardware affinity chain (#128 → #129 → #130 → #131)
- orama-system v1.1.0.0 version centralization (25+ surfaces, sync_version.py)
- AGY migration (Gemini CLI retired 2026-06-18, invoke_agent personas live)
- perpetua-core RC-1 as-built documented (all 16 tasks done, push gate open)
- Post-merge CodeRabbit sweeps across all PRs in both repos
- Hermes sync + reflection branch memory integration

---

## Priority Stack (execute in order)

### L1 — Blocking: perpetua-core hardware review gate

**What:** End-to-end review of `feat/salvage-plugins-rc1` on both hardware targets before pushing to `perpetua-core` main and tagging `v0.2.0-alpha`.

**Hardware targets:**
- Mac: Ollama `localhost:11434` — models: `qwen3.5:9b-nvfp4`, `qwen3-coder:480b-cloud`
- Win: LM Studio `$LM_STUDIO_WIN_ENDPOINT` (e.g. `<win-lan-ip>:1234` — read from `~/.openclaw/state/last_discovery.json`) — model: `qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2`

**Why blocking:** Phase 3 (Orchestration & API Layer) cannot start until `v0.2.0-alpha` is tagged. All three repos (oramasys/perpetua-core, Perpetua-Tools, orama-system) have downstream work waiting on this milestone.

**Verification checklist:**
- [ ] `python3 -m pytest` — all 56 tests in perpetua-core green
- [ ] Mac Ollama: `python3 -c "from perpetua_core.discovery import probe; ..."` → health OK
- [ ] Win LM Studio: `curl http://$LM_STUDIO_WIN_ENDPOINT/v1/models` → 27B model listed
- [ ] `engine.ainvoke` round-trip on both hardware targets
- [ ] `git push origin feat/salvage-plugins-rc1` → `git tag v0.2.0-alpha`

**Refs:**
- `oramasys/perpetua-core` HEAD `56f2a6d`
- `orama-system/docs/v2/15-phase1-as-built.md` § Salvage Translation RC-1
- `orama-system/docs/v2/04-build-order.md` — Phase 2 DONE, Phase 3 NEXT

---

### L2 — ✅ DONE (`890e0c8`): oramaclaw store.py TOCTOU lock

**File:** `orama-system/src/oramaclaw/store.py:163`
**Severity:** 🔴 Critical (CodeRabbit) — concurrent data corruption

**Root cause:** Lock acquisition uses `exists()`/`read()`/`overwrite()` — a classic TOCTOU race. Two concurrent `apply` runs can both pass the `lock_path.exists()` check and proceed to write, corrupting `registry/journal` state.

**Fix direction:** Replace with atomic exclusive-create using `O_CREAT | O_EXCL`:
```python
import os, fcntl

def _acquire_lock(lock_path: Path) -> None:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, json.dumps({"pid": os.getpid(), "acquired": time.time()}).encode())
        os.close(fd)
    except FileExistsError:
        # Another process holds the lock — read PID and check staleness
        ...
```

**Test to write:** `test_concurrent_apply_does_not_corrupt_registry` (two threads, shared tmpdir, assert final state is valid).

---

### L3 — ✅ DONE (`55ec2f4`): repo_hygiene.py LINT-010/011/012

**File:** `orama-system/scripts/review/repo_hygiene.py`

Three linter rules to add, each catching a recurring silent failure pattern:

| Rule | Pattern | Symptom caught |
|------|---------|----------------|
| `LINT-010` | All-`1.` numbered lists in `## Procedure` sections outside code fences | The openclaw step bug (9 SKILL.md files had `1.` for every step; agent runtimes read raw text) |
| `LINT-011` | `(deprecated)` inside `trigger:` strings in SKILL.md frontmatter | Routing matchers see literal `(deprecated)` — breaks existing routes silently |
| `LINT-012` | `hermes -z` flag in any tracked `.md` file (see description) | Deprecated flag; `hermes chat --query` is the current syntax |

**Implementation pattern** (follow existing `check_stale_skill_path_refs` pattern):
```python
def check_skill_trigger_quality(root: Path) -> list[str]:
    errors = []
    for skill_md in root.rglob("SKILL.md"):
        text = skill_md.read_text()
        if "(deprecated)" in text and "trigger:" in text:
            errors.append(f"LINT-011: {skill_md} — (deprecated) in trigger string")
        if re.search(r"^1\. ", text[text.find("## Procedure"):], re.MULTILINE):
            ...
    return errors
```

---

### L4 — ✅ DONE (`890e0c8`): post-merge-review-sweep.yml GitHub Action

**What:** A GitHub Action (or PT `.agent` scheduled task) that runs after any PR merge and creates a summary of unresolved review comments, so the manual polling step is replaced.

**Workflow sketch:**
```yaml
on:
  pull_request:
    types: [closed]

jobs:
  cr-sweep:
    if: github.event.pull_request.merged == true
    runs-on: ubuntu-latest
    steps:
      - name: Fetch unresolved review comments
        run: |
          gh pr view ${{ github.event.pull_request.number }} \
            --json reviewThreads \
            --jq '[.reviewThreads[] | select(.isResolved == false)]' \
          | python3 scripts/ci/summarize_cr_comments.py
```

**Why:** In this session, finding unresolved comments required manual API polling across 8 PRs. Many were stale (already fixed) — the verify step before applying is still manual, but discovery should be automatic.

---

### L5 — ✅ DONE (PT `c91a4f6`): combine-never-replace in PT/.agent/AGENTS.md

**File:** `Perpetua-Tools/.agent/AGENTS.md`

**What to add:** A formal "Multi-agent merge conflict protocol" section:
1. `git merge --no-commit --no-ff` — enumerate ALL conflicts before touching any file
2. Present every conflict with both sides shown — never guess resolution
3. Wait for human direction: combine / take-ours / take-theirs / build-union
4. Resolve all in one pass with the directed strategy
5. Push → wait for CI → perform GitHub API merge
6. Wait 10 minutes between merges; verify `mergeable_state=clean`

**Why:** The strategy was invented per-session and lives only in episodic memory. Encoding it in AGENTS.md makes it available to any agent (Hermes, Codex, Claude) as a first-class protocol.

---

## Session artifacts worth preserving

| Artifact | Location | Notes |
|----------|----------|-------|
| Version SSoT | `orama-system/src/orama_system/_version.py` | Edit only here; sync script propagates |
| Sync script | `orama-system/scripts/sync_version.py` | `--check` is the CI gate |
| Affinity chain | `PT/src/utils/hardware_policy.py` + `_normalize_policy()` | 4-PR chain, 13 tests |
| AGY personas | `orama-system/agy-gemini.md` + `scripts/agy/invoke_agent.sh` | 3 personas |
| As-built RC-1 | `orama-system/docs/v2/15-phase1-as-built.md` | perpetua-core Phase 2 complete |
| Memory | `PT/.agent/memory/` — 61 episodic, 79 lessons | Hermes sync integrated |

---

## Deferred (not blocking, schedule separately)

| Item | File | Why deferred |
|------|------|-------------|
| `engine.py` orphan conflicts | `src/oramaclaw/engine.py:269` | Requires understanding retry loop semantics fully |
| `engine.py` timeout bypass | `src/oramaclaw/engine.py:293` | Coupled to orphan conflict fix |
| Periscope L4 integration | `docs/plans/2026-05-24-periscope-l4-integration-plan.md` | 52 open items, separate session |

---

*Next review: start of next substantive session, or when L1 (perpetua-core gate) clears.*
