<!-- lint-ignore LINT-013 -->
# 57 — MiniGraph Kimi Reconciliation: Findings for `oramasys/perpetua-core`

> **Repository standard:** everything executable lives under `/src`; no
> root-level `scripts`/`tests`/`tools`/`examples`; data output and produced
> binaries stay `.gitignore`d, never committed with secrets, personal paths,
> or SecOps material. Additive — see
> [`46-repository-standard.md`](46-repository-standard.md).
> **Status:** reference doc — findings only, no code changes here. The
> actual `oramasys/perpetua-core` changes happen from Claude Code CLI, not
> from this session (org-level token access is blocked here — see §0).
> **Corrects a real mistake made mid-session:** work was done against
> `diazMelgarejo/perpetua-core`, believing it canonical. It is not — see
> `15-phase1-as-built.md`'s own language calling it "the divergent
> wrong-repo." The canonical kernel is `oramasys/perpetua-core`, commit
> `2f717f5` as of the 2026-05-01 as-built snapshot, with further RC-1 work
> on 2026-05-17/18. This doc's findings should be checked against
> whatever `oramasys/perpetua-core`'s *current* `engine.py` actually
> contains, not assumed from that snapshot.

---

## 0. Why this doc exists instead of a direct PR

This session's token cannot reach the `oramasys` GitHub org at all —
`GET /orgs/oramasys/repos` returns a 403 with GitHub's own message: *"The
'oramasys' organization forbids access via a fine-grained personal access
token if the token's lifetime is greater than 366 days."* Confirmed
directly, not assumed. No clone, no read, no push access. Per direct
instruction, the actual `oramasys/perpetua-core` change lands from Claude
Code CLI instead; this doc is what that session needs to apply it precisely.

---

## 1. What was actually verified, and against what

Three turns of this same investigation built and behaviorally tested a
parallel `perpetua_core.graph.MiniGraph` implementation — never merged into
any real repo, kept as a standalone artifact for exactly this purpose: to
surface real, reproducible bugs and a real design proposal, worded
precisely enough to check against the actual canonical file rather than
guessed at.

**Important honesty check, done before writing this doc, not skipped:**
`docs/v2/06-open-questions.md` and `15-phase1-as-built.md` both confirm
OQ12 (the `max_steps` safety guard) was **already resolved on 2026-05-17**
— `engine.ainvoke` raises on overflow, covered by
`tests/graph/test_engine_max_steps.py`. This doc does **not** claim to be
filling an open gap. What follows is a specific, reproducible *semantic*
bug pattern — worth checking against the existing guard's precise
behavior, not assumed to already be present or already be absent.

## 2. Finding 1 — `max_steps` guard: check for this specific semantic bug

