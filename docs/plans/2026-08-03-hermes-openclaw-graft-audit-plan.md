# Implementation Plan: OpenClaw → Hermes Skill Grafting

**Scope:** Farm operational patterns from `openclaw-skills` and enrich
`hermes-harness/commands` so Hermes instances can be controlled end-to-end with
the same rigor OpenClaw agents already have.

**Complexity:** **Large** — cross-tree architecture, existing absorption map,
PT runtime boundary, and thin-wrapper install path.

**Worktree:** `cursor/hermes-openclaw-graft-audit-f559` (from merged `main`)

**Sources:**

- **SOURCE (subset/inspiration):**
  `bin/orama-system/skills/openclaw-skills`
- **TARGET (superset for enrichment):**
  `bin/orama-system/skills/hermes-harness/commands`

---

## Requirements Restatement

You want to:

1. **Isolate comparison work** on a fresh branch + git worktree from **merged
   `main`** (not a feature PR branch).
2. Treat **`openclaw-skills/`** as the **source subset** — proven operational
   patterns for running/configuring OpenClaw agents (The Nine Skills + shared
   protocol/scripts).
3. Treat **`hermes-harness/commands/`** as the **target superset** — where
   durable Hermes operator commands live and should absorb useful OpenClaw
   patterns.
4. Produce a **repeatable farming methodology**: extract
   patterns/algorithms/strategies → map → graft/merge into existing Hermes
   commands and references — **without** duplicating OpenClaw-specific config
   paths where Hermes has its own runtime.

**Success looks like:** a documented gap matrix, a pattern catalog, prioritized
graft targets, and a phased merge plan that reuses existing absorption
infrastructure (`hermes-skill-absorption-map.md`, thin-skill installer,
universal invocation protocol) rather than inventing parallel skill trees.

---

## Current State (from `main` audit)

| Dimension | **SOURCE: `openclaw-skills`** | **TARGET: `hermes-harness/commands`** |
| --------- | ----------------------------- | -------------------------------------- |
| **Count** | 11 `SKILL.md` (9 ops + master + `codex-openclaw-agent`) | ~10 command cards + spawn/orama/delegate core |
| **Model** | Overlay cards extending `cc-openclaw` upstream; JSON envelope | Thin slash-command shells → `scripts/*.sh` / PT `hermes_harness.py` |
| **Strengths** | Lifecycle pipelines (status→change→stow→restart), secret hygiene, agent scaffolding templates, `json-response.sh`, universal protocol | PT-backed pipeline, LAN co-orchestration, partner dispatch, hardware policy gate, thin Hermes install |
| **Scripts** | `json-response.sh`, `openclaw-mcp-stdio-clean.sh`, `codex-openclaw-agent/scripts/*` | `hermes_spawn.sh`, `resolve_perp_harness.sh`, `install_hermes_thin_skills.py`, coord/LAN suite |
| **Existing bridge** | `universal-skill-protocol.md` already lists Hermes discovery path | `hermes-skill-absorption-map.md`, `openclaw-to-hermes-migration.md` |

**Key insight:** OpenClaw skills are **config/lifecycle operators** for a gateway
home; Hermes commands are **runtime orchestration operators** for AIAgent
instances. Grafting is **pattern transfer**, not file copy — e.g. adopt
OpenClaw's `status→verify→act` discipline inside `hermes-spawn` /
`pt-orama-*` gates, not `openclaw-stow` verbatim on Windows Hermes.

---

## Patterns to Mirror (codebase grounding)

| Category | Source | Pattern |
| -------- | ------ | ------- |
| **Naming** | `openclaw-skills/skills/openclaw-status/SKILL.md` | `{domain}-{verb}` skill IDs; overlay `extends:` upstream |
| **Invocation** | `openclaw-skills/references/universal-skill-protocol.md` | `{skill_id, args, agent_id, home}` — Hermes maps legacy `openclaw_home` → `home` when ingesting OpenClaw envelopes |
| **Shell I/O** | `openclaw-skills/scripts/json-response.sh` | `set -euo pipefail`; stdout=JSON only; stderr=logs |
| **Lifecycle** | `openclaw-status` → `openclaw-restart` → `openclaw-stow` | Always audit before mutate; canonical restart sequence |
| **Secrets** | `openclaw-add-secret` | Never in envelope; Keychain + 3-file propagation |
| **Hermes bridge** | `hermes-harness/scripts/resolve_perp_harness.sh` | Fail-closed PT root resolution before spawn |
| **Absorption** | `hermes-harness/references/hermes-skill-absorption-map.md` | Redirect stubs → canonical supersets; archive pointers |
| **Thin install** | `hermes-harness/scripts/install_hermes_thin_skills.py` | ≤60-line Hermes stubs pointing at `commands/*/SKILL.md` |
| **Tests** | `tests/test_hermes_spawn.py` | `pytest.mark.integration`; subprocess lifecycle in temp dirs |

