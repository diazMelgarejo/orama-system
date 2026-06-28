# 18 — Periscope as L4 Glass

> **Date:** 2026-05-24
> **Status:** Design — pending implementation plan in `docs/plans/2026-05-24-periscope-l4-integration-plan.md`
> **Repo:** `diazMelgarejo/periscope` (fork of `latentsignal-org/periscope`, upstream tracks `wesm/agentsview`)
> **Local path:** `~/code/oramasys/tools/periscope` (cloned 2026-05-24, all 3 branches local)

### Branch model (canonical)

| Branch | Role |
|--------|------|
| **`agentsview`** | Grandmother — latest upstream agentsview lineage |
| **`main`** | Tracks **latentsignal-org/periscope** only (upstream mirror; **not** the build target) |
| **`merged`** | **Build branch** — `agentsview` + `main` + fork work; **all fork PRs base here** |

**Cursor agents:** install repo rules once per clone — `bash scripts/periscope/install-cursor-rules.sh`
(from orama-system) → writes `.cursor/rules/openclaw-fork-guide.mdc` in the periscope repo.
Reference: [`docs/reference/periscope-cursor-repo-rules.md`](../reference/periscope-cursor-repo-rules.md).

---

## Mission

> **Make every decision an OpenClaw agent makes legible to a human in real time.**
> If a model picked wrong, if an envelope routed wrong, if a context page truncated wrong — the operator sees it the moment it happens, not in the post-mortem.

Periscope is **L4** in the OpenClaw stack:

```
L1 — AlphaClaw          : edge gateway, request/response transport
L2 — Perpetua-Tools     : middleware, orchestrator contracts, state
L3 — orama-system       : stateless methodology, agent graph, policy
L4 — Periscope          : observability glass, session corpus, guidance  ← THIS DOC
```

Periscope is **not** a replacement for any of L1–L3. It is the read-side reflection layer: it ingests what L1–L3 emit, indexes it, and turns it into something a human can navigate and reason about.

---

## What Periscope already is (2026-05-24 snapshot)

CRG graph: **6 593 nodes / 79 901 edges / 28 communities / 6 032 bge-m3 embeddings** (built today).
Languages by lines: Go 3 311 KB, TypeScript 772 KB, Svelte 644 KB, Rust 47 KB, Python 30 KB, Shell 30 KB, Kotlin 4 KB.

Community map (top 20):

| Community | Nodes | Purpose |
|-----------|------:|---------|
| `frontend/src` (Svelte stores) | 2 027 | Web UI: dashboard, session viewer, context page, timeline, heatmap |
| `internal/parser` | 924 | Per-agent session-log parsers (Claude Code, Cursor, Codex, Gemini, Zed/Zencoder, Cortex, Piebald, forge…) |
| `internal/server` | 795 | Go HTTP API + SSE; routes under `/api/v1/sessions/*` |
| `internal/db` | 600 | SQLite (FTS5) — local session storage |
| `internal/sync` | 314 | Periodic + on-demand session ingest |
| `internal/postgres` | 311 | Optional Postgres backend |
| `cmd/agentsview` | 238 | **Still on old name — see Pending Work § A.1** |
| `internal/signals` | 110 | Session signal detection (truncation risk, context drift) |
| `frontend/e2e` | 96 | Playwright suite |
| `internal/config` | 96 | Config loading |
| `desktop/src-tauri` | 72 | Rust desktop wrapper |
| `internal/summarize` | 63 | LLM session summarization (Phase A) |
| `internal/insight` | 47 | Guidance banners (Phase B) — "continue, rewind, compact, fresh" |
| `internal/importer` | 40 | claude.jsonl + other agent file ingest |
| `internal/update` | 39 | In-app updater |
| `internal/ssh` | 35 | SSH session capture |
| `internal/llm` | 21 | LLM client for summarize + insight |
| `jetbrains-plugin/src` | 15 | Kotlin plugin (scaffold) |

External-facing primitives we can reuse without forking:

- Go HTTP API: `GET /api/v1/sessions`, `GET /api/v1/sessions/{id}/context`, `GET /api/v1/sessions/{id}/context/timeline`, `GET /api/v1/sessions/{id}/messages`, SSE stream `GET /api/v1/sessions/{id}/events`
- CLI: `periscope`, `periscope sync`, `periscope usage daily`, `periscope usage statusline`
- IPC token: `~/.periscope/config.toml` with `cursor_secret` (base64) — already present on this machine
- Local DB: SQLite at `~/.periscope/db.sqlite` (FTS5 indexed)

