<!-- lint-ignore LINT-013 -->
# 58 — MiniGraph Implementation Plan for `oramasys/perpetua-core`

> **Audience:** a future agent (Claude Code CLI or equivalent) with real
> read/write access to `oramasys/perpetua-core`, which this session never
> had. Written to be followed literally.
>
> **Companion doc:**
> [`57-minigraph-kimi-reconciliation-perpetua-core-findings.md`](57-minigraph-kimi-reconciliation-perpetua-core-findings.md)
> ("Part I") records findings from a session that could not read the
> target repo. This doc ("Part II") grounds every step in
> `docs/v2/01-kernel-spec.md` — the repo's own canonical spec, which IS
> readable from orama-system and IS authoritative. Where Part I's
> parallel-kernel code and the canonical spec disagree, **the canonical
> spec wins.** §II.1 lists every known disagreement explicitly so you do
> not have to discover them by trial.
>
> **Split from Part I on 2026-08-27** once the combined doc passed 500
> lines — see `repo_hygiene.py`'s advisory threshold. No content was
> lost or altered in the split beyond heading-level promotion.

## II.0 Preconditions — verify before writing anything

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

## II.1 Canonical-vs-Part-I API differences (read before copying any code)

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

**Two rows above are not just "canonical wins," on reflection — flag
these for the maintainer's judgment, do not silently implement against
canonical if the concern below is real:**

- **`self.end` vs. `START`/`END` sentinels.** Canonical's `self.end` is a
  *per-instance* attribute (`self.end: str = "__end__"`) rather than a
  module-level constant. Two genuine costs: (1) nothing stops two
  `MiniGraph` instances in the same process disagreeing on what "end"
  means, which invites accidental inconsistency for something that
  should be universal; (2) the traversal loop needs `while node and
  node != self.end`, an extra null-check the sentinel version avoids
  (`while node != END` is sufficient when `START`/`END` are always-defined
  constants). Real LangGraph — which the spec explicitly targets for
  "API-compatible... mental model" — exports `START`/`END` as importable
  module constants, closer to the sentinel design than to `self.end`.
  **Do not silently switch this** — it is Task 4-adjacent (a design
  question, not a bug), file it alongside §II.5 rather than bundling it
  into Tasks 1-3's PR.
- **Async-only `NodeFn` vs. accepting sync or async.** Canonical requires
  every node to be `async def`, even a pure, non-I/O transformation like
  `lambda s: {"x": s.x + 1}`. Real LangGraph accepts both — precisely
  because most graph nodes are simple synchronous transforms and only
  some are I/O-bound. Forcing `async def` on the simple case is exactly
  the syntactic-noise-for-no-benefit tradeoff the spec's own
  LangGraph-compatibility goal argues against. **Also flag, don't
  silently change** — this is more consequential than the sentinel
  question, since it would break every existing node function signature
  in the canonical repo if changed, which is a real migration cost to
  weigh against the ergonomic gain.

## II.2 Task 1 — `max_steps` semantics (refinement, ~10 min)

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

## II.3 Task 2 — reject non-dict node returns (~10 min)

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

## II.4 Task 3 — reject empty/non-string edge routes (~10 min)

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

## II.5 Task 4 — observability: EVALUATE, do not implement blindly

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

## II.6 Docs conflict — RESOLVED in `01-kernel-spec.md`; as-built repo still needs migrating

**2026-08-27 update:** `01-kernel-spec.md`'s file tree previously showed
root-level `tests/`, genuinely conflicting with
`46-repository-standard.md`'s "no root-level tests" rule. This has been
fixed directly in `01-kernel-spec.md` (this same commit) — the tree and
every path reference throughout that document now nest both
`perpetua_core/` and `tests/` under `src/`:

```text
perpetua-core/
├── pyproject.toml
├── LICENSE
├── README.md
└── src/
    ├── perpetua_core/
    │   └── ...
    └── tests/
        └── ...
```

**What this does NOT do:** move any actual files in
`oramasys/perpetua-core`. That repo was unreachable from this session
(see Part I §0). `15-phase1-as-built.md` records the as-built repo's tests at
root-level `tests/graph/test_engine_max_steps.py` — meaning the **spec**
now says `src/tests/...` but the **real repo**, as of the last
verifiable snapshot, still has root-level `tests/`. This is a genuine,
separate migration task, not resolved by this doc.

**Action for the CLI session:**

1. Confirm whether `oramasys/perpetua-core`'s current tree still has
   root-level `perpetua_core/` and `tests/`, or whether it already
   moved to `src/` independently since the last snapshot this session
   could see.
2. If it still needs moving: this is a mechanical `git mv` (both
   directories under a new `src/`), a `pyproject.toml` packaging-config
   update (see the note added to `01-kernel-spec.md`'s Repo Layout
   section — `[tool.setuptools.packages.find] where = ["src"]` or
   equivalent), and an import-path sanity check
   (`python -c "import perpetua_core; ..."` per acceptance criterion 1).
   Do this as its **own commit**, separate from Tasks 1-3 (§II.2-II.4)
   — a pure structural move should never share a commit with a
   behavior change, so either can be reverted independently.
3. If it already matches `src/` layout: nothing to do here; note that
   in the PR description as a "no change needed" outcome, same
   discipline as §II.2-II.4.

## II.7 Verification — run before opening the PR

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

## II.8 PR shape

- **Branch:** `fix/minigraph-guard-semantics-and-delta-validation`
- **One commit per task** (§II.2, §II.3, §II.4), so any single fix can
  be reverted independently.
- **If §II.6's `src/` migration is genuinely needed**, that is its own
  commit (or its own PR, if `git mv` + packaging-config changes touch
  enough files to obscure the three behavior fixes) — a pure structural
  move should never share a commit with a behavior change.
- **§II.5 gets no commit** unless investigation concludes work is
  needed — and then it is a **separate PR**, because it is a design
  change, not a bug fix.
- **PR description must state**, for each of the three tasks (and the
  §II.6 migration, if attempted), whether the canonical repo already
  handled it or genuinely needed the change. A "no change needed"
  outcome is a successful, valuable result — not a failure to deliver.
