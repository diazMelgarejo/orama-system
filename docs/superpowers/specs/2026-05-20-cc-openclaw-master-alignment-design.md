# cc-openclaw Master Alignment Design (2026-05-20)

> **For agentic workers:** Implement with `superpowers:subagent-driven-development` on branch
> `feat/openclaw-skills-submodule`. Review before execution — each sub-project has a
> confirmation gate. **Do NOT push until all 4 sub-projects pass local test + review.**

**Goal:** Properly attribute and wire `rahulsub-be/cc-openclaw` as a git submodule, enshrine
the Two-Layer Architecture, make all SKILL.md files compliance-passing, and bake the
search-frugality + Windows-coder-always-utilized policies into every orchestrator role.

**Repos affected:** `diazMelgarejo/orama-system` (primary), `diazMelgarejo/Perpetua-Tools` (secondary)

**Branch:** `feat/openclaw-skills-submodule` (already open in orama-system)

---

## 0 — Context and Motivation

### What cc-openclaw is

`rahulsub-be/cc-openclaw` (MIT, GitHub) is the **upstream source** of The Nine OpenClaw
operational skills. Its core insight (from the Trilogy AI Substack article, 2026):
_"non-deterministic systems need deterministic configuration management"_ — skills separate
the *what* from the *how*, letting any agent execute consistent procedures.

Our work **extends** the upstream by adding:
- Provider substrate layer (model routing via `v1/OpenRouter.md`)
- PT/orama-system integration (`pt-orama-weave.md`, `universal-skill-protocol.md`)
- Search frugality rules (Gbrain → Brave → Perplexity → Grok)
- Windows coder always-utilized policy
- Agent template files and idempotent install machinery

The upstream repo has NO provider substrate. All routing/model decisions are our additions.

### The Two-Layer Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│  Layer 1 — OpenClaw Operations (cc-openclaw)                      │
│  The Nine Skills + PT/orama weave + search frugality + extensions │
│  Upstream: rahulsub-be/cc-openclaw (MIT)                          │
│  Location: bin/orama-system/skills/openclaw-skills/               │
│    └── cc-openclaw/   ← git submodule (upstream, Nine Skills)     │
│    └── references/    ← our extensions (openrouter-defaults, etc) │
│    └── templates/     ← our agent template files                  │
│    └── scripts/       ← our operational scripts                   │
│    └── SKILL.md       ← our master skill (extends upstream)       │
├───────────────────────────────────────────────────────────────────┤
│  Layer 0 — Provider Substrate                                     │
│  v1/OpenRouter.md — free model stack, openclaw.json shape,        │
│  rate limits (Tier A-F), security rules, Gemini routing policy    │
│  Location: OpenClaw/v1/OpenRouter.md (canonical, do not copy)     │
└───────────────────────────────────────────────────────────────────┘
```

**Cross-references in CLAUDE.md files MUST state:**
> "cc-openclaw = `v1/OpenRouter.md` (Layer 0 substrate) + `openclaw-skills/` (Layer 1 ops).
> The upstream Nine Skills are in `openclaw-skills/cc-openclaw/` (submodule). Our extensions
> live at `openclaw-skills/` root."

---

## Sub-Project A — Submodule Wiring + Attribution

### A1 — Register cc-openclaw as git submodule

Target path: `bin/orama-system/skills/openclaw-skills/cc-openclaw`
Source: `https://github.com/rahulsub-be/cc-openclaw.git`

```bash
cd /path/to/orama-system
git submodule add https://github.com/rahulsub-be/cc-openclaw.git \
  bin/orama-system/skills/openclaw-skills/cc-openclaw
git submodule update --init --recursive
```

**If already present (idempotent guard):**
```bash
if [ ! -f "bin/orama-system/skills/openclaw-skills/cc-openclaw/README.md" ]; then
  git submodule add https://github.com/rahulsub-be/cc-openclaw.git \
    bin/orama-system/skills/openclaw-skills/cc-openclaw
fi
git submodule update --init --recursive bin/orama-system/skills/openclaw-skills/cc-openclaw
```

### A2 — Idempotent install script

**File:** `scripts/install-openclaw-skills.sh`

