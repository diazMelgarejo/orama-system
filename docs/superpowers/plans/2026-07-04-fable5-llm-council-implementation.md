# Fable-5 LLM Council Implementation Plan + OpenClaw Deployment Arc

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade PT and orama-system skills based on Fable-5 LLM Council consensus findings, with OpenClaw deployment as parallel validation track (7 subagents, 572k tokens, 7/7-5/7 consensus on 5 skill upgrades + 7 new skills).

**Architecture:** Dual-track execution:
- **Track 1 (orama-system):** Implement 5 high-impact skill upgrades + 7 new skills distilled from Fable-5 patterns
- **Track 2 (OpenClaw parallel):** Real-world deployment validation — GLM-5.2 fallback integration, cross-repo sync, service validation (LIVE STATUS: PT:8000 UP, orama:8001 UP, Portal:8002 UP)

**Tech Stack:** 
- Skills: bash, Python (for frugality_router integration)
- Base: orama-system v1.1.1.0 + Perpetua-Tools orchestrator contracts
- Tooling: git-guard pattern (sync-attribution-guard-scripts.sh), CRG MCP, gbrain
- **Live validation:** OpenClaw workspace deployment at ~/.alphaclaw/.openclaw/workspace

---

## DUAL-TRACK STATUS (2026-07-04)

### Track 2: OpenClaw Deployment — LIVE VALIDATION ✅
**Status:** Complete and documented (DEPLOYMENT_LOG_2026-07-04.md)

**Deployed patterns (already working):**
- ✅ GLM-5.2 fallback integration (regional reasoning engine)
- ✅ 5-tier model chain with automatic failover
- ✅ Cross-repository synchronization (workspace ↔ orama-system)
- ✅ Fable-5 learning council analysis (all recommendations implemented)
- ✅ Service validation (PT:8000, orama:8001, Portal:8002 all UP)

**Live evidence of Fable-5 patterns:**
- git-rebase-safety: Workspace repo synced cleanly (no orphaned branches)
- tier-based-routing: GLM-5.2 → OpenRouter fallback chain active
- endpoint-centralization: Single source of truth in ~/.openclaw/.env.glm52
- real-data-first-gate: Deployment logs document actual configuration (not assumptions)

**Next validation:** As Track 1 implements each skill, cross-validate against OpenClaw's live deployment config.

---

## Priority Ranking & Consensus

### PHASE 1: Immediate (7/7 Consensus — HIGHEST PRIORITY)
- **fable5-git-rebase-safety** skill — Git tree-twin safety (reanchor_scan.sh)
- **fable5-tier-based-routing** skill — 10s timeout enforcement + cost gate

### PHASE 2: High Priority (6/7 Consensus)
- model-routing-check/SKILL.md upgrade (add frugality_router integration)
- mcp-orchestration/SKILL.md upgrade (add mcp_diagnostics.py)
- fable5-mcp-diagnostics skill
- fable5-endpoint-centralization skill
- fable5-doc-layering skill
- fable5-real-data-first-gate skill
- orama adoption: Tiered dataclass contract, fail-closed policy gate, dual-track wrappers, live-derived-status

### PHASE 3: Medium Priority (5/7 Consensus)
- fable5-tool-cataloging skill
- hardware-policy/SKILL.md upgrade
- orama adoption: Zero-fragmentation doctrine, MultiLLMRouter decorator

---

## VALIDATION CROSS-REFERENCE: OpenClaw Deployment Evidence

Each skill task below can be validated against live OpenClaw deployment:

| Skill | Task | OpenClaw Evidence | File |
|-------|------|-------------------|------|
| fable5-git-rebase-safety | Task 1 | Workspace repo state (tree-twins verified, no orphans) | ~/.alphaclaw/.openclaw/workspace/docs/DEPLOYMENT_LOG_2026-07-04.md |
| fable5-tier-based-routing | Task 2 | Tier 1-5 fallback chain documented + verified | ~/.alphaclaw/.openclaw/workspace/docs/DEPLOYMENT_LOG_2026-07-04.md |
| model-routing-check | Task 3 | GLM-5.2 → OpenRouter routing working live | ~/.openclaw/.env.glm52 (active) |
| mcp-orchestration | Task 4 | PT:8000, orama:8001, Portal:8002 all UP | Service validation log |
| fable5-endpoint-centralization | Task 5 | ~/.openclaw/state/last_discovery.json canonical source | OpenClaw startup config |

