# Hermes-Harness Canonical Onboarding & Skill Absorption (2026-06-24)

> **Date:** 2026-06-24 · **Owner:** orama-system (canonical skills) · **Consumer:** Hermes local harness (L1)
> **Status:** 📋 PLANNED — 4 Hermes plans steelmanned + 3 architecture decisions (2026-06-24): parametrize IPs, localhost-when-local, preserve-then-migrate Windows  — refined: missing absorption targets may be created; scripts allowed; phases restructured for dependency order
> **Author:** orama-system canonical skill leads
> **Approval gate:** explicit "approve" from user before any execution

---

## Provenance

This plan synthesizes five verified sources:

1. `skill-comparison-2026-06-22.md` — Hermes-vs-orama absorption map
2. `2026-06-22_204500-orama-skill-enrichment.md` — skill-merge tasks
3. `2026-06-23_hermes-harness-part-02-PLAN.md` — evidence matrix + canaries + `/v1/models` resolution
4. `2026-06-22_215500-windows-install-startup.md` — Windows/Mac install parity
5. `2026-06-24-hermes-windows-hardware-policy-walkthrough.md` — live hardware-affinity architecture and Windows walkthrough plan

All paths are repo-relative to `orama-system` root.

---

## Ground-Truth Reframing

The source plans reference five skills as canonical targets: `hermes-agent`, `pt-orama-harness-integration`, `local-inference`, `perpetua-hardware`, and PR #96. **None of these exist in `orama-system` `main` today.** They are Hermes local-environment skills or aspirational targets.

What `orama-system` actually has:

- `bin/orama-system/skills/hermes-harness/SKILL.md` — exists
- `bin/orama-system/skills/hermes-harness/commands/pt-orama-council/SKILL.md` — exists
- `bin/orama-system/skills/hermes-harness/commands/pt-orama-review/SKILL.md` — exists
- `bin/orama-system/skills/hermes-harness/commands/pt-orama-delegate/SKILL.md` — exists
- `bin/orama-system/skills/hermes-harness/commands/pt-hardware-policy/SKILL.md` — exists
- `bin/orama-system/skills/hermes-harness/references/` — 6 reference files including `ecc-hermes-cross-harness.md`, `hermes-windows-partner-readiness.md`, `hermes-council-review-gates.md`
- `bin/orama-system/skills/hermes-harness/scripts/install_hermes_thin_skills.py` — exists
- `bin/orama-system/skills/openclaw-skills/SKILL.md` — the authority to mirror

**Reframed outcome:** enrich what exists first, then create any missing absorption targets as redirect-only stubs so the canonical tree is complete. The real value is structural parity with `openclaw-skills`, hardened canaries, live `/v1/models` resolution, ECC distillation, Windows parity, hardware-policy wiring, and helper scripts under `scripts/`.

---

## Measurable Goals

| #   | Goal                                                                                                    |
| --- | ------------------------------------------------------------------------------------------------------- |
| 1   | `hermes-harness/SKILL.md` matches `openclaw-skills/SKILL.md` in authority-bearing sections              |
| 2   | All partner lanes have a canary with exact expected output, timeout ≤15 s, and degraded fallback        |
| 3   | LM Studio dispatch is gated on live `/v1/models` fetch; zero invented model IDs in tracked files        |
| 4   | `ecc-hermes-cross-harness.md` is distilled into ≤4 reference cards (≤150 lines each); original retained |
| 5   | `install_hermes_thin_skills.py --verify` exits 0; user wrappers never clobbered                         |
| 6   | Windows reaches Mac/Linux parity via thin wrappers → canonical; no deletion until verified migration    |
| 7   | All LAN IPs are parametrized to env vars; no hardcoded literals in skills/plans/docs                    |
| 8   | Locality rule enforced: own-machine services reach via `localhost`; cross-machine via `$IP`             |
| 9   | Missing absorption-target stubs exist with redirect headers where canonical targets are absent          |
| 10  | Helper scripts under `scripts/` exist where automation is missing; `references/` remains read-only      |

---

## Non-Goals

