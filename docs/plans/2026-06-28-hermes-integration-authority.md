<!-- /autoplan restore point: ~/.gstack/projects/orama-system/main-autoplan-restore-2026-06-28-hermes-integration-authority.md -->

# Hermes Integration Authority Spec
**Version:** 1.1.0-harmonized  
**Status:** Approved — implemented 2026-06-28 (main batch `hermes-integration-authority`)  
**Date:** 2026-06-28

---

## 1. Thesis

Hermes is **not** a replacement for OpenClaw. Hermes is an **operator shell** that consumes the same canonical PT-orama/ECC skills OpenClaw consumes, but through a different invocation surface. Orchestrators must treat Hermes and OpenClaw as **co-equal harness adapters** over a single durable skill corpus.

> **One sentence:** OpenClaw owns the fabric; Hermes owns operator-side dispatch, install, provider wiring, and cross-harness coordination.

---

## 2. Authority Model

| Layer | Owner skill | Responsibility | Inviolable rule |
|---|---|---|---|
| **Fabric** | `openclaw-skills` | Gateway, stow, restart, cron, secrets, agent lifecycle | Never overwritten by Hermes |
| **Operator shell** | `hermes-harness` | Hermes install, provider config, skill import, partner CLIs, cross-harness dispatch | Never re-implements OpenClaw procedures |
| **Hardware affinity** | `hardware-affinity-gate` via `perpetua-hardware` | Model routing, NEVER gates, tier selection | PT-orama is SSoT; orama references, never re-declares |
| **LLM council / delegation / lesson mining** | `pt-orama-council`, `pt-orama-delegate`, `pt-orama-lesson-mining` | Multi-model evaluation, bounded delegation, memory graduation | Thin Hermes wrappers only; canonical body stays in repo |

**Anti-pattern (forbidden):**
- Hermes running `openclaw-restart` logic inline
- Hermes storing its own copy of hardware routing rules
- Hermes importing `~/.hermes` state into a repo or message payload

---

## 3. Universal Invocation Protocol

Cross-harness contract uses a **core envelope** (required everywhere) plus **harness extension fields** (optional components). OpenClaw and Hermes are subsets of one superset schema; runners ignore unknown optional fields.

Reference: `openclaw-skills/references/universal-skill-protocol.md` (Nine Skills) and new `hermes-harness/references/hermes-universal-invocation-protocol.md` (operator extensions).

### 3.1 Core envelope (all harnesses)

```json
{
  "skill_id": "pt-orama-council",
  "args": {
    "task": "evaluate PR #108 against security review checklist"
  },
  "agent_id": "hermes"
}
```

| Field | Required | Rule |
|---|---|---|
| `skill_id` | yes | Canonical slug; resolve path via registry (§5), not cache |
| `args` | yes | Flat JSON object; use `{}` when none |
| `agent_id` | yes | Invoking agent who owns the audit trail: `hermes`, `codex`, `claude`, `openclaw`, `agy`, `orchestrator` |
| `executor_id` | no | Who runs the skill body; required when delegating (`codex`, `agy`); defaults to `agent_id` |

### 3.2 Harness extension fields (optional components)

Committed specs and skill docs use **env placeholders only**. Runners expand to absolute paths programmatically at runtime before any file I/O. Never commit workstation absolute paths.

| Field | When required | Committed placeholder | Runtime expansion |
|---|---|---|---|
| `harness` | Hermes / multi-harness dispatch | `"hermes"` | Echo only; no path expansion |
| `orama_system_root` | Hermes operator skills | `"$ORAMA_SYSTEM_PATH"` | `git rev-parse --show-toplevel` or env |
| `openclaw_home` | OpenClaw fabric skills | `"$OPENCLAW_HOME"` | User-supplied or default `~/.openclaw` |
| `canonical_skill_root` | Path-relative resolution | `"bin/orama-system/skills"` | Join with expanded `orama_system_root` |
| `repo_root` | **Deprecated alias** | Use `orama_system_root` | Same expansion rule |