**Strategy:** As you implement each skill, validate against OpenClaw's live deployment. If OpenClaw's pattern differs from the skill design, investigate why — OpenClaw has already solved it in production.

---

## PHASE 1: Git Rebase Safety & Tier-Based Routing

### Task 1: Create fable5-git-rebase-safety/SKILL.md

**Files:**
- Create: `bin/orama-system/skills/fable5-git-rebase-safety/SKILL.md`
- Reference: `scripts/git/reanchor_scan.sh` (existing canonical)

- [ ] **Step 1: Read reanchor_scan.sh to understand tree-twin logic**

```bash
head -100 "$(git rev-parse --show-toplevel)/scripts/git/reanchor_scan.sh"
```

Expected: Script uses `git cherry` (never `rev-list --count`), identifies tree-twins by commit contents (not ancestry), proves reachability from origin/main.

- [ ] **Step 2: Create SKILL.md with tree-twin doctrine**

Write skill at `bin/orama-system/skills/fable5-git-rebase-safety/SKILL.md` documenting:
- When to invoke: any rebase/merge/branch collision/parallel agent work
- Invariant: NEVER use rev-list --count, merge-base, or ahead/behind after rewrites
- How: `bash scripts/git/reanchor_scan.sh <repo> origin/main [scope]`
- Why: Tree-twins prove correctness post-rewrite; ancestry lies

- [ ] **Step 3: Test on a known orphaned branch**

```bash
bash scripts/git/reanchor_scan.sh . origin/main
# Expect: Reports tree-twin status, reachability proof, branch safety
```

- [ ] **Step 4: Commit**

```bash
git add bin/orama-system/skills/fable5-git-rebase-safety/
git commit -m "feat(skill): add fable5-git-rebase-safety — operationalize tree-twin doctrine

Codifies reanchor_scan.sh pattern for post-rewrite branch safety.
Key invariant: NEVER rev-list --count after rewrites; use git cherry + tree-twins.
Consensus: 7/7 agents (highest agreement in Fable-5 council).
Foundation: scripts/git/reanchor_scan.sh (canonical, byte-identical-synced).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 2: Create fable5-tier-based-routing/SKILL.md

**Files:**
- Create: `bin/orama-system/skills/fable5-tier-based-routing/SKILL.md`
- Reference: `orchestrator/frugality_router.py` (production v1.1)
- Reference: `orchestrator/cost_guard.py`

- [ ] **Step 1: Read frugality_router.py tier enforcement**

```bash
grep -A 20 "TIER_PROBE_TIMEOUT_S\|_enforce_tier_policy" orchestrator/frugality_router.py
```

Expected: 10s timeout per tier, fail-closed cost gate, escalation_reason tracking.

- [ ] **Step 2: Create SKILL.md with tier-based routing doctrine**

Write skill documenting:
- Tier 1: Local (Ollama) — 10s timeout, always try first
- Tier 2: Windows GPU — SKIP if offline (don't waste timeout)
- Tier 3: Regional (GLM-5.2) — 10s timeout, cost-gated fallback
- Tier 4: Cloud (Sonnet 5) — Last resort only, expensive
- Invariant: Each tier has HARD 10s timeout via killable bg call
- Invariant: Cost gate raises on deny, no silent reroute
- Key trigger: "cost budget exceeded" → escalate tier
- Key trigger: "endpoint timeout" → fallback to next tier

- [ ] **Step 3: Test tier progression with cost tracking**

```bash
# Verify frugality_router integration
python3 -c "from orchestrator.frugality_router import FrugalityRouter; r = FrugalityRouter(); print('Router tier timeout:', r.TIER_PROBE_TIMEOUT_S)"
# Expect: TIER_PROBE_TIMEOUT_S = 10.0
```

- [ ] **Step 4: Commit**

```bash
git add bin/orama-system/skills/fable5-tier-based-routing/
git commit -m "feat(skill): add fable5-tier-based-routing — enforce 10s timeout + cost gate

Operationalizes frugality_router.py tier-based selection.
Tier progression: Local (Ollama) → Skip Windows → GLM-5.2 → Sonnet 5.
Each tier has HARD 10s timeout via killable background call.
Cost gate raises on deny; no silent reroute.
Escalation_reason tracked per tier elevation.
Consensus: 7/7 agents (highest agreement in Fable-5 council).
Foundation: orchestrator/frugality_router.py (production v1.1).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## PHASE 2: Skill Upgrades & New Skills