- Any change to the live Windows machine, `~/.hermes`, or LM Studio config
- Any executable logic in `references/` files
- Auto-merging Hermes local skills into orama without upstream plan
- Deleting Windows-local references before verified thin-wrapper parity
- Changing orama-system attribution/history-rewrite policy

---

## Skill Absorption Decisions (from skill-comparison-2026-06-22)

| Hermes Skill                                             | Category             | orama-system Target    | Decision                                                         |
| -------------------------------------------------------- | -------------------- | ---------------------- | ---------------------------------------------------------------- |
| `pt-orama-harness-integration`                           | autonomous-ai-agents | `hermes-harness`       | **Absorb** — cross-harness thin-adapter logic belongs in harness |
| `hermes-agent`                                           | autonomous-ai-agents | `hermes-harness`       | **Absorb** — self-config/setup is harness territory              |
| `local-inference`                                        | mlops                | `perpetua-hardware`    | **Absorb** — hardware-aware model selection, canary, affinity    |
| `perpetua-hardware`                                      | mlops                | `perpetua-hardware`    | **Create if missing** — hardware policy SSoT target              |
| `pt-orama-council`                                       | autonomous-ai-agents | `hermes-harness`       | Keep separate — user-facing council command                      |
| `plan`, `systematic-debugging`, `requesting-code-review` | software-development | adjacent orama skills  | Keep separate                                                    |
| `claude-code`, `codex`                                   | autonomous-ai-agents | `codex-openclaw-agent` | Keep separate                                                    |

**Outcome:** if `perpetua-hardware`, `hermes-agent`, `local-inference`, or `pt-orama-harness-integration` do not exist under `bin/orama-system/skills/`, create them as **redirect-only stubs** pointing to the canonical target. Never delete history.

---

## Phase 0 — Repo Hygiene + Branch Prep

| Task                  | Command / Action                                                                                                                                    |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| Sync `orama-system`   | `git fetch origin && git checkout main && git reset --hard origin/main && git clean -fd`                                                            |
| Sync `Perpetua-Tools` | `git fetch origin && git checkout main && git reset --hard origin/main && git clean -fd`                                                            |
| Create branch         | `git checkout -b feat/hermes-harness-onboarding`                                                                                                    |
| Verify paths          | Confirm canonical skill roots under `bin/orama-system/skills/`                                                                                      |
| Hygiene check         | `grep -rn 'C:\\\\Users\\\\lab' bin/orama-system/skills/hermes-harness docs/plans/2026-06-24-hermes-harness-canonical-onboarding.md` → must be empty |

---

## Phase 1 — Parametrize LAN IPs + Locality Rule (foundational)

**Decision (user, 2026-06-24):** every machine IP must be an environment variable; no tracked IP literals in skills/plans/docs. When code runs **on** a machine, it must reach that machine's services via `localhost`; parametrized IP is used **only** for cross-machine calls.

**Canonical helper contract:**

```
resolve_endpoint(target_machine, service):
    if running_on(target_machine): return f"http://localhost:{port}"
    else: return f"http://{env_ip(target_machine)}:{port}"
```

| Caller runs on | Wants service on | Resolves to |
| -------------- | ---------------- | ----------- |
| Mac            | Mac              | `localhost` |
| Mac            | Windows          | `$WIN_IP`   |
| Windows        | Windows          | `localhost` |
| Windows        | Mac              | `$MAC_IP`   |

**Env-var contract** (document in `references/lan-endpoint-contract.md`):

| Variable                  | Meaning             | Code-only fallback                   |
| ------------------------- | ------------------- | ------------------------------------ |
| `MAC_IP`                  | Mac host LAN IP     | `192.168.254.110`                    |
| `WIN_IP`                  | Windows host LAN IP | `192.168.254.108`                    |
| `LM_STUDIO_MAC_ENDPOINT`  | Mac LM Studio URL   | `http://{MAC_IP}:1234`               |
| `LM_STUDIO_WIN_ENDPOINTS` | Win LM Studio URLs  | `http://{WIN_IP}:1234`               |
| `OLLAMA_MAC_ENDPOINT`     | Mac Ollama URL      | `http://{localhost-or-MAC_IP}:11434` |
| `OLLAMA_WINDOWS_ENDPOINT` | Win Ollama URL      | `http://{localhost-or-WIN_IP}:11434` |

