<!-- lint-ignore LINT-013 -->
# Hermes-Harness Canonical Onboarding & Skill Absorption (2026-06-24)

> **Date:** 2026-06-24 (enriched 2026-06-25) · **Owner:** orama-system (L3 canonical skills) · **Consumer:** Hermes local harness (L1)
> **Status:** 🔄 IN PROGRESS — Phases 1–5+7+8 ✅ shipped; **Phase 6+9 ✅ Win testdrive 2026-06-28** (`verify_partner_canaries` + thin wrappers); PR #108 ✅ merged; LINT-013 ✅
> **Author:** orama-system canonical skill leads + session synthesis
> **Review trigger:** user review of this artifact before any skill/code execution

> **Cross-repo path contract (read before any path below):** the L2 middleware repo's canonical name is **Perpetua-Tools**, but its on-disk clone name varies by host. **Always reference it through `$PERPETUA_TOOLS_PATH`** — never a literal sibling name. This repo (L3) is `$ORAMA_SYSTEM_PATH`. The ECC vendor mirror is `$PERPETUA_TOOLS_PATH/vendor/ecc-tools`. Literal `Perpetua-Tools/…` / `Perplexity-Tools/…` paths are treated as defects.
>
> **v2 orbit:** agate repo migration plan → [`docs/v2/42-agate-hardware-policy-orbit.md`](../v2/42-agate-hardware-policy-orbit.md)

---

## Executive Summary

This is the single canonical onboarding plan for the Hermes harness inside PT-orama. It unifies five authored plans, cross-repo memory invariants, ECC cross-harness architecture, ECC2 migration guidance, Windows install/startup parity, and the hardware-affinity enforcement stack into one repo-relative, GitHub-safe narrative.

**Outcome:** enrich what exists under `bin/orama-system/skills/hermes-harness/` first; create redirect-only absorption stubs where targets are missing; reach structural parity with `openclaw-skills`; wire Hermes to the same PT hardware-policy path as OpenClaw; preserve Windows-local references until thin-wrapper parity is verified.

**This session (2026-06-25):** plan synthesis + Phase 0 only — branch created, sibling repos verified, plan rewritten. No skill edits, no script changes, no live Windows mutations.

---

## Provenance

This plan synthesizes verified sources (all paths repo-relative to `orama-system` root unless noted):

| # | Source | Contribution |
|---|--------|--------------|
| 1 | `skill-comparison-2026-06-22.md` (workspace root) | Hermes-vs-orama absorption map |
| 2 | `2026-06-22_204500-orama-skill-enrichment.md` (workspace root) | Skill-merge tasks, redirect stub pattern |
| 3 | `2026-06-23_hermes-harness-part-02-PLAN.md` (workspace root) | Evidence matrix, canaries, `/v1/models` resolution, thin wrappers |
| 4 | `2026-06-22_215500-windows-install-startup.md` (workspace root) | Windows/Mac install parity, shared platform contract |
| 5 | `docs/plans/2026-06-24-hermes-windows-hardware-policy-walkthrough.md` | Hardware-affinity architecture, live Windows walkthrough checklist |
| 6 | `Cross-Repo-Memory-Seed.md` (workspace root) | Background invariants — hardware, git, path hygiene, agent behavior |
| 7 | `docs/plans/2026-06-24-optimization-priorities.md` | Strategic backlog context (L1–L5); not blocking Hermes onboarding |
| 8 | ECC public docs (cited by URL) | Cross-harness portability, Hermes boundary, ECC2 migration bring-up |

**ECC canonical URLs** (retained per project convention; local vendor mirror lives at `$PERPETUA_TOOLS_PATH/vendor/ecc-tools`):

