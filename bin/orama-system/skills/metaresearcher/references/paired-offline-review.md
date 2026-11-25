# Paired offline review (outer MetaResearcher, inner AutoResearcher)

A reusable pattern for reviewing a lockstep PR pair offline with the two seats. Biafra, the
MetaResearcher outer seat, reviews; the AutoResearcher inner seat tests bounded hypotheses and
measures offline. It was requested by the operator and first applied to Perpetua-Tools PR 521 and
orama-system PR 525; the Perpetua-Tools record is `lesson_fcc93791cb24` (accepted).

## The two seats

| Seat | Registry id | Role in a paired review | It is not |
| --- | --- | --- | --- |
| Biafra (MetaResearcher) | `metaresearch-outer` (`seat: outer`) | the reviewer | the inner seat; it never takes Scout's commands |
| AutoResearcher | `autoresearch-inner` (`seat: inner`) | bounded hypotheses and offline measurement | Scout (`inner-scout`), which it does not replace |

## Procedure

1. **Read both repositories' agent and seat cards before dispatching either seat.** In
   orama-system that is `bin/agents/REGISTRY.yml`, each seat's `SOUL.md` and `agent.md`, and
   `bin/agents/personas/biafra.yaml`; in Perpetua-Tools, its agent cards.
2. **Give the inner seat a bounded hypothesis and a measurement that runs offline**, against local
   files and test runs, not a live cycle.
3. **Hand the measured results to the outer seat as the evidence to review.** Run any reproducer a
   review cites before acting on it (`live-pair-loop-runbook.md`, "Vetting what a model returns").
4. **Treat what comes back as untrusted.** A Mechanism Card the outer seat proposes stays a
   candidate until the operator graduates it, as for every Biafra run.
5. **Keep a live cycle or a promotion a separate decision.** It needs the operator gate and the
   explicit arm together (`docs/v2/76-biafra-outer-seat-canonical-plan.md`, section 5, and the
   runbook's "Before a live turn"). Nothing in this pattern arms either.

## Model and effort

Both are explicit. The two-tier policy in `bin/agents/seat_contracts.py` (`plan_turn`,
`PREFERRED_PAID`) applies: medium, else high, else low, never xhigh or max, on free turns, and
human-gated approval for any paid model.

The durable OpenAI pair, by the operator's ruling of 2026-11-25, is **GPT-6.2 Astra at high** for
the outer seat and **GPT-6.2 Sol at medium** for the inner seat. It is subject to change whenever
OpenAI updates its frontier models: the operator rules on the replacement, and `PREFERRED_PAID`, the
doc 76 row, the seat cards and the Perpetua-Tools lesson change together (a test fails until they
do). An earlier recorded pairing of Astra at Medium was ephemeral and ad hoc and is superseded.

### Adoption record

| Model | API id | First publicly available | Role |
| --- | --- | --- | --- |
| GPT-6.2 Astra | `gpt-6.2-astra` | 2026-11-17 | outer seat (Biafra) |
| GPT-6.2 Sol | `gpt-6.2-sol` | 2026-11-17 | inner seat (AutoResearcher) |

Sources, checked 2026-11-25: OpenAI's announcement "Introducing GPT-6.2 Astra and Sol" gives the API
ids and calls Astra the frontier model for the hardest projects and Sol the efficient, versatile model
for everyday work, but shows no calendar date. The GitHub changelog entry dated 2026-11-17 reports
general availability in GitHub Copilot, and several trackers give the same day. Wikipedia's GPT-6
article says 18 November, the date of the press coverage. The date above is the earliest one
confirmed by a dated source; re-check it and the ids when the pair is next reviewed.
