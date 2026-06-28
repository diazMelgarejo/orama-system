# 41 — Agentic-Stack, Gstack, Gbrain, RAG, and Memory (Union-Blend Doctrine)

> **Status:** Active planning doc (v1 operational path in Perpetua-Tools today)  
> **Date:** 2026-06-26  
> **Cross-refs:** [`19-gstack-optional-integration.md`](19-gstack-optional-integration.md), [`20-rag-and-memory-design.md`](20-rag-and-memory-design.md), [`11-idempotency-and-guard-patterns.md`](11-idempotency-and-guard-patterns.md), orama `scripts/install-openclaw-skills.sh`, PT `scripts/git/agentic-stack-vendor.md`

---

## 1. Problem statement

Perpetua-Tools vendors [agentic-stack](https://github.com/codejunkie99/agentic-stack) at
`vendor/agentic-stack` (like `vendor/ecc-tools`). PT also owns a **heavily customized**
`.agent/` brain (episodic memory, graduated lessons, gstack-aware skills, hardware-policy
wiring, git-proxy, etc.) that agents adapted for our harnesses.

Upstream `agentic-stack upgrade` refreshes skeleton-owned `.agent/` infrastructure
(memory tools, harness hooks, adapter manifests). A naive upgrade would **overwrite**
in-house adaptations. We need the same **patch-on-top / union-merge** model already proven
for `openclaw-skills` in orama-system.

**Non-goal:** editing tracked files inside `vendor/agentic-stack` or committing blended
output back into the submodule. `vendor/` stays a clean upstream pin; `.agent/` stays
project-owned.

---

## 2. Reference pattern — openclaw-skills (orama)

```
bin/orama-system/skills/openclaw-skills/
├── cc-openclaw/          ← git submodule (upstream Nine Skills)
├── skills/               ← our extensions (versioned in orama-system)
├── references/           ← PT-orama weave docs
└── SKILL.md              ← master card + upstream attribution
```

`scripts/install-openclaw-skills.sh` (called from `start.sh`):

1. `git submodule update --init` → sync pinned SHA (idempotent)
2. Smoke-check upstream skills present
3. **No copy step** — extensions already live beside the submodule

Agentic-stack follows the same split:

| Layer | Path | Git treatment |
|-------|------|---------------|
| Upstream skeleton + adapters | `vendor/agentic-stack/` | Submodule gitlink only |
| Live operational brain | `Perpetua-Tools/.agent/` | Tracked in PT; union-merge at upgrade time |
| Harness thin wrappers | `.claude/skills/`, `.cursor/`, Hermes commands, etc. | Pointer-only; canonical bodies in `.agent/` or orama |

---

## 3. Idempotent install + upgrade preview workflow

### 3.1 Fresh clone / `start.sh` parity

```bash
# Perpetua-Tools root
git submodule update --init vendor/agentic-stack
bash scripts/git/install-agentic-stack.sh
```

`install-agentic-stack.sh` is idempotent (safe on every shell startup, like
`install-openclaw-skills.sh`).

### 3.2 Mandatory dry-run before any `.agent/` harmonization

After submodule sync, **always** preview upstream deltas before applying:

```bash
# Requires agentic-stack >= v0.16 (upgrade verb). Older gitlinks fall back to doctor.
cd "$PT_ROOT"
export AGENTIC_STACK_ROOT="$PT_ROOT/vendor/agentic-stack"
python3 -m harness_manager.cli upgrade --dry-run "$PT_ROOT"
```

**Operator checklist from dry-run output:**

| Category | Action |
|----------|--------|
| New skeleton tools under `.agent/tools/` | Union-merge: keep PT files; manually port useful upstream fixes |
| Changed harness hooks | Diff per adapter; prefer PT hooks if gstack/gbrain wired |
| New skills in upstream template | Add to `.agent/skills/` only if triggers don't collide |
| Adapter manifest / `install.json` | Update metadata; never drop PT adapter entries |
| **Brain bridge / external Brain** | **BLOCK** — see §5 |

Only after human review of dry-run output:

```bash
python3 -m harness_manager.cli upgrade --yes "$PT_ROOT"   # when ready
# Then manually reconcile any flagged paths — never blind --yes
```

Bump `vendor/agentic-stack` gitlink separately via `scripts/git/agentic-stack-submodule-sync.sh upgrade`
after reading [CHANGELOG.md](https://github.com/codejunkie99/agentic-stack/blob/master/CHANGELOG.md).

---

## 4. Harness coverage matrix

Adapters ship inside `vendor/agentic-stack/adapters/`. PT installs thin surfaces per host.

### Windows

| Host | agentic-stack adapter | PT / orama loading surface |
|------|----------------------|----------------------------|
| Antigravity CLI | `antigravity` | `ANTIGRAVITY.md` → `.agent/AGENTS.md` |
| Antigravity IDE | `antigravity` | same brain mount |
| Hermes | `hermes` | thin `/pt-orama-*` wrappers → canonical orama skills |
| Cursor Agent / Cursor CLI | `cursor` | `.cursor/` rules + skills mirror |
| Codex | `codex` | `.codex/` wrappers |
| Claude Desktop App | `claude-code` | `.claude/settings.json` hooks → `.agent/harness/hooks/` |

### Linux + macOS

| Host | agentic-stack adapter | PT / orama loading surface |
|------|----------------------|----------------------------|
| OpenClaw | `openclaw` | orama `openclaw-skills` + AlphaClaw lifecycle |
| Claude CLI (`claude`) | `claude-code` | `.claude/skills/` thin wrappers |
| Claude Desktop | `claude-code` | same hook wiring |
| Cursor Agent | `cursor` | `.cursor/` mirror |

**Invariant:** every harness reads the **same** `.agent/memory/` and `.agent/skills/`.
Adapter-specific files are pointers and hook registration only — zero fragmentation of
lesson bodies (see [`27-git-governance-zero-fragmentation.md`](27-git-governance-zero-fragmentation.md)).

---

## 5. Block external Brain integration (gstack is canonical)

agentic-stack v0.18+ adds optional integration with
[codejunkie99/brain](https://github.com/codejunkie99/brain) via `.agent/tools/brain_bridge.py`
and `agentic-stack brain *` CLI verbs.

**PT policy: block Brain adoption until dual-backend bridge ships.**

| Memory layer | Canonical PT/orama implementation | Upstream Brain |
|--------------|-----------------------------------|----------------|
| Project episodic + semantic | `.agent/memory/` (learn.py, recall.py, auto_dream) | Do not enable |
| Long-horizon semantic RAG | **Gbrain** (gstack) via orama `gstack` skill | Deferred |
| Graph audit / routing memory | `GossipBus` + future LanceDB (see doc 20) | N/A |

**Upgrade blocklist (review on every dry-run):**

- Do **not** add `.agent/tools/brain_bridge.py` from upstream without PT fork review
- Do **not** wire `agentic-stack brain install` in CI or `start.sh`
- Do **not** store secrets or workstation paths in any brain export

### 5.1 Future — dual backend bridge (planned)

Extend PT-owned `.agent/tools/brain_bridge.py` (not vendored copy) to multiplex:

```
.agent/tools/brain_bridge.py
├── backend=gbrain   → gstack gbrain CLI / MCP (canonical today)
└── backend=brain    → codejunkie99/brain CLI (optional, air-gapped installs)
```

CLI surface (mirrors upstream Brain verbs):

```bash
agentic-stack gbrain query  "..."    # mirrors: agentic-stack brain query
agentic-stack gbrain write  "..."    # mirrors: agentic-stack brain write
agentic-stack gbrain status          # mirrors: agentic-stack brain status
```

Implementation lives in a PT wrapper script or harness_manager plugin patch applied
**outside** `vendor/` (e.g. `scripts/git/agentic-stack-gbrain-shim.py` invoked from PATH).
`vendor/agentic-stack` gitlink bumps do not include this shim.

---

## 6. Gstack + Gbrain + RAG + `.agent/` memory — how they fit

```
┌─────────────────────────────────────────────────────────────────┐
│  Harness (Cursor, Hermes, OpenClaw, Codex, Claude, Antigravity)  │
└────────────────────────────┬────────────────────────────────────┘
                             │ hooks + recall.py / learn.py
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  .agent/memory/  (PT-owned, union-merged)                       │
│  episodic → semantic lessons → DECISIONS / WORKSPACE            │
└────────────┬───────────────────────────────┬────────────────────┘
             │                               │
             │ project-scoped recall          │ explicit @tool / skill
             ▼                               ▼
┌────────────────────────┐    ┌──────────────────────────────────┐
│  orama gstack skill    │    │  Gbrain (pgvector + FTS)         │
│  /investigate /qa …    │───▶│  repo + cross-repo knowledge     │
└────────────────────────┘    └──────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│  v2 RAG plane (doc 20): GossipBus → LanceDB + RRF + embed       │
│  GbrainSearchTool in perpetua-core graph (optional sidecar)     │
└─────────────────────────────────────────────────────────────────┘
```

| Concern | Owner | Retrieval trigger |
|---------|-------|-------------------|
| "What did we decide last session?" | `.agent/memory/` | `recall.py` at task start |
| "What does the indexed codebase know?" | Gbrain | gstack skills, supervisor resolver |
| "What happened in this job's audit trail?" | GossipBus / future RAG | graph MemoryNode (v2) |
| "External long-term Brain store" | codejunkie99/brain | **blocked** until §5.1 |

**Search frugality** (orama openclaw-skills universal protocol) still applies:
gbrain → CRG → Brave → Perplexity → Grok. `.agent/recall.py` runs before web search.

---

## 7. Union-merge rules (runtime, no vendor edits)

When `upgrade --dry-run` shows a changed file that also exists in PT `.agent/`:

| File class | Merge strategy |
|------------|----------------|
| `memory/episodic/*`, `semantic/lessons.jsonl` | **Keep PT** — append-only union; never replace |
| `memory/semantic/LESSONS.md` | **Regenerate** from `lessons.jsonl` via `render_lessons.py` |
| `tools/*.py` | **Keep PT** if customized; port upstream bugfixes manually |
| `skills/*` | Union by skill id; PT triggers win on collision |
| `protocols/*` | Diff; prefer PT permissions if gstack/git-proxy referenced |
| `harness/hooks/*` | Per-adapter review; must not break gbrain recall hooks |
| New upstream-only files | Copy into `.agent/` **only** after dry-run review |

**Never** `git add` inside `vendor/agentic-stack/`. Local patches to upstream belong in
PT scripts (like `ecc-local-additions.patch` pattern) only when absolutely necessary.

---

## 8. orama-system wiring

`start.sh` symlinks `lib/shared/agentic_stack` → `$PT_DIR/vendor/agentic-stack` when
Perpetua-Tools is present. orama does **not** duplicate `.agent/` — it consumes PT's
brain via sibling repo discovery (`PERPETUA_TOOLS_ROOT`, workspace-path-resolution).

Future: optional `scripts/install-agentic-stack.sh` call from `start.sh` after PT
submodule detection (mirror openclaw-skills block).

---

## 9. Acceptance gates

- [ ] `bash scripts/git/install-agentic-stack.sh` exits 0 on clean clone (PT)
- [ ] `upgrade --dry-run` (or `doctor` on older pin) runs before any manual upgrade apply
- [ ] No `brain_bridge.py` from upstream landed without §5.1 review
- [ ] `python3 .agent/tools/recall.py "agentic-stack upgrade"` surfaces graduated lessons
- [ ] All harnesses in §4 still resolve `.agent/AGENTS.md` after adapter install
- [ ] `repo_hygiene.py` passes — no workstation paths in memory exports

---

## 10. Open questions

| # | Question | Default bias |
|---|----------|--------------|
| OQ41.1 | Bump gitlink to v0.18+ for `upgrade` verb now or after gbrain shim? | Bump for `upgrade --dry-run`; keep Brain blocked |
| OQ41.2 | Should `start.sh` call `install-agentic-stack.sh` automatically? | Yes, after PT_DIR resolved (idempotent) |
| OQ41.3 | Single `agentic-stack gbrain` entry point vs separate `gbrain` CLI? | Mirror `brain *` surface for adapter parity |
