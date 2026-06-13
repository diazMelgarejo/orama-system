# Fable 5 Distillation To-Do List

> /autoplan-reviewed 2026-06-13 (Codex + Claude, 6/6 consensus). v1 = offline distiller; v2 = live/stateful infra.
> Live Fable 5 trial runs in Claude Code on Claude Desktop (RAG wired) — that kicks off v2.

## V1 — Offline distillation CLI (approved, ships in days)

- [ ] Add at least one **real** session export to `docs/distill-fable-5/fixtures/` (unblocks everything).
- [ ] Build `bin/orama-system/scripts/distill_session.py` as a **stateless, offline** CLI
      (`--input <export> --dry-run --non-interactive`); no network, no API keys, no PT mutation.
- [ ] Parser behind a `SessionExportParser` interface; one concrete v1 format; unknown formats fail with a clear error.
- [ ] Emit `docs/distill-fable-5/runs/<timestamp>/`: normalized transcript, extracted lessons, **proposed** PT snippets/diffs, verification summary.
- [ ] Call existing `verify_before_done.py` + `capture_lesson.py` via their current CLI; **fail closed** on non-zero (or record explicit skip).
- [ ] Tests: parser-fixture, dry-run structure/snapshot, hook-invocation (mocked), no-network regression, unknown-format rejection.
- [ ] Acceptance: `--input <fixture> --dry-run` exits 0, emits the run dir, creates no router/cache state, needs no cloud creds.

## V2 — Backlog (deferred; each item needs an ADR before build)

> Kickoff: trial live Fable 5 via Claude Code on Claude Desktop, capture a real export → becomes a v1 parser adapter.

- [ ] **Build** `MultiLLMRouter` (greenfield) as a caching/batching **decorator over** existing `worker_registry`/`model_registry` dispatch — in Perpetua-Tools, never a parallel router.
- [ ] Cache correctness/safety: temp-0 + success-only caching, TTL, redaction, key isolation, invalidation.
- [ ] `Perpetua-Tools/config/{models,routing,devices}.yml`: add Fable 5 + fallback chain (Oramasys → LM Studio Win → LM Studio Mac → Ollama) **when providers are live**.
- [ ] `model_registry.py` dynamic thresholding; `cost_guard.py` Fable budget + escalation rules, **default-deny + fail-closed**, keys via Keychain/.env.
- [ ] Eval: minimal output-diff harness on a fixed prompt set first; DeepEval only if needed.
- [ ] `.github/workflows/ci.yml`: SKILL.md/YAML structural validation (pre-commit) — after v1 lands.
- [ ] OSS-pattern emulation (for v2, ADR each): Langfuse traces (additive to `capture_lesson.py`/`LESSONS.md`, methodology only), ClawRouter scoring, Manifest cost-tiering, Helicone proxy-caching.