---

## Phase 0 — Isolated Worktree (no code changes yet)

**Goal:** Compare without disturbing PR #268/#270 work.

```bash
cd /agent/repos/orama-system
git fetch origin main
git worktree add .worktrees/orama-hermes-graft-audit \
  -b cursor/hermes-openclaw-graft-audit-f559 origin/main
cd .worktrees/orama-hermes-graft-audit
git submodule update --init \
  bin/orama-system/skills/openclaw-skills/cc-openclaw  # if comparing upstream overlays
```

**Deliverable:** `docs/plans/2026-08-03-hermes-openclaw-graft-audit-plan.md` (this
file) + future `…-graft-audit.md` inventory artifact when Phase 1 completes.

---

## Phase 1 — Inventory & Diff Matrix (read-only)

### 1A. OpenClaw pattern harvest sheet

For each of **The Nine Skills** + `codex-openclaw-agent`, extract:

| Field | What to capture |
| ----- | --------------- |
| **Trigger** | When the skill fires |
| **Preconditions** | status checks, dry-run gates |
| **Algorithm** | ordered steps (numbered) |
| **Artifacts** | files/dirs touched |
| **Output contract** | JSON shape / follow-ups |
| **Harness notes** | `agent_compatibility` list |
| **Hermes analogue?** | existing command, partial, or gap |

### 1B. Hermes command capability sheet

For each `hermes-harness/commands/*`:

| Command | Runtime | PT dependency | OpenClaw overlap | Gap |
| ------- | ------- | ------------- | ---------------- | --- |
| `hermes-spawn` | `hermes_spawn.sh` | `hermes_harness.py` | partial (start/stop/status) | no pre-flight status audit |
| `hermes-orama` | PT pipeline | full 5-stage | none direct | no envelope/result JSON |
| `hermes-delegate` | ThreadPool executor | `spawn_hermes_agent` | parallel fan-out | no bounded result schema |
| `pt-orama-council/review/delegate` | partner scripts | Codex/AGY | council ≈ multi-agent | no OpenClaw-style verify chain |
| `windows-hermes-setup` | PS1 + install | PATH/canaries | ≈ bootstrap | different from `openclaw-new-agent` |
| `lan-peer-self-talk` | probe/assign | discovery JSON | Mac↔Win only | no OpenClaw gateway equivalent |

### 1C. Produce a **Graft Matrix** (single table)

Rows = OpenClaw patterns. Columns = Hermes target (command / script /
reference). Cells = `ADOPT` | `ADAPT` | `SKIP` | `NEW`.

**Example rows:**

| OpenClaw pattern | Hermes target | Action |
| ---------------- | ------------- | ------ |
| `openclaw-status` pre-flight audit | New `hermes-status` command or extend `hermes-spawn status` | **ADAPT** |
| Universal JSON envelope | All `commands/*` + `hermes_spawn.sh` stdout | **ADOPT** |
| `openclaw-restart` 5-step sequence | `coord_pulse.sh` / spawn recovery | **ADAPT** (no launchd on Win) |
| `openclaw-add-secret` 3-file sync | Hermes env + PT `.env.local` policy | **ADAPT** (no Keychain on Win) |
| `openclaw-dream-setup` memory cron | `pt-orama-lesson-mining` + GossipBus | **MERGE** |
| Agent directive templates | `install_hermes_profiles.py` + `bin/agents/*/SOUL.md` | **ALREADY ABSORBED** — verify parity |
| `codex-openclaw-agent` bind scripts | `dispatch_codex_partner.py` pattern | **ADAPT** for Hermes-native bind |

---

## Phase 1.5 — Reality checkpoint (2026-08-03 research)

**GBrain:** orama code index refreshed (905 pages). Memory corpus searchable.
**EXA + FireCrawl:** NousResearch delegation docs + `delegate_tool.py` scraped.
**PT `.agent/memory`:** PR222 Hermes staging, coord_pulse, portable-brain lessons.