---

## Why it belongs in OpenClaw

Today, OpenClaw has **no operator glass**. When an orama job fails:

1. Operator opens a terminal.
2. `tail -f` on three log files.
3. `grep` for a correlation ID.
4. Reads the orchestrator state by hand.

Periscope already solves the read-side of this problem for AI coding agents. It has:

- A session corpus (SQLite + FTS5 + optional Postgres)
- A parser plugin for every major coding agent we touch (Claude Code, Cursor, Codex, Gemini)
- A Svelte UI that visualizes context window usage, message timeline, tool calls, and cost
- An LLM-backed summarizer + guidance layer
- A Tauri desktop app + a JetBrains plugin scaffold

What it does **not** have:

- A parser for OpenClaw envelopes
- A parser for AlphaClaw gateway events
- A parser for PT orchestrator state transitions
- A signal that knows about orama's hardware-affinity policy or Sentinel Node alerts
- A view that overlays AlphaClaw routing on top of the session timeline

Those are the integration deltas. None of them require forking periscope — they are parser additions + a small number of new server routes.

---

## Integration shape

Periscope runs as a **sidecar** to the rest of the stack. It reads, never writes back into L1–L3. The data path is one-way:

```
                       ┌────────────────────────┐
                       │  Operator browser/IDE  │
                       └───────────┬────────────┘
                                   │ http://127.0.0.1:8080
                                   ▼
        ┌─────────────────────────────────────────────────┐
        │  Periscope (L4)                                  │
        │   ┌──────────────────────────────────────────┐  │
        │   │  Go server  /api/v1/*                     │  │
        │   │   • sessions, context, timeline, events   │  │
        │   │   • SSE stream                            │  │
        │   └───────────────┬──────────────────────────┘  │
        │                   │                              │
        │   ┌───────────────▼──────────────────────────┐  │
        │   │  Parsers (per-agent)                     │  │
        │   │   claude / cursor / codex / gemini /     │  │
        │   │   openclaw / alphaclaw / pt-orchestrator │  │
        │   │      └─── NEW (this design)              │  │
        │   └───────────────┬──────────────────────────┘  │
        │                   │                              │
        │   ┌───────────────▼──────────────────────────┐  │
        │   │  SQLite + FTS5  (optional Postgres)      │  │
        │   └──────────────────────────────────────────┘  │
        └──────────────▲──────────────────────────────────┘
                       │ tails session files / event logs
        ┌──────────────┴──────────────────────────────────┐
        │  L3 orama-system / L2 PT / L1 AlphaClaw          │
        │  (write their own logs the same way they do      │
        │   today — periscope just learns to read them)    │
        └──────────────────────────────────────────────────┘
```

**Hard invariant:** periscope never writes to AlphaClaw / PT / orama. It is observation-only. The existing data contracts (envelopes, orchestrator state, gateway events) stay where they are.

---

## What we add (and where)

### New parsers — upstream-friendly additions to `internal/parser`

| Parser | Source file pattern | Why |
|--------|--------------------|-----|
| `parser/openclaw.go` | `~/.openclaw/sessions/*.jsonl` | Read OpenClaw envelopes (`request`/`response`/`error`/`heartbeat`) |
| `parser/alphaclaw.go` | `~/.openclaw/state/alphaclaw-events.jsonl` | Read gateway routing decisions, model choices, mirror-policy hits |
| `parser/pt_orchestrator.go` | `Perpetua-Tools/.state/orchestrator-events.jsonl` | Read orchestrator state transitions (route → dispatch → respond) |

Each parser implements periscope's existing `parser.Parser` interface (one file = one parser). Tests live in `internal/parser/*_test.go` next to the parser.

### New signals — additions to `internal/signals`

| Signal | What it watches | When it fires |
|--------|-----------------|---------------|
| `affinity_mismatch` | OpenClaw envelope `target_tier` vs actual backend | When a tier-3 spec lands on a tier-1 backend (D14 mirror policy violation) |
| `mirror_policy_hit` | `lmstudio-mac` mirror exclusion | When orama's `_MIRROR_BACKENDS` selector kicked in |
| `verifier_block` | Crystallization-without-approved-result gate | When PT's verifier gate denied a crystallization |
| `swarm_drift` | Sentinel Node misalignment scores | When 2+ agents disagree on a sub-goal interpretation |
| `context_pressure` | Existing periscope signal + OpenClaw-specific token budgets | When an orama job's per-step budget is near exhausted |

