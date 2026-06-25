<!-- lint-ignore LINT-012 -->
# Hermes-Harness Canonical Onboarding & Skill Absorption (2026-06-24)

> **Date:** 2026-06-24 · **Owner:** orama-system (canonical skills) · **Consumer:** Hermes local harness (L1)
> **Status:** 📋 PLANNED — 4 Hermes plans steelmanned + 3 architecture decisions (2026-06-24): parametrize IPs, localhost-when-local, preserve-then-migrate Windows
> **Author:** claude-sonnet-4.6 + cyre
> **Review trigger:** before next hermes-harness enrichment session
> **Approval gate:** explicit "approve" from user before any execution

---

## Provenance & honest framing

This plan synthesizes four Hermes-authored planning documents:
1. `2026-06-22_204500-orama-skill-enrichment.md` — skill absorption (merge duplicates)
2. `2026-06-23_hermes-harness-canonical-onboarding.md` — enrich hermes-harness to authority
3. `2026-06-23_hermes-harness-part-02-PLAN.md` — Part 02, with evidence matrix + canaries
4. `2026-06-22_215500-windows-install-startup.md` — Windows/Mac install parity

**Ground-truth correction (verified against the live repo before writing this plan):**

The source plans repeatedly reference five skills as if they live in orama-system:
`hermes-agent`, `pt-orama-harness-integration`, `local-inference`, `perpetua-hardware`,
and a PR #96 on branch `codex/hermes-ecc-harness-skills`. **None of these exist in
orama-system `main` today.** They are Hermes *local-environment* skills (per
`skill-comparison-2026-06-22.md`, which is a Hermes-vs-orama listing). The absorption
targets named in the plans (`perpetua-hardware`, etc.) are also absent.

What orama-system actually has today:
- `bin/orama-system/skills/hermes-harness/SKILL.md` — already exists, already has
  Purpose / Operating Thesis / Platform Harness Model / Windows Bring-Up / Procedure /
  Verification / Boundaries / References sections
- `bin/orama-system/skills/hermes-harness/commands/` — 4 thin wrappers already exist:
  `pt-orama-council`, `pt-orama-review`, `pt-orama-delegate`, `pt-hardware-policy`
- `bin/orama-system/skills/hermes-harness/references/` — 6 reference files including
  `ecc-hermes-cross-harness.md`, `hermes-windows-partner-readiness.md`,
  `hermes-council-review-gates.md`, `workspace-path-resolution.md`
- `bin/orama-system/skills/hermes-harness/scripts/install_hermes_thin_skills.py` — exists
- `bin/orama-system/skills/openclaw-skills/SKILL.md` — the 295-line authority to mirror

**Therefore this plan is reframed from "absorb 5 skills" to "enrich what exists":**
the genuine, executable value in the four Hermes plans is (a) bringing `hermes-harness`
to structural parity with `openclaw-skills`, (b) hardening partner-lane canaries with
exact success text and timeouts, (c) enforcing live LM Studio `/v1/models` resolution,
and (d) distilling the existing `ecc-hermes-cross-harness.md` into focused ≤150-line cards.
The "absorption" of non-existent skills is dropped as a no-op; if those Hermes skills are
ever upstreamed, a separate migration plan will handle them.

---

## Goals (measurable)

1. `hermes-harness/SKILL.md` matches `openclaw-skills/SKILL.md` section-for-section in
   the authority-bearing sections (compatibility matrix, model routing, attribution,
   verification gates, search frugality, Windows coder policy).
2. All four partner lanes (Hermes, AGY, LM Studio, Codex) have a canary with **exact
   expected output, timeout ≤15 s, and a documented degraded fallback**.
3. LM Studio dispatch is gated on a live `GET /v1/models` fetch — no invented model IDs
   in any tracked file; session-scoped cache with canary-triggered invalidation.
4. The 700+ line `ecc-hermes-cross-harness.md` is distilled into ≤4 focused reference
   cards (≤150 lines each), and the original is retained (not deleted) as the source.
5. `install_hermes_thin_skills.py --verify` exits 0 for all wrappers; user-edited
   wrappers (`created_by: user`) are never clobbered.

---

## Non-goals