- [Cross-harness architecture](https://github.com/affaan-m/ECC/blob/main/docs/architecture/cross-harness.md)
- [Hermes x ECC setup](https://github.com/affaan-m/ECC/blob/main/docs/HERMES-SETUP.md)
- [Hermes/OpenClaw migration](https://github.com/affaan-m/ECC/blob/main/docs/HERMES-OPENCLAW-MIGRATION.md)

**PT-orama adaptation reference:** `bin/orama-system/skills/hermes-harness/references/ecc-hermes-cross-harness.md`

---

## Background & Invariants

Extracted from `Cross-Repo-Memory-Seed.md` and ECC architecture. These constraints govern every phase below.

### Hardware & Models

- **One policy file, all harnesses:** `$PERPETUA_TOOLS_PATH/config/model_hardware_policy.yml` is SSoT; canonical API is `$PERPETUA_TOOLS_PATH/src/utils/hardware_policy.py`; CLI validation is `$PERPETUA_TOOLS_PATH/scripts/hardware_policy_cli.py` — never duplicate parsers.
- **Platform role reversal on Windows:** Hermes is the parallel local orchestrator; LM Studio Win lives at `localhost:1234`. Mac OpenClaw reaches Win over LAN; Win must not infer affinity from `/v1/models` list alone (LM Studio LAN proxy lists cross-platform models).
- **Provider name, not model list:** enforcement uses `lmstudio-mac` vs `lmstudio-win`, not endpoint model membership.
- **Model IDs from live probes:** resolve via `/v1/models` or `/api/tags` at runtime; zero invented IDs in tracked files.
- **Reasoning models:** `max_tokens >= 4096`, `commandTimeout >= 300s`; Windows may return `reasoning_content` when `text` is empty.
- **Known invalid IDs:** do not re-add unverified names (e.g. `qwen3-coder-14b`, `gemma4:e4b`).

### Path, Encoding & Locality

- **Repo-relative or env-var paths only** in tracked files — no workstation absolute paths.
- **Cross-repo paths via env var only:** sibling repos are reached through `$PERPETUA_TOOLS_PATH` / `$ORAMA_SYSTEM_PATH`, never a literal sibling directory name (the on-disk clone name varies by host — see the cross-repo path contract at the top of this plan).
- **Locality rule:** when code runs on a machine, reach that machine's services via `localhost`; parametrized IP (`$MAC_IP`, `$WIN_IP`) is for cross-machine calls only.
- **UTF-8 everywhere on Windows:** `encoding="utf-8"` on all `open()`; set `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8` in PowerShell sessions.
- **`openclaw.json`:** never overwrite — always read → deep-merge → write; use `${HOME}` not absolute home paths.

### Git & Governance

- Never force-push shared branches without explicit human instruction.
- After suspected rewrites: `scripts/git/reanchor_scan.sh`, then `git cherry -v`.
- `node_modules/`, `__pycache__/`, `.venv/`, `dist/`, `build/` are never tracked.
- **Thin wrapper rule:** canonical skill bodies live in-repo; Hermes local skills, `~/.codex/skills`, and `.claude/skills` are adapters only.
- **Attribution guards** are canonical in orama-system; sync outward — never hand-edit downstream copies.
- **Agent behavior:** read area `AGENTS.md` first; never override explicit user instructions with a guess; workers review/propose but never commit/deploy/delete without explicit instruction.

### ECC Cross-Harness Rule

Put durable behavior in shared source first (`skills/`, `rules/`, hooks, MCP configs). Harness-specific files adapt loading, command names, event shapes, and platform limits only. If a workflow requires editing three harness copies, the shared source is in the wrong place.

**Hermes boundary:** Hermes is an operator shell consuming ECC/PT-orama assets — not the public ECC runtime. Ship sanitized docs and reusable patterns; never ship OAuth tokens, raw `~/.hermes` exports, or private workspace memory.

---

## ECC2 Migration Layer (Future Session Control Plane)

ECC2 is the alpha Rust control plane (`ecc2/` in the ECC vendor tree) for multi-session orchestration, worktree-aware scaffolding, and observability. It sits **above** individual harness installs and does **not** replace the Hermes thin-wrapper + PT hardware-policy path defined in this plan.

**Bring-up order** (from [HERMES-SETUP.md](https://github.com/affaan-m/ECC/blob/main/docs/HERMES-SETUP.md)):

1. `ecc migrate audit --source ~/.hermes` — inventory legacy workspace before importing
2. Plan/scaffold before copy:
   - `ecc migrate plan` / `ecc migrate scaffold`
   - `ecc migrate import-skills --output-dir migration-artifacts/skills`
   - `ecc migrate import-tools --output-dir migration-artifacts/tools`
   - `ecc migrate import-plugins --output-dir migration-artifacts/plugins`
   - `ecc migrate import-schedules --dry-run`
   - `ecc migrate import-remote --dry-run`
   - `ecc migrate import-env --dry-run`
   - `ecc migrate import-memory` (sanitized workspace memory only)
3. Verify ECC baseline: `node tests/run-all.js` → zero failures
4. Install Hermes; point at ECC-imported / PT-orama canonical skills
5. Register daily MCP servers; authenticate providers locally
6. Start small cron surface before heavy personal workflows

**PT-orama stance:** Hermes onboarding Phases 1–11 deliver canonical skills, hardware gates, and thin wrappers first. ECC2 migration is a **parallel track** documented here for operator continuity — execute only after this plan's skill/harness gates pass and user approves ECC2-specific work.

**Local alpha validation** (when ECC2 work is approved):

```bash
cd ecc2
cargo test
cargo run -- dashboard
```

---

## Ground-Truth Reframing

Source plans reference five skills as canonical targets: `hermes-agent`, `pt-orama-harness-integration`, `local-inference`, `perpetua-hardware`, and PR #96 context. **On `main` today, absorption targets may be absent** — they may exist only as Hermes-local skills or aspirational names.

### What exists in orama-system today

| Asset | Path | Status |
|-------|------|--------|
| Canonical harness skill | `bin/orama-system/skills/hermes-harness/SKILL.md` | exists |
| Council command | `bin/orama-system/skills/hermes-harness/commands/pt-orama-council/SKILL.md` | exists |
| Review command | `bin/orama-system/skills/hermes-harness/commands/pt-orama-review/SKILL.md` | exists |
| Delegate command | `bin/orama-system/skills/hermes-harness/commands/pt-orama-delegate/SKILL.md` | exists |
| Hardware policy command | `bin/orama-system/skills/hermes-harness/commands/pt-hardware-policy/SKILL.md` | exists |
| Reference cards | `bin/orama-system/skills/hermes-harness/references/` (6 files) | exists |
| Thin skill installer | `bin/orama-system/skills/hermes-harness/scripts/install_hermes_thin_skills.py` | exists |
| OpenClaw authority to mirror | `bin/orama-system/skills/openclaw-skills/SKILL.md` | exists |
| Hardware affinity pointer | `bin/orama-system/skills/hardware-affinity-gate/SKILL.md` | exists (pointer to PT) |

### Reframed outcome

Enrich existing assets first; create **redirect-only stubs** for missing absorption targets; distill `ecc-hermes-cross-harness.md` into ≤4 cards; harden partner canaries; enforce live `/v1/models` resolution; wire Windows to the same PT CLI path as `start.sh --hardware-policy`.

---

## Platform Harness Model

Three hosts, two harness families, **one** policy file (`$PERPETUA_TOOLS_PATH/config/model_hardware_policy.yml`):

> **Single source of truth for this model:** the host/harness table, role-reversal diagram, and enforcement stack below are summarized here for context only. The authoritative copy lives in [`docs/hermes-hardware-policy-cross-harness.md`](../hermes-hardware-policy-cross-harness.md). Per the ECC Cross-Harness Rule, do not edit the model in three places — change it there and link.

| Host OS | Primary harness | Startup gate | LM Studio role | Orchestrator role |
|---------|-----------------|--------------|----------------|-------------------|
| **macOS** | OpenClaw (`start.sh`) | `./start.sh --hardware-policy` | Mac MLX home; Win GGUF = **NEVER_MAC** | Mac orchestrator |
| **Linux** | OpenClaw (`start.sh`) | same as macOS | Any documented PT profile (physical HW permitting) | Full hardware matrix peer |
| **Windows 11** | Hermes + `start.ps1` | `.\platform\windows\start.ps1 --hardware-policy` | Win GGUF at **localhost:1234** | Hermes = parallel local orchestrator |

**Role reversal on Windows:**

```text
Mac OpenClaw orchestrator              Windows Hermes orchestrator
─────────────────────────              ───────────────────────────
LM Studio Win over LAN ($WIN_IP:1234)   LM Studio Win at localhost:1234
windows_only = NEVER_MAC               windows_only = ALLOWED (physical home)
Mac MLX = home                         Mac MLX = NEVER_WIN
```

**Enforcement stack:**

```text
config/model_hardware_policy.yml  →  src/utils/hardware_policy.py  →  scripts/hardware_policy_cli.py
                                              ↑                                    ↑
                                    launch_researchers.py              start.sh / start.ps1 / Hermes pt-hardware-policy
```

---

## Skill Absorption Decisions

From `skill-comparison-2026-06-22.md` and skill-enrichment plan:

| Hermes / source skill | Category | orama-system target | Decision |
|-----------------------|----------|---------------------|----------|
| `pt-orama-harness-integration` | autonomous-ai-agents | `hermes-harness` | **Absorb** — cross-harness thin-adapter logic |
| `hermes-agent` | autonomous-ai-agents | `hermes-harness` | **Absorb** — self-config/setup is harness territory |
| `local-inference` | mlops | `perpetua-hardware` | **Absorb** — hardware-aware selection, canary, affinity |
| `perpetua-hardware` | mlops | `perpetua-hardware` | **Create if missing** — hardware policy SSoT skill target |
| `pt-orama-council` | autonomous-ai-agents | `hermes-harness/commands/` | **Keep separate** — user-facing council command |
| `plan`, `systematic-debugging`, `requesting-code-review` | software-development | adjacent orama skills | **Keep separate** |
| `claude-code`, `codex` | autonomous-ai-agents | `codex-openclaw-agent` | **Keep separate** |

**Redirect stub pattern** (when target missing):

```markdown
---
name: <slug>
description: "Redirect stub. Canonical guidance lives in <target>."
version: 1.0.0
redirect_to: bin/orama-system/skills/<target>/SKILL.md
status: absorbed
---

# <Display Name>

This skill has been absorbed into `<target>`.

Use `bin/orama-system/skills/<target>/SKILL.md` for canonical guidance.
```

**Rule:** redirect stubs contain no procedure, no script, no secret, no machine path. Never delete history.

---

## Measurable Goals

| # | Goal |
|---|------|
| 1 | `hermes-harness/SKILL.md` matches `openclaw-skills/SKILL.md` in authority-bearing sections |
| 2 | All partner lanes have a canary with exact expected output, timeout ≤15 s, and degraded fallback |
| 3 | LM Studio dispatch gated on live `/v1/models` fetch; zero invented model IDs in tracked files |
| 4 | `ecc-hermes-cross-harness.md` distilled into ≤4 reference cards (≤150 lines each); original retained |
| 5 | `install_hermes_thin_skills.py --verify` exits 0; user wrappers (`created_by: user`) never clobbered |
| 6 | Windows reaches Mac/Linux parity via thin wrappers → canonical; no deletion until verified migration |
| 7 | All LAN endpoints parametrized to env vars; no hardcoded IP literals in skills/plans/docs |
| 8 | Locality rule enforced: own-machine services via `localhost`; cross-machine via `$MAC_IP` / `$WIN_IP` |
| 9 | Missing absorption-target stubs exist with redirect headers where canonical targets are absent |
| 10 | Helper scripts under `scripts/` only where automation is missing; `references/` remains read-only |

---

## Non-Goals

- Any change to the live Windows machine, `~/.hermes`, or LM Studio config during plan-only sessions
- Any executable logic in `references/` files
- Auto-merging Hermes local skills into orama without upstream plan approval
- Deleting Windows-local references before verified thin-wrapper parity
- Changing orama-system attribution/history-rewrite policy
- Executing ECC2 migration commands against live operator state without separate approval

---

## Phase 0 — Repo Hygiene + Branch Prep ✅ (2026-06-25)

| Task | Action | Status |
|------|--------|--------|
| Sync orama-system | `git fetch origin`; branch `feat/hermes-harness-onboarding` from current tree (local plan edits preserved) | ✅ done |
| Sync Perpetua-Tools | `git fetch origin`; verified `main...origin/main` in `$PERPETUA_TOOLS_PATH` | ✅ done |
| Sync ECC vendor | `$PERPETUA_TOOLS_PATH/vendor/ecc-tools` checked out on `main` @ latest `origin/main` | ✅ done |
| Verify skill roots | Confirm paths under `bin/orama-system/skills/hermes-harness/` | ✅ done |
| Hygiene grep | No workstation absolute paths in plan or hermes-harness tracked paths | ✅ verified |

**Phase 0 verification commands:**

```bash
# orama-system root
git status -sb
git branch --show-current   # expect: feat/hermes-harness-onboarding

# scan for workstation absolute paths (repo hygiene)
python scripts/review/repo_hygiene.py --paths docs/plans bin/orama-system/skills/hermes-harness 2>/dev/null || rg -n '[A-Za-z]:\\\\Users\\\\' docs/plans bin/orama-system/skills/hermes-harness
# expect: empty / pass

grep -rn '192\.168\.' docs/plans/2026-06-24-hermes-harness-canonical-onboarding.md
# expect: empty (env-var names only)
```

**Evidence rule (S2):** a `✅` row is only valid when backed by captured command output (paste into the row or link a log). Apply the plan's own "verify programmatically, never visually" directive to the plan itself — do not mark a row green on intent. The `Sync Perpetua-Tools` row above was reconciled against the real on-disk clone name during the 2026-06-25 review pass.

---

## Phase 1 — Parametrize LAN IPs + Locality Rule

**Decision:** every machine IP is an environment variable; no tracked IP literals in skills/plans/docs. When code runs **on** a machine, reach that machine's services via `localhost`.

**Canonical helper contract:**

```text
resolve_endpoint(target_machine, service):
    if running_on(target_machine): return f"http://localhost:{port}"
    else: return f"http://{env_ip(target_machine)}:{port}"
```

| Caller runs on | Wants service on | Resolves to |
|----------------|------------------|-------------|
| Mac | Mac | `localhost` |
| Mac | Windows | `$WIN_IP` |
| Windows | Windows | `localhost` |
| Windows | Mac | `$MAC_IP` |

**Env-var contract** (document in `references/lan-endpoint-contract.md`):

| Variable | Meaning | Code-only fallback |
|----------|---------|-------------------|
| `MAC_IP` | Mac host LAN IP | documented in resolution code only |
| `WIN_IP` | Windows host LAN IP | documented in resolution code only |
| `LM_STUDIO_MAC_ENDPOINT` | Mac LM Studio URL | `http://{MAC_IP}:1234` |
| `LM_STUDIO_WIN_ENDPOINT` | Win LM Studio URL | `http://{WIN_IP}:1234` (cross-machine); `localhost:1234` when on Win |
| `OLLAMA_MAC_ENDPOINT` | Mac Ollama URL | `http://localhost:11434` or `$MAC_IP:11434` |
| `OLLAMA_WINDOWS_ENDPOINT` | Win Ollama URL | `http://localhost:11434` or `$WIN_IP:11434` |

**Tasks:**

0. **Cross-repo path-resolution contract (do this first — S1).** Add a single helper `resolve_repo_root(PERPETUA_TOOLS | ORAMA_SYSTEM)` (env-var first: `$PERPETUA_TOOLS_PATH` / `$ORAMA_SYSTEM_PATH`, with a documented in-code fallback) and route every cross-repo path through it. No literal sibling directory names anywhere in skills/plans/docs/scripts. This dissolves the Perpetua-Tools↔Perplexity-Tools on-disk mismatch (B1) and extends the locality rule from cross-*machine* to cross-*repo*.
1. Extract the locality primitives into a shared helper and apply in `$PERPETUA_TOOLS_PATH/src/perpetua_tools/alphaclaw_bootstrap.py`. ⚠️ **Corrected 2026-06-25:** `resolve_local_or_remote()` named in earlier drafts **does not exist** in PT. The real reusable primitives are `_loopback_host_from_endpoint()`, `_is_local_endpoint()`, and `_get_local_ips()` (currently module-private in `$PERPETUA_TOOLS_PATH/src/perpetua_tools/agent_launcher.py` — module path verified). Promote those, don't invent a new name.
2. Add `bin/orama-system/skills/hermes-harness/references/lan-endpoint-contract.md`
3. Replace raw IP literals in tracked Hermes plans/docs with variable names — **including the pre-existing literal `192.168.254.103`** in `docs/plans/2026-06-24-optimization-priorities.md` (see Acceptance). (Note: `agent_launcher.py:105` also carries a `192.168.254.110` fallback default — that one is inside resolution code and is the blessed exception, not a violation.)
4. Add symmetric Windows self-heal: non-loopback local endpoint → normalize to `localhost` + warn. ✅ **Confirmed scoped correctly:** the Mac half already exists (`agent_launcher.py:115–123`); only the Windows half is missing.

**Acceptance:** `grep -rn '192\.168\.' src/ scripts/ bin/ docs/` returns only fallback defaults inside resolution code. ✅ **M2 gate cleared (2026-06-25):** `192.168.254.103` in `optimization-priorities.md` (lines 32/39) replaced with `$LM_STUDIO_WIN_ENDPOINT` in this PR. Remaining `192.168.` hits are all inside resolution fallback code — expected exceptions.

**Pre-flight gate (S5) — fail-closed, run before any Phase 1 task lands:** a single probe asserts (a) `$PERPETUA_TOOLS_PATH` resolves to a real dir, (b) `$PERPETUA_TOOLS_PATH/scripts/hardware_policy_cli.py` imports, (c) the target `/v1/models` endpoint is reachable, (d) no `192.168` literal in the touched scope. One gate replaces a dozen scattered assumptions; abort the phase if any assertion fails.

---

## Phase 2 — Create Missing Absorption Targets

Creation checklist (redirect-only if absent):

- [ ] `perpetua-hardware` → canonical root or self-redirect
- [ ] `hermes-agent` → `hermes-harness`
- [ ] `local-inference` → `perpetua-hardware`
- [ ] `pt-orama-harness-integration` → `hermes-harness`

Update `skill-comparison-2026-06-22.md` decision column: MERGE / KEEP-SEPARATE / INVESTIGATE for adjacent pairs (`plan`, `systematic-debugging`, `git-worktree-hygiene`, etc.).

---

## Phase 3 — Enrich `hermes-harness/SKILL.md` to Canonical Authority

Target: structural parity with `openclaw-skills/SKILL.md` (additive only).

| Section | Adaptation |
|---------|------------|
| The Three Commands (+ hardware) | Table of `pt-orama-council`, `pt-orama-review`, `pt-orama-delegate`, `pt-hardware-policy` |
| Universal Invocation Protocol | Hermes slash-command envelope |
| Default Model Routing | LM Studio localhost-first → Nous provider → OpenRouter fallback |
| Agent Compatibility Matrix | Hermes, Codex, AGY, LM Studio (Gemini retired 2026-06-18) |
| Windows Coder Policy | Git Bash requirement; Node/npm from LM Studio; `HERMES_GIT_BASH_PATH` |
| Attribution & Layering | orama-system (L3) → Perpetua-Tools (L2) → Hermes local (L1) |
| Verification Gates | 5-lane canary block (Phase 6) |
| Search Frugality Rule | Same as openclaw-skills, Hermes-scoped |
| Hardware Policy Gate | Mandatory PT hardware-affinity check before model dispatch |

**Acceptance:** section-heading diff vs `openclaw-skills/SKILL.md` shows no authority gap; no machine-specific paths.

---

## Phase 4 — Distill ECC Cross-Harness Rules into Reference Cards

Source: `references/ecc-hermes-cross-harness.md` (retain, do not delete).

Create under `bin/orama-system/skills/hermes-harness/references/`:

| Card | Purpose | Source section |
|------|---------|----------------|
| `ecc-setup-distilled.md` | PT-orama adaptation table, bring-up order, import-vs-skip | §26–53 |
| `ecc-migration-rules.md` | Decision map: source artifact → durable target | §54–74 |
| `cross-harness-protocol.md` | Shared-source-first; harness-specific only for loading/cmd-names/platform | §75–89 |
| `partner-prompt-contract.md` | Bounded worker contract: role/goal/constraints/output shape | §90–111 |

Constraints: each ≤150 lines; canonical command cards point to these, not raw ECC URLs.

---

## Phase 5 — Hardware-Affinity Integration

From `docs/plans/2026-06-24-hermes-windows-hardware-policy-walkthrough.md`:

- Policy SSoT: `$PERPETUA_TOOLS_PATH/config/model_hardware_policy.yml`
- Canonical API: `$PERPETUA_TOOLS_PATH/src/utils/hardware_policy.py`
- CLI: `$PERPETUA_TOOLS_PATH/scripts/hardware_policy_cli.py` (delegates to API — **never duplicate parsers**)
- Hermes must call PT hardware-affinity gate before model dispatch
- `pt-hardware-policy` command card wires Hermes to same path as OpenClaw
- Entries: `./start.sh --hardware-policy` and `.\platform\windows\start.ps1 --hardware-policy`

**Five gaps closed (PT PRs #128–#131):** blind fallback, platform never passed, preferred-model bypass, alias sections ignored, duplicate CLI parser.

**Acceptance:** Hermes Windows dispatch respects `NEVER_MAC`, `NEVER_WIN`, alias normalization; `grep '_simple_policy_parse|def _forbidden' --glob '*.py'` in PT finds no duplicate parsers.

---

## Phase 6 — Harden Partner-Lane Canaries

Canonical table (lives in `hermes-harness/SKILL.md` + `hermes-windows-partner-readiness.md`):

| Lane | Command | Expected Exact Output | Timeout | Degraded Path |
|------|---------|----------------------|---------|---------------|
| Hermes | `hermes chat --query "Reply with exactly: HERMES_READY" --safe-mode --provider nous --model stepfun/step-3.7-flash:free --max-turns 1` | `HERMES_READY` | 15 s | Mark UNAVAILABLE; continue with verified lanes |
| AGY | `agy --print "Reply with exactly: AGY_READY"` | visible `AGY_READY` | 10 s | Mark UNAVAILABLE; Codex reviewer fallback |
| LM Studio | `GET http://localhost:1234/v1/models` + chat canary | valid JSON + completion <15 s | 15 s | Mark UNAVAILABLE; fall back to Nous provider |
| Codex | `codex --version` | version string | 5 s | Mark UNAVAILABLE; no reviewer fallback |
| Git Bash | `$HERMES_GIT_BASH_PATH --noprofile --norc -lc 'echo hermes-bash-ok'` | `hermes-bash-ok` | 5 s | Mark UNAVAILABLE; block Windows coder lane |

**Rule:** failure, empty stdout, timeout, auth error, or quota exhaustion → UNAVAILABLE. Remaining verified lanes continue.

**Note:** reasoning-model LM Studio canaries may need up to **180 s** and `max_tokens >= 4096` for 27B GGUF — document in partner-readiness reference without lowering the 15 s gate for fast-path lanes.

---

## Phase 7 — Live LM Studio `/v1/models` Resolution

Enhance `references/hermes-windows-partner-readiness.md`:

1. `GET http://localhost:1234/v1/models` (cross-machine fallback via `$WIN_IP` / `$MAC_IP`, never hardcoded)
2. Parse `data[].id` for exact model identifiers
3. Reject invented model names
4. Select by capability tag (reasoning / coding / fast)
5. Cache for session ONLY; re-validate on canary failure or >15 min elapsed
6. Never trust cached ID across restarts
7. Cross-check selected ID against PT hardware policy before dispatch

Cross-link `pt-hardware-policy` command card → this section.

---

## Phase 8 — Windows Install, Startup & Config (References-Only)

From `2026-06-22_215500-windows-install-startup.md` — shared platform contract across three OS targets.

### Existing Windows assets

- `platform/windows/install.ps1`
- `platform/windows/start.ps1`
- `platform/windows/requirements-windows.txt`
- `platform/windows/README.md`

### Shared install/startup contract (proposed PT doc)

New: `$PERPETUA_TOOLS_PATH/docs/install-startup-contract.md` covering:

- idempotent install guarantees
- env launch order and fallback chain
- LM Studio localhost-first resolution
- platform-specific orchestrator map (Hermes on Win; OpenClaw on Mac/Linux)
- verification canary commands

### References-only cards (no executable logic)

| File | Contents |
|------|----------|
| `references/windows-onboarding-config.md` | PowerShell encoding, `HERMES_GIT_BASH_PATH`, `HERMES_HOME`, uv path, Node/npm from LM Studio |
| `references/windows-provider-routing.md` | Nous default, LM Studio `http://127.0.0.1:1234/v1`, OpenRouter free-tier fallback |

### Windows dogfood invariant

Windows development should default through the Hermes Agent Harness (eat-our-own-dogfood). Codex → AGY → second Hermes coding agent is the documented fallback chain — no Mac orchestrator for Windows flows.

### Live Windows walkthrough (deferred)

Execute Phases A–F from `docs/plans/2026-06-24-hermes-windows-hardware-policy-walkthrough.md` on a physical Win11 host **after** Phases 1–9 land and user approves live validation.

---

## Phase 9 — Windows Additive Migration (Preserve-Then-Migrate)

**Decision:** do not delete Windows-local references until verified thin-wrapper parity.

Sequence:

1. Enrich canonical `hermes-harness` (Phases 1–8)
2. Generate Windows thin wrappers via `install_hermes_thin_skills.py` pointing to `bin/orama-system/skills/hermes-harness/...`
3. Run Windows-local references **and** new thin wrappers in parallel; verify on live Windows machine
4. Only after verification: mark Windows-local references as superseded (redirect header), still not deleted
5. Deletion of redundant local copies is a separate, later, explicit step requiring its own approval

**Expected wrappers after install:** `/pt-hardware-policy`, `/pt-orama-council`, `/pt-orama-review`, `/pt-orama-delegate`

Invariant: Windows never loses working skill access during transition. `created_by: user` wrappers never touched.

---

## Phase 10 — Helper Scripts (allowance)

Scripts may be added under `bin/orama-system/skills/hermes-harness/scripts/` when automation is missing.

| Rule | Detail |
|------|--------|
| No executable logic in `references/` | references are read-only markdown cards |
| Scripts are additive | never modify/delete existing scripts without explicit approval |
| Scripts must be linted | pass `python -m py_compile` or shellcheck before commit |
| Scripts must be idempotent | re-running produces same result |
| Scripts must not touch `~/.hermes` | operate on canonical repo files only |

Candidate scripts (create only if absent):

- `scripts/repo_hygiene.py` — scan for absolute paths, raw IPs, secrets in tracked docs
- `scripts/sync_hermes_thin_wrappers.py` — refresh local Hermes wrappers from canonical source
- `scripts/verify_partner_canaries.py` — run canary table and report PASS/FAIL/UNAVAILABLE

---

## Phase 11 — Installer Verification

Depends on Phases 6–10.

```bash
# orama-system root
python bin/orama-system/skills/hermes-harness/scripts/install_hermes_thin_skills.py --install
python bin/orama-system/skills/hermes-harness/scripts/install_hermes_thin_skills.py --verify
python bin/orama-system/skills/hermes-harness/scripts/install_hermes_thin_skills.py --test
pytest tests/test_hermes_thin_skills.py -q
```

**Pass criteria:** exit 0; four wrappers validate; user wrappers preserved.

---

## Executable Roll-up

**Reversibility legend (S3):** **A** = additive in orama-system, fully reversible · **B** = touches the L2 PT repo / cross-repo · **C** = mutates a live host (Hermes skill dirs, `openclaw.json`, Windows runtime).

| Phase | Tasks | Depends On | Tier | Verification |
|-------|-------|------------|------|--------------|
| 0 | Repo sync + branch prep | — | A | clean tree on `feat/hermes-harness-onboarding` ✅ |
| 1 | Cross-repo path contract + parametrize LAN IPs + locality helper | — | B | no raw IP literals outside resolution-code fallbacks; `$PERPETUA_TOOLS_PATH` resolves |
| 2 | Create missing absorption-target redirect stubs | 0 | A | redirect-only; no executable logic |
| 3 | Enrich `hermes-harness/SKILL.md` | 0, 2 | A | section-heading diff vs `openclaw-skills/SKILL.md` |
| 4 | Distill 4 ECC reference cards | 3 | A | ≤150 lines each; xref checks pass |
| 5 | Hardware-affinity wiring | 1 | B | Hermes calls PT policy before dispatch |
| 6 | Partner-lane canary table | 3 | A | exact text + timeout + degraded path for every lane |
| 7 | `/v1/models` resolution | 4, 1 | A | canary fetches real IDs via locality-resolved host |
| 8 | Windows references-only cards + install contract | 4, 1 | B | no executable logic; paths sanitized (PT contract doc = B) |
| 9 | Windows additive migration | 3, 5, 8 | C | thin wrappers verified; locals still functional |
| 10 | Helper scripts (if needed) | 0 | A | lint/typecheck pass; idempotent |
| 11 | Installer verification | 6, 7, 8, 9, 10 | C | `install_hermes_thin_skills.py --verify` exit 0; writes user skill dirs |

---

## Risk Register

| Risk | Mitigation |
|------|------------|
| Plans reference non-existent skills | Create redirect stubs; drop no-op absorption |
| Windows/Mac divergence | Shared contract in references; harness-specific only in wrappers |
| Thin wrappers drift from canonical | `install_hermes_thin_skills.py --verify` in CI/pre-commit |
| LM Studio model IDs invented | Mandatory live `/v1/models` fetch + PT policy check before dispatch |
| AGY quota blocks reviewer lane | Codex fallback documented (AGY retired 2026-06-18) |
| Hardcoded LAN IP leaks | Phase 1: all IPs parametrized |
| Own-machine reachable via LAN IP | Phase 1: locality rule + shared helper + self-heal |
| Windows stranded with no skills | Phase 9: additive migration; locals preserved |
| Locality helper drift | Share `_is_local_endpoint()` / `_loopback_host_from_endpoint()` from `agent_launcher.py`; eliminate duplicate parsers |
| Private state leaks | `created_by: agent` guard; never copy `~/.hermes` raw |
| Absolute paths in tracked files | Repo-relative or env-var forms only |
| ECC2 migration conflated with harness onboarding | ECC2 section is parallel track; requires separate approval |
| Nested merge integrity | Verify with `git diff origin/main...origin/<branch>` before merge |

---

## Success Metrics

- [ ] `hermes-harness/SKILL.md` authority coverage ≥ `openclaw-skills/SKILL.md`
- [ ] 4 ECC reference cards exist, are ≤150 lines each, and are referenced from canonical cards
- [ ] All 5 canary lanes have exact success text, timeout ≤15 s, and degraded fallback
- [ ] `/v1/models` resolution mandatory before LM Studio dispatch; zero invented IDs
- [ ] Windows config lives only in `references/`, no executable logic
- [ ] `install_hermes_thin_skills.py --verify` exits 0; user wrappers preserved
- [ ] Main orama agent retains final judgment in all council workflows
- [ ] No commits/deploys/deletes/account-changes by worker agents
- [ ] Zero absolute workstation paths in tracked files
- [ ] No raw IP literals in skills/plans/docs; only env-var resolution code
- [ ] Own-machine services resolve to `localhost`; cross-machine to `$IP`; one shared helper
- [ ] `alphaclaw_bootstrap.py` at locality-rule parity with `agent_launcher.py`
- [ ] Windows reaches Mac/Linux parity via thin wrappers → canonical; locals still functional
- [ ] Missing absorption targets created as redirect stubs where absent
- [ ] Helper scripts added only under `scripts/`; `references/` remains read-only
- [ ] Live Windows walkthrough (hardware policy Phases A–F) recorded when executed

---


---

## Session addendum (2026-06-26)

### What landed (no live Windows needed)

| Phase | Commit | What |
|---|---|---|
| 1 — SKILL.md authority | `a75ad68` | Three Commands, Universal Invocation, Model Routing, Compatibility Matrix, Verification Gates |
| 2 — 4 ECC reference cards | `a75ad68` | `ecc-setup-distilled`, `ecc-migration-rules`, `cross-harness-protocol`, `partner-prompt-contract` |
| 3 — Canary table | `a75ad68` | Inside SKILL.md § Verification Gates |
| 4 — `/v1/models` resolution | `a75ad68` | `hermes-windows-partner-readiness.md` |
| 5 — Windows config cards | `a75ad68` | `windows-onboarding-config.md`, `windows-provider-routing.md` |
| 7+8 — Locality rule | `a75ad68` + `40d3f65` | `lan-endpoint-contract.md`; PT `resolve_local_or_remote()`; `alphaclaw_bootstrap.py` |
| PR #108 merge | `a81a364` | hash/runtime split; 5 new skills; 1135 test lines |
| LINT-013 | `2bad649` | Blocks raw LAN IP literals in skill/plan/doc files |

### Still deferred (need live Windows)
- ~~Phase 6 — `install_hermes_thin_skills.py --install --verify --test`~~ ✅ 2026-06-28 Win
- ~~Phase 9 — Windows thin wrapper migration + verification~~ ✅ 2026-06-28 Win

### Win testdrive evidence (2026-06-28)
- `verify_partner_canaries.py`: LM Studio + Hermes PASS; Codex + cursor-agent PASS; AGY UNAVAILABLE (timeout)
- `ensure-partner-cli-paths.ps1`: User PATH idempotent for partner CLIs
- Canary model: `stepfun/step-3.7-flash:free` (Nous); LM Studio uses `/api/v0/models` `state=loaded` only

### Merlin adaptations accepted (2026-06-26)
- Plans going forward: one-page index + sub-spec links (progressive disclosure for planning docs)
- Schema extraction as next evolution beyond LINT-013:
  `schemas/topology.schema.json` · `schemas/devices.schema.json` · `schemas/skills.schema.json`
- Step 8 dashboard (Vanilla JS / Chart.js) — separate work stream, not yet scheduled

## Approval Gate

**Plan synthesis (2026-06-25):** user confirmed plan-only execution for this session — Phases 1–11 **not** started.

**Tiered approval (S6) — a single "approve" no longer covers everything; the three tiers carry very different blast radius (see Reversibility legend in the Executable Roll-up):**

- **Tier A — additive in orama-system (safe, reversible).** Phases 2, 3, 4, 6, 7, 10. Stubs, SKILL.md enrichment, ECC reference cards, canary table, helper scripts. Approve with **"approve A"**.
- **Tier B — touches the L2 PT repo / cross-repo.** Phases 1, 5, 8 (PT install-contract doc). Requires `$PERPETUA_TOOLS_PATH` resolved and the path-contract pre-flight green. Approve with **"approve B"** (implies A).
- **Tier C — mutates a live host.** Phases 9, 11 (writes Hermes/user skill dirs) and the deferred live-Windows walkthrough (`openclaw.json`, runtime). Approve with **"approve C"** (implies A+B).

Confirm the standing decisions before any tier:

1. Missing absorption targets may be created as redirect stubs where absent.
2. Helper scripts may be added under `scripts/` with the guardrails above.
3. Architectural decisions: cross-repo path contract (`$PERPETUA_TOOLS_PATH`) + parametrize IPs + localhost-when-local + preserve-then-migrate Windows.
4. ECC URLs remain `affaan-m/ECC`; local vendor mirror is `$PERPETUA_TOOLS_PATH/vendor/ecc-tools`.
5. ECC2 migration is a parallel track — not in scope for initial harness phases unless separately approved.
6. Review enriched `hermes-harness/SKILL.md` draft (Phase 3).
7. Review 4 new ECC reference card drafts + `lan-endpoint-contract.md` (Phases 1, 4).
8. Review hardware-affinity wiring plan (`pt-hardware-policy`) (Phase 5).
9. Explicit tiered approval (**"approve A/B/C"**) from user.

---

## Verification Plan (This Session)

### Automated

```bash
# orama-system
git status -sb
git branch --show-current

rg -n '[A-Za-z]:\\\\Users\\\\' docs/plans/2026-06-24-hermes-harness-canonical-onboarding.md bin/orama-system/skills/hermes-harness
grep -rn '192\.168\.' docs/plans/2026-06-24-hermes-harness-canonical-onboarding.md
```

### Manual

- [ ] User reviews this enriched plan artifact on branch `feat/hermes-harness-onboarding`
- [ ] User replies **"approve"** to begin Phases 1–11
- [ ] Live Windows walkthrough scheduled separately per hardware-policy walkthrough plan

---

## Changelog

| Date | Event |
|------|-------|
| 2026-06-24 | Initial plan: 4 Hermes plans steelmanned + 3 architecture decisions |
| 2026-06-25 | Full cohesive rewrite: Cross-Repo-Memory invariants, ECC2 section, hardware walkthrough integration, Phase 0 branch prep on `feat/hermes-harness-onboarding` |
| 2026-06-25 | Code review saved: [`docs/2026-06-25-pr108-hermes-discover-code-review.md`](../2026-06-25-pr108-hermes-discover-code-review.md) (`bb62766` hash/runtime split) |

---

## Related

- [PR #108 code review](../2026-06-25-pr108-hermes-discover-code-review.md)
- [Cross-harness hardware policy architecture](../hermes-hardware-policy-cross-harness.md)
- [Hermes Windows hardware walkthrough](2026-06-24-hermes-windows-hardware-policy-walkthrough.md)
