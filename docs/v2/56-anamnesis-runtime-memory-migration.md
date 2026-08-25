# 56 — Anamnesis Runtime Memory Migration and v1 Controller Contract

> **Status:** v1 controller implementation approved; v2 runtime backend deferred until
> [`oramasys/anamnesis`](https://github.com/oramasys/anamnesis) exists and is explicitly
> provisioned. This is a migration contract, not an Anamnesis implementation.
> **Scope:** preserves PT `.agent` as v1 development-memory authority; introduces no
> runtime service, repository, daemon, or automatic push.

## Decision

In v1, Perpetua-Tools' tracked `.agent/` Agentic-Stack remains the canonical
development and system memory. `capture_lesson.py` is a stable frontend/controller:
it gathers a structured lesson and delegates it to PT's existing `learn.py` pipeline.
It does not write a competing Orama lesson store by default.

In v2, the same frontend may route **runtime** evidence to the tentative
`oramasys/anamnesis` backend. That backend is intentionally absent now. A runtime
capture therefore fails closed with `ORAMASYS_LESSON_E_ANAMNESIS_UNAVAILABLE` rather
than falling back to a tracked or untracked log without operator intent.

This creates a pure internal persistence migration: the user-facing capture and
customization workflow stays stable. No deprecation is announced.

## Current controller contract

| Context | Default backend | Result today |
|---|---|---|
| `--mode development --backend auto` | `pt-agent` | Requires `PERPETUA_TOOLS_ROOT` (or `--pt-root`) and delegates to `.agent/tools/learn.py` |
| `--mode runtime --backend auto` | `anamnesis` | Fails closed until Anamnesis is provisioned |
| `--backend legacy` | legacy Markdown | Explicit standalone compatibility escape hatch only |
| `--review` / `--stats` with PT | PT semantic rendered view | Reads, never creates or mutates memory |

The public flags `--pattern`, `--quick`, `--review`, `--stats`, and `--dir` remain
supported. `--quick` now genuinely gathers only a prevention rule and emits a valid
structured payload. Controller failures have stable, machine-readable error codes and
exit code `3`.

The legacy backend performs an atomic replacement after constructing the complete
file, so an interrupted write cannot leave an incomplete entry. It is never selected
implicitly.

## v2 provisioning contract (deferred implementation)

When Anamnesis exists, runtime memory will be private by default, with a repo-local
gitignored store as the sensible default. Operators may disable capture or deliberately
configure an external path, environment/configured location, or another local provider.
No runtime memory is committed by default.

One user-level OramaSys-wide bundle holds runtime evidence. Entries carry internal
project namespaces/tags so project-specific observations do not become general policy.
Raw evidence is preserved locally. Only sanitized, technical, non-personal patterns
are eligible for promotion.

`ORAMASYS_ALLOW_AUTOMATIC_PUSH` defaults to `false`. An agent may meet configured
pattern thresholds, graduate, and commit a candidate, but it must never push without
human approval unless an operator deliberately overrides that policy.

## Weekly crystallization and contribution

The default cadence is weekly. The promotion run combines PT development lessons with
private runtime evidence, applies both the Orama crystallization formula and PT
`auto_dream` patterns, and creates a sanitized consolidated candidate. Sanitization is
required before a commit and repeated after human approval immediately before any push.

The default commit target is a dedicated PT memory branch/worktree. A local-only
repository target is supported only by deliberate configuration. Candidate upstream
contributions are prepared on a fork branch; pushing them remains HITL-gated.

## Compatibility and acceptance checks

- Development capture delegates to PT `learn.py`; it does not create `tasks/lessons.md`.
- A runtime request without provisioned Anamnesis fails closed and identifies the cause.
- Legacy capture remains available only through `--backend legacy` and is atomic.
- `--quick` produces a complete structured lesson through the selected backend.
- Tests cover backend resolution, PT delegation, runtime fail-closed behavior, legacy
  compatibility, and quick capture.
- The eventual Anamnesis implementation must add configuration, private-store,
  promotion, redaction, and HITL-push tests before becoming the default runtime backend.

## Supersession map

This document partially supersedes only persistence/backend claims in these active
documents; their historical design evidence remains intact:

- [`02-modules/lessons-and-skill-authoring.md`](02-modules/lessons-and-skill-authoring.md)
- [`20-rag-and-memory-design.md`](20-rag-and-memory-design.md)
- [`35-langfuse-trace-tree-pattern.md`](35-langfuse-trace-tree-pattern.md)
- [`41-agentic-stack-gstack-gbrain-memory-blend.md`](41-agentic-stack-gstack-gbrain-memory-blend.md)

Archived plans and historical `LESSONS.md` references remain immutable records. New
work follows this controller contract rather than copying their old direct-append
instructions.
