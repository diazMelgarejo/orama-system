# Golden Path Example

## Input

> "ultrathink this: our nightly gbrain sync keeps failing with
> CONNECTION_CLOSED from the supabase pooler, and I need a
> production-ready fix, not a band-aid."

## Expected Behavior

```text
AFRP: Type C | Level Practitioner | Mode 2
Scope: production-grade fix for a recurring gbrain sync connection failure
```

1. **Search first** — `gbrain search "CONNECTION_CLOSED supabase pooler"`
   before any broad Grep/Read/web call (Step 1, frugality chain).
2. **Context Immersion** — scan the sync script, recent git history around
   it, and any prior lesson entries about pooler behavior.
3. **Visionary Architecture** — propose the fix (e.g. connection retry with
   backoff, or a pooler-mode change); run CIDF `decide()` before any file
   write.
4. **Ruthless Refinement** — cut anything not required to fix the failure
   class, not just today's symptom.
5. **Masterful Execution** — plan → craft with a test that reproduces the
   original failure → verify programmatically (never "looks fixed").
6. **Crystallize** — capture a lesson if the root cause was non-obvious;
   note the assumptions ledger.

## Second Input (PR merge)

> "apply the system to: reconcile two divergent branches — one team
> rewrote the auth module, another added feature flags on top of the old
> version. Get this mergeable."

## Expected Behavior

- Loads `references/integrative-merge.md` before touching the conflict
  (mandatory for any PR/conflict work).
- Classifies the merge mode (additive → union → superset → synthesize →
  architecturally-correct → api-correct) instead of defaulting to
  `--ours`/`--theirs`.
- Simulates first (`git merge --no-commit --no-ff` + `--diff-filter=U` +
  abort) before committing to an approach.
- Synthesizes both branches' intent — the rewritten auth module keeps its
  shape, the feature flags land on top of it — rather than deleting either
  side's work.

## Third Input (ambiguous slash command)

> "/skillify"

## Expected Behavior

```text
AFRP: Type D | Level (undetermined) | Mode (clarify first)
Scope: unclear which of three tools "skillify" refers to
```

- Does **not** classify this as an obvious Type A/C just because a specific
  skill was invoked by name — recognizes that at least three tools answer
  to "skillify" with unrelated jobs (this repo's canonical skill builder,
  gstack's browser-scrape codifier, Anthropic's general-purpose
  `skill-creator` plugin) and that picking wrong means doing the wrong
  *thing entirely*, not just doing the right thing imperfectly.
- Raises an `AskUserQuestion` interrupt offering all three, per
  `oramasys-skillify`'s Workflow step 0 — does not guess from the invoked
  name alone.
- Only proceeds with the 5-stage process once the target is confirmed
  orama-system-scoped.
- See AFRP `failure-modes.md` Failure Mode 6 (Premature Confidence) for
  the failure this avoids.