These ride on the existing `internal/signals` plumbing. No schema changes.

### New routes — additions to `internal/server`

Strictly additive:

| Route | Returns |
|-------|---------|
| `GET /api/v1/openclaw/jobs` | List of recent orama jobs (id, branch, status, cost, signal count) |
| `GET /api/v1/openclaw/jobs/{id}` | Job detail: envelope chain, agent decisions, verifier results |
| `GET /api/v1/openclaw/jobs/{id}/signals` | Signals (above) for this job |
| `GET /api/v1/openclaw/topology` | Live LAN topology snapshot: Mac/Win endpoints, model availability |

The Svelte frontend gets one new route group under `frontend/src/routes/openclaw/*` that consumes the above.

### CLI surface

```bash
periscope                          # existing — start server + open UI
periscope openclaw status          # NEW — print orama health (delegates to orama API /healthz)
periscope openclaw watch <job-id>  # NEW — SSE tail of one orama job
periscope usage daily --agent orama   # existing — orama already shows up if envelope parser is loaded
```

No CLI-breaking changes. New commands sit under an `openclaw` subcommand so periscope-without-OpenClaw remains identical.

### Optional: gbrain bridge

If gbrain is configured, periscope can write session summaries (`internal/summarize` output) into the user's `~/.gstack/` brain via a new `internal/bridge/gbrain.go`. This is **off by default** and gated by `~/.periscope/config.toml`:

```toml
[bridge.gbrain]
enabled = false
source = "periscope-src"
emit_summaries = true   # one gbrain page per session summary
emit_signals   = false  # noisy; opt-in
```

Pure addition. Same one-way invariant: periscope writes summaries, never reads gbrain for its UI.

---

## Open questions for brainstorming

| OQ | Question | Default if no answer |
|----|----------|----------------------|
| OQ1 | Live IPC vs file-tail for OpenClaw events? | File-tail (`~/.openclaw/sessions/*.jsonl`) — works with restarts, no race conditions, matches existing parser pattern |
| OQ2 | Single binary `periscope` or separate `periscope-openclaw`? | Single — new parsers + routes are additive, no extra deps |
| OQ3 | Run periscope in `orama-system/start.sh`? | Optional — env var `PERISCOPE_AUTOSTART=1` opts in; default off |
| OQ4 | gbrain source name on first install? | `periscope-src` (matches what we just registered) |
| OQ5 | Carry periscope's PR-tracking back upstream to `latentsignal-org/periscope`? | Yes for parsers (they help all users); no for `internal/server` OpenClaw routes (specific to our stack — keep in fork) |
| OQ6 | Authentication for `/api/v1/openclaw/*` routes? | Reuse existing periscope `cursor_secret` IPC token — no new auth surface |
| OQ7 | Periscope ↔ AlphaClaw direct, or via PT adapter? | Always via PT adapter; AlphaClaw is L1, periscope reads PT's event log not gateway internals (matches "orama talks to AlphaClaw through PT" invariant) |
| OQ8 | JetBrains plugin priority? | Low for now — VS Code + Cursor users dominate; JetBrains plugin stays as a scaffold |
| OQ9 | Postgres backend for periscope when we already have orama LanceDB plans? | Independent — periscope's Postgres is for cross-machine session sync (laptop ↔ desktop). LanceDB is for orama job/decision history. They serve different corpora |
| OQ10 | Periscope IDE plugin auth flow vs SSO? | Token-only (existing `cursor_secret`) — no SSO. Aligns with OpenClaw's local-first posture |

---

## Pending Work registry (as of 2026-05-24)

Two categories — both addressed in the companion implementation plan.

### A. Periscope upstream maintenance (independent of OpenClaw integration)