**Harmonized example (Hermes dispatch):**

```json
{
  "skill_id": "pt-orama-council",
  "args": {},
  "agent_id": "hermes",
  "executor_id": "codex",
  "harness": "hermes",
  "orama_system_root": "$ORAMA_SYSTEM_PATH",
  "canonical_skill_root": "bin/orama-system/skills"
}
```

**Harmonized example (OpenClaw fabric dispatch):**

```json
{
  "skill_id": "openclaw-status",
  "args": {},
  "agent_id": "claude",
  "openclaw_home": "$OPENCLAW_HOME"
}
```

**Cross-harness orchestrator** may carry both `orama_system_root` and `openclaw_home` when chaining operator + fabric steps. Child calls inherit parent-expanded paths; do not re-placeholder mid-chain.

### 3.3 Result shape (superset / subset)

**Core result (OpenClaw-compatible — required):**

```json
{
  "status": "ok",
  "files_modified": [],
  "follow_up_actions": []
}
```

| Field | Required | Rule |
|---|---|---|
| `status` | yes | `ok`, `needs_input`, `partial`, `error` (canonical); Hermes may also emit `blocked` as alias for `needs_input` when preconditions fail |
| `files_modified` | yes | Paths relative to target home (`openclaw_home` or `orama_system_root`); empty for read-only |
| `follow_up_actions` | yes | Actionable next steps; never empty on `needs_input` / `blocked` / `error` |

**Hermes extension fields (optional):**

| Field | Type | When |
|---|---|---|
| `harness` | string | Echo dispatch harness |
| `skill_id` | string | Echo invoked skill |
| `agent_id` | string | Echo invoking agent |
| `output` | object | Structured skill output (`summary`, `artifacts`) |
| `warnings` | array | Non-fatal issues |
| `errors` | array | Fatal detail when `status` is `error` |
| `checks` | array | Verification steps performed (health/bootstrap) |

Hermes runners must always populate the **core trio**; extension fields are additive. OpenClaw-only runners may omit Hermes extensions. Parsers must accept the superset and treat missing optional fields as absent.

---

## 4. Hermes / OpenClaw Integration Contract

### 4.1 Orchestrator responsibilities

1. **Resolve canonical skill by path** — never by local cache. Hermes must `git fetch origin --prune` then `git pull --ff-only` from expanded `orama_system_root` before loading a skill body.
2. **Load by slug** — Hermes local commands map `/<slug>` to registry canonical path (§5). Command cards live under `hermes-harness/commands/<slug>/`.
3. **Suppress private state** — any Hermes config, memory, or secret stays in `$LOCALAPPDATA/hermes` and is never attached to skill output.
4. **Fail-closed on hardware mismatch** — if `hardware-affinity-gate` returns `NEVER`, the orchestrator stops; no silent fallback through Hermes.

### 4.2 What changes in OpenClaw

None. OpenClaw’s authority over the fabric is unchanged. The only *new* rule:

> If an orchestrator is running under Hermes and encounters an `openclaw-*` skill, it **must** dispatch through `openclaw-skills`’s universal protocol rather than invoking Hermes inline.

### 4.3 Hermes bootstrap gate

Before any non-trivial dispatch on Windows, orchestrators must run:

```powershell
$env:HERMES_HOME = if ($env:HERMES_HOME) { $env:HERMES_HOME } else { "$env:LOCALAPPDATA\hermes" }
$installDir = Join-Path $env:HERMES_HOME "hermes-agent"
if (-not (Test-Path "$installDir\.git")) { throw "HERMES_NOT_INSTALLED" }
& $env:HERMES_GIT_BASH_PATH --noprofile --norc -lc 'echo hermes-bash-ok'
```

Return as health envelope (core + extensions):

```json
{
  "status": "ok",
  "files_modified": [],
  "follow_up_actions": [],
  "harness": "hermes",
  "checks": ["hermes-bash-ok", "install_dir_present"],
  "output": { "bash": "hermes-bash-ok", "install_dir": "$HERMES_HOME/hermes-agent" }
}
```

