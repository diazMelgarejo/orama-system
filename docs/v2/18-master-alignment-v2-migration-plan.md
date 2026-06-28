# 18 — Master Alignment & v2 Migration Plan

**Date:** 2026-05-20
**Context:** Analysis of `docs/superpowers/specs/2026-05-20-cc-openclaw-master-alignment-design.md` vs. the new v2 microkernel in `~/code/oramasys/` (`oramasys`, `perpetua-core`, `agate`).

> **Cross-repo canonical (2026-06-01).** The active tri-repo (AlphaClaw → PT → orama) migration
> resume anchor is **[`Perpetua-Tools/docs/2026-05-31-tri-repo-alignment-completion-plan.md`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/2026-05-31-tri-repo-alignment-completion-plan.md)**
> — the combined A+B canonical plan (single-yardstick goal + locked decisions **D1–D5** + **SSEA**
> gates + v2.0 multi-agent write-orchestration). That doc governs the live v1 `diazMelgarejo/*`
> migration; this v2 doc is the forward-looking L3 microkernel design (`oramasys`/`perpetua-core`/`agate`).
> ⚠ **Active blocker:** PT `main` is being churned to detached HEAD by a concurrent Cursor agent —
> land PT edits via the GitHub API and confirm a stable checkout before any Gate-2 code work.

## 1. Alignment Sanity & Efficiency Check

Using `gbrain query` and directory analysis, the master alignment design was checked against the 3 new repos.

**Findings (Misalignment Detected):**
- **Architecture Mismatch:** The design spec assumes a v1 `orama-system` structure (e.g., `orchestrator/contracts.py`, `orchestrator/supervisor.py`, `orchestrator/spawn_reconciliation.py`). The new v2 system (`oramasys/oramasys/orama`) uses a clean-slate `api/` and `graph/` structure.
- **Skill Submodule Pathing:** The spec forces a git submodule at `bin/orama-system/skills/openclaw-skills/cc-openclaw`. In v2, `bin/` is largely deprecated in favor of proper Python modules or dedicated plugin boundaries in `oramasys/plugins/`.
- **Spawning Gate:** Modifying `spawn_reconciliation.py` is a v1 hack. In v2, this should be a core capability of the graph's dispatch node.

**Conclusion:** The design is highly effective for stabilizing v1, but executing it verbatim on the new 3 repos is impossible because the targeted v1 orchestrator files do not exist there.

## 2. Prevailing Conventions: Mining for v2

We will NEVER adopt the full frameworks below, but we will mine them to implement the `cc-openclaw` master alignment in v2 elegantly:

- **Pydantic AI Slim:** We will extract its `@tool` decorator logic to handle `openclaw-skills`. Instead of raw bash scripts and manual manifest parsing (Layer 1), skills can be parsed and validated with Pydantic typing before execution.
- **LangGraph:** We will extract their state checkpointing concept. The "Windows coder always-utilized policy" requires knowing agent states; a durable graph checkpointer ensures we can pause a task, route it to an idle Windows coder, and resume it without losing state.
- **CrewAI / AutoGen:** We will extract their multi-agent orchestration/handoff patterns. The "Search frugality" rules (Gbrain → Brave → Perplexity → Grok) can be modeled as specialized agents handing off to each other within the v2 kernel, avoiding massive parallel API calls.

## 3. Implementation Plan for v2 Merging (Future Work)

We are in the **PLAN stage**. We will not write to the 3 new repos yet.

**Step A: Re-target the Submodule (`cc-openclaw`)**
- Instead of adding the submodule to `bin/orama-system/skills/`, map it to `oramasys/orama/plugins/openclaw-skills/`.
- Wrap the raw skills using the mined **Pydantic AI Slim** extraction logic so `oramasys` understands them as typed graph tools natively.

**Step B: Enforce Frugality and Hardware Policies via Graph Routing**
- Implement the **Windows Coder Pool** policy not via a raw shell environment variable, but as a routing constraint in `oramasys/orama/graph/dispatch.py`. 
- Incorporate **LangGraph-style** checkpointing so tasks dispatched to `$WIN_CODER_ENDPOINTS` can safely suspend and resume.
- Implement the **Search Frugality Rule** as a sequential subgraph (try Gbrain node → if empty, route to Brave node → etc.), extracting patterns from **CrewAI** sequential routing.

**Step C: Compliance Audit Automation**
- Migrate the SKILL.md compliance audit into a Python pre-commit hook or CI step inside `perpetua-core` or `oramasys`, replacing the manual `grep` checks from v1.

**Next Steps:** Continue researching `oramasys` module boundaries to map exactly where the Two-Layer Architecture fits without polluting the v2 microkernel.