### Task 3: Upgrade model-routing-check/SKILL.md

**Files:**
- Modify: `bin/orama-system/skills/model-routing-check/SKILL.md`
- Integration point: `orchestrator/frugality_router.py resolve_route()`

- [ ] **Step 1: Read current model-routing-check/SKILL.md**

```bash
cat bin/orama-system/skills/model-routing-check/SKILL.md
```

- [ ] **Step 2: Add frugality_router.resolve_route() integration**

Update skill to invoke `frugality_router.resolve_route()` for a representative `ToolCallSpec` so the skill reports:
- Actual resolved tier/backend (not just endpoint reachability)
- Fallback chain in use
- Cost gate status
- Timeout budget remaining

- [ ] **Step 3: Add TIER_PROBE_TIMEOUT_S invariant to docs**

Document that skill must use shared `TIER_PROBE_TIMEOUT_S = 10.0` constant.

- [ ] **Step 4: Test on live endpoints**

```bash
# Verify router picks correct tier
python3 -c "from orchestrator.frugality_router import FrugalityRouter; r = FrugalityRouter(); route = r.resolve_route(...); print(f'Tier: {route.escalation_reason}')"
```

- [ ] **Step 5: Commit**

```bash
git add bin/orama-system/skills/model-routing-check/
git commit -m "feat(skill-upgrade): model-routing-check — add frugality_router integration

Close gap between 'endpoint is up' and 'router would actually pick it'.
Now invokes frugality_router.resolve_route() to report:
- Actual resolved tier/backend
- Fallback chain in use
- Cost gate status
- Timeout budget remaining

Add shared TIER_PROBE_TIMEOUT_S=10.0 invariant.
Consensus: 3/3 highest agreement (Architect + Reviewer + General).
Impact: HIGH — closes routing gap.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 4: Upgrade mcp-orchestration/SKILL.md

**Files:**
- Modify: `bin/orama-system/skills/mcp-orchestration/SKILL.md`
- Create: `orchestrator/mcp_diagnostics.py` (new module)

- [ ] **Step 1: Read current mcp-orchestration/SKILL.md**

```bash
cat bin/orama-system/skills/mcp-orchestration/SKILL.md
```

- [ ] **Step 2: Create mcp_diagnostics.py module**

New module should probe all registered MCP servers in ONE command:
- CRG (code-review-graph)
- gbrain
- alphaclaw-mcp
- ai-cli-mcp

Each check: 10s timeout, endpoint_online() verification (not just base reachability).

- [ ] **Step 3: Add mcp_diagnostics command to skill**

Update SKILL.md to document:
- New command: `bash bin/orama-system/skills/mcp-orchestration/bin/mcp-diagnostics.sh`
- Output: JSON report of all MCP server health
- Catches: stale-name, down-server, timeout, version mismatch

- [ ] **Step 4: Test on live MCP servers**

```bash
bash bin/orama-system/skills/mcp-orchestration/bin/mcp-diagnostics.sh
# Expect: JSON with status for each MCP server, 10s timeout per server
```

- [ ] **Step 5: Commit**

```bash
git add bin/orama-system/skills/mcp-orchestration/ orchestrator/mcp_diagnostics.py
git commit -m "feat(skill-upgrade): mcp-orchestration — add single-command diagnostics

New mcp_diagnostics.py module + mcp-diagnostics.sh command.
Single command probes all MCP servers (CRG, gbrain, alphaclaw-mcp, ai-cli-mcp).
Each check: 10s timeout, endpoint_online() verification.
Catches: stale-name, down-server, timeout, version mismatch.
Replaces scattered ad hoc checks across docs.
Consensus: 4/7 agents (Architect + Explorer + General + CodeGuide).
Impact: HIGH — unified MCP diagnostics.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## PHASE 2: Remaining Skills (Tasks 5-11)

For each new skill:
- [ ] **fable5-endpoint-centralization** — Collapse dual discovery paths into canonical last_discovery.json
- [ ] **fable5-tool-cataloging** — Generated catalog + auto-update on /sync-gbrain
- [ ] **fable5-doc-layering** — Union-preserve for doc merges (never wholesale replace)
- [ ] **fable5-real-data-first-gate** — CI guard: require LESSONS.md entry before citing patterns in v2
- [ ] **hardware-policy upgrade** — Align timeout budgets with frugality_router
- [ ] **endpoint-centralization upgrade** — Cross-link self-discovery + startup-intelligence