Placeholders in committed examples; runners expand `install_dir` at runtime.

---

## 5. Subskill Registry (Hermes-facing)

These are the Hermes-primary entry points into canonical PT-orama skills. Each must have a thin wrapper in `~/.claude/skills` or `~/.agents/skills` that points back to the canonical path.

| Wrapper slug | Canonical target | Harness | Notes |
|---|---|---|---|
| `pt-orama-council` | `hermes-harness/commands/pt-orama-council/SKILL.md` | Hermes / Codex | 5-model council |
| `pt-orama-review` | `hermes-harness/commands/pt-orama-review/SKILL.md` | Hermes / Codex | Findings-first review |
| `pt-orama-delegate` | `hermes-harness/commands/pt-orama-delegate/SKILL.md` | Hermes / AGY | Bounded delegation |
| `pt-orama-lesson-mining` | `hermes-harness/commands/pt-orama-lesson-mining/SKILL.md` | Hermes / Codex | **Optional** — not installed by default; no PT dependency |
| `pt-hardware-policy` | `hermes-harness/commands/pt-hardware-policy/SKILL.md` | Hermes | Thin wrapper over `hardware-affinity-gate` |
| `hermes-harness` | `hermes-harness/SKILL.md` | Hermes | Install / provider / import |
| `local-inference` | `local-inference/SKILL.md` (redirect stub) | Hermes | Redirect → `hardware-affinity-gate` |
| `openclaw-add-secret` | `openclaw-skills/skills/openclaw-add-secret/SKILL.md` | Hermes | macOS keychain; Win returns `blocked` |
| `openclaw-status` | `openclaw-skills/skills/openclaw-status/SKILL.md` | Hermes | Health envelope |
| `openclaw-restart` | `openclaw-skills/skills/openclaw-restart/SKILL.md` | Hermes | Restart envelope; Mac fabric primary |

**Wrapper policy (mandatory)**
- Wrapper body ≤ 60 lines
- Contains exactly: canonical repo root, canonical `SKILL.md` path, redirect docstring
- Calls `git fetch origin --prune` before reading canonical
- Calls `git pull --ff-only` only if repo is clean and on tracking branch
- No cached copies of upstream SKILL.md, references, scripts, assets

---

## 6. Windows-Specific Authority

`hermes-harness` owns the Windows bring-up recipe because it is Hermes-specific install/provider logic, **not** because OpenClaw is absent on Windows.

| Concern | Current owner | Target owner |
|---|---|---|
| `HERMES_HOME`, Git Bash path, venv launcher | `hermes-harness` | Stay |
| LM Studio / Ollama endpoint wiring | `hardware-affinity-gate` | Stay |
| `start.sh` / `start.ps1` canary smoke test | `platform/windows/` + `platform/macos/` scripts | Invoked by `hermes-harness`; not owned by `openclaw-skills` |
| Partner CLI paths (`codex`, `agy`, `gemini`) | `hermes-harness` | Stay |
| Clipboard / OCR / MCP installs | `hermes-harness` | Stay |

**Rule:** if a procedure appears in both `openclaw-skills` and `hermes-harness`, the `openclaw-skills` version is the canonical fab-layer procedure; Hermes calls it, never re-implements it.

---

## 7. Failure Modes and Recovery

| Failure | Detection | Recovery |
|---|---|---|
| `git pull --ff-only` fails | Non-zero exit + stderr contains `refusing to merge` | Return `blocked`; `follow_up_actions`: ["git status --short --branch", "rebase or stash"] |
| Hermes `chat` returns empty | `stdout` empty after `--max-turns 1` | Retry once with `--provider nous --model stepfun/step-3.7-flash:free`; if still empty, return `error` |
| `HERMES_GIT_BASH_PATH` invalid | `hermes-bash-ok` missing from bootstrap probe | Return `blocked`; `follow_up_actions`: ["set HERMES_GIT_BASH_PATH to literal bash.exe"] |
| LM Studio canary exceeds threshold | `time_total > 180s` for 27B reasoning | Return `blocked`; `follow_up_actions`: ["switch tier to shared fallback", "check gpu_offload"] |
| `nul` file in repo | Windows `type nul` artifact | Delete before commit; add to `.gitignore` |
| Stale submodule pointer | `git submodule status` shows `-` prefix | Run `git submodule update --init`; return `ok` with updated sha |