- Creating `perpetua-hardware`, `hermes-agent`, `local-inference`, or
  `pt-orama-harness-integration` skills (they don't exist here; out of scope).
- Any change to the live Windows machine, `~/.hermes`, or LM Studio config.
- Any executable logic in `references/` files (references are read-only cards).
- Auto-merging Hermes local skills into orama (would require a separate upstream plan).

---

## Phase 1 — Enrich `hermes-harness/SKILL.md` to canonical authority

**Target:** structural parity with `openclaw-skills/SKILL.md`.

Add or expand these sections (keep all existing ones; additive only):

| Section | Mirror source in openclaw-skills | Adaptation for Hermes |
|---|---|---|
| The Three Commands | "The Nine Skills" table | Table: `pt-orama-council` / `pt-orama-review` / `pt-orama-delegate` + canonical paths + one-line purpose |
| Universal Invocation Protocol | OpenClaw envelope | Hermes slash-command envelope: `{"command": "pt-orama-council", "args": {...}}` |
| Default Model Routing | OpenRouter fallback stack | LM Studio localhost-first → Nous provider → OpenRouter free tier |
| Agent Compatibility Matrix | 9-agent matrix | Hermes, Codex, AGY, LM Studio (Gemini row marked retired per 2026-06-18) |
| Attribution & Layering | L3→L2→L1 | orama-system (L3) → Perpetua-Tools (L2) → Hermes local (L1) |
| Verification Gates | — | The 4-lane canary block (see Phase 3) |
| Search Frugality Rule | openclaw-skills rule | Same rule, Hermes-scoped |

**Acceptance:** `diff` section-heading coverage vs `openclaw-skills/SKILL.md` shows no
authority gap; no machine-specific paths; renders as the onboarding reference.

---

## Phase 2 — Distill ECC cross-harness rules into ≤150-line cards

**Source:** existing `references/ecc-hermes-cross-harness.md` (retain it, don't delete).

Create under `hermes-harness/references/`:

| New card | Purpose | Source section |
|---|---|---|
| `ecc-setup-distilled.md` | PT-orama adaptation table, bring-up order, import-vs-skip | §26-53 |
| `ecc-migration-rules.md` | Decision map: source artifact → durable target | §54-74 |
| `cross-harness-protocol.md` | Shared-source-first; harness-specific only for loading/cmd-names/platform | §75-89 |
| `partner-prompt-contract.md` | Bounded worker contract: role/goal/constraints/output shape | §90-111 |

**Constraints:** each ≤150 lines, no duplicate content across cards, canonical command
cards point to these (not to raw ECC docs). LINT-010/011/012 must pass on all new files.

---

## Phase 3 — Harden partner-lane canaries

Single canonical canary table (lives in `hermes-harness/SKILL.md` + referenced by
`hermes-windows-partner-readiness.md`):

| Lane | Command | Expected exact output | Timeout | Degraded path |
|---|---|---|---|---|
| Hermes | `hermes chat --query "Reply with exactly: HERMES_READY" --safe-mode --provider nous --model nvidia/nemotron-3-ultra:free --max-turns 1` | `HERMES_READY` | 15 s | Mark UNAVAILABLE; continue with remaining verified lanes |
| AGY | `agy --print "Reply with exactly: AGY_READY"` | visible `AGY_READY` | 10 s | Mark UNAVAILABLE; Codex reviewer fallback |
| LM Studio | `GET http://127.0.0.1:1234/v1/models` + chat canary | valid JSON + completion <15 s | 15 s | Mark UNAVAILABLE; fall back to Nous provider |
| Codex | `codex --version` | version string | 5 s | Mark UNAVAILABLE; no reviewer fallback |
| Git Bash | `$HERMES_GIT_BASH_PATH --noprofile --norc -lc 'echo hermes-bash-ok'` | `hermes-bash-ok` | 5 s | Mark UNAVAILABLE; block Windows coder lane |

**Rule:** failure, empty stdout, timeout, auth error, or quota exhaustion → UNAVAILABLE.
Remaining verified lanes continue. (This matches the AGY retirement reality from 2026-06-18.)

**Note:** the canary commands use `hermes chat`, never the retired `hermes -z` (LINT-012).

---

## Phase 4 — Live LM Studio `/v1/models` resolution

Enhance `references/hermes-windows-partner-readiness.md`:

```
Before ANY LM Studio dispatch:
1. GET http://localhost:1234/v1/models  (LAN fallback: configured .env value, not hardcoded)
2. Parse data[].id for exact model identifiers
3. Reject invented model names (e.g. "Qwen 3.6 Coder")
4. Select by capability tag (reasoning / coding / fast)
5. Cache for session ONLY; re-validate on canary failure or >15 min elapsed
6. Never trust a cached ID across restarts
```

This aligns with the PT hardware-affinity work already on `main`: the canonical
`hardware_policy.load_policy()` enforces NEVER_MAC; this adds the live-ID-resolution
layer the policy assumes. Cross-link `pt-hardware-policy` command card → this section.

**Resolved (was open question):** the LAN-fallback IP is now governed by the
parametrization contract in Phase 7 below. No tracked literal; the canonical source is
the env-var set documented there. The `/v1/models` fetch uses the host resolved by the
locality rule (Phase 8) — `localhost` when PT runs on the same OS as the LM Studio host,
the parametrized remote IP only for genuine cross-machine calls.

---

## Phase 5 — Windows config as references-only

Create (references-only, no executable logic):

| File | Contents |
|---|---|
| `references/windows-onboarding-config.md` | PowerShell encoding, `HERMES_GIT_BASH_PATH`, `HERMES_HOME`, uv path, Node/npm from LM Studio (`%USERPROFILE%`-relative, never absolute) |
| `references/windows-provider-routing.md` | Nous default `qwen/qwen3-coder:free`, LM Studio `http://127.0.0.1:1234/v1`, OpenRouter free-tier fallback |

**Hard rule:** no executable logic; thin wrappers read these. All paths `%USERPROFILE%`-
relative or env-var form (anti-doxxing / LINT-006).

---

## Phase 6 — Installer verification

`install_hermes_thin_skills.py --install --verify --test`:
- exits 0; all wrappers exist and validate
- `created_by: user` wrappers never clobbered
- wrapper metadata records canonical_source, repo, branch_at_install
- council wrapper references `cross-harness-protocol.md` + `partner-prompt-contract.md`

---

## Phase 7 — Parametrize all LAN IPs to env-interpretable variables

**Decision (user, 2026-06-24):** every machine IP must be an environment variable that
both orama-system and Perpetua-Tools code resolve at runtime. No tracked IP literals in
source, skills, or docs — only fallback defaults inside the var-resolution code.

**Ground truth (verified):** PT `src/perpetua_tools/agent_launcher.py` already implements
this contract: `MAC_IP`, `WIN_IP`, `LM_STUDIO_MAC_ENDPOINT`, `LM_STUDIO_WIN_ENDPOINTS`,
`MAC_LMS_HOST/PORT`, `WINDOWS_IP/PORT` are all `os.getenv(...)` with documented fallbacks.
The gap is **inconsistent application** — `src/perpetua_tools/alphaclaw_bootstrap.py`
defines `MAC_IP`/`WIN_IP` as bare LAN defaults without the locality preference, and the
Hermes plans/docs carry raw literals.

**Canonical variable contract** (single source — document in PT `.env.example` + a new
`hermes-harness/references/lan-endpoint-contract.md`):

| Variable | Meaning | Fallback (code-only) |
|---|---|---|
| `MAC_IP` | Mac host LAN IP | `192.168.254.110` |
| `WIN_IP` | Windows host LAN IP | `192.168.254.108` |
| `MAC_LMS_HOST` / `MAC_LMS_PORT` | Mac LM Studio endpoint parts | from `LM_STUDIO_MAC_ENDPOINT` then `MAC_IP`:1234 |
| `WINDOWS_IP` / `WINDOWS_PORT` | Win Ollama/LM Studio endpoint parts | from `LM_STUDIO_WIN_ENDPOINTS` then `WIN_IP`:11434 |
| `LM_STUDIO_MAC_ENDPOINT` | full Mac LM Studio URL | `http://{MAC_IP}:1234` |
| `LM_STUDIO_WIN_ENDPOINTS` | comma-list of Win LM Studio URLs | `http://{WIN_IP}:1234` |
| `OLLAMA_MAC_ENDPOINT` | Mac Ollama URL | `http://{localhost-or-MAC_IP}:11434` |
| `OLLAMA_WINDOWS_ENDPOINT` | Win Ollama URL | `http://{localhost-or-WIN_IP}:11434` |
| `LM_STUDIO_API_TOKEN` | bearer token | `lm-studio` (dev) |

**Tasks:**
1. Bring `alphaclaw_bootstrap.py` to the same locality-aware resolution as
   `agent_launcher.py` (it currently lacks the `RUNNING_ON_*` → localhost preference).
2. Add `hermes-harness/references/lan-endpoint-contract.md` documenting the full var set
   (references-only; no executable logic). orama Windows installer + start scripts read it.
3. Replace every raw IP literal in tracked Hermes plans/docs with the variable name.
4. `start.sh` / `start.ps1` export the resolved values so child processes inherit them.

**Acceptance:** `grep -rn '192\.168\.' src/ scripts/ bin/ docs/` returns only
fallback-default lines inside resolution code (clearly commented), never a hardcoded
endpoint in a skill, plan, or doc. A new hygiene rule (LINT-013, optional) can enforce this.

---

## Phase 8 — Locality rule: prefer localhost when on the same machine

**Decision (user, 2026-06-24):** when code runs **on** a machine, it must reach that
machine's own services via `localhost`, never the LAN IP. The remote/parametrized IP is
used **only** for genuine cross-machine calls (Mac→Windows or Windows→Mac).

**Ground truth (verified):** `agent_launcher.py` already does this:
- Mac Ollama: `"http://localhost:11434" if RUNNING_ON_MAC else f"http://{MAC_IP}:11434"`
  (lines 106-110), with an explicit self-heal that normalizes any non-loopback Mac
  endpoint to localhost when `RUNNING_ON_MAC` (lines 119-126).
- Win endpoint: `"localhost" if RUNNING_ON_WINDOWS else "192.168.254.108"` (lines 225-227).

**The rule, stated canonically:**

```
resolve_endpoint(target_machine, service):
    if running_on(target_machine):        # I am the Mac, asking for Mac's LM Studio
        return f"http://localhost:{port}" # → loopback, always
    else:                                 # I am the Mac, asking for Windows' LM Studio
        return f"http://{env_ip(target_machine)}:{port}"  # → parametrized LAN IP
```

| Caller runs on | Wants service on | Resolves to |
|---|---|---|
| Mac | Mac | `localhost` |
| Mac | Windows | `$WIN_IP` (parametrized) |
| Windows | Windows | `localhost` |
| Windows | Mac | `$MAC_IP` (parametrized) |

**Tasks:**
1. Extract the locality rule into one shared helper (e.g. `resolve_local_or_remote(host_role)`),
   currently duplicated inline for Mac and Win in `agent_launcher.py`. One canonical
   implementation; both Mac and Win paths call it. (Duplicate-parser elimination — see
   PT DECISIONS.md 2026-06-24.)
2. Apply the same helper in `alphaclaw_bootstrap.py` (currently missing the rule entirely).
3. The Hermes `hermes-harness` `/v1/models` resolution (Phase 4) uses this helper:
   on Windows it hits `http://localhost:1234/v1/models`; only a Mac→Windows council call
   uses `$WIN_IP`.
4. Self-heal log on mismatch (already present for Mac; add the symmetric Win self-heal):
   if a non-loopback endpoint is configured for the local machine, normalize to localhost
   and warn — "live/canonical localhost beats stale LAN config."

**Acceptance:** on Windows, `resolve_endpoint("windows", "lmstudio")` → `localhost`; a
Mac-orchestrator council call to the Windows coder uses `$WIN_IP`. Symmetric for Mac.
No code path reaches its own machine via LAN IP.

---

## Phase 9 — Preserve Hermes local Windows references until migration completes

**Decision (user, 2026-06-24):** do **not** delete or break the Hermes local Windows
references yet. Keep them functional until the bulk of their information has been
successfully redirected to the canonical orama-system location and converted to thin
wrappers — the same end-state Mac/Linux already have (thin local wrappers pointing to
canonical `bin/orama-system/skills/...`).

**Why this sequencing matters:** the four Hermes plans assume canonical targets that
don't exist yet (see Provenance). Deleting the Windows-local references before the
canonical content is in place and verified would strand the Windows harness with no
working skills. Mac/Linux already point at canonical; Windows must reach the same state
**by migration, not by deletion**.

**Migration sequence (no deletion until the final step):**
1. Enrich canonical `hermes-harness` (Phases 1-8) — canonical content lands first.
2. Generate Windows thin wrappers from canonical via `install_hermes_thin_skills.py`,
   pointing to `bin/orama-system/skills/hermes-harness/...` (mirrors Mac/Linux wrappers).
3. Run both in parallel: Windows-local references AND new thin wrappers coexist.
   Verify the thin wrappers resolve correctly on the live Windows machine.
4. Only after verification: mark the Windows-local references as superseded
   (redirect header, `created_by: agent` retained for regeneration) — **still not deleted**.
5. Deletion of the now-redundant local copies is a **separate, later, explicit step**
   requiring its own approval — never bundled into this enrichment work.

**Invariant:** at no point does Windows lose working skill access. The transition is
additive (wrappers added alongside) → verified → redirect headers → (much later) cleanup.
`created_by: user` wrappers are never touched at any stage.

**Acceptance:** Windows reaches Mac/Linux parity — thin wrappers pointing to canonical —
with the original local references still present and functional until an explicit,
separately-approved cleanup step.

---



| Phase | Depends on | Verification |
|---|---|---|
| 1 — enrich SKILL.md | — | section-heading diff vs openclaw-skills; hygiene OK |
| 2 — 4 ECC cards | 1 | ≤150 lines each; xref checks; LINT-010/011/012 pass |
| 3 — canary table | 1 | every lane has exact text + timeout + degraded path |
| 7 — parametrize LAN IPs | — | no raw IP literals outside resolution-code fallbacks |
| 8 — locality rule (localhost-when-local) | 7 | own-machine → localhost; cross-machine → `$IP`; shared helper |
| 4 — /v1/models resolution | 2, 8 | canary fetches real IDs via locality-resolved host |
| 5 — Windows references | 2, 7 | references-only; paths sanitized; IPs parametrized |
| 9 — preserve Windows locals → thin wrappers | 1-8 | Windows parity (wrappers) with locals still functional; no deletion |
| 6 — installer verify | 3,4,5,9 | `--verify` exit 0; user wrappers preserved |
| 10 — approval gate | all | explicit "approve" from user before merge |

**Note on ordering:** Phases 7 and 8 (parametrization + locality) have no dependency on
the skill-enrichment phases and can land first as a self-contained PT/orama code change.
Phase 9 (Windows migration) is deliberately last and its *deletion* step is explicitly
deferred to a separate future plan.

---

## Risk register

| Risk | Mitigation |
|---|---|
| Plans reference non-existent skills | This plan drops those as no-ops; only enriches what exists |
| Windows/Mac divergence | Shared contract in references; harness-specific only in wrappers |
| Thin wrappers drift from canonical | `install_hermes_thin_skills.py --verify` in CI/pre-commit |
| LM Studio model IDs invented | Mandatory live `/v1/models` fetch before dispatch |
| AGY quota blocks reviewer | Codex fallback documented (AGY already retired 2026-06-18) |
| Hardcoded LAN IP leaks / drifts | Phase 7: all IPs parametrized to env vars; only code-fallback defaults remain; optional LINT-013 |
| Code reaches own machine via LAN IP (slow/fragile) | Phase 8: locality rule — localhost when on-machine, `$IP` only cross-machine; shared helper + self-heal |
| Windows stranded with no skills if locals deleted early | Phase 9: additive migration — wrappers added alongside locals → verified → redirect → (later, separate) cleanup; never lose working access |
| Locality rule duplicated Mac/Win and drifts | Phase 8 task 1: extract single shared `resolve_local_or_remote()` helper (duplicate-parser elimination) |
| Private state leaks into tracked files | `created_by: agent` guard; `%USERPROFILE%`-relative paths; never copy `~/.hermes` raw |
| Absolute workstation paths in docs | repo_hygiene LINT-006 gate; all paths relative/env-var |

---

## Success metrics

- [ ] `hermes-harness/SKILL.md` section coverage ≥ `openclaw-skills/SKILL.md`
- [ ] 4 ECC reference cards exist, ≤150 lines each, referenced from canonical cards
- [ ] All 5 canary lanes have exact success text, timeout ≤15 s, degraded fallback
- [ ] `/v1/models` resolution mandatory before LM Studio dispatch; zero invented IDs
- [ ] Windows config lives only in `references/`, no executable logic
- [ ] `install_hermes_thin_skills.py --verify` exits 0; user wrappers preserved
- [ ] Main orama agent retains final judgment in all council workflows
- [ ] No commits/deploys/deletes/account-changes by worker agents
- [ ] Zero absolute workstation paths in any tracked file (LINT-006)
- [ ] Phase 7: no raw IP literal in any skill/plan/doc; only env-var-resolution fallbacks
- [ ] Phase 8: on each OS, own-machine services resolve to `localhost`; cross-machine to `$IP`; one shared helper
- [ ] Phase 8: `alphaclaw_bootstrap.py` brought to locality-rule parity with `agent_launcher.py`
- [ ] Phase 9: Windows reaches Mac/Linux parity (thin wrappers → canonical) with local references still functional; no deletion in this plan

---

## Approval gate

Before execution:
1. Confirm the ground-truth reframing above is correct (skills to absorb don't exist here).
2. Confirm the three architectural decisions (2026-06-24): parametrize IPs (Phase 7),
   localhost-when-local locality rule (Phase 8), preserve-then-migrate Windows locals (Phase 9).
3. Review the enriched `hermes-harness/SKILL.md` draft.
4. Review the 4 new ECC reference card drafts + `lan-endpoint-contract.md`.
5. Explicit **"approve"** from user. (Phase 9 deletion step is separately approved, later.)
