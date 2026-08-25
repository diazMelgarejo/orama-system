# Module: Lessons + SKILL.md Authoring Tooling

> Status: partially superseded for persistence — see
> [`56-anamnesis-runtime-memory-migration.md`](../56-anamnesis-runtime-memory-migration.md).
> The capture workflow remains; only its backend ownership changes.

## What it does

Ports the existing lessons capture system (`docs/LESSONS.md`, `/self-improve` skill, `scripts/capture_lesson.py`) and SKILL.md authoring toolchain from v1 into the v2 module ecosystem.

## Current state in v1.0 RC

- PT `.agent/memory/` — canonical tracked v1 development memory, shared through PT
- `scripts/capture_lesson.py` — stable frontend/controller; delegates to PT in development
- `orama-system/SKILL.md` + `bin/orama-system/SKILL.md` — the mother skill

## v2 migration

- Lessons format stays structured; PT's Agentic-Stack model is canonical in v1
- Runtime persistence moves only when provisioned Anamnesis exists; it is not implemented here
- `GossipBus` events can auto-trigger lesson capture at graph completion
- SKILL.md authoring moves to a dedicated `oramasys/orama/skills/` namespace
- AFRP gate + CIDF content insertion framework preserved as non-kernel utilities

## TDD note

The lessons system IS part of the TDD policy (per `tdd.md`): every completed graph run should capture one lesson. This module makes that automatic.
