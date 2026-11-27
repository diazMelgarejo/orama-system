# Remediation Batch Dependency Order & Review Rules

**Canonical Card:** `bin/orama-system/references/remediation-batch-dependency-and-review-rules.md`  
**Related Doctrine:**

- [`post-review-micro-remediation.md`](post-review-micro-remediation.md)
- [`remediation-exemplar-cross-system-bounds-and-fencing.md`](remediation-exemplar-cross-system-bounds-and-fencing.md)
- [`branch-local-pattern-remediation.md`](branch-local-pattern-remediation.md)

---

## 1. Empirical Rules from Prior Pair Remediation Cycles (2026-11-17)

- **Reproduce every finding before fixing it, and expect the reason to differ.**
  Rolling back a committed reservation raised `UnknownReservationError`, which is what made one
  double-release finding real; a NUL byte in an argv failed only after the one-attempt marker was
  claimed. A fix written from the comment alone would have missed the actual defect.
- **Saved harness drivers and run copies are evidence, not code to keep current.**
  Do not rewrite them to satisfy a review. Document the known limit in a README beside them (for
  example "predates the mandatory spend guard") and answer the comment with an evidence-backed
  decline that points at that note.

---

## 2. Rules from the Review of the Review

- **A claim must name its enforcer.**
  For every sentence that says "refuses", "forces", "only X writes", or "never", find the line
  that enforces it and say which entry point does. If the check lives in the command and not the
  guard, or in the live path and not the dry path, say so. Bot reviewers keep threads open until
  the sentence matches the mechanical code path.
- **A new default location needs a neutralizing fixture.**
  When a resolver gains a fallback (such as a CI checkout), every test that asserts "nothing
  found" must neutralize it in the shared fixture, and one test must prove the fallback is used.
  CI has the location and a local laptop does not, so failure shows only in CI: create the
  location locally and run the suite before pushing.
- **Account for every path, then check the claims.**
  Release a reservation only when the process never launched. After launch, settle it; if
  settlement fails, retain the reservation as liability until reconciliation. Process-group
  cleanup and operations that can fail between acquisition and completion (claiming a marker,
  writing a ledger) belong inside the cleanup block.

---

## 3. Dependency Order of a Remediation Batch (2026-11-25)

Build the task list from what each step needs, not from the order the requests arrived in. A batch
that touches research, docs, memory, commits, and a push has one workable linear order:

1. **Independent reads first, in parallel:** Research (a model's release date, an upstream document)
   and diagnosis (why a pull request shows a merge conflict, what a failing check actually says)
   need nothing from each other, so run them together before any edits.
2. **Research feeds the docs and the code:** Record a fact only after its source is read, with the
   source and the date it was checked. When the best source carries no date, say so and name the one
   that does.
3. **Docs and memory feed the commits:** A commit message cites the doc and the lesson, so write and
   verify them first, then commit in logical batches. Tests come before the docs they prove.
4. **Restack in order before pushing:** The base pull request first, then each stacked branch on
   the previous tip, so the chain remains strictly linear.
5. **One push per repository comes last:** With every ref in a single command. Review replies and
   pull-request-body follow-ups cite pushed SHAs, so they follow the push; the body follow-up also
   requires the operator's explicit grant.
