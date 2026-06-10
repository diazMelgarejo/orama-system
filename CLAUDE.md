# orama-system — Claude Code Navigation

> Renamed: ultrathink-system → orama-system (2026-04-20, ὅραμα = "that which is seen / vision / revelation")
> Package: `@diazmelgarejo/orama-system@0.9.9.9`
> GitHub: <https://github.com/diazMelgarejo/orama-system>

---

## § 0 — Active Goal (read this first, every session)

```
GOAL.md is active. Do not skip it.
```

1. **Read [`GOAL.md`](GOAL.md)** at the start of every session — before any
   other work, before reading the mother skill, before any tool call.
2. **Run the § 4.0 baseline scan** from GOAL.md immediately after reading it:
   ```bash
   grep -rn "ultrathink" \
     --include="*.py" --include="*.json" --include="SKILL.md" \
     --include="*.sh" --include="*.toml" \
     bin/ .claude/ .agents/ api_server.py \
     | grep -vi "legacy\|deprecated\|historical\|shim\|alias\|compat\|successor"
   ```
3. **Check which ACs already pass.** Do not redo passing work.
4. **If GOAL.md does not yet say `GOAL COMPLETE`:** pick the highest-leverage
   failing AC, fix it, re-run the full gate. Loop until all 10 ACs are green.
5. **If GOAL.md says `GOAL COMPLETE`:** proceed with the session's primary task.

> This block stays in CLAUDE.md until GOAL.md prints `GOAL COMPLETE — oramasys
> rename consistent, all gates green.` At that point, remove § 0 and delete
> GOAL.md in the same commit.

---

## Meta-rule: Progressive Disclosure (Horse Pulls Cart)

**Documents own content. This file navigates.**

> "The horse pulls the cart, not the other way around."

- When in doubt: read the doc, don't restate it here.
- This file's job is routing + constraints. Docs are the source of truth.
- Skills operationalize docs — they don't copy them.
- Full instructions → [`../CLAUDE-instru.md`](../CLAUDE-instru.md)

---

## § 0 — Architectural Contracts

**Source of truth:** [`docs/2026-05-14--UNIFIED-ABSORPTION-PLAN.md`](docs/2026-05-14--UNIFIED-ABSORPTION-PLAN.md) §§ 0–2.
Read before any structural change. Below is a navigation summary only.

