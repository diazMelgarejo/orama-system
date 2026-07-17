# Contribution Standards (CONTRIBUTING.md + PR template)

> **Role:** the shared baseline for what a `CONTRIBUTING.md` and pull-request
> template should do across `orama-system` and `Perpetua-Tools`, and how the
> oramasys method's own hard-won practices feed into them.
> **Additive, not a replacement:** never overrides a repository's current,
> more-specific policy (its security policy, branch rules, CI commands). Verify
> the target repo's live guide before adoption.
> **Origin:** synthesized 2026-07-17 from open-source community best practices
> (GitHub Docs on contributor guides and PR templates) augmented by the exact
> review/remediation process refined across the PT PR #205–#246 arc.

---

## The three questions a contributor guide answers

1. How do I report a problem or propose work?
2. How do I submit a reviewable change?
3. What proof and conduct does this project expect?

The PR template turns the review conversation into a durable record: **what
changed, why, how it was tested, and what risk remains.** The goal is durable
understanding proportionate to risk — not more ceremony.

## Durable shared rules

- Keep the guide short, concrete, and easy for GitHub to find
  (`.github/`, repo root, or `docs/`; `.github` wins).
- One PR = one logical change; discuss design-level work before coding it.
- Open unfinished work as a **draft**; request review only when description,
  tests, and risk notes are complete.
- Ask for facts a reviewer can verify, not "follows best practices."
- Every PR-template prompt is a strongly-recommended evidence request, not a
  mandatory self-certification. Add a field only after it prevents a recurring
  review failure; drop one reviewers never use.

## What the oramasys method contributes to these standards

The generic OSS baseline is augmented by practices this method proved under
fire. These are the portable habits — use them by default, defer to a repo's
stricter local rule:

1. **Orient before acting** — search existing decisions, implementations, and
   tests (and `.agent/memory/` lessons) before proposing new work. (Stage 1:
   Context Immersion.)
2. **Make intent visible** — for non-trivial work, state problem, scope,
   assumptions, and the evidence that would show success before changing files.
3. **Preserve useful work** — content overlap is not duplication; classify what
   is duplicate, superseded, complementary, or still uncertain before dropping
   or merging anything. Check derivation direction.
4. **Prove behavior the project's native way** — a focused test or programmatic
   check over "looks right"; a fix found via real usage isn't validated by unit
   tests alone until the real path is exercised and the broken invariant
   re-checked. (Directive #4: Verify First.)
5. **Treat security as a design input** — trust boundaries, validation, secrets,
   authorization, transport, rendering, before review.
6. **Post-review micro-remediation** — cluster review findings by root cause and
   fix the abstraction once; safety-ref before any destructive git op; every
   finding fixed / superseded / documented, never silent. See
   [`post-review-micro-remediation.md`](post-review-micro-remediation.md).
7. **Leave an honest handoff** — record verification, known limits, and explicit
   deferrals so a later human or agent needn't reconstruct the work.
8. **Keep memory writes tool-native** — route `.agent/memory/` changes through
   the memory tooling so referential integrity holds; if you must reconstruct
   by hand, verify the invariant programmatically and say so. (A manual bypass
   is the exact pattern that caused the learn.py evidence-mirror gap.)

## Reference skeletons

Adoption-ready `CONTRIBUTING.md` and `.github/pull_request_template.md`
skeletons live in each repo. `Perpetua-Tools` carries the first concrete
instances (PT PR #247); use them as the pattern, replacing PT-specific links
and commands with the target repo's own. Do **not** copy one repo's
security references, branch rules, or agent procedures into another by
assumption.

## See also

- [`post-review-micro-remediation.md`](post-review-micro-remediation.md) — the review-remediation discipline referenced above
- [`multi-agent-collaboration-protocol.md`](multi-agent-collaboration-protocol.md) — concurrent-branch merge protocol
- `Perpetua-Tools` `CONTRIBUTING.md` + `.github/pull_request_template.md` — the first concrete instances