```bash
#!/usr/bin/env bash
# install-openclaw-skills.sh — idempotent at every start.sh call and on fresh installs
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
SKILL_ROOT="$REPO_ROOT/bin/orama-system/skills/openclaw-skills"
UPSTREAM_DIR="$SKILL_ROOT/cc-openclaw"

# 1. Initialize submodule if missing
if [ ! -f "$UPSTREAM_DIR/README.md" ]; then
  echo "[install-openclaw-skills] Initializing cc-openclaw submodule..."
  git -C "$REPO_ROOT" submodule update --init --recursive \
    bin/orama-system/skills/openclaw-skills/cc-openclaw
else
  echo "[install-openclaw-skills] cc-openclaw submodule already present, skipping init."
fi

# 2. Verify Nine Skills are present (smoke check)
REQUIRED_SKILLS=(
  openclaw-new-agent openclaw-add-channel openclaw-add-cron
  openclaw-dream-setup openclaw-add-script openclaw-add-secret
  openclaw-status openclaw-restart openclaw-stow
)
for skill in "${REQUIRED_SKILLS[@]}"; do
  if [ ! -f "$UPSTREAM_DIR/skills/$skill/SKILL.md" ] && \
     [ ! -f "$UPSTREAM_DIR/.claude/skills/$skill/SKILL.md" ]; then
    echo "[install-openclaw-skills] WARNING: $skill SKILL.md not found in upstream"
  fi
done

# 3. Our extensions are already in $SKILL_ROOT — no copy needed (patch-on-top model)
echo "[install-openclaw-skills] Extensions at $SKILL_ROOT are versioned in orama-system."
echo "[install-openclaw-skills] Done."
```

### A3 — Wire into start.sh

Add to `start.sh` (after environment checks, before gateway start):
```bash
bash "$REPO_ROOT/scripts/install-openclaw-skills.sh"
```

### A4 — Update master SKILL.md frontmatter

Add to `openclaw-skills/SKILL.md` YAML frontmatter:
```yaml
upstream: https://github.com/rahulsub-be/cc-openclaw
upstream_license: MIT
upstream_path: bin/orama-system/skills/openclaw-skills/cc-openclaw
layer: "1 — Operations (builds on Layer 0: v1/OpenRouter.md)"
```

Add attribution section to `openclaw-skills/SKILL.md` body:
```markdown
## Attribution

The Nine Skills originate from [cc-openclaw](https://github.com/rahulsub-be/cc-openclaw)
(MIT, Rahul Subramanian). The upstream lives at `cc-openclaw/` (git submodule).

Extensions in this directory (`references/`, `templates/`, `scripts/`, this `SKILL.md`)
are orama-system additions and are NOT in the upstream repo.

Layer 0 (provider substrate): `v1/OpenRouter.md` — free model stack, openclaw.json shape,
rate limits. See `references/openrouter-defaults.md` for the distilled routing table.
```

---

## Sub-Project B — SKILL.md Compliance Audit

### B1 — Required frontmatter template

All SKILL.md files targeting agents MUST have:
```yaml
---
name: <kebab-case-skill-id>
description: <one sentence. Start with a verb. Include the trigger condition.>
version: "1.0"
agent_compatibility:
  - Claude
  - Codex
  - Gemini          # only if skill works there
  - Hermes          # only if skill works there
layer: "<0|1|agent-local>"
upstream: <URL>     # only if derived from external source
upstream_license: <MIT|Apache-2.0|...>  # only if upstream is set
---
```

### B2 — Required cross-links

Each subskill SKILL.md MUST contain a `## References` section with:
- `references/openrouter-defaults.md` — model routing source of truth
- `references/universal-skill-protocol.md` — invocation envelope standard
- `references/pt-orama-weave.md` — how PT + orama-system cooperate

### B3 — Target files and required fixes

| File | Missing | Action |
|------|---------|--------|
| `openclaw-skills/SKILL.md` | `upstream`, `layer`, attribution body section | Add (A4 covers this) |
| `openclaw-skills/skills/*/SKILL.md` (×9) | `upstream`, `layer`, `## References` | Add to all nine |
| `AlphaClaw/SKILL.md` | `version`, `layer`, `## References` | Add |
| `AlphaClaw/.claude/skills/cherry-pick-down/SKILL.md` | `version`, `layer` | Add |
| `AlphaClaw/.claude/skills/macos-port-status/SKILL.md` | `version`, `layer` | Add |
| `.agents/skills/agent-failure-postmortem/SKILL.md` | Full frontmatter, cross-links | Add |
| `.agents/skills/codex-mcp-debugging/SKILL.md` | Full frontmatter, cross-links | Add |
| `.agents/skills/supabase*/SKILL.md` (×2) | `agent_compatibility`, cross-links | Add |

