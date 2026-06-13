# Fable 5 Distillation To-Do List

> /autoplan-reviewed 2026-06-13 (Codex + Claude, 6/6 consensus). v1 = offline distiller; v2 = live/stateful infra.
> Live Fable 5 trial runs in Claude Code on Claude Desktop (RAG wired) — that kicks off v2.

## V1 — Offline distillation CLI (approved, ships in days)

- [x] Add at least one **real** session export to `docs/distill-fable-5/fixtures/` (unblocks everything).
      → `fixtures/sample_session.json` (orama-session-export-v1 format, synthetic, committed).
- [x] Build `bin/orama-system/scripts/distill_session.py` as a **stateless, offline** CLI
      (`--input <export> --dry-run --non-interactive --output-dir`); no network, no API keys, no PT mutation.
- [x] Parser behind a `SessionExportParser` interface; `OramaSessionExportV1Parser` + `GenericJsonTranscriptParser`; unknown formats exit 2 with documented error.
- [x] Emit `docs/distill-fable-5/runs/<timestamp>/`: normalized transcript, extracted lessons, **proposed** PT snippets/diffs, verification summary, MODELS_PERFORMANCE_DELTA.md.
- [x] Call existing `verify_before_done.py` (`--no-interact`) + `capture_lesson.py` (`--review`) via their current CLI; **fail closed** on non-zero.
- [x] Tests: `tests/test_distill_session.py` already exists with 7 tests covering all acceptance criteria (RED until distill_session.py shipped).
- [x] Harmonize `docs/distill-fable-5/implementation-plan.md`: frugal emulation principle, 13-tool catalog grouped (Group A v1 / Group B v2 / 9 deferred), 3 success metrics, corrected MultiLLMRouter framing + Grok model IDs, ADR cross-links.
- [ ] **[USER ACTION]** Run `pytest tests/test_distill_session.py -v` to verify acceptance (tests go GREEN → v1 DONE).

## V2 — Backlog (ADR-gated; kickoff is IMMEDIATELY available)

> **Kickoff NOW:** Group A tools (Claude Chat Exporter, AI Distiller, Claude Pre-commit, Pre-commit Framework)
> are built INTO Claude — usable with actual Fable 5 runs today. Export a real Fable 5 session via
> Claude Chat Exporter → run `distill_session.py --input <export>` → discover the actual schema →
> `FableExportParser` adapter (first item below). No separate "Claude Desktop trial" gate required.

- [ ] **FableExportParser** — add a `SessionExportParser` subclass for the actual Fable 5 export format (discovered by running Claude Chat Exporter on a real session and passing to `distill_session.py`). Drop-in: append to `_PARSERS` in `distill_session.py`, no other changes.
- [ ] **Build** `MultiLLMRouter` (greenfield) as a caching/batching **decorator over** existing `worker_registry`/`model_registry` dispatch — in Perpetua-Tools, never a parallel router. Target path: `perpetua.core.multi_llm_router` (v2 package; Grok's AntiGravity reference). Seam: `OrchestrationSupervisor._dispatch` at `orchestrator/supervisor.py:534`. Anthropic leg: `anthropic.AsyncAnthropic()` (NOT OpenAI-compatible endpoint).
- [ ] Cache correctness/safety: temp-0 + success-only caching, TTL, redaction, key isolation, invalidation.
- [ ] `Perpetua-Tools/config/{models,routing,devices}.yml`: add Fable 5 + fallback chain (Oramasys → LM Studio Win → LM Studio Mac → Ollama) **when providers are live**.
- [ ] `model_registry.py` dynamic thresholding; `cost_guard.py` Fable budget + escalation rules, **default-deny + fail-closed**, keys via Keychain/.env.
- [ ] Eval: minimal output-diff harness on a fixed prompt set first; DeepEval only if needed.
- [ ] `.github/workflows/ci.yml`: SKILL.md/YAML structural validation (pre-commit) — after v1 lands.
- [ ] OSS Group B emulation (ADR each): [1] Langfuse traces (additive to `capture_lesson.py`/`LESSONS.md`, methodology only), [4] ClawRouter scoring, [3] Manifest cost-tiering, [2] Helicone proxy-caching.
- [ ] OSS Group deferred (ADR or cut before any build): [5] NadirRouter, [7] Claude Artifact Unpacker, [9] DeepEval, [10] Agent-Distillation, [13] Cozeloop.
- [ ] **[PROBE 2026-06-14 05:00]** Verify Win coder (`$LM_STUDIO_WIN_ENDPOINTS`) is online → update delegation plan; see `$OPENCLAW_ROOT/agy-gemini.md` for AgentRouter config.
- [ ] **ADR-030** (next free): `MultiLLMRouter` caching/batching decorator — write and approve before any v2 build starts.
