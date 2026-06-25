<!-- lint-ignore LINT-012 -->
# Hermes-Harness Canonical Onboarding & Skill Absorption (2026-06-24)

> **Date:** 2026-06-24 · **Owner:** orama-system (canonical skills) · **Consumer:** Hermes local harness (L1)
> **Status:** 📋 PLANNED — steelmanned from 4 Hermes-authored plans + `skill-comparison-2026-06-22.md`
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

**Open question (flag, don't guess):** the Hermes plans hardcode the LAN fallback IP
(`192.168.254.100` in one doc, `.103` in the affinity work). Per the repo's
no-hardcoded-ephemeral-values rule, the LAN fallback must come from `.env` /
`.agent/install.json`, not a tracked literal. **Confirm the canonical fallback source
before execution.**

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

## Execution sequence

| Phase | Depends on | Verification |
|---|---|---|
| 1 — enrich SKILL.md | — | section-heading diff vs openclaw-skills; hygiene OK |
| 2 — 4 ECC cards | 1 | ≤150 lines each; xref checks; LINT-010/011/012 pass |
| 3 — canary table | 1 | every lane has exact text + timeout + degraded path |
| 4 — /v1/models resolution | 2 | canary fetches real IDs; no invented IDs in tracked files |
| 5 — Windows references | 2 | references-only (no executable logic); paths sanitized |
| 6 — installer verify | 3,4,5 | `--verify` exit 0; user wrappers preserved |
| 7 — approval gate | all | explicit "approve" from user before merge |

---

## Risk register

| Risk | Mitigation |
|---|---|
| Plans reference non-existent skills | This plan drops those as no-ops; only enriches what exists |
| Windows/Mac divergence | Shared contract in references; harness-specific only in wrappers |
| Thin wrappers drift from canonical | `install_hermes_thin_skills.py --verify` in CI/pre-commit |
| LM Studio model IDs invented | Mandatory live `/v1/models` fetch before dispatch |
| AGY quota blocks reviewer | Codex fallback documented (AGY already retired 2026-06-18) |
| Hardcoded LAN IP leaks / drifts | LAN fallback from `.env` only — OPEN QUESTION, confirm before exec |
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

---

## Approval gate

Before execution:
1. Confirm the ground-truth reframing above is correct (skills to absorb don't exist here).
2. Resolve the OPEN QUESTION: canonical source for the LM Studio LAN-fallback IP.
3. Review the enriched `hermes-harness/SKILL.md` draft.
4. Review the 4 new ECC reference card drafts.
5. Explicit **"approve"** from user.