Canonical taxonomy: `bin/orama-system/skills/hermes-harness/references/hermes-dispatch-taxonomy.md`

### Dispatch truth table

| orama name today | Actual lane | Native Hermes equivalent |
| ---------------- | ----------- | ------------------------ |
| `hermes-delegate` | **L-PT** ThreadPool + `spawn_hermes_agent` | `delegate_task` (not wired) |
| `hermes-orama` / `hermes_harness.py` | **L-PT** sequential `AIAgent.chat` | N/A (script, not in-session) |
| `hermes-spawn` | **L-PT** PT harness PID lifecycle | N/A |
| `coord_pulse.ps1` | **L-Fleet** cursor-agent one-shot | N/A |
| `subagent/win-coder/…` git branches | **L-Fleet** inbox coordination | N/A |
| `bin/agents/REGISTRY.yml` roles | **Staging** profile materialization | Profiles ≠ runtime children |
| Interactive Hermes `delegate_task` | **L-H1** | Canonical Nous behavior |

### Windows Hermes commands (session-evidence)

Verified in fleet results + `coord_pulse.ps1` (not hypothetical):

- `install.ps1`, `install-hermes-harness.ps1 -RunDoctor`
- `install_coord_pulse.ps1`, `coord_pulse.ps1 -DryRun`
- `hermes backup`, `hermes doctor`, `hermes profile list`
- `hermes_spawn.sh` start/stop/status (PID file, not `AIAgent.chat` probe)
- `cursor-agent --print --model composer-2.5` via coord_pulse enqueue

### Plan corrections recalled (Win / Hermes staging)

| Incident | Fix |
| -------- | --- |
| PR #222 body clobber (aguara replaced Phase B scope) | Append-only restore from ladder + review-gate docs |
| discover.py Win platform role | `RUNNING_ON_WINDOWS` + LM Studio model list |
| coord_pulse `$Args` collision | `-LanArgs` (matches `start.ps1`) |
| `.env.local` vs Task Scheduler | User-level env for `ORAMA_SYSTEM_PATH` / `PERPETUA_TOOLS_PATH` |
| SKILL.md all-`1.` procedure lists | LINT-010; Hermes reads raw markdown |

### Graft wave reorder (mandatory)

1. **Wave 0** — taxonomy doc + SKILL lane tags + registry `dispatch_lane` field
2. **Wave 1** — JSON envelope on shell commands (all lanes)
3. **SKIP** `recursive-spawn-protocol` → `hermes-delegate` until rename
4. **NEW** optional `hermes-native-delegate` card (L-H1 docs only)

### `bin/agents/` staging amendments

Add to each `REGISTRY.yml` role (or `agent.md` header):

| Role group | `dispatch_lane` | `native_hermes_delegate` |
| ---------- | --------------- | ------------------------ |
| context → crystallizer pipeline | `L-PT` | `false` |
| orchestrator | `L-Fleet` (Win default) | `false` |
| coder / win-researcher / autoresearcher | `L-Fleet` | `false` |
| hermes-monitor | `L-H1` when in interactive Hermes | `true` (future skills only) |

---

## Phase 2 — Farming Methodology (how to extract, not just list)

### 2A. Pattern taxonomy

Classify every harvested item into one bucket:

1. **Protocol** — envelopes, error shapes, chaining rules
   (`universal-skill-protocol.md`)
2. **Lifecycle** — ordered gates (status → dry-run → mutate → verify)
3. **Algorithm** — deterministic step lists (cron install, secret propagation)
4. **Technique** — idempotent scripts, marker regions, lock/PID patterns
5. **Skill card** — markdown operator surface (thin command)
6. **Script** — executable helper (belongs in `scripts/`, not SKILL body)

### 2B. Farming workflow (per pattern)

```text
1. READ  openclaw skill + upstream cc-openclaw baseline (if overlay)
2. EXTRACT numbered algorithm + I/O contract into a scratch card
3. MAP   to hermes-harness target via absorption map rules
4. CLASSIFY ADOPT | ADAPT | SKIP (OpenClaw-only paths → SKIP)
5. DRAFT minimal diff: command card + script + reference cross-link
6. VERIFY against hermes-universal-invocation-protocol.md envelope
7. REGISTER in hermes-skill-absorption-map.md (additive row)
8. TEST  pytest integration for any new shell script behavior
```