**Tasks:**

1. Extract `resolve_local_or_remote()` from `Perpetua-Tools/src/perpetua_tools/agent_launcher.py` into shared helper; apply in `alphaclaw_bootstrap.py`
2. Add `bin/orama-system/skills/hermes-harness/references/lan-endpoint-contract.md`
3. Replace every raw IP literal in tracked Hermes plans/docs with variable names
4. Add symmetric Windows self-heal: non-loopback local endpoint → normalize to `localhost` + warn

**Acceptance:** `grep -rn '192\.168\.' src/ scripts/ bin/ docs/` returns only fallback-defaults inside resolution code.

---

## Phase 2 — Create Missing Absorption Targets (if absent)

For each missing skill, create a **redirect-only stub** under `bin/orama-system/skills/<slug>/SKILL.md`:

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

**Creation checklist:**

- [ ] `perpetua-hardware` → `perpetua-hardware` (creates canonical root if missing)
- [ ] `hermes-agent` → `hermes-harness`
- [ ] `local-inference` → `perpetua-hardware`
- [ ] `pt-orama-harness-integration` → `hermes-harness`

**Rule:** redirect stubs are never executable. They contain no procedure, no script, no secret, no machine path.

---

## Phase 3 — Enrich `hermes-harness/SKILL.md` to Canonical Authority

Target: structural parity with `openclaw-skills/SKILL.md`.

Add/expand (additive only):

| Section                       | Adaptation                                                                                      |
| ----------------------------- | ----------------------------------------------------------------------------------------------- |
| The Three Commands            | Table of `pt-orama-council`, `pt-orama-review`, `pt-orama-delegate` + canonical paths + purpose |
| Universal Invocation Protocol | Hermes slash-command envelope                                                                   |
| Default Model Routing         | LM Studio localhost-first → Nous provider → OpenRouter fallback                                 |
| Agent Compatibility Matrix    | Hermes, Codex, AGY, LM Studio (Gemini retired 2026-06-18)                                       |
| Attribution & Layering        | orama-system (L3) → Perpetua-Tools (L2) → Hermes local (L1)                                     |
| Verification Gates            | 5-lane canary block (see Phase 6)                                                               |
| Search Frugality Rule         | Same as openclaw-skills, Hermes-scoped                                                          |
| Hardware Policy Gate          | Mandatory PT hardware-affinity check before model dispatch                                      |

**Acceptance:** section-heading diff vs `openclaw-skills/SKILL.md` shows no authority gap; no machine-specific paths; renders as onboarding reference.

---

## Phase 4 — Distill ECC Cross-Harness Rules into Reference Cards

