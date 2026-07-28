# Plan: Hermes Agent Canonical Staging + Profile Thin-Wrapper Install

> **Reality checkpoint — verified 2026-07-27:** The canonical staging files and installer scripts now exist under `$ORAMA_SYSTEM_PATH`, but the current Hermes host has **not** materialized the staged fleet: Hermes **v0.19.0 (2026.7.20)** runs from `$HERMES_HOME`, `default` is the only listed profile, and `$HERMES_HOME/profiles/` is absent. Therefore, distinguish **tracked profile templates** from **installed isolated profiles** and do not state that a profile exists until `install_hermes_profiles.py --verify` and `hermes profile list` both confirm it. Native `hermes backup` / `hermes import` are the baseline full-home recovery path; the Orama export/restore utility complements them. See [official configuration docs](https://hermes-agent.nousresearch.com/docs/user-guide/configuration) and [official CLI docs](https://hermes-agent.nousresearch.com/docs/reference/cli-commands).

**Date:** 2026-07-26  
**Status:** ✅ Win `install.ps1` wired — operator live test on RTX 5080 (fresh) + RTX 3080 (existing)  
**Owner:** orama-system (L3 canonical skills + `bin/agents` staging)  
**Consumers:** Hermes installations (profiles + thin skills), Perpetua-Tools install chain, OpenClaw migration operators  

**Source inputs:**

| Document | Role |
|----------|------|
| [`OpenClaw/references/Hermes-Harness-Guide-for-Orama+Perpetua.md`](../../../OpenClaw/references/Hermes-Harness-Guide-for-Orama+Perpetua.md) | Three-layer brain/harness/memory model; `hermes claw migrate` sequence |
| [`OpenClaw/references/2026-07-26_111557-hermes-openclaw-migration-cross-repo-plan.md`](../../../OpenClaw/references/2026-07-26_111557-hermes-openclaw-migration-cross-repo-plan.md) | Cross-repo phases 0–5, PT memory ledger, harness reference cards |
| [`OpenClaw/references/raft-Hermes-Plan-09c.md`](../../../OpenClaw/references/raft-Hermes-Plan-09c.md) | Stow/skills/delegate_task ideas — **adopt patterns, not paths** |
| [`docs/plans/2026-06-24-hermes-harness-canonical-onboarding.md`](2026-06-24-hermes-harness-canonical-onboarding.md) | Existing absorption + thin-wrapper doctrine (extends, does not replace) |

**Complexity:** **Large** (multi-surface install wiring + profile manifest + doc absorption; core Python installer is **Medium**)

---

## Summary

Move durable Hermes persona/guidance (SOUL, profile stubs, role `agent.md`, orchestration READMEs) into **tracked canonical staging** at `bin/agents/`, then materialize them into live Hermes installations as **profiles + thin command wrappers** during `install.sh` / `install.ps1` — mirroring how `install_hermes_thin_skills.py` already handles harness **commands**, not full brain copies.

OpenClaw fleet content migrates via Hermes’s supported `hermes claw migrate` for portable brain state; orama-system owns **templates, registry, and install automation** — never raw `$HERMES_HOME` secrets or session DBs in git.

**Staged this session (2026-07-26):** `bin/agents/REGISTRY.yml`, pipeline `SOUL.md` distillates, review gate doc — see review gate for live fleet snapshot.

---

## Requirements restatement

1. **Canonical staging (pre-install):** All Hermes-relevant agent guidance that today lives in OpenClaw workspaces or scattered references must have a **single tracked home** under `orama-system/bin/agents/` before PT/orama install runs.
2. **Thin wrappers at install:** Live Hermes installs receive **redirect-only** skills and **profile trees** generated from canonical sources — same pattern as `install_hermes_thin_skills.py`, aligned with Hermes internal profile/portable-brain docs.
3. **Harness stays harness:** Operational LAN/queue/coord scripts remain in `bin/orama-system/skills/hermes-harness/`; persona/profile material does **not** duplicate into harness `references/` prose blobs when `bin/agents/` is the SSoT.
4. **Progressive disclosure:** Long procedures live in `hermes-harness/references/` cards; command `SKILL.md` files stay short and link outward (existing pattern).
5. **Congruent with existing skills:** Extend `install_hermes_thin_skills.py`, `hermes-skill-absorption-map.md`, and `windows-hermes-setup` — do not introduce parallel GNU Stow or a second wrapper installer unless the existing script cannot be extended cleanly.
6. **Cross-repo:** PT `.agent` memory records migration lessons; PT does not become the canonical store for Hermes SOUL/profile templates.

---

## Architecture (three layers — do not conflate)

```text
┌─────────────────────────────────────────────────────────────────┐
│ L3 orama-system (tracked, git-auditable)                        │
│  bin/agents/{role}/SOUL.md, agent.md, README                    │
│  bin/agents/REGISTRY.yml          ← role ↔ Hermes profile slug    │
│  bin/orama-system/skills/hermes-harness/  ← ops + install scripts │
└────────────────────────────┬────────────────────────────────────┘
                             │ install.ps1 / install.sh / installers
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ L1 Hermes portable brain (local only)                           │
│  $HERMES_HOME/SOUL.md, profiles/<slug>/, memories/, skills/      │
│  Thin wrappers → canonical paths under $ORAMA_SYSTEM_PATH         │
└────────────────────────────┬────────────────────────────────────┘
                             │ separate concern
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ L2 Perpetua-Tools .agent/  ← project lessons, not persona SSoT   │
└─────────────────────────────────────────────────────────────────┘
```

**OpenClaw → Hermes:** use `hermes claw migrate` for one-time brain import; then **reconcile** imported profiles against `bin/agents/REGISTRY.yml` so canonical templates remain authoritative for reinstalls.

---

## What already exists (do not reinvent)

| Asset | Location | Gap |
|-------|----------|-----|
| Role SOUL + agent cards | `bin/agents/*/SOUL.md`, `agent.md` | No `REGISTRY.yml`; no Hermes profile install |
| 7-agent Claude/OpenClaw install | `scripts/install-multi-agent.sh` | Copies to `~/.claude/agents`, `~/.openclaw/agents` — **not Hermes profiles** |
| Command thin wrappers | `bin/orama-system/skills/hermes-harness/scripts/install_hermes_thin_skills.py` | Skills only; no profile SOUL staging |
| Absorption map | `references/hermes-skill-absorption-map.md` | Needs profile/agent staging row |
| Onboarding plan | `docs/plans/2026-06-24-hermes-harness-canonical-onboarding.md` | IN PROGRESS — this plan is the **profile/staging** slice |
| Orchestrator code | `bin/agents/orchestrator/*.py`, `dispatcher.py` | Stays in `bin/agents/`; not copied to Hermes |

---

## Adopt vs defer from `raft-Hermes-Plan-09c.md`

| 09c idea | Verdict | Orama adaptation |
|----------|---------|------------------|
| GNU Stow symlink deploy | **Defer** | Use `install_hermes_thin_skills.py` + new `install_hermes_profiles.py` (repo-native, provenance stamp, `--verify`) |
| `perpetua-tools/src/hermes_harness.py` | **Defer Phase 4+** | Overlaps `bin/agents/orchestrator/` + PT `OrchestrationSupervisor`; document boundary first |
| `/hermes-spawn`, `/hermes-orama` slash skills | **Phase 4 optional** | If added, live under `hermes-harness/commands/` with thin wrappers — not `orama-system/skills/` wrong path |
| `delegate_task` / `AIAgent` spawning | **Reference card** | `references/hermes-programmatic-spawn.md` — link Hermes docs; no new PT runtime until profile install is stable |
| Profile-per-role OpenClaw agents | **Adopt** | `REGISTRY.yml` + `hermes profile create` automation |
| `~/.hermes/config.yaml` delegation block | **Adopt as template** | `bin/agents/templates/config-delegation-snippet.yaml` (non-secret defaults) |

---

## Patterns to mirror

| Category | Source | Pattern |
|----------|--------|---------|
| Naming | `bin/orama-system/skills/hermes-harness/scripts/install_hermes_thin_skills.py` | `HermesWrapper` dataclass; `WRAPPERS` list; `created_by: agent` marker; `--install --verify` |
| Errors | same | Fail loud if canonical card missing before writing; `resolve_repo_root()` via `git rev-parse` |
| Logging | `install_hermes_thin_skills.py` | Print factual wired / not wired / already correct per target |
| Data access | `bin/agents/orchestrator/task_schema.py` | Role vocabulary in tracked markdown + YAML registry — Python orchestration stays separate from Hermes profile files |
| Tests | `tests/test_hermes_thin_skills.py` (if present) | Extend with profile installer dry-run / verify tests |

---

## Files to change (implementation phases)

| File | Action | Why |
|------|--------|-----|
| `bin/agents/REGISTRY.yml` | **CREATE** | Maps role folder → Hermes profile slug, description, optional OpenClaw agent id |
| `bin/agents/README.md` | **CREATE/UPDATE** | Staging contract: SOUL vs agent.md vs Hermes profile layout |
| `bin/agents/templates/profile/` | **CREATE** | Optional `USER.md` / `MEMORY.md` stubs, `config-delegation-snippet.yaml` |
| `bin/orama-system/skills/hermes-harness/references/hermes-portable-brain-map.md` | **CREATE** | Distilled from Harness Guide (no workstation paths) |
| `bin/orama-system/skills/hermes-harness/references/openclaw-to-hermes-migration.md` | **CREATE** | `hermes claw migrate` sequence + gap archive ledger |
| `bin/orama-system/skills/hermes-harness/references/hermes-profile-install.md` | **CREATE** | Operator card: registry → profiles → verify |
| `bin/orama-system/skills/hermes-harness/scripts/install_hermes_profiles.py` | **CREATE** | Materialize `bin/agents` into `$HERMES_HOME/profiles/<slug>/` |
| `bin/orama-system/skills/hermes-harness/scripts/install_hermes_thin_skills.py` | **UPDATE** | Call profile installer when `--install`; link registry in verify output |
| `bin/orama-system/skills/hermes-harness/references/hermes-skill-absorption-map.md` | **UPDATE** | Row for `bin/agents` staging + profile installer |
| `bin/orama-system/skills/hermes-harness/commands/windows-hermes-setup/SKILL.md` | **UPDATE** | Link new reference cards + profile install step |
| `bin/orama-system/skills/hermes-harness/SKILL.md` | **UPDATE** | Profile staging section; cross-link `bin/agents` |
| `scripts/install-multi-agent.sh` | **UPDATE** | Point to `install_hermes_profiles.py`; deprecate blind `cp -r bin` to OpenClaw only |
| `platform/windows/install.ps1` | **UPDATE** | After ECC/Hermes probe: `install_hermes_profiles.py --install --verify` |
| `platform/macos/start.sh` (or mac install hook) | **UPDATE** | Same profile install hook when Hermes present |
| `docs/plans/2026-06-24-hermes-harness-canonical-onboarding.md` | **UPDATE** | Link this plan; mark profile-staging milestone |
| `OpenClaw/references/*` (optional) | **UPDATE** | Pointers to orama canonical plan (no duplicate bodies) |

**PT (Phase 6 only):** record lessons via `learn.py` — no new persona files in `.agent/`.

---

## Tasks

### Phase 0 — Inventory & registry (no Hermes mutations)

- **Action:** Audit OpenClaw workspaces + live `$HERMES_HOME/profiles/` for SOUL/AGENTS/IDENTITY content; map each to `bin/agents/<role>/` or new role folder.
- **Mirror:** `hermes-skill-absorption-map.md` table format.
- **Deliverable:** `bin/agents/REGISTRY.yml` draft + gap list (what stays in migration archive only).
- **Validate:**
  ```bash
  cd "$ORAMA_SYSTEM_PATH"
  test -f bin/agents/REGISTRY.yml
  python3 -c "import yaml; yaml.safe_load(open('bin/agents/REGISTRY.yml'))"
  ```

### Phase 1 — Canonical staging hygiene

- **Action:** Ensure every registry role has `SOUL.md` + `agent.md`; align naming with Hermes profile slug; remove duplicate prose between SOUL and agent.md (SOUL = persona; agent.md = stage contract / Claude subagent card).
- **Mirror:** Existing `bin/agents/orchestrator/SOUL.md` tone.
- **Validate:** `scripts/verify-package.sh` agent dirs; manual read of REGISTRY vs filesystem.

### Phase 2 — Reference cards (progressive disclosure)

- **Action:** Add `hermes-portable-brain-map.md`, `openclaw-to-hermes-migration.md`, `hermes-profile-install.md` under `hermes-harness/references/`; env-var paths only (`$ORAMA_SYSTEM_PATH`, `$HERMES_HOME`, `$PERPETUA_TOOLS_PATH`).
- **Mirror:** `references/windows-hermes-setup.md` structure (operator playbook + validation commands).
- **Validate:**
  ```bash
  grep -R "hermes-portable-brain-map\|openclaw-to-hermes-migration\|hermes-profile-install" \
    bin/orama-system/skills/hermes-harness -n
  ```

### Phase 3 — `install_hermes_profiles.py`

- **Action:** New installer parallel to `install_hermes_thin_skills.py`:
  - Read `bin/agents/REGISTRY.yml`
  - For each profile: ensure `$HERMES_HOME/profiles/<slug>/` exists
  - Copy/sync `SOUL.md` from `bin/agents/<role>/SOUL.md` (never overwrite non-empty `MEMORY.md` / `USER.md` without `--force-memory`)
  - Optional: `hermes profile create <slug> --description "..."` if profile missing (shell out, dry-run first)
  - Write thin `skills/` redirects inside profile only if Hermes requires per-profile skill paths
- **Mirror:** `install_hermes_thin_skills.py` (`--install`, `--verify`, `--dry-run`, provenance footer).
- **Validate:**
  ```bash
  python3 bin/orama-system/skills/hermes-harness/scripts/install_hermes_profiles.py --dry-run
  python3 bin/orama-system/skills/hermes-harness/scripts/install_hermes_profiles.py --install --verify
  hermes profile list
  ```

### Phase 4 — Install chain wiring

- **Action:** Hook profile installer into `platform/windows/install.ps1` and macOS install/start path; update `windows-hermes-setup` procedure step 5→6 to include profiles.
- **Mirror:** Existing `install_hermes_thin_skills.py --install --verify` call in windows-hermes-setup.
- **Validate:** Windows Hermes setup skill dry-run on operator machine; `hermes doctor`.

### Phase 5 — OpenClaw migration operator path

- **Action:** Document ordered procedure in `openclaw-to-hermes-migration.md`:
  1. `hermes backup`
  2. `hermes claw migrate --dry-run`
  3. `hermes claw migrate --preset full` (no secrets first)
  4. Run `install_hermes_profiles.py --install --verify` to **reconcile** canonical SOUL over imports
  5. Record gaps from `$HERMES_HOME/migration/openclaw/*/archive/`
  6. `hermes claw cleanup` only after verification gates (from cross-repo plan Phase 5)
- **Validate:** Operator checklist in doc; no secrets in tracked files.

### Phase 6 — PT memory + skill absorption updates

- **Action:** PT `learn.py` entries for: layered brain model, profiles-not-monolith, harness thin wrappers, preview-before-migrate.
- **Update:** `hermes-skill-absorption-map.md`, `hermes-harness/SKILL.md` cross-links.
- **Validate:** `repo_hygiene.py` on changed orama paths; PT lesson grep.

### Phase 7 (optional, later) — Programmatic spawn

- **Action:** Only if needed after Phase 3–5 stable: evaluate `delegate_task` / `AIAgent` bridge in PT orchestrator vs new thin command skills (`hermes-delegate` pattern from 09c).
- **Defer until:** Profile install + `hermes claw migrate` reconciliation proven on Win + Mac.

---

## Validation (full gate)

```bash
cd "$ORAMA_SYSTEM_PATH"

# Structure
test -f bin/agents/REGISTRY.yml
python3 bin/orama-system/skills/hermes-harness/scripts/install_hermes_profiles.py --verify
python3 bin/orama-system/skills/hermes-harness/scripts/install_hermes_thin_skills.py --verify

# Docs linked from command card
grep -q "hermes-profile-install" bin/orama-system/skills/hermes-harness/commands/windows-hermes-setup/SKILL.md

# Hygiene
python3 scripts/review/repo_hygiene.py .

# Hermes operator (when Hermes installed)
hermes doctor
hermes profile list
hermes skills list
```

---

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Overwriting operator-tuned profile memory | Medium | Default: sync SOUL only; `--force-memory` explicit; never track secrets |
| Duplicating 09c `hermes_harness.py` alongside `bin/agents` orchestrator | High if rushed | Defer Phase 7; keep orchestration in orama Python + PT supervisor |
| `install-multi-agent.sh` copies whole `bin/` to OpenClaw | Medium | Narrow copy to `ultrathink-network` agent cards; profiles via new installer only |
| OpenClaw path literals in new docs | Medium | Env-var contract from 2026-06-24 onboarding plan |
| Hermes `profile create` CLI drift across versions | Low | Probe in installer; document minimum Hermes version in reference card |
| Concurrent-agent collision (identity audit lesson) | Medium | Plan on `main` via PR; single writer for REGISTRY.yml |

---

## Acceptance

- [ ] `bin/agents/REGISTRY.yml` exists and matches role folders
- [ ] `install_hermes_profiles.py --install --verify` passes on at least one Hermes host
- [ ] `install.ps1` / mac install invokes profile installer when Hermes detected
- [ ] Three new reference cards exist and are linked from `windows-hermes-setup`
- [ ] `hermes-skill-absorption-map.md` documents profile staging
- [ ] Salvage compare content (`2026-07-24-006` skillify lesson) unchanged — unrelated to this work
- [ ] No secrets, workstation paths, or private literals in tracked files
- [ ] PT migration lessons recorded (Phase 6)

---

## Suggested PR split

1. **PR-A (orama):** Phase 0–2 — registry + reference cards only (docs-safe).
2. **PR-B (orama):** Phase 3 — `install_hermes_profiles.py` + tests.
3. **PR-C (orama):** Phase 4 — install.ps1 / start.sh hooks + skill cross-links.
4. **PR-D (PT):** Phase 6 — memory lessons only.

---

**WAITING FOR REVIEW:** All agents/operators review [`2026-07-26-hermes-openclaw-staging-review-gate.md`](2026-07-26-hermes-openclaw-staging-review-gate.md). Reply `approve staging` to unblock Phase 3+ (`install_hermes_profiles.py`, install hooks).
