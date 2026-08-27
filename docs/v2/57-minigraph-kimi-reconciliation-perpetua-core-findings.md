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

## Part II — Implementation Plan for `oramasys/perpetua-core`

> **Audience:** a future agent (Claude Code CLI or equivalent) with real
> read/write access to `oramasys/perpetua-core`, which this session never
> had. Written to be followed literally.
>
> **Read this first, before any code:** Part I above was written by a
> session that could not read the target repo. Part II grounds every step
> in `docs/v2/01-kernel-spec.md` — the repo's own canonical spec, which
> IS readable from orama-system and IS authoritative. Where Part I's
> parallel-kernel code and the canonical spec disagree, **the canonical
> spec wins.** §II.1 lists every known disagreement explicitly so you do
> not have to discover them by trial.

### II.0 Preconditions — verify before writing anything

Do not skip. Each is a real failure mode this plan was written to prevent.

1. **Confirm the repo.** `oramasys/perpetua-core` — NOT
   `diazMelgarejo/perpetua-core`. The latter is called "the divergent
   wrong-repo" by `15-phase1-as-built.md` and contains a non-canonical
   192-line engine plus a `competing.zip`. Never push there.
2. **Read the actual current `perpetua_core/graph/engine.py`.** Every
   finding in Part I was reproduced against a *parallel* kernel, never
   against the real file. Some may already be fixed. Some may not apply.
   Confirm before changing.
3. **Read `perpetua_core/graph/plugins/streaming.py`** (or wherever
   streaming lives now). This determines whether §II.5's proposal is
   redundant.
4. **Run the existing suite and record the baseline count.**
   `15-phase1-as-built.md` says 32 tests as of 2026-05-01, "38 (est.)"
   after the 2026-05-17/18 RC-1 work. Get the real number before
   changing anything, so any regression is attributable.
5. **Confirm `tests/graph/test_engine_max_steps.py` exists** and read it.
   OQ12 was resolved 2026-05-17; §II.2 is a refinement to an existing
   guard, not a new feature.

### II.1 Canonical-vs-Part-I API differences (read before copying any code)

Part I's code samples come from a parallel kernel with a different API.
Do **not** paste them verbatim. Translate to canonical shape:

| Concern | Part I parallel kernel | **Canonical (`01-kernel-spec.md`)** |
| --- | --- | --- |
| Entry point | `set_entry(target)` | `set_start(name)` |
| Sentinels | `START` / `END` module constants | `self.start: str \| None`, `self.end: str = "__end__"` |
| Node signature | sync **or** async (`inspect.isawaitable`) | `NodeFn = Callable[[PerpetuaState], Awaitable[dict]]` — **async only** |
| `max_steps` default | `200` | **`50`** (§7b, explicit MUST) |
| Plugin loading | three composition mechanisms, ad hoc | `MiniGraph.use(plugin)` + `GraphPlugin` Protocol |
| Observability | proposed `asteps()` generator | `GraphPlugin.on_node_start` / `on_node_end` hooks (§7a) |
| Kernel size target | ~99 lines | **~70 lines** (D8, and the spec's own "Kernel target") |

**The single most important line in this table** is the last two rows:
the canonical spec already has a plugin-observability answer
(`GraphPlugin` Protocol). §II.5 exists only to evaluate whether it is
sufficient — not to replace it.

### II.2 Task 1 — `max_steps` semantics (refinement, ~10 min)

**Precondition:** `tests/graph/test_engine_max_steps.py` exists (OQ12,
resolved 2026-05-17).

**Step 1 — write the failing test first.** Add to that file:

```python
@pytest.mark.asyncio
async def test_max_steps_reports_last_completed_node_not_next_node():
    """A 2-node alternating cycle. A 1-node self-loop cannot catch this:
    'node about to be attempted' and 'last node completed' are the same
    name in that case, so an off-by-one and a wrong-node attribution
    both hide."""
    g = MiniGraph()
    g.add_node("a", lambda s: _delta({}))
    g.add_node("b", lambda s: _delta({}))
    g.set_start("a")
    g.add_edge("a", "b")
    g.add_edge("b", "a")
    with pytest.raises(RuntimeError) as exc:
        await g.ainvoke(PerpetuaState(), max_steps=3)
    # exact assertions depend on the real exception shape -- read it first
    assert "a" in str(exc.value), "should name the last node that ACTUALLY ran"
```

Adapt `_delta` and the `max_steps` passing convention to whatever the
real engine uses — read it, do not assume.

**Step 2 — run it.** If it passes, the canonical engine is already
correct. **Stop here and record that in the PR description.** Do not
"fix" working code.

**Step 3 — only if it fails**, apply:

```python
steps = 0
last_node = START_EQUIVALENT          # whatever self.start resolves to
while node and node != self.end:
    if steps >= max_steps:            # check BEFORE increment
        raise RuntimeError(...)       # match the existing exception type
    current = node
    ...                               # execute current
    last_node = current               # only after successful entry
    steps += 1
    node = ...                        # resolve next edge
```

### II.3 Task 2 — reject non-dict node returns (~10 min)

**Step 1 — failing test first:**

```python
@pytest.mark.asyncio
async def test_node_returning_none_is_rejected_not_silently_merged():
    g = MiniGraph()
    async def forgot_to_return(state):
        pass                          # returns None
    g.add_node("broken", forgot_to_return)
    g.set_start("broken")
    with pytest.raises(TypeError, match="expected dict"):
        await g.ainvoke(PerpetuaState())
```

**Step 2 — if it fails, fix in `ainvoke`**, immediately after awaiting
the node and before merging:

```python
if not isinstance(delta, dict):
    raise TypeError(f"node {node!r} returned {type(delta).__name__}; expected dict delta")
```

**Do not** use `delta or {}` — that is the bug. An explicit `{}` still
passes `isinstance`; only non-dicts are rejected.

### II.4 Task 3 — reject empty/non-string edge routes (~10 min)

**Step 1 — failing test first:**

```python
@pytest.mark.asyncio
async def test_router_returning_empty_string_raises_clear_error():
    g = MiniGraph()
    g.add_node("n", _noop_node)
    g.set_start("n")
    g.add_edge("n", lambda s: "")      # router bug: unhandled case
    with pytest.raises(ValueError, match="invalid route"):
        await g.ainvoke(PerpetuaState())
```

Without the fix this surfaces as a bare `KeyError: ''` — technically an
error, but it names nothing useful.

**Step 2 — if it fails**, wrap edge resolution:

```python
target = edge(state) if callable(edge) else edge
if not isinstance(target, str) or not target:
    raise ValueError(f"edge from {node!r} resolved to invalid route: {target!r}")
node = target
```

### II.5 Task 4 — observability: EVALUATE, do not implement blindly

**This is not an approved change. It is a decision to make.**

The canonical spec already mandates (§7a) a `GraphPlugin` Protocol with
`on_node_start(state, node_name)` and `on_node_end(state, node_name,
delta)`. Part I proposed an `asteps()` async-generator seam instead,
written before this session had read §7a.

**Do this:**

1. Read `graph/plugins/streaming.py` and confirm whether `GraphPlugin`
   hooks are actually implemented and wired into `ainvoke`.
2. **If they are** — `asteps()` is redundant. Record that and close the
   item. Adding a second observability mechanism would violate the
   spec's own "Tier-3 features ship as plugins, never embedded in
   engine.py" rule and grow a ~70-line kernel for no gain.
3. **If they are not** (Protocol declared but never called) — the real
   gap is that the canonical hooks are unwired, not that a new seam is
   needed. Wire `on_node_start`/`on_node_end` into `ainvoke`. That is
   the spec-compliant fix.
4. **Only if** both are absent and a concrete plugin needs streaming
   semantics the hooks cannot express (e.g. backpressure, or consuming
   execution lazily) should `asteps()` be reconsidered — and then as a
   spec amendment proposal to `01-kernel-spec.md`, not a silent
   engine change.

**Cost datapoint, for the decision only:** adding `asteps()` to Part I's
parallel kernel grew it 99 → 116 lines (+17). Against a ~70-line
canonical kernel that is a ~24% increase, weighed against a spec that
sets ~70 as the target. Do not assume the delta transfers exactly;
measure if you get that far.

### II.6 Known conflict between two canonical docs — resolve, don't guess

`01-kernel-spec.md`'s file tree (line ~39) shows **root-level `tests/`**:

```text
└── tests/
    ├── test_state.py
    ├── test_minigraph.py
```

`46-repository-standard.md` — explicitly cross-cutting and additive —
says the opposite: *"Everything executable belongs under `/src`. No
root-level: scripts, tests, tools, examples."*

These cannot both hold. `46` is the newer, explicitly cross-cutting
standard and says it is additive to earlier docs, which argues it wins.
But `01-kernel-spec.md` is the kernel's own spec and `15-phase1-as-built.md`
records tests at `tests/graph/test_engine_max_steps.py` (root-level),
i.e. **as-built follows `01`, not `46`.**

**Do not silently pick one.** Put new tests wherever the existing tests
already live (match as-built reality), and raise the contradiction as a
separate docs issue. Relocating an existing suite is out of scope for a
3-fix PR and would bury the actual changes.

### II.7 Verification — run before opening the PR

From `01-kernel-spec.md`'s own acceptance criteria, the subset these
changes can affect:

1. `python -c "import perpetua_core; perpetua_core.MiniGraph()"` — no
   circular imports.
2. `pytest tests/test_minigraph.py` — 3-node graph end-to-end,
   `nodes_visited` populated.
3. `pytest tests/graph/test_engine_max_steps.py` — including the new
   2-node-cycle case.
4. Full suite — must equal the §II.0 baseline **plus** the new tests.
   Any pre-existing failure must be reported as pre-existing, with
   evidence it fails on the unmodified tree too.
5. **Import boundary lint (CI gate):** `grep -r "from oramasys" perpetua-core/`
   returns nothing.
6. Confirm kernel line count against the ~70-line target:
   `wc -l perpetua_core/graph/engine.py`. If these fixes push it
   materially past ~70, say so explicitly in the PR rather than letting
   it drift silently — D8 is a locked decision.

### II.8 PR shape

- **Branch:** `fix/minigraph-guard-semantics-and-delta-validation`
- **One commit per task** (§II.2, §II.3, §II.4), so any single fix can
  be reverted independently.
- **§II.5 gets no commit** unless investigation concludes work is
  needed — and then it is a **separate PR**, because it is a design
  change, not a bug fix.
- **PR description must state**, for each of the three tasks, whether
  the canonical engine already handled it (test passed immediately) or
  genuinely needed the fix. A "no change needed" outcome is a
  successful, valuable result — not a failure to deliver.