**The bug pattern, reproduced against my own parallel kernel (not
`oramasys/perpetua-core` directly, since it couldn't be reached):** a
guard that increments the step counter *then* checks it, and reports
"the node about to be attempted" as the failure's `last_node`, gives a
wrong answer for anything except a 1-node self-loop.

```python
# BUGGY pattern -- looks correct on a 1-node self-loop test, silently
# wrong on anything else:
while node != END:
    steps += 1
    if steps > max_steps:
        raise MaxStepsExceeded(steps, node)  # `node` here was never entered
    ...
```

Reproduced with a 2-node alternating cycle (`a -> b -> a -> b...`,
`max_steps=3`): this pattern reports `steps=4, last_node='b'` — a node
that never actually ran in the failing attempt, and a count one higher
than what was requested. A 1-node self-loop test cannot catch this,
because "the node about to be attempted" and "the last node that
completed" happen to be the same name in that specific case.

**The fix**, verified against the reproduction above:

```python
# CORRECT: check before incrementing; track last_node separately,
# updated only on successful entry into a node.
steps = 0
last_node = START
while node != END:
    if steps >= max_steps:
        raise MaxStepsExceeded(steps, last_node)
    current = node
    ...  # execute current
    last_node = current
    steps += 1
    node = _next(current, state)
```

**Action for the CLI session:** read `oramasys/perpetua-core`'s actual
current `graph/engine.py` and `tests/graph/test_engine_max_steps.py`.
If the existing test only exercises a 1-node self-loop (matching the
gap this finding describes), add a 2-node alternating-cycle test case
using the reproduction above before deciding whether the existing guard
needs the fix — it may already be correct; this doc cannot confirm
either way without read access.

## 3. Finding 2 — non-dict node returns

Verified against my parallel kernel: `state.merge(result or {})` silently
turns a node returning `None` into an empty delta — a node with a missing
`return` statement appears to succeed rather than surfacing as a bug.

**Fix, verified:**

```python
if not isinstance(result, dict):
    raise TypeError(f"node {current!r} returned {type(result).__name__}; expected dict delta")
state = state.merge(result)
```

An explicitly-returned `{}` ("no changes") still correctly passes this
check — only non-dict returns are rejected.

**Action for the CLI session:** check whether `oramasys/perpetua-core`'s
`engine.py` already validates node-return types. If not, this is a small,
low-risk addition; the pattern above is copy-pasteable.

## 4. Finding 3 — empty/non-string edge routes

Verified against my parallel kernel: a conditional edge function
returning `""` produced a bare, unhelpful `KeyError: ''` (the kernel tried
to look up a node literally named empty-string) rather than a message
explaining a router returned an invalid route.

**Fix, verified:**

```python
def _next(self, current, state):
    edge = self._edges.get(current, END)
    target = edge(state) if callable(edge) else edge
    if not isinstance(target, str) or not target:
        raise ValueError(f"edge from {current!r} resolved to invalid route: {target!r}")
    return target
```

**Action for the CLI session:** same check-first pattern as Finding 2 —
verify against the actual current file before applying.

## 5. Proposal (not a verified bug fix) — `asteps()` scheduler seam

This is a genuine design proposal, not a reproduced bug, and should be
weighed as one. The problem it solves: a tracing/streaming plugin
currently has no legitimate way to observe per-step execution
(`node.start`, `node.end`, `edge.selected`, `interrupted`, `done`)
without reaching into `CompiledGraph`'s private node/edge maps — which
`oramasys/perpetua-core`'s existing `graph/plugins/streaming.py` may
already solve differently (unverified — this doc has no read access to
that file).

**The shape, if adopted:** an async generator that becomes the *sole*
scheduler; `ainvoke()` is rewritten to just drain it, so there is one
execution path, not two that could quietly drift apart:

```python
async def asteps(self, state):
    node = self._next(START, state)
    steps = 0
    last_node = START
    while node != END:
        if steps >= self._max_steps:
            raise MaxStepsExceeded(steps, last_node)
        current = node
        yield ("node.start", current, state)
        state = state.merge({"nodes_visited": [*state.nodes_visited, current]})
        last_node = current
        fn = self._nodes[current]
        try:
            result = fn(state)
            if inspect.isawaitable(result):
                result = await result
        except Exception as exc:
            if type(exc).__name__ == "Interrupt" and hasattr(exc, "prompt"):
                state = state.merge({"status": "interrupted", "metadata": {
                    **state.metadata, "interrupt_prompt": exc.prompt,
                    "interrupt_payload": getattr(exc, "payload", None),
                    "interrupt_node": current,
                }})
                yield ("interrupted", current, state)
                return
            raise
        if not isinstance(result, dict):
            raise TypeError(f"node {current!r} returned {type(result).__name__}; expected dict delta")
        state = state.merge(result)
        yield ("node.end", current, state)
        steps += 1
        node = self._next(current, state)
        yield ("edge.selected", current, state)
    state = state.merge({"status": "done"})
    yield ("done", END, state)

async def ainvoke(self, state):
    final = state
    async for _kind, _node, final in self.asteps(state):
        pass
    return final
```

**Cost, measured on the parallel kernel, not estimated:** adding this
grew that kernel from 99 to 116 lines (17 over its own ~99 target). If
`oramasys/perpetua-core`'s real engine is genuinely at ~65-70 lines per
`15-phase1-as-built.md`, the proportional cost of adding this seam there
needs its own measurement — do not assume the 17-line delta transfers
directly.

**Action for the CLI session:** read `graph/plugins/streaming.py` first.
If it already gives plugins a non-internals-reaching way to observe
execution, this proposal may be redundant — don't adopt it reflexively
just because it's written up here.

## 6. What this doc deliberately does not claim

- Does not claim `oramasys/perpetua-core`'s current `engine.py` has any
  of these three bugs — only that this exact pattern was reproduced in a
  parallel, never-merged implementation, and is specific enough to check
  for directly.
- Does not include a line-by-line diff against the real file, because
  this session never had read access to it — only to the 2026-05-01
  as-built snapshot description, over three months stale relative to
  today.
- Does not recommend blindly applying the `asteps()` proposal — it is
  flagged as a design option to evaluate against whatever
  `graph/plugins/streaming.py` already does, not a verified gap.

## 7. Source material

Full reconciliation history (harmonization ledger, rejected/adopted
Kimi-bundle claims, the coordinator/orchestrator terminology sidebar,
and three prior rounds of behavioral verification against a parallel
kernel) is preserved in the conversation this doc was extracted from, not
duplicated here to avoid this file drifting out of sync with a longer
document nobody will keep updated. If deeper rationale is needed for any
of the three findings above, ask for the fuller record rather than
assuming this summary is exhaustive.

---

## Part II — moved to its own document

The implementation plan for `oramasys/perpetua-core` (previously Part II
of this same file) is now its own document:
[`58-minigraph-implementation-plan-perpetua-core.md`](58-minigraph-implementation-plan-perpetua-core.md).
Split out on 2026-08-27 once this combined file passed the 500-line
advisory threshold `repo_hygiene.py` flags. No content was lost or
altered in the split beyond heading-level promotion (`## Part II` → the
new doc's `#` title; `### II.X` → `## II.X`).