---

## 8. Sweeping Policy Statements

1. **Hermes is first-class.** If a skill is loadable by OpenClaw, it is loadable by Hermes — same canonical file, same JSON envelope, same result shape.
2. **No shadow skills.** Hermes must not maintain private copies of PT-orama/ECC skill bodies. All Hermes skills are wrappers or redirect stubs.
3. **PT-orama owns routing.** Hardware affinity, model IDs, NEVER lists, and tier definitions live in Perpetua-Tools. orama-system references them. Hermes consumes both.
4. **Windows parity.** Anything achievable on macOS via `openclaw-skills` is achievable on Windows via `hermes-harness` + `openclaw-skills`. Missing parity is a bug, not a limitation.
5. **Live-model reality.** The working model in this Hermes session is `nous:stepfun/step-3.7-flash:free`. Any provider/model routing doc must reflect this as an approved Windows sidecar, not a placeholder.
6. **Memory dreaming is mandatory before merge.** No PR touching skill absorption may land without a successful `auto_dream.py` + `show.py` verification cycle on the live Windows+Hermes testdrive.
7. **No workstation doxxing.** All paths in repo content use `$ORAMA_SYSTEM_PATH`, `$OPENCLAW_HOME`, `$HERMES_HOME`, or GitHub URLs. Absolute workstation paths are a CI failure. Runners expand placeholders programmatically at runtime only.
8. **Main integration with logical batches.** Land coherent units on `main` when the Windows testdrive is green. Avoid per-task feature branches that fragment fast-moving harness work and complicate merge resolution. Name batches in plan docs (e.g. `2026-06-28-hermes-integration-authority`). Mac E2E and tag bumps follow in the next batch, not a blocking branch fork.

---

## 9. Migration Checklist (for manual execution)

- [ ] Update `hermes-harness/SKILL.md` to include §3 envelope + result shape
- [ ] Add `layer`, `upstream`, `agent_compatibility` frontmatter to `hermes-harness`
- [ ] Add 10-row subskill registry table to `hermes-harness`
- [ ] Add Hermes bootstrap gate with health envelope to `hermes-harness`
- [ ] Align `.agents/skills/skillify/SKILL.md` with `bin/orama-system/skills/skillify/SKILL.md` validator constraint
- [ ] Add post-edit validation guard to `hardware-affinity-gate/SKILL.md` (already done)
- [ ] Ensure `nul` file is removed and `.gitignore` updated
- [ ] Run `auto_dream.py` on Windows + `show.py` verification
- [ ] Commit on `main` as logical batch `hermes-integration-authority` after interrogation closes
- [ ] Fast-forward both repos to `origin/main` after batch lands

---

## 10. Interrogation Resolutions (D2=C — closed 2026-06-28)

### Q1 — Partner dispatch: layered envelopes (OSI-style)

Each layer carries the **core trio** (`skill_id`, `args`, `agent_id`) plus layer-specific extensions.

| Layer | Name | Who reads it | Adds |
|-------|------|--------------|------|
| L3 | Intent | Orchestrator | `harness` |
| L2 | Dispatch | Hermes | `orama_system_root`, `executor_id` |
| L1 | Transport | Partner CLI (internal) | codex/agy flags — not in committed docs |
| L0 | Result | All auditors | core result superset (§3.3) |

Codex and AGY share L3/L2; only L1 transport differs. L2→L1 translation stays inside runners (`dispatch_codex_partner.py`, AGY scripts).