| Topic | Where |
|-------|-------|
| Banned terminology (coordinator → orchestrator, etc.) | [§ 1 / Terminology](docs/2026-05-14--UNIFIED-ABSORPTION-PLAN.md#-1--governing-principles-non-negotiable) |
| 8 governing principles | [§ 1](docs/2026-05-14--UNIFIED-ABSORPTION-PLAN.md#-1--governing-principles-non-negotiable) |
| **Hard requirements** (Mac: Ollama + qwen3.5:9b-nvfp4 + bge-m3; Win: LM Studio) | [§ 2 / Hardware](docs/2026-05-14--UNIFIED-ABSORPTION-PLAN.md) · [`../CLAUDE-instru.md § 6`](../CLAUDE-instru.md) |
| Shared types (all 5 live in PT's `orchestrator/contracts.py`) | [§ 2 / Types](docs/2026-05-14--UNIFIED-ABSORPTION-PLAN.md) |
| Verifier gate (crystallization blocked without approved result) | [§ 2 / Gates](docs/2026-05-14--UNIFIED-ABSORPTION-PLAN.md) |
| V1 scope boundary (MAESTRO/HITL deferred) | [§ 2 / V1](docs/2026-05-14--UNIFIED-ABSORPTION-PLAN.md) |
| HITL accountability classes | [`docs/HUMAN-IN-LOOP-ACCOUNTABILITY.md`](docs/HUMAN-IN-LOOP-ACCOUNTABILITY.md) |
| Search frugality rule (gbrain → CRG → Brave → Perplexity → Grok) | [`bin/orama-system/SKILL.md § Search Policy`](bin/orama-system/SKILL.md) |
| Win coder pool (`$WIN_CODER_ENDPOINTS`, always-utilized) | [`bin/orama-system/SKILL.md § Windows Coder Pool`](bin/orama-system/SKILL.md) |

**Quick invariants (full detail in doc above):**
- `orchestrator` only — never `coordinator` in public APIs, schemas, config, or headings
- PT is runtime/state authority; orama is **stateless** methodology
- **Mac hard requirements:** Ollama running (`localhost:11434`) with `qwen3.5:9b-nvfp4` (inference) + `bge-m3` (embeddings) — system does not start without these
- **Win hard requirement:** LM Studio at `$LM_STUDIO_WIN_ENDPOINTS` — no fallback; fail loudly if unavailable
- **Everything else optional:** LM Studio Mac, cloud APIs, other local models
- One heavy model at a time on Windows GPU
- `@field_validator` (Pydantic V2) — never deprecated `@validator`
- `depth=0` validated server-side; workers cannot spawn sub-workers in V1

---

## § 1 — Continuous Learning

Every session: read [`docs/LESSONS.md`](docs/LESSONS.md) (human-browsable) and [`.claude/lessons/LESSONS.md`](.claude/lessons/LESSONS.md) (ECC canonical) at start; append discoveries before exit.
Instinct path: `.claude/homunculus/instincts/inherited/orama-system-instincts.yaml`
Full spec: [continuous-learning-v2](https://github.com/affaan-m/everything-claude-code/tree/main/skills/continuous-learning-v2)

---

## § 2 — ECC Post-Merge Workflow

After any ECC Tools PR merges:

```bash
git pull origin main
# Then in Claude Code:
/instinct-import .claude/homunculus/instincts/inherited/orama-system-instincts.yaml
/instinct-status
git add -A && git commit -m "chore(ecc): post-merge instinct import sync" && git push origin main
```

Or: `/ecc-sync` (`.claude/commands/ecc-sync.md`)

---

## § 3 — Agent Skills & Mother Skill

Before significant changes, load the mother skill:

```claude
/skill bin/orama-system/SKILL.md
```

| Resource | Purpose |
|----------|---------|
| [`SKILL.md`](SKILL.md) | Agent behavioral rules — every "never" with commands |
| [`bin/orama-system/SKILL.md`](bin/orama-system/SKILL.md) | Mother skill: AFRP gate, CIDF, gstack routing |
| [`docs/how-to/first-run-and-code-review.md`](docs/how-to/first-run-and-code-review.md) | E2E: fresh machine → MCP → graph → code-review skill |
| [`docs/SECURITY-POLICY.md`](docs/SECURITY-POLICY.md) | Canonical security posture (fixes 1–3 done; 4–6 queued) |
| [`docs/reference/agent-first-open-visibility.md`](docs/reference/agent-first-open-visibility.md) | What Cursor / Claude Code / OpenClaw see on first open |
| [`docs/wiki/08-git-hygiene-and-branching.md`](docs/wiki/08-git-hygiene-and-branching.md) § [Official commit identity policy (2026-05-25)](docs/wiki/08-git-hygiene-and-branching.md#official-commit-identity-policy-2026-05-25) | Approved authors, co-author allowlist, `install-local-hooks.sh` |
| [`docs/LESSONS.md`](docs/LESSONS.md) | Chronological session log |
| [`docs/wiki/README.md`](docs/wiki/README.md) | Wiki index — lesson deep-dives |

---

## § 4 — Three-Repo Architecture

```
AlphaClaw (L1 — infra) → Perpetua-Tools (L2 — middleware) → orama-system (L3 — THIS REPO — orchestration)
```

Full architecture: [`docs/2026-05-14--UNIFIED-ABSORPTION-PLAN.md`](docs/2026-05-14--UNIFIED-ABSORPTION-PLAN.md)
Current as-built: [`docs/v2/`](docs/v2/)
Path map (harness/skill locations): see `§ 8` of the archived full CLAUDE.md in [`docs/archive/`](docs/archive/)

**Critical invariants:**
- `start.sh` delegates gateway decisions to PT's `orchestrator/alphaclaw_manager.py` — never add routing logic to `start.sh`
- orama API stays stateless (no Redis)
- orama talks to AlphaClaw through PT's adapter, never directly

---

## § 5 — AutoResearcher

Plugin: `uditgoenka/autoresearch`. Activate per-session: `/autoresearch`.
Read + write [`docs/LESSONS.md`](docs/LESSONS.md) around experiment runs.
Full setup: [`docs/wiki/06-multi-agent-collab.md`](docs/wiki/06-multi-agent-collab.md)

---

## § 6 — Repository Identity & Git Hygiene

- Commit identity: `cyre <Lawrence@cyre.me>`, `cyre <diazMelgarejo@gmail.com>`, or `Codex <codex@openai.com>` — verify with `bash scripts/git/check_identity.sh`
- Official policy (authors + `Co-authored-by` allowlist): [`docs/wiki/08-git-hygiene-and-branching.md`](docs/wiki/08-git-hygiene-and-branching.md#official-commit-identity-policy-2026-05-25) — install hooks with `bash scripts/git/install-local-hooks.sh`
- Dated branches: `yyyy-mm-dd-NNN-brief-summary`
- Never commit `.env`, `.env.local`, generated `.paths`
- **No workstation paths in tracked files** (docs included): use `$OPENCLAW_ROOT`/`~`/`$REPO_ROOT`, never literal `/Users/<name>/…` or the `…/claude/OpenClaw` tree. CI enforces via `scripts/review/repo_hygiene.py` — run it before committing docs with shell commands. See [wiki/08 § Portable paths](docs/wiki/08-git-hygiene-and-branching.md).
- **History was rewritten — judging branches:** NEVER use ahead/behind, `rev-list --count`, or `merge-base` to decide if a branch is orphaned/divergent (meaningless across a rewrite). Run the tree-twin scan `scripts/git/reanchor_scan.sh <repo> origin/main [scope]`. Protocol: [`AGENTS.md` § History-rewrite](AGENTS.md) · method [git-history-surgery SKILL.md](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/git-history-surgery/SKILL.md) · why [LESSONS § 2026-06-05](docs/LESSONS.md).
- **Attribution guards: single source of truth (ZERO fragmentation).** orama `scripts/git/` is canonical for `audit_attribution.sh`, `banned_attribution_lib.sh`, `check_commit_message.sh`, `check_identity.sh`, `daily-attribution-guard.sh` (+ deps). They are **byte-identical in every repo**. NEVER hand-edit a guard in a downstream repo (causes silent drift — e.g. a stale strict-mode allowlist blocking valid pushes). Edit orama's copy, then `bash scripts/git/sync-attribution-guard-scripts.sh <target>`. `daily-attribution-guard.sh` is self-contained (derives `REPO_ROOT`) — never a thin wrapper. Org-wide plan: [`docs/v2/`](docs/v2/).
- Full rules: [`docs/wiki/08-git-hygiene-and-branching.md`](docs/wiki/08-git-hygiene-and-branching.md)

---

## § 7 — gstack

gstack v1.37.0.0 at `~/.claude/skills/gstack` (global-git).

Safety rules:
- ALWAYS use `/browse` for web — NEVER `mcp__claude-in-chrome__*` directly
- `/investigate` for root-cause; `/ship` before any publish

Load routing table + GBrain config:
```
/skill bin/orama-system/gstack/SKILL.md
```

---

## § 8 — Semantic Memory: gbrain + code-review-graph Unified Embeddings

Both gbrain and code-review-graph now use **Ollama bge-m3** (1024-dim, local, free).
`semantic_search_nodes` and `gbrain search` operate in the same vector space.

**Current state (2026-05-24):**
- gbrain: `ollama:bge-m3` (1024-dim) — `~/.gbrain/config.json`, Supabase pgvector — 5 sources (AlphaClaw 478pp, PT 725pp, orama-src 192pp, periscope 14pp, default 1599pp)
- CRG: `openai` provider → Ollama `localhost:11434/v1` — wired via `.mcp.json` — **1 461 nodes, 1 257 bge-m3 embeddings, 12 communities** (orama-system graph)
- Idempotent env setup: `bash bin/orama-system/skills/mcp-install/scripts/setup-embeddings`
- Toggle: `bash bin/orama-system/skills/code-review/scripts/crg-embed-mode [gbrain|local|status]`
- **CRG graph build (MCP-only, not in install chain):** On fresh clone call `build_or_update_graph_tool` then `embed_graph_tool(provider="openai", model="bge-m3")` inside Claude Code
- Reference docs: `bin/orama-system/skills/mcp-install/references/setup-embeddings.md` + `bin/orama-system/skills/code-review/references/crg-embed-mode.md`

**Storage roadmap (decided 2026-05-15):**
- v2.1: LanceDB + bge-m3 for RAG/session memory; v2.5: DuckDB for fleet analytics
- gbrain (pgvector) = codebase index; LanceDB = orama job/decision history — coexist

**Full integration plan:** [`docs/plans/2026-05-19-gbrain-crg-embedding-integration.md`](docs/plans/2026-05-19-gbrain-crg-embedding-integration.md)
See also: [`../CLAUDE-instru.md § 0.5.1`](../CLAUDE-instru.md)

---

## GBrain Search Guidance (configured by /sync-gbrain)
<!-- gstack-gbrain-search-guidance:start -->

GBrain is set up and synced on this machine. The agent should prefer gbrain
over Grep when the question is semantic or when you don't know the exact
identifier yet.

**This worktree is pinned to a worktree-scoped code source** via the
`.gbrain-source` file in the repo root (kubectl-style context). Any
`gbrain code-def`, `code-refs`, `code-callers`, `code-callees`, or `query`
call from anywhere under this worktree routes to that source by default —
no `--source` flag needed. Conductor sibling worktrees of the same repo
each have their own pin and their own indexed pages, so semantic results
match the actual code on disk in this worktree.

Two indexed corpora available via the `gbrain` CLI:
- This worktree's code (auto-pinned via `.gbrain-source` → `orama-src`).
- `~/.gstack/` curated memory (registered as `gstack-brain-lawrencecyremelgarejo` source via
  the existing federation pipeline).

Prefer gbrain when:
- "Where is X handled?" / semantic intent, no exact string yet:
    `gbrain search "<terms>"` or `gbrain query "<question>"`
- "Where is symbol Y defined?" / symbol-based code questions:
    `gbrain code-def <symbol>` or `gbrain code-refs <symbol>`
- "What calls Y?" / "What does Y depend on?":
    `gbrain code-callers <symbol>` / `gbrain code-callees <symbol>`
- "What did we decide last time?" / past plans, retros, learnings:
    `gbrain search "<terms>" --source gstack-brain-lawrencecyremelgarejo`

Grep is still right for known exact strings, regex, multiline patterns, and
file globs. If `gbrain` fails with `getaddrinfo ENOTFOUND` inside a Cursor
agent sandbox, see [`orama-system/docs/local-env-catch-up.md`](orama-system/docs/local-env-catch-up.md)
§ gbrain ENOTFOUND — use CRG MCP (`*_tool` names above) on the host, then scoped Read.
Run `/sync-gbrain` after meaningful code changes; for ongoing
auto-sync across all worktrees, run `gbrain autopilot --install` once per
machine — gbrain's daemon handles incremental refresh on a schedule.

<!-- gstack-gbrain-search-guidance:end -->

---

## § 9 — Parallel Agents & Git Worktrees

**When to create a worktree:** task requires parallel file writes by multiple agents.
**When to stay on canonical:** read-only, sequential, or single-agent work.

| Need | Action |
|------|--------|
| 2+ agents writing simultaneously | `scripts/worktree-bootstrap.sh <repo> <branch> <slug> [gbrain-source]` |
| Done with worktree | invoke `finishing-a-development-branch` skill |
| Query CRG from worktree | pass `repo_root=<canonical-path>` — never rebuild from worktree |

**Location:** `~/Documents/oramasys/worktrees/<slug>/`
**Full doctrine:** `docs/v2/22-worktree-parallel-agents.md`
**Real-time skill:** `~/.claude/skills/using-git-worktrees/SKILL.md`
**Hardware (2026-05-24):** 1 Win RTX3080 + Mac Ollama. All inference via PT dispatch.
