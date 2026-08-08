---
name: pt-orama-security-planner
version: 1.0.0
description: >-
  Delegate security queue planning for PT-orama SECURITY.md closure. Activates when
  planning PR3+ security remediation, zero-queue SECURITY.md work, or invoking the
  pt-orama-security-planner Cursor subagent.
compatibility: cursor, claude-code, hermes
allowed-tools: bash, file-operations
triggers:
  - pt-orama-security-planner
  - security pr3 queue
  - security.md zero queue
  - security remediation plan
---

# pt-orama-security-planner

Thin wrapper. Canonical subagent: `.cursor/agents/pt-orama-security-planner.md`.

## Purpose

Route security queue planning through the canonical PT-orama subagent and plan artifacts.

## When to Use

- Planning PR3+ SECURITY.md queue closure
- Delegating security remediation design before implementation

## Before Use

Load canonical skills:

- `bin/orama-system/skills/oramasys-method/SKILL.md`
- `bin/orama-system/skills/hermes-harness/SKILL.md` (pt-orama-harness-integration)

## Invoke

In Cursor, delegate with:

```text
Use the pt-orama-security-planner subagent to plan PR3+ SECURITY.md queue closure.
```

Canonical plan artifact: `docs/plans/2026-06-28-security-pr3-pr6-zero-queue-plan.md`.

Do not copy behavior from this wrapper — read the subagent file.

## Boundaries

### Always Do

- Read the canonical subagent file before delegating.
- Load oramasys-method and hermes-harness context for PT-orama security work.
- Point implementers at the canonical plan artifact under `docs/plans/`.

### Ask First

- Expanding scope beyond the documented PR3–PR6 security queue.
- Editing SECURITY.md closure order without reviewing the zero-queue plan.

### Never Do

- Copy subagent behavior into this wrapper instead of reading the source file.
- Implement security fixes from this card without the canonical plan artifact.
