# Anti-Patterns

## Skipping the AFRP Gate

Problem: jumping straight into a 5-stage build for a request that's
actually Type A (simple lookup), or worse, skipping classification
entirely on a genuinely complex Type C request and improvising instead.

Fix: state `AFRP: Type [A/B/C/D] | Level [...] | Mode [1/2/3]` before any
stage or tool call, every time, for any non-trivial task.

## Parallel-Firing Every Search Tool

Problem: calling gbrain, CRG, Brave, and Perplexity all at once "to be
thorough."

Fix: follow the frugality chain in
[`../search-frugality.md`](../references/search-frugality.md) — stop at
the first tool that answers.

## Trusting Visual Confirmation

Problem: marking Stage 4 complete because the output "looks right" in a
preview, without a programmatic check.

Fix: verify programmatically per Step 4 — re-read the artifact, check the
signature, run tests.

## Wholesale `--ours` / `--theirs` on a PR Conflict

Problem: resolving a merge conflict by picking one branch's version
entirely, silently deleting the other branch's working content.

Fix: classify the merge mode first via
[`../integrative-merge.md`](../references/integrative-merge.md); synthesize,
never amputate.

## Assuming Which Tool a Same-Named Slash Command Means

Problem: seeing `/skillify` (or "make me a skill") invoked and assuming it
obviously means this repo's own skill builder, when the same name/phrase
also legitimately routes to gstack's unrelated `/skillify` (codifies a
browser scrape) or Anthropic's official `skill-creator` plugin
(general-purpose, outside this repo's conventions). Classifying this as
Type A/C ("obviously this repo's tool") instead of Type D hides real
ambiguity behind a confident-looking invocation.

Fix: treat a same-named tool collision as Type D until the target is
confirmed — `oramasys-skillify`'s Workflow step 0 AskUserQuestion interrupt,
not a guess from the invocation name alone. See AFRP `failure-modes.md`
Failure Mode 6 (Premature Confidence).

## Hardcoding Local Endpoints or Secrets

Problem: pasting a literal LAN IP, workstation path, or credential into a
plan, lesson, or generated artifact "just this once."

Fix: use the env var / registry indirection this repo already has
(`$WIN_CODER_ENDPOINTS`, `$OMNIROUTE_TOKEN`, the portable-memory
local-topology invariant in `docs/v2/47-portable-memory-local-topology-invariant.md`)
— tracked files name categories, concrete values live outside git.
