# 45 — Single-Operator-LAN Threat-Model Descope (D23)

> **Status:** Decided 2026-07-12 (Perpetua-Tools STM next-increment plan, `/autoplan` CEO+Eng review)
> **Parent:** [`23-security-preconditions.md`](23-security-preconditions.md), [`24-security-first-platform.md`](24-security-first-platform.md), [`31-security-harness-excellence-plan.md`](31-security-harness-excellence-plan.md)
> **PT source:** `Perpetua-Tools/docs/phase-0-specifications/MULTIAGENT-SWARM-SECURITY-ANALYSIS.md` § Addendum, `PATTERN-SYNTHESIS.md` § "GATE on P5/P6/P13"

---

## Decision

**BFT/Sybil-resistant P2P security patterns (witness quorum, reputation-decay scoring, equivocation detection — sourced from Kademlia/PBFT/Bitcoin) should not be wired into production for a topology that is actually a single operator's own small, self-administered LAN, regardless of how many self-owned nodes exist on it.** This is a general principle, not a one-off PT call — it generalizes to any orama/PT/AlphaClaw subsystem that inherited a P2P-derived adversarial threat model without re-deriving it against the actual deployment.

## Why this generalizes beyond StateTransitionManager

The pattern set (P5 witness quorum, P6 reputation-decay, P13 equivocation) was extracted from production P2P systems (BitTorrent DHT, SWIM, Bitcoin/Ethereum BFT) that assume **strangers with economic incentive to attack a quorum they have no stake in**. Applying that threat model requires re-deriving three questions against the *actual* deployment before wiring any such pattern, not assuming the pattern source's premise transfers:

1. **Real witnesses?** Do ≥2 independent, non-collaborating observers actually exist and report in, or is there only ever one observer?
2. **Real trust boundary?** How many distinct *administrative identities* actually control the nodes in question — not node count, but who has credentials/access to how many of them? A quorum spanning N machines under 1 operator's control defends against nothing a compromise of that operator's primary machine doesn't already defeat.
3. **Real observed failure mode?** What does this system's actual incident history show — self-inflicted operational flakiness (crashes, DHCP moves, timeouts) or genuine adversarial behavior (forged identities, contradicting reports)? Zero adversarial incidents across a project's full operational history is decisive evidence, not merely suggestive.

## Case study (concrete instance this decision generalizes from)

Perpetua-Tools' `StateTransitionManager.evaluate_observation()` pipeline (P5/P6/P13-gated) was fully implemented, tested (35/35 passing), and reviewed by a 4-voice CEO review + 5-voice Eng review before this question was asked. All the engineering was sound. The threat-model re-check found:

- Q1: zero real witnesses — the only live code path (`_probe()` in `orchestrator/connectivity.py`) is a single self-observer, not a multi-witness system.
- Q2: the actual trust boundary is 2 machines (Mac + 1 Win RTX3080), 1 operator, 1 administrative identity — not the aspirational 3–100 node table the original threat-model doc described.
- Q3: a full grep of the project's incident log (`docs/LESSONS.md`) found zero adversarial incidents ever — 100% of logged incidents were DHCP reassignment, GPU/process crashes, and network timeouts.

**Verdict: descope.** The patterns were not wrong to design or implement (they remain tested, available code) — they were premature to *wire into production* against a threat that doesn't exist at current scale. This was **not discovered by better engineering** — the implementation was already correct and well-tested. It was discovered by asking the premise question the pattern-extraction methodology itself never re-derived against the actual deployment.

## What does NOT get descoped

Patterns whose value doesn't depend on an adversarial second party remain valid regardless of this decision:
- Monotonic epoch/sequence ordering (P8) — protects against out-of-order application even with zero adversaries.
- Bounded LRU caches / reorder buffers (P9, P18) — protect against memory-growth DoS from ordinary peer churn, not just attackers.
- Distance-metric bucketing (P2) — useful for routing-table hygiene independent of Sybil concerns.
- Durable audit logging (P19) — general forensic value, not contingent on having an adversary to audit.

The distinguishing test: **does this pattern's value require an adversary, or does it also hold under honest-but-flaky operation?** Patterns that fail this test should be checked against Q1–Q3 above before wiring, not assumed necessary because they were in the original pattern-extraction methodology.

## When to revisit

Re-run Q1–Q3 (not just re-check node count) if Fleet Mode, or any future initiative, introduces a **genuine change in trust boundary** — i.e., nodes administered by a different person or organization joining the mesh, not just more self-owned nodes under the same operator. More nodes alone does not retrigger this decision; a new administrative identity does.

## Application to other repos

This decision should inform review of any orama-system or AlphaClaw subsystem that has adopted P2P-derived adversarial patterns (witness quorum, reputation scoring, equivocation/slashing, Sybil-resistance) without an explicit Q1–Q3 check against the actual current deployment. Check [`31-security-harness-excellence-plan.md`](31-security-harness-excellence-plan.md) and [`32-agentic-security-controls.md`](32-agentic-security-controls.md) for candidates the next time either is revisited.

## References

- Full threat-model addendum (Q1/Q2/Q3 detail, incident citations): `Perpetua-Tools/docs/phase-0-specifications/MULTIAGENT-SWARM-SECURITY-ANALYSIS.md` § "Addendum: Single-Operator LAN Premise Check"
- Gate record: `Perpetua-Tools/docs/phase-0-specifications/PATTERN-SYNTHESIS.md` § "GATE on P5/P6/P13"
- Full review chain (4-voice CEO + 5-voice Eng review that surfaced this question): `Perpetua-Tools/docs/phase-0-specifications/2026-07-12-ceo-review-quad-voices/`, `2026-07-12-eng-review-voices/`
- Forward plan and resolution: `Perpetua-Tools/docs/phase-0-specifications/2026-07-12-stm-next-increment-plan.md`