### 2C. Anti-patterns (do not farm)

- Copying `openclaw_home`, `stow`, `launchctl`, or `jobs.json` handling into
  Hermes Win paths
- Duplicating skills already marked **absorbed** in
  `hermes-skill-absorption-map.md`
- Creating parallel trees under `~/.hermes/skills/` without
  `install_hermes_thin_skills.py`
- Cross-repo symlinks (per orama policy — thin stubs + GitHub URLs only)

---

## Phase 3 — Grafting Strategy (merge into existing superset)

### Wave 0 — Dispatch taxonomy + path doctrine (DONE on graft branch)

**Goal:** Stop conflating L-H1 / L-PT / L-Fleet before any protocol or lifecycle grafts.

| Deliverable | Status |
| ----------- | ------ |
| `references/hermes-dispatch-taxonomy.md` | **Done** — three lanes, command catalog, graft rules |
| `references/openclaw-workspace-path-doctrine.md` | **Done** — ban `$OPENCLAW_ROOT` in committed prose |
| `references/openclaw-pattern-graft-registry.md` | **Done** — Wave 0 graft matrix |
| `commands/hermes-delegate` / `hermes-orama` / `hermes-spawn` SKILL wording | **Done** — L-PT lane tags; `hermes-delegate` ≠ `delegate_task` |
| `hermes-harness/SKILL.md` dispatch section | **Done** |
| `scripts/resolve_perp_harness.sh` fallback | **Done** — git crawl from ORAMA mother + `$HOME`; not `$OPENCLAW_HOME` |
| `references/workspace-path-resolution.md` | **Done** — git crawl rows; no layout literals |
| `bin/agents/REGISTRY.yml` | **Done** — `dispatch_lane` + `native_hermes_delegate` per role |
| `references/hermes-skill-absorption-map.md` | **Done** — additive Wave 0 row |
| Harness `references/results/*.md` `$OPENCLAW_ROOT` scrub | **Done** — historical fleet cards |
| `references/hermes-portable-brain-map.md` | **Done** — path doctrine pointer |

**Explicit SKIP (Wave 0):** graft OpenClaw `recursive-spawn-protocol` into `hermes-delegate`
until rename (e.g. `hermes-pt-parallel`). `hermes-delegate` stays L-PT documentation only.

**Path doctrine (committed prose):**

| Use | Do not use |
| --- | ---------- |
| `$REPO_ROOT`, `$ORAMA_SYSTEM_PATH`, `$PERPETUA_TOOLS_ROOT` | `$OPENCLAW_ROOT` |
| Git crawl: mother-of-orama + `$HOME` | Hardcoded workstation or layout paths in repo |
| `$HOME` for user-level runtime | `$OPENCLAW_HOME` for cross-repo discovery |

Canonical: `bin/orama-system/skills/hermes-harness/references/openclaw-workspace-path-doctrine.md`

### Wave 1 — Protocol harmonization (low risk, high leverage)

**Files:**

| File | Action | Why |
| ---- | ------ | --- |
| `hermes-harness/references/hermes-universal-invocation-protocol.md` | UPDATE | Align L3 envelope with OpenClaw `{skill_id, args, agent_id, home}` shape |
| `hermes-harness/scripts/json-response.sh` | CREATE (port from openclaw) | Shared JSON stdout for all Hermes shell commands |
| `commands/hermes-spawn`, `hermes-delegate`, `hermes-orama` | UPDATE | Emit normalized JSON on success/error |

**Mirror:** `openclaw-skills/scripts/json-response.sh`,
`universal-skill-protocol.md` result schema.

### Wave 2 — Lifecycle commands (OpenClaw ops → Hermes ops)

| New/adapted command | Inspired by | Hermes behavior |
| ------------------- | ----------- | --------------- |
| `hermes-status` (NEW) | `openclaw-status` | PT root resolved, spawn sessions, partner canaries, profile list |
| `hermes-doctor` (NEW or extend `verify_partner_canaries.py`) | `openclaw-status` + ECC doctor | Single JSON health report |
| Extend `hermes-spawn start` | `openclaw-restart` pre-checks | Require `hermes-status` pass or `--force` |

**Mirror:** `commands/hermes-spawn/SKILL.md` + `scripts/hermes_spawn.sh` lock/PID
patterns.

### Wave 3 — Orchestration grafts (algorithms, not config)