### Q2 — Dual identity fields

| Field | Meaning |
|-------|---------|
| `agent_id` | Initiator / audit owner (`hermes`) |
| `executor_id` | Runner (`codex`, `agy`, `hermes`) |

Required when delegating; `executor_id` defaults to `agent_id` for local Hermes execution.

### Q3 — Path casing: warn-only

Expand via `git rev-parse --show-toplevel` or env. Casing mismatch → `warnings[]`, not `blocked`.

---

## 11. Harmonization Ledger (D2=B)

| Item | Decision |
|------|----------|
| P1–P5 | User overrides applied in §3, §5, §8 |
| Taste | All recommendations accepted |
| Q1 | OSI-style layered envelopes |
| Q2 | `agent_id` + `executor_id` |
| Q3 | Warn-only casing |

**Gate:** D2=B+C+D complete. L1:B transport. Implemented on `main` 2026-06-28.

---

## 12. Open Questions (superseded — see §10)

1. ~~Codex/AGY envelope~~ → §10 Q1
2. ~~agent_id restriction~~ → §10 Q2
3. ~~Path casing~~ → §10 Q3

---

## GSTACK REVIEW REPORT

**/autoplan completed:** 2026-06-28 · Branch: `main` @ `3a4d66d` · Phases: CEO ✅ · Design skipped (no UI) · Eng ✅ · DX ✅

### Plan Summary

Draft authority spec to bring `hermes-harness` to structural parity with `openclaw-skills`: universal JSON envelope, subskill registry, layer metadata, bootstrap gate, boundaries, and health JSON. Thesis (Hermes = operator shell, OpenClaw = fabric) is sound and matches merged absorption work.

### Premises — confirm before implementation <gstack-qid:autoplan-premises-hermes-authority>

| # | Premise | Verdict | Notes |
|---|---------|---------|-------|
| P1 | Hermes and OpenClaw are co-equal harness adapters over one corpus | **Accept** | Matches `cross-harness-protocol.md` + absorption map |
| P2 | Universal envelope can be shared across harnesses | **Challenge** | OpenClaw uses `openclaw_home`; plan adds `repo_root` + `harness` — needs harmonization spec |
| P3 | All registry slugs in §5 exist at stated paths | **Reject** | 6/10 paths wrong or missing (see Eng §3) |
| P4 | `repo_root` must be absolute in envelope | **Challenge** | Conflicts with §8.7 (no workstation paths in repo) — resolve at runtime |
| P5 | Feature-branch-only policy (§8.8) | **Challenge** | Contradicts recent direct-to-main Win testdrive workflow |

**Reply with premise overrides** (e.g. "P3: fix paths" / "P4: env-only" / "P5: drop") before implementation.

**User response (2026-06-28):** P1 accept · P2 accept+harmonize superset/subset · P3 fix+runtime parametrize · P4 runtime-resolve · P5 main+batches · all taste recommendations accepted · D2=B+C+D.

---

### CEO Dual Voices — Consensus

| Dimension | Claude | Codex | Consensus |
|-----------|--------|-------|-----------|
| Right problem (authority gap vs feature work)? | Yes | N/A | Partial — gap is real |
| Scope calibrated? | Slightly heavy | N/A | DISAGREE — registry + protocol + policies + migration in one PR |
| OpenClaw fabric untouched? | Yes | N/A | CONFIRMED |
| Windows parity stated correctly? | Mostly | N/A | DISAGREE — §6 misattributes `start.ps1` owner |

**Mode:** SELECTIVE EXPANSION — implement protocol + registry + frontmatter first; defer lesson-mining slug until canonical exists.

**NOT in scope (defer):**
- Automating envelope in Python dispatcher (spec-only v1)
- Rewriting `universal-skill-protocol.md` for Nine Skills (reference only)
- Mac cross-harness E2E (separate handoff doc)