Source: existing `references/ecc-hermes-cross-harness.md` (retain, don't delete).

Create under `bin/orama-system/skills/hermes-harness/references/`:

| Card                         | Purpose                                                                   | Source section |
| ---------------------------- | ------------------------------------------------------------------------- | -------------- |
| `ecc-setup-distilled.md`     | PT-orama adaptation table, bring-up order, import-vs-skip                 | §26-53         |
| `ecc-migration-rules.md`     | Decision map: source artifact → durable target                            | §54-74         |
| `cross-harness-protocol.md`  | Shared-source-first; harness-specific only for loading/cmd-names/platform | §75-89         |
| `partner-prompt-contract.md` | Bounded worker contract: role/goal/constraints/output shape               | §90-111        |

Constraints: each ≤150 lines, no duplicate content, canonical command cards point to these (not raw ECC docs).

---

## Phase 5 — Hardware-Affinity Integration

From `2026-06-24-hermes-windows-hardware-policy-walkthrough.md`:

- Canonical policy: `Perpetua-Tools/config/model_hardware_policy.yml`
- Canonical API: `Perpetua-Tools/src/utils/hardware_policy.py`
- Hermes must call PT hardware-affinity gate before model dispatch
- `pt-hardware-policy` command card wires Hermes to the same enforcement path as OpenClaw
- `start.sh --hardware-policy` and `platform/windows/start.ps1 --hardware-policy` both call the same CLI

Acceptance: Hermes Windows dispatch respects `NEVER_MAC`, `NEVER_WIN`, and alias normalization; no duplicate parser logic.

---

## Phase 6 — Harden Partner-Lane Canaries

Single canonical table (lives in `hermes-harness/SKILL.md` + referenced by `hermes-windows-partner-readiness.md`):

| Lane      | Command                                                                                                                                 | Expected Exact Output         | Timeout | Degraded Path                                  |
| --------- | --------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------- | ------- | ---------------------------------------------- |
| Hermes    | `hermes chat --query "Reply with exactly: HERMES_READY" --safe-mode --provider nous --model nvidia/nemotron-3-ultra:free --max-turns 1` | `HERMES_READY`                | 15 s    | Mark UNAVAILABLE; continue with verified lanes |
| AGY       | `agy --print "Reply with exactly: AGY_READY"`                                                                                           | visible `AGY_READY`           | 10 s    | Mark UNAVAILABLE; Codex reviewer fallback      |
| LM Studio | `GET http://localhost:1234/v1/models` + chat canary                                                                                     | valid JSON + completion <15 s | 15 s    | Mark UNAVAILABLE; fall back to Nous provider   |
| Codex     | `codex --version`                                                                                                                       | version string                | 5 s     | Mark UNAVAILABLE; no reviewer fallback         |
| Git Bash  | `$HERMES_GIT_BASH_PATH --noprofile --norc -lc 'echo hermes-bash-ok'`                                                                    | `hermes-bash-ok`              | 5 s     | Mark UNAVAILABLE; block Windows coder lane     |

Rule: failure, empty stdout, timeout, auth error, or quota exhaustion → UNAVAILABLE. Remaining verified lanes continue.

---

## Phase 7 — Live LM Studio `/v1/models` Resolution

Enhance `references/hermes-windows-partner-readiness.md`:

1. `GET http://localhost:1234/v1/models` (LAN fallback via env var, never hardcoded)
2. Parse `data[].id` for exact model identifiers
3. Reject invented model names
4. Select by capability tag (reasoning / coding / fast)
5. Cache for session ONLY; re-validate on canary failure or >15 min elapsed
6. Never trust cached ID across restarts

This uses the locality-resolved host from Phase 1. Cross-link `pt-hardware-policy` command card → this section.

---

## Phase 8 — Windows Config as References-Only

Create (references-only, no executable logic):

| File                                      | Contents                                                                                                                |
| ----------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `references/windows-onboarding-config.md` | PowerShell encoding, `HERMES_GIT_BASH_PATH`, `HERMES_HOME`, uv path, Node/npm from LM Studio (`%USERPROFILE%`-relative) |
| `references/windows-provider-routing.md`  | Nous default `qwen/qwen3-coder:free`, LM Studio `http://127.0.0.1:1234/v1`, OpenRouter free-tier fallback               |

Hard rule: no executable logic; thin wrappers read these.

---

## Phase 9 — Windows Additive Migration (Preserve-Then-Migrate)

**Decision:** do not delete Windows-local references until verified thin-wrapper parity.

Sequence:

1. Enrich canonical `hermes-harness` (Phases 1–8)
2. Generate Windows thin wrappers via `install_hermes_thin_skills.py` pointing to `bin/orama-system/skills/hermes-harness/...`
3. Run Windows-local references **and** new thin wrappers in parallel; verify on live Windows machine
4. Only after verification: mark Windows-local references as superseded (redirect header), still not deleted
5. Deletion of redundant local copies is a separate, later, explicit step requiring its own approval

Invariant: Windows never loses working skill access during transition. `created_by: user` wrappers never touched.

---

## Phase 10 — Helper Scripts (allowance)

Scripts may be added under `bin/orama-system/skills/hermes-harness/scripts/` when automation is missing. Guardrails:

| Rule                                 | Detail                                                            |
| ------------------------------------ | ----------------------------------------------------------------- |
| No executable logic in `references/` | references are read-only markdown cards                           |
| Scripts are additive                 | never modify or delete existing scripts without explicit approval |
| Scripts must be linted               | pass `python -m py_compile` or shellcheck before commit           |
| Scripts must be idempotent           | re-running produces same result; no destructive side effects      |
| Scripts must not touch `~/.hermes`   | they operate on canonical repo files only                         |

Candidate scripts (create only if absent):

- `scripts/repo_hygiene.py` — scan for absolute paths, raw IPs, secrets in tracked docs
- `scripts/sync_hermes_thin_wrappers.py` — refresh local Hermes wrappers from canonical source
- `scripts/verify_partner_canaries.py` — run canary table and report PASS/FAIL/UNAVAILABLE

---

## Executable Roll-up

| Phase | Tasks                                           | Depends On     | Verification                                         |
| ----- | ----------------------------------------------- | -------------- | ---------------------------------------------------- |
| 0     | Repo sync + branch prep                         | —              | clean tree on `feat/hermes-harness-onboarding`       |
| 1     | Parametrize LAN IPs + locality helper           | —              | no raw IP literals outside resolution-code fallbacks |
| 2     | Create missing absorption-target redirect stubs | 0              | redirect-only; no executable logic                   |
| 3     | Enrich `hermes-harness/SKILL.md`                | 0, 2           | section-heading diff vs `openclaw-skills/SKILL.md`   |
| 4     | Distill 4 ECC reference cards                   | 3              | ≤150 lines each; xref checks pass                    |
| 5     | Hardware-affinity wiring                        | 1              | Hermes calls PT policy before dispatch               |
| 6     | Partner-lane canary table                       | 3              | exact text + timeout + degraded path for every lane  |
| 7     | `/v1/models` resolution                         | 4, 1           | canary fetches real IDs via locality-resolved host   |
| 8     | Windows references-only cards                   | 4, 1           | no executable logic; paths sanitized                 |
| 9     | Windows additive migration                      | 3, 5, 8        | thin wrappers verified; locals still functional      |
| 10    | Helper scripts (if needed)                      | 0              | lint/typecheck pass; idempotent                      |
| 11    | Installer verification                          | 6, 7, 8, 9, 10 | `install_hermes_thin_skills.py --verify` exit 0      |

---

## Risk Register

| Risk                                | Mitigation                                                                    |
| ----------------------------------- | ----------------------------------------------------------------------------- |
| Plans reference non-existent skills | Create redirect stubs; no-op absorption dropped                               |
| Windows/Mac divergence              | Shared contract in references; harness-specific only in wrappers              |
| Thin wrappers drift from canonical  | `install_hermes_thin_skills.py --verify` in CI/pre-commit                     |
| LM Studio model IDs invented        | Mandatory live `/v1/models` fetch before dispatch                             |
| AGY quota blocks reviewer lane      | Codex fallback documented (AGY retired 2026-06-18)                            |
| Hardcoded LAN IP leaks              | Phase 1: all IPs parametrized; only code-fallback defaults remain             |
| Own-machine reachable via LAN IP    | Phase 1: locality rule + shared helper + self-heal                            |
| Windows stranded with no skills     | Phase 9: additive migration; locals preserved until separate cleanup approval |
| Locality helper drift               | Single `resolve_local_or_remote()`; duplicate-parser elimination              |
| Private state leaks                 | `created_by: agent` guard; never copy `~/.hermes` raw                         |
| Absolute paths in tracked files     | Repo-relative or env-var forms only                                           |
| Scripts overreach                   | Scripts guardrails: references-only markdown; no live-env mutation            |

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

---

## Approval Gate

Before execution:

1. Confirm missing absorption targets may be created as redirect stubs where absent.
2. Confirm helper scripts may be added under `scripts/` with the guardrails above.
3. Confirm two architectural decisions: parametrize IPs + localhost-when-local + preserve-then-migrate Windows.
4. Confirm ECC2 references are preferred over ECC 1.x for Hermes integration.
5. Review enriched `hermes-harness/SKILL.md` draft.
6. Review 4 new ECC reference card drafts + `lan-endpoint-contract.md`.
7. Review hardware-affinity wiring plan (`pt-hardware-policy`).
8. Explicit **"approve"** from user.