| OpenClaw source | Hermes merge target |
| --------------- | ------------------- |
| `openclaw-dream-setup` token budgets + cron shape | `pt-orama-lesson-mining` + `references/update-all-agents-comms.md` |
| `openclaw-add-script` scaffold rules | New `hermes-add-script` or section in `skillify` references |
| `recursive-spawn-protocol.md` | **SKIP** → `hermes-delegate` until L-PT rename; optional future `hermes-native-delegate` (L-H1 only) |
| `codex-openclaw-agent` bind flow | `dispatch_codex_partner.py` + `pt-orama-delegate` preflight |

### Wave 4 — Command consolidation (reduce duplication)

- Inline Python in `hermes-delegate/SKILL.md` → extract `scripts/hermes_delegate.py`
  (mirror `hermes_spawn.sh` extraction)
- Deduplicate PT root resolver: single `resolve_perp_harness.sh` sourced everywhere
- Update `install_hermes_thin_skills.py` manifest when new commands land

### Wave 5 — Documentation & absorption ledger

- Append rows to `hermes-skill-absorption-map.md` (additive only)
- Add `references/openclaw-pattern-graft-registry.md` — living map of ADOPT/ADAPT
  decisions
- Cross-link from `openclaw-skills/SKILL.md` → Hermes equivalents where absorbed

---

## Phase 4 — Comparison Worktree Outputs

Before any merge to `main`, the audit worktree should produce:

1. **`docs/plans/…-graft-audit.md`** — full Graft Matrix
2. **`.claude/plans/hermes-openclaw-graft.plan.md`** — executable task breakdown
   (if using PRD flow later)
3. **Gap scorecard** — % of Nine Skills + `codex-openclaw-agent` patterns with Hermes ADOPT/ADAPT coverage
4. **No code on `main`** until Wave 1 is approved

---

## Files Likely to Change (post-confirmation)

| File | Action |
| ---- | ------ |
| `hermes-harness/references/openclaw-pattern-graft-registry.md` | CREATE |
| `hermes-harness/references/hermes-universal-invocation-protocol.md` | UPDATE |
| `hermes-harness/scripts/json-response.sh` | CREATE |
| `hermes-harness/commands/hermes-status/SKILL.md` | CREATE |
| `hermes-harness/scripts/hermes_status.sh` | CREATE |
| `hermes-harness/scripts/hermes_delegate.py` | CREATE (extract) |
| `hermes-harness/references/hermes-skill-absorption-map.md` | UPDATE (additive) |
| `tests/test_hermes_status.py` | CREATE |
| `hermes-harness/scripts/install_hermes_thin_skills.py` | UPDATE |

---

## Validation

```bash
# Audit worktree — inventory only
find bin/orama-system/skills/openclaw-skills -name SKILL.md | wc -l
find bin/orama-system/skills/hermes-harness/commands -name SKILL.md | wc -l

# After each wave
python3 -m pytest tests/test_hermes_spawn.py tests/test_hermes_status.py -q
python3 bin/orama-system/skills/hermes-harness/scripts/install_hermes_thin_skills.py --verify
bash scripts/ci/run_agent_security_scans.sh  # skill-scanner collisions
npx markdownlint-cli2 "bin/orama-system/skills/hermes-harness/**/*.md"
```

---

## Risks

| Risk | Likelihood | Mitigation |
| ---- | ---------- | ---------- |
| Confusing OpenClaw gateway ops with Hermes runtime ops | High | Graft Matrix `SKIP` column; platform tags on every command |
| Duplicating already-absorbed content | Medium | Start from `hermes-skill-absorption-map.md`; diff before write |
| PT `hermes_harness.py` boundary creep | Medium | Keep spawn/pipeline in PT; orama owns command cards + shell |
| Skill-scanner name collisions | Medium | `{skill-prefix}-*.md` naming (checklist lesson) |
| `cc-openclaw` submodule uninitialized | Medium | Phase 0 init; document upstream-only patterns separately |
| Win/Mac path divergence | High | Separate PS1 vs bash script pairs; shared JSON contract only |

---

## Recommended Execution Order