**What already exists:**
- `openclaw-skills` envelope + result shape (§55–80)
- `install_hermes_thin_skills.py` (4 wrappers: council/review/delegate/hardware-policy)
- Absorption map + `.agents` thin wrappers (2026-06-28)
- `verify_partner_canaries.py` + JSON-capable patterns in partner dispatch

---

### Eng Review — Architecture

```
┌─────────────────────────────────────────────────────────┐
│ L3 orama-system canonical skills                        │
│  openclaw-skills (fabric)  │  hermes-harness (operator)│
└──────────────┬──────────────────────────┬───────────────┘
               │ universal envelope      │
               ▼                         ▼
┌──────────────────────┐    ┌──────────────────────────┐
│ openclaw_home target   │    │ ORAMA_SYSTEM_PATH +      │
│ Nine Skills overlays   │    │ hermes-harness/commands/*│
└──────────────────────┘    └──────────────────────────┘
               │                         │
               └───────────┬─────────────┘
                           ▼
              Perpetua-Tools hardware_policy_cli (SSoT)
```

**Critical fixes required in §5 registry:**

| Slug in plan | Plan path (wrong) | Actual canonical path |
|--------------|-------------------|------------------------|
| `pt-orama-council` | `skills/pt-orama-council/` | `skills/hermes-harness/commands/pt-orama-council/` |
| `pt-orama-review` | same pattern | `.../commands/pt-orama-review/` |
| `pt-orama-delegate` | same pattern | `.../commands/pt-orama-delegate/` |
| `pt-hardware-policy` | `skills/pt-hardware-policy/` | `.../commands/pt-hardware-policy/` |
| `pt-orama-lesson-mining` | `skills/pt-orama-lesson-mining/` | **DOES NOT EXIST** — use PT `learn.py` or create command |
| `local-inference` | `skills/local-inference/` | ✅ redirect stub exists |
| `openclaw-*` | `skills/openclaw-*/` | ✅ under `openclaw-skills/skills/openclaw-*/` |

**Envelope harmonization (recommended):**

```json
{
  "skill_id": "pt-orama-council",
  "args": {},
  "agent_id": "hermes",
  "harness": "hermes",
  "orama_system_root": "$ORAMA_SYSTEM_PATH",
  "openclaw_home": "$OPENCLAW_HOME",
  "canonical_skill_root": "bin/orama-system/skills"
}
```

- At **runtime**, runners resolve env vars to absolute paths internally; envelopes in **committed docs** use placeholders only.
- **Result superset:** keep OpenClaw `files_modified` + add Hermes `output`/`warnings`/`errors` as optional extensions (backward compatible).

**Test plan:** `tests/test_hermes_thin_skills.py` + new `tests/test_hermes_invoke_envelope.py` (schema validation only, no live Hermes).

---

### DX Review — Scorecard (8 dimensions, /10)

| Dimension | Score | Gap |
|-----------|-------|-----|
| Getting started | 6 | No single `hermes-harness --status` JSON entrypoint yet |
| API/CLI naming | 7 | `harness` vs `agent_id` overlap confuses dispatchers |
| Error messages | 8 | `blocked` + `follow_up_actions` is good |
| Docs findability | 7 | Must link `universal-skill-protocol.md` explicitly |
| Upgrade path | 6 | Envelope versioning not specified |
| Dev environment | 7 | Bootstrap gate documented |
| Escape hatches | 8 | Thin-wrapper policy clear |
| Consistency with OpenClaw | 5 | Divergent field names until harmonized |

**TTHW target:** operator runs bootstrap + one envelope dispatch in < 5 min after `git pull`.

---

### User Challenges (both models recommend change)

**Challenge 1: §8.8 feature-branch-only**
- You said: recent work landed directly on `main` with logical batches.
- Models recommend: keep authority spec on feature branch; merge after Mac E2E.
- If we're wrong: blocks velocity on Windows-validated fixes.
- **Default:** your direct-to-main workflow stands unless you explicitly revert.