### B4 — Division of labor check (no overlaps)

Use Gbrain to verify no two skills share primary responsibilities:
```bash
gbrain query "which openclaw skills overlap in responsibility?"
gbrain code-def "openclaw-add-secret"   # check callers
gbrain code-def "openclaw-add-channel"  # should be sole secrets caller
```

If overlaps found: consolidate into the canonical skill; add `## Deprecated` note to the redundant one.

---

## Sub-Project C — Search Frugality + Windows Coder Policy

### C1 — Search frugality rule (canonical text)

```markdown
## Search Frugality Rule

**RULE: Never guess when information is scarce.**
Search in this order — stop at the first satisfying result:

1. `/sync-gbrain` + `gbrain query "<question>"`  — local semantic memory, zero cost
2. `code-review-graph: semantic_search_nodes`    — structural code context
3. Brave Search API                              — web facts, current state
4. Perplexity API (inline)                       — deep web synthesis
5. Grok API                                      — last resort only

**NEVER:** parallel-fire all search tools. Use the cheapest first.
**ALWAYS:** `AskUserQuestion` for decisions — never auto-select between ambiguous options.
```

**Files that receive this rule:**
1. `openclaw-skills/SKILL.md` (master) — add as `## Search Frugality Rule` section
2. `openclaw-skills/references/universal-skill-protocol.md` — add as § Search
3. `bin/orama-system/SKILL.md` (mother skill) — add as `## Search Policy` section
4. `orama-system/CLAUDE.md` (§ 0 invariants) — add one-line pointer
5. `Perpetua-Tools/CLAUDE.md` (§ 0 invariants) — add one-line pointer

### C2 — Windows coder always-utilized policy (canonical text)

```markdown
## Windows Coder Always-Utilized Policy

**RULE: Every available Windows coder MUST be given work as soon as it is idle.**

Endpoint pool: `$WIN_CODER_ENDPOINTS` (default: `192.168.254.103:1234`)

Dispatch protocol:
1. Before routing any task to Mac-only paths, check if a Windows coder is free.
2. If free AND task is compatible (Python, Go, TypeScript, general coding):
   → dispatch to Windows coder FIRST.
3. If offline or no model loaded: skip silently, log WARN, do not fail.
4. As more Windows coders are added to `$WIN_CODER_ENDPOINTS`, they join the pool
   automatically — same rule applies to all.

**Never leave a Windows coder idle if pending compatible work exists.**
```

**Files that receive this policy:**
1. `orama-system/CLAUDE.md` (§ 0 invariants) — add `Win coder pool` row to table
2. `bin/orama-system/SKILL.md` (mother skill) — add `## Windows Coder Pool` section
3. `openclaw-skills/SKILL.md` — add as `## Windows Coder Policy` section
4. `openclaw-skills/references/universal-skill-protocol.md` — add § Windows Coder
5. `Perpetua-Tools/CLAUDE.md` — add one-line pointer

---

## Sub-Project D — Spawning Gate Wired to openclaw-skills Primary

### D1 — Spawn dispatch priority (new rule in supervisor.py)

```python
# orchestrator/supervisor.py — spawn gate (pseudocode)
async def _dispatch_task(task: TaskEnvelope) -> WorkerResult:
    # 1. openclaw-skills primary path
    if skill_id := _infer_skill(task):
        envelope = resolve_skill(skill_id, task.args, agent_id=task.worker_id)
        return await _run_skill_envelope(envelope)

    # 2. Windows coder pool — always check before Mac-local
    if win_endpoint := await _get_free_windows_coder():
        return await _dispatch_to_endpoint(task, win_endpoint)

    # 3. Local Mac model
    if await _local_model_available():
        return await _dispatch_local(task)

    # 4. Online fallback (Claude / Codex / Gemini)
    return await _dispatch_online(task)
```

### D2 — Contracts update