1. **Phase 0** — worktree + audit doc (this file)
2. **Phase 1** — Graft Matrix (read-only)
3. **Phase 1.5** — taxonomy + lane tags (this file §1.5 + `hermes-dispatch-taxonomy.md`)
4. **Wave 0** — lane tags on skills + REGISTRY; no `hermes-delegate` / `delegate_task` conflation
5. **Wave 1** — JSON protocol harmonization (smallest shippable graft)
6. **Wave 2** — `hermes-status` / doctor gate
7. **Waves 3–5** — deeper merges prioritized by Graft Matrix scores

---

## Acceptance Criteria

- [ ] Isolated worktree from `main` with audit artifact committed
- [ ] Graft Matrix covers all Nine OpenClaw skills + `codex-openclaw-agent`
- [ ] Every `ADOPT`/`ADAPT` row has a concrete Hermes command/script target
- [ ] No OpenClaw-only paths copied verbatim into Hermes Win flows
- [ ] Absorption map updated additively for each merged pattern
- [ ] Integration tests for new shell entrypoints
- [ ] `install_hermes_thin_skills.py --verify` passes after new commands

---

## Appendix A — OpenClaw Skills Tree Summary (`main`)

```text
openclaw-skills/
├── SKILL.md                          # Master skill (The Nine Skills index + ops rules)
├── cc-openclaw/                        # Upstream git submodule
├── codex-openclaw-agent/               # Orama extension: dedicated Codex sub-agent
├── references/                         # Shared cross-harness contracts
├── scripts/                            # Shared helpers (json-response.sh, etc.)
├── skills/                             # The Nine Skills (Orama overlays)
│   ├── openclaw-new-agent/SKILL.md
│   ├── openclaw-add-channel/SKILL.md
│   ├── openclaw-add-cron/SKILL.md
│   ├── openclaw-dream-setup/SKILL.md
│   ├── openclaw-add-script/SKILL.md
│   ├── openclaw-add-secret/SKILL.md
│   ├── openclaw-status/SKILL.md
│   ├── openclaw-restart/SKILL.md
│   └── openclaw-stow/SKILL.md
└── templates/                          # Agent directive scaffolds
```

**Dispatch stack (PT-Orama weave):**

```text
orama-system (L3) → Perpetua-Tools dispatcher (L2) → openclaw-skills/{skill_id} → OpenClaw home (L1)
```

---

## Appendix B — Hermes Harness Command Inventory (`main`)

| Command | Purpose |
| ------- | ------- |
| `hermes-spawn` | `start\|stop\|status` for background Hermes session |
| `hermes-orama` | Full Orama 5-stage pipeline via PT |
| `hermes-delegate` | 2–5 parallel executor workers |
| `pt-orama-council` | 5-model council coordination |
| `pt-orama-review` | Findings-first review |
| `pt-orama-delegate` | Bounded specialist subtask |
| `pt-hardware-policy` | Model↔hardware affinity gate |
| `lan-peer-self-talk` | Mac↔Win LAN probe |
| `windows-hermes-setup` | Windows PATH, ECC doctor, thin-skill install |
| `pt-orama-lesson-mining` | *(optional)* session insights → memory |

**Key scripts:** `resolve_perp_harness.sh`, `hermes_spawn.sh`,
`install_hermes_thin_skills.py`, `verify_partner_canaries.py`,
`dispatch_codex_partner.py`, LAN/coord suite (24 files total under `scripts/`).

---

## Appendix C — Known Gaps vs Full Orchestration Harness

| Present | Missing / deferred |
| ------- | ------------------ |
| Thin command cards + universal JSON envelope (partial) | No unified **task API** |
| Single-session spawn + parallel delegate | No **fleet manager** |
| Mac↔Win pulse + job queues | No **central scheduler** |
| Partner dispatch (Codex/AGY) | **L1 portal dispatch** blocked on P5 |
| GossipBus + inbox drops | No built-in OTel/Periscope transport in spawn/delegate |
| Hardware policy gate at edge | Pipeline model defaults not wired through PT ModelRegistry |
| Verifier stage in pipeline | No server-side verifier gate blocking crystallization |
| V1 `depth=0` | No recursive worker trees or HITL approval flows |

---

## Status

| Milestone | State |
| --------- | ----- |
| Phase 0 worktree | **Done** — `.worktrees/orama-hermes-graft-audit` on `cursor/hermes-openclaw-graft-audit-f559` |
| This plan document | **Done** — saved 2026-08-03 |
| Phase 1 Graft Matrix | **Pending** — read-only audit |
| Wave 1+ implementation | **Pending** — awaits explicit confirmation |