| # | Item | Branch state | Status |
|---|------|--------------|--------|
| A.1 | Rename `cmd/agentsview/` → `cmd/periscope/` (15 Go files) | Land on **`merged`**; `main` stays upstream mirror | **Open** |
| A.2 | Keep fork build work on **`merged`** (do **not** merge `merged` → `main`) | Rust lib rename, wheel/Docker/CI fixes live on build branch | **Open** |
| A.3 | Cherry-pick or rebase `agentsview` branch updates (5 commits: Piebald support #478, forge agent #476, dep batch #475, Claude subagent linking #459, tool input preview #463) | Tracking upstream `latentsignal-org/periscope` | **Open** |
| A.4 | Deps onto **`merged`** (not `main`); close mistaken main-target PRs | See `scripts/periscope/rebuild-deps-prs-onto-merged.sh` | **In progress** |
| A.5 | Rename `agentsview.io` mentions in README install URLs to `periscope.io` (or equivalent) | Not done — placeholder host | **Open** (depends on domain decision) |
| A.6 | `agentsview` strings in `.air.toml` + `.roborev.toml` (dev tools) | Affects local dev hot-reload | **Open** |

### B. OpenClaw ↔ Periscope integration (this design)

| # | Item | Touches | Status |
|---|------|---------|--------|
| B.1 | OpenClaw envelope parser | `internal/parser/openclaw.go` + tests | Designed, not built |
| B.2 | AlphaClaw event parser | `internal/parser/alphaclaw.go` + tests | Designed, not built |
| B.3 | PT orchestrator event parser | `internal/parser/pt_orchestrator.go` + tests | Designed, not built |
| B.4 | 5 new signals (affinity, mirror, verifier, swarm, context-pressure) | `internal/signals/*.go` + tests | Designed, not built |
| B.5 | `/api/v1/openclaw/*` routes | `internal/server/openclaw.go` + tests | Designed, not built |
| B.6 | `periscope openclaw status` + `watch` CLI | `cmd/periscope/openclaw.go` | Designed, not built |
| B.7 | Svelte route group `/openclaw/jobs/*` | `frontend/src/routes/openclaw/*` | Designed, not built |
| B.8 | Optional gbrain bridge | `internal/bridge/gbrain.go` (opt-in) | Designed, not built |
| B.9 | `PERISCOPE_AUTOSTART` in `orama-system/start.sh` | `start.sh` + `bin/orama-system/scripts/lib/openclaw-env.sh` | Designed, not built |
| B.10 | Add periscope to `CLAUDE-instru.md` registry as L4 | One-line addition | Designed, not built |
| B.11 | `.env` template — `PERISCOPE_URL=http://127.0.0.1:8080`, `PERISCOPE_TOKEN=<read ~/.periscope/config.toml>` | Add to consolidated template | Designed, not built |

---

## Risk register

| Risk | Mitigation |
|------|------------|
| Upstream divergence (we fork further from `latentsignal-org/periscope`) | Parsers go upstream as PRs; OpenClaw-specific routes stay in fork. Periodic `agentsview` branch sync keeps base current |
| Periscope's SQLite schema changes break our parsers | Lock to a periscope tag in `orama-system/install.sh`; pin via `periscope-v0.30.0` style release tag |
| Adding 3 parsers + 5 signals balloons periscope binary size | New parsers are pure Go, no new deps; signals reuse existing plumbing. Expected size delta: < 1 MB |
| Tauri desktop app rebuild churn | We are not modifying desktop/* — the existing Tauri build covers OpenClaw views automatically via the new Svelte routes |
| `cmd/agentsview` rename breaks downstream consumers (e.g. `agentsview.io/install.sh`) | Land the rename on `merged` first, ship a one-version compatibility shim that exposes `agentsview` as an alias for `periscope`, deprecate in next minor |

---

## Decision: scope of v1 integration

Recommendation: **B.1 + B.2 + B.3 + B.5 + B.10 + B.11 only.** That is:

- Three parsers (OpenClaw, AlphaClaw, PT orchestrator)
- One route group (`/api/v1/openclaw/*`)
- Two doc updates (CLAUDE-instru.md, .env template)

This gives a working glass layer with one week of work. Everything else (signals, CLI subcommands, frontend route, gbrain bridge, autostart) is v2 — they polish, not enable.

Independently: do **A.2 (merge `merged` → `main`)** and **A.1 (`cmd/agentsview` → `cmd/periscope` rename)** in their own dedicated PR, since that work is plain upstream maintenance and not gated by integration design.

See `docs/plans/2026-05-24-periscope-l4-integration-plan.md` for the task-by-task plan.

---

## Notes

- Periscope's existing `~/.periscope/config.toml` already carries `cursor_secret = "MFy87WbdbrEO5Xuqu8JdVX3IJ+U8d5pcuESWhU3nmnk="` — the IPC token. We reuse it for the new `/api/v1/openclaw/*` routes via the same middleware.
- `cmd/agentsview/*` rename also affects `install.sh` and `setup_macos.py` once we drop the binary name compatibility shim. Track in plan task A.2.
- gbrain source `periscope-src` is registered and federated as of 2026-05-24. Initial sync: 14 files / 98 chunks / 14 pages embedded.
- CRG graph for periscope: built and embedded today. Stays current via `build_or_update_graph_tool` after each meaningful change.