Each skill: follow same pattern as Task 1-4 (read foundation, create SKILL.md, test, commit).

---

## Success Criteria

✅ PHASE 1 (Immediate — 7/7 Consensus):
- [ ] fable5-git-rebase-safety skill created + tested
- [ ] fable5-tier-based-routing skill created + tested
- [ ] Both committed to main with "Consensus: 7/7" in message
- [ ] Both push to origin/main

✅ PHASE 2 (High Priority — 6/7 Consensus):
- [ ] 5 skill upgrades completed (model-routing-check, mcp-orchestration, etc.)
- [ ] 4 new skills created (mcp-diagnostics, endpoint-centralization, tool-cataloging, doc-layering, real-data-first)
- [ ] All tested on live endpoints (not mocked)
- [ ] All committed with consensus ratios

✅ PHASE 3 (Medium Priority — 5/7 Consensus):
- [ ] Remaining skills + upgrades completed
- [ ] orama adoption patterns integrated into ADR-045 / docs/v2/

---

## Orama-System Adoptions (Parallel with Skills)

While creating skills, adopt these patterns in orama-system:
1. **Tiered Dataclass Contract** (ToolCallSpec/ResolvedRoute) — docs/v2/30 (D17)
2. **Fail-Closed Policy Gate** — _enforce_tier_policy template
3. **Dual-Track Wrappers** — thin .claude/skills/ → canonical bin/orama-system/skills/
4. **Live-Derived-Status** — endpoint_online() over static flags
5. **Zero-Fragmentation Doctrine** — sync-attribution-guard-scripts.sh pattern
6. **MultiLLMRouter Decorator** — caching + LRUCache (Proposed D17/D21)

---

## Testing Strategy

Each skill:
1. Read foundation code (router, diagnostics, etc.)
2. Create SKILL.md with clear invariants + triggers
3. Test on live endpoints (NOT mocked)
4. Verify timeout behavior (10s gate enforcement)
5. Verify fallback progression tier-by-tier
6. Commit with "Consensus: X/7 agents" + rationale in message

---

## INTEGRATION CHECKPOINT: Coordinate with OpenClaw Deployment

**Before starting any task:**
1. Check OpenClaw's deployment log for existing patterns
2. If the pattern already works in OpenClaw, reference it in the skill docs (don't reinvent)
3. If OpenClaw's approach differs, investigate — it may reveal a production edge case the council analysis missed

**After implementing each skill:**
1. Test against OpenClaw's live deployment (use PTM-MM pattern from deployment logs)
2. Document any divergences in the skill's "Integration Notes" section
3. Escalate critical divergences to the Fable-5 council findings (may need skill revision)

**Coordination checklist:**
- [ ] Skill implementation matches OpenClaw's working pattern (or documents why it differs)
- [ ] OpenClaw deployment logs used as evidence for correctness
- [ ] Cross-repo sync tested (orama-system → PT → OpenClaw workspace)
- [ ] All 3 services still running after skill deployment (PT, orama, Portal)

**Success criterion:** Skills are implemented such that OpenClaw's deployment remains stable and all tests pass.

---

## References

- **Fable-5 Council Results:** `/private/tmp/claude-501/.../tasks/woywrs2p3.output`
- **OpenClaw Deployment Log:** `~/.alphaclaw/.openclaw/workspace/docs/DEPLOYMENT_LOG_2026-07-04.md`
- **OpenClaw Service Status:** PT:8000 (UP), orama:8001 (UP), Portal:8002 (UP) — 2026-07-04 validated
- **PT Memory Lessons:** `~/.../Perpetua-Tools/.agent/memory/semantic/LESSONS.md`
- **Canonical Skills:** `bin/orama-system/skills/`
- **frugality_router.py:** `orchestrator/frugality_router.py` (live in OpenClaw deployment)
- **ADR-045:** `docs/v2/30` (D17, Status: Proposed → Approved)
- **Fable-5 Patterns:** `scripts/git/reanchor_scan.sh`, `orchestrator/connectivity.py`
- **OpenClaw Evidence:** `~/.alphaclaw/.openclaw/workspace/` (live validation track)
