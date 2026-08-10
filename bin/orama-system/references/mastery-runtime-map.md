# ORAMASYS Mastery v3 — v1 Runtime Ownership Map

> Purpose: point to the canonical v1 runtime home for each mastery meta-layer.
> This file is an index, not a second copy of the mastery prose.
>
> Human-facing unified reference:
> [`../../../docs/v2/references/ORAMASYS-MASTERY-v3.md`](../../../docs/v2/references/ORAMASYS-MASTERY-v3.md)

## Ownership

| Layer | Canonical v1 runtime home | Contract |
|---|---|---|
| M1 Spec Contract | [`../SKILL.md`](../SKILL.md) — `Pre-Flight: Spec Contract` | Establish role, goal, constraints before AFRP |
| M2 Amplifier Objective Tree | [`../SKILL.md`](../SKILL.md) + [`amplifier-principle.md`](amplifier-principle.md) | Resolve explicit, hidden, and system objectives |
| M3 Collaborative Reasoning Safety | [`collaborative-reasoning-safety.md`](collaborative-reasoning-safety.md) | Builder/Critic/Adversary/Judge, anti-groupthink, confidence tracking |
| M4 Output Discipline | [`../SKILL.md`](../SKILL.md) — Stage 5 `Output shape` | Six-section substantial-deliverable contract |
| M5 Lessons Architecture | [`../../../docs/LESSONS.md`](../../../docs/LESSONS.md) + `scripts/capture_lesson.py` | Corrections become durable, reviewable learning without duplicating lessons in the mother skill |
| M6 Communication Guidelines | [`communication-guidelines.md`](communication-guidelines.md) | Runtime-forward writing guidance; not retroactive rewrite law |

## Zero-duplication rule

- The mother skill carries only the operational stubs needed in the execution path.
- M3 and M6 live in their dedicated references.
- M5 lesson content remains in the lessons architecture; the mother skill only invokes the loop.
- The human mastery document remains the unified explanatory reference.
- Do not paste the full M3/M5/M6 prose into `bin/orama-system/SKILL.md`.

## P3 boundary

This v1 convergence work must not create the v2 repository scaffold or the §5c v2-only skills.
The executable convergence gate checks representative P3 sentinel paths and fails if this PR creates them.

## Verification

Run:

```bash
python3 scripts/verify_mastery_convergence.py
```

The verifier checks canonical ownership, required semantics, thin-wrapper status, and the P3 no-touch boundary.
