# 35 — Langfuse Trace-Tree Pattern: Additive Extension of `capture_lesson.py`

> **Canonical home:** `orama-system/docs/v2/35-langfuse-trace-tree-pattern.md`
> **Status:** Proposed — approve before any implementation
> **Locks decision:** D18

---

## 1. Context

Langfuse is an OSS observability platform for LLM applications. Its core contribution
is a **trace-tree model**: each session becomes a root trace with nested spans
(generation, retrieval, evaluation), timestamped and tagged with metadata like
model, cost, latency, input/output token counts.

`capture_lesson.py` and `LESSONS.md` already capture session learnings as flat
chronological entries. They have no hierarchy, no per-span timing, no cost
attribution, and no structured query path.

The v2 distillation plan (Group B, item [1]) says: emulate the Langfuse
**trace-tree pattern** as an additive extension of the existing lesson/LESSONS
machinery — methodology only, never a Langfuse installation, never runtime state.

---

## 2. Decision (D18)

**What to build:** A structured trace annotation layer on top of `capture_lesson.py`
and `LESSONS.md` that adds optional hierarchical context — root trace → child spans
— to existing flat lesson entries. Pure orama methodology (L3). No new service,
no Langfuse dependency, no runtime state in PT (L2).

**What it is NOT:**
- Not a Langfuse installation or SDK wrapper.
- Not a new service or daemon.
- Not runtime state (no Redis, no DB, no PT changes).
- Not a replacement for `capture_lesson.py` — strictly additive.
- Not fatal to the calling session: trace annotation is **best-effort**. If `trace_session.py` fails (file write error, schema validation error, missing gitignore), it emits a `WARNING` to stderr but does **not** raise or block the caller. A non-zero exit from `trace_session.py` is a warning condition only.
- Not implementable before D17 is approved: the trace schema receives route-context from the D17 §3.7 route-provenance stripping normalization (`:607` return). **D18 implementation is blocked until D17 is approved.**

**Form:** A thin wrapper / helper (`orama-system/bin/orama-system/scripts/trace_session.py`)
that produces structured JSONL trace records alongside existing LESSONS.md entries.
The trace records are human-readable and machine-parseable; they feed `distill_session.py`
as richer input for pattern extraction.

---

## 3. Trace schema

```jsonl
{"trace_id": "<uuid>", "session_id": "<slug>", "root": true, "ts_start": "<iso>", "ts_end": "<iso>", "model": "<id>", "tags": [...]}
{"trace_id": "<uuid>", "parent_id": "<root_uuid>", "span": "generation", "label": "<step>", "ts_start": "...", "ts_end": "...", "model": "<id>"}
{"trace_id": "<uuid>", "parent_id": "<root_uuid>", "span": "lesson", "label": "<category>", "body": "<lesson text>", "lesson_id": "<capture_lesson ref>"}
```

> **L2/L3 boundary — token/cost data lives in PT (L2), not in orama traces:** `tokens_in`,
> `tokens_out`, and `cost_usd` are **excluded** from this L3 trace schema. orama (L3) cannot
> self-compute these values — they come from provider responses that L3 never sees.
>
> **Where the data lives (D17 + D20):** D17's decorator extracts provider-reported usage
> from the real `_inner` result and calls `CostGuard.record_spend(model_id, tokens_in,
> tokens_out, cost_usd)` (D20). This is the canonical home for token/cost data in PT (L2).
>
> **v2.1 path (future ADR):** If trace spans need token/cost annotation, PT L2 may forward
> the recorded values to `trace_session.py` as optional caller-supplied metadata after each
> dispatch — orama stores what L2 gives it, never computes it. This requires its own ADR.

Output location: `docs/distill-fable-5/traces/<session-slug>.jsonl`.

> **REQUIRED pre-condition:** `.gitignore` entries `docs/distill-fable-5/traces/` and `docs/distill-fable-5/runs/` **MUST be committed** before this implementation begins and before any trace file is written. This is a correctness requirement, not a recommendation — trace files may contain session prompt content. Verify with `git check-ignore -v docs/distill-fable-5/traces/` before the first `trace_session.py` invocation.

---

## 4. Integration points

| Existing hook | Change |
|--------------|--------|
| `capture_lesson.py --review` | `capture_lesson.py` emits **Markdown** to `LESSONS.md` — not JSON. A `trace_id` field **cannot** be injected into a Markdown template. Instead, `trace_session.py` writes a companion `lesson_ref` span entry in the JSONL trace file that records the session slug and timestamp, enabling correlation without mutating `LESSONS.md` or `capture_lesson.py`. |
| `distill_session.py --input` | Accepts optional `--trace <file.jsonl>`; enriches extracted lessons with span context |
| `LESSONS.md` | No change — flat chronological format preserved; trace file is a companion, not a replacement |

---

## 5. What stays in orama (L3) vs PT (L2)

| Layer | What lives there |
|-------|-----------------|
| orama (L3) | `trace_session.py`, trace JSONL files, `distill_session.py` trace enrichment |
| PT (L2) | Nothing — L2 has no visibility into trace files |

The L3/L2 boundary is absolute: orama produces trace records for methodology
purposes; PT never reads or writes them.

---

## 6. Alternatives rejected

| Alternative | Why rejected |
|-------------|-------------|
| Install Langfuse (self-hosted) | Adds a service dependency; violates "emulation not importation" |
| Use OpenTelemetry spans | OTEL is for distributed systems tracing; overkill for a single-machine methodology tool |
| Extend LESSONS.md with nested structure | Breaks existing flat format; harder to parse |
| Embed trace data in `capture_lesson.py` output | Conflates lessons (human-readable) with trace data (machine-structured) |

---

## 7. Consequences

**Positive:**
- `distill_session.py` gains per-span cost and latency context → better proposals.
- Session replay is possible **within a single completed session**: reconstruct what happened from trace + lessons for post-session analysis. Trace files are **ephemeral and machine-local** — not designed for cross-session aggregation or cross-machine durability in v2 (v3 concern). Do not treat trace files as a durable budget ledger or a cross-session audit record.
- Zero new dependencies; zero runtime risk; no PT changes.

**Negative / constraints:**
- Trace files are session-local; no cross-session aggregation in v2 (v3 concern).
- Cost attribution requires callers to emit token counts — not auto-instrumented.

---

## 8. Open questions

- **Q1:** Should `trace_session.py` be a CLI or a library imported by `distill_session.py`?
  Recommend: CLI first (consistent with existing scripts), importable in v2.1.
- **Q2:** Gitignore traces by default or commit them? Recommend: gitignore by default
  with explicit `--commit-trace` flag for audit sessions.

---

## 9. Locked decision

**D18 — Langfuse trace-tree is a methodology annotation layer in orama, not a service (2026-06-17)**

orama emulates Langfuse's trace-tree pattern as an additive JSONL annotation layer
(`trace_session.py`) alongside existing `capture_lesson.py`/`LESSONS.md`. Never
a Langfuse installation, never runtime state, never a PT change. Gate doc: this file.

---

## 10. Cross-references

- D17: `30-multi-llm-router-caching-batching-decorator.md` (the L2 router that produces token/cost data trace_session.py consumes)
- `docs/distill-fable-5/implementation-plan.md` — Group B [1]
- `bin/orama-system/scripts/capture_lesson.py` — existing lesson hook (additive integration point)
- `bin/orama-system/scripts/distill_session.py` — primary consumer of trace enrichment