Add to `orchestrator/contracts.py`:
```python
class OrchestrationSession(BaseModel):
    # ... existing fields ...
    windows_coder_pool: list[str] = Field(
        default_factory=lambda: list(
            filter(None, os.environ.get("WIN_CODER_ENDPOINTS", "").split(","))
        ),
        description="LM Studio endpoints for Windows coders. Checked before Mac-local dispatch.",
    )
```

### D3 — spawn_reconciliation.py gate

Add `_try_skill_envelope()` as the first check in `reconcile_spawn()`:
```python
def _try_skill_envelope(task: TaskEnvelope) -> SkillEnvelope | None:
    """Return a SkillEnvelope if this task maps to a known openclaw-skills ID."""
    skill_map = {
        "new_agent": "openclaw-new-agent",
        "add_channel": "openclaw-add-channel",
        "add_cron": "openclaw-add-cron",
        # ... etc
    }
    if sid := skill_map.get(task.task_type):
        try:
            return resolve_skill(sid, task.args, agent_id=task.worker_id)
        except (SkillResolutionError, RecursionBudgetExceeded):
            return None
    return None
```

---

## File Map (complete)

| File | Action | Sub-project |
|------|--------|-------------|
| `bin/orama-system/skills/openclaw-skills/cc-openclaw/` | NEW — git submodule | A |
| `scripts/install-openclaw-skills.sh` | NEW — idempotent installer | A |
| `start.sh` | EDIT — call installer | A |
| `bin/orama-system/skills/openclaw-skills/SKILL.md` | EDIT — attribution + frugality + Windows | A,C |
| `bin/orama-system/skills/openclaw-skills/skills/*/SKILL.md` (×9) | EDIT — frontmatter + references | B |
| `AlphaClaw/SKILL.md` | EDIT — frontmatter | B |
| `.agents/skills/*/SKILL.md` (×4) | EDIT — frontmatter + cross-links | B |
| `bin/orama-system/skills/openclaw-skills/references/universal-skill-protocol.md` | EDIT — search + Windows rules | C |
| `bin/orama-system/SKILL.md` | EDIT — search + Windows policy sections | C |
| `orama-system/CLAUDE.md` | EDIT — §0 invariants + pointers | C |
| `Perpetua-Tools/CLAUDE.md` | EDIT — §0 invariants + pointers | C |
| `orchestrator/contracts.py` | EDIT — `windows_coder_pool` field | D |
| `orchestrator/supervisor.py` | EDIT — Windows coder idle-check | D |
| `orchestrator/spawn_reconciliation.py` | EDIT — `_try_skill_envelope()` gate | D |

---

## Execution Order

```
feat/openclaw-skills-submodule branch (already open)
│
├── Sub-A: Submodule + install script + start.sh + SKILL.md attribution
│   Test: git submodule status; bash scripts/install-openclaw-skills.sh
│   ↓
├── Sub-B + Sub-C (parallel agents):
│   ├── Sub-B: SKILL.md compliance (frontmatter + cross-links for all 14 files)
│   └── Sub-C: Search frugality + Windows coder policy (5 SKILL.md/CLAUDE.md files each)
│   Test: grep for required frontmatter fields; grep for search frugality rule
│   ↓
└── Sub-D: Spawning gate (contracts.py, supervisor.py, spawn_reconciliation.py)
    Test: pytest tests/ -k "spawn or skill_resolver or windows_coder"
    ↓
    PR: feat/openclaw-skills-submodule → main (both repos, lockstep commit)
```

---

## Verification Checklist

```bash
# A: Submodule
git submodule status bin/orama-system/skills/openclaw-skills/cc-openclaw
bash scripts/install-openclaw-skills.sh   # must print "Done." with no warnings

# B: Compliance
grep -rL "upstream:" bin/orama-system/skills/openclaw-skills/skills/  # must return empty

# C: Search frugality rule present
grep -r "Search Frugality Rule" bin/orama-system/skills/openclaw-skills/SKILL.md
grep -r "WIN_CODER_ENDPOINTS" orama-system/CLAUDE.md

# D: Spawning gate
python -c "from orchestrator.contracts import OrchestrationSession; s = OrchestrationSession(); print(s.windows_coder_pool)"
pytest tests/test_openclaw_skill_resolver.py -v
```

---

## Open Questions (none — all decisions made)

All architecture decisions were confirmed by user during brainstorming (2026-05-20).
No placeholders remain. See conversation history for decision rationale.