**Challenge 2: §3.1 `repo_root` absolute required**
- You said: no hardcoded paths in repo (§8.7).
- Models recommend: `orama_system_root` env placeholder in docs; absolute only at runtime inside runners.
- **Default:** env-placeholder in spec text.

---

### Taste Decisions (your call)

1. **Result shape:** OpenClaw-minimal (`status`, `files_modified`, `follow_up_actions`) vs Hermes-extended (`output`, `warnings`, `errors`) — **recommend superset** (P1 completeness).
2. **`pt-orama-lesson-mining`:** create new `commands/pt-orama-lesson-mining` wrapping PT `learn.py` vs drop from registry until PT command exists — **recommend create stub command** pointing to PT `.agent/tools/learn.py`.
3. **OpenClaw skills in Hermes registry:** include `openclaw-status`/`restart` on Windows Hermes vs "Mac fabric only" — **recommend keep as thin wrappers** but document Mac-only execution with `blocked` envelope on Win.

---

### Decision Audit Trail

| # | Phase | Decision | Class | Principle | Rationale |
|---|-------|----------|-------|-----------|-----------|
| 1 | CEO | SELECTIVE EXPANSION | mechanical | P2 | Protocol first, no dispatcher code in v1 |
| 2 | CEO | Defer lesson-mining until canonical path exists | mechanical | P5 | Slug missing today |
| 3 | Eng | Fix all §5 paths to `hermes-harness/commands/*` | mechanical | P5 | Wrong paths break install script |
| 4 | Eng | Envelope uses env placeholders in docs | taste→challenge | P5 | Aligns with LINT-006 |
| 5 | Eng | Result shape = OpenClaw fields + optional Hermes extensions | taste | P1 | Backward compatible completeness |
| 6 | DX | Add `verify_health.json` schema beside bootstrap gate | mechanical | P1 | Replaces ad-hoc PowerShell checks |
| 7 | CEO | Drop or soften §8.8 feature-branch mandate | user challenge | P6 | User workflow is direct-to-main |

---

### Implementation Tasks (aggregated)

- [ ] **P1 (human: 30m / CC: 10m) — hermes-harness** — Add § Universal Invocation Protocol mirroring openclaw-skills with harmonized fields
- [ ] **P1 — hermes-harness** — Add `layer`, `upstream`, `agent_compatibility` frontmatter
- [ ] **P1 — hermes-harness** — Add Subskill Registry table (corrected paths; 6 commands + redirects)
- [ ] **P1 — hermes-harness** — Add bootstrap gate + JSON health envelope; link `verify_partner_canaries.py`
- [ ] **P1 — hermes-harness** — Expand Boundaries to match openclaw Operational Rules rigor
- [ ] **P2 — hermes-harness/commands** — Create `pt-orama-lesson-mining` OR remove from registry
- [ ] **P2 — install_hermes_thin_skills.py** — Add lesson-mining wrapper if command created
- [ ] **P2 — tests** — `test_hermes_invoke_envelope.py` JSON schema tests
- [ ] **P3 — references** — New `hermes-universal-invocation-protocol.md` (≤150 lines) distilled from this plan
- [ ] **P3 — docs** — Fix §6: `start.ps1`/`start.ps1` live under `platform/windows/`, invoked by hermes-harness

---

### Cross-Phase Themes

**Path accuracy** — CEO scope + Eng registry both flag wrong canonical paths; fix before any wrapper regeneration.

**Envelope vs policy tension** — absolute `repo_root` fights anti-doxxing; resolve once in §3.

---

### Approval Gate

**Status:** D2 = B + C + D — overrides applied in §3/§5/§8/§11; ship deferred to post-interrogation turn.

Reply with interrogation answers (§10) or:
- **A)** Approve harmonized plan → implement batch on `main`
- **B)** More overrides
- **C)** Continue interrogation
- **D)** Further plan revision
- **E)** Reject

~~After approval, implement on feature branch `feat/hermes-integration-authority` (unless you override Challenge 1).~~
