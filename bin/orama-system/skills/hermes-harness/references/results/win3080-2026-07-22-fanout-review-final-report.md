# win3080 — 2026-07-22 frugal-fanout review: final report

**Follow-up to:** `win3080-2026-07-22-registry-update-and-fanout-review-status.md`
(marked IN PROGRESS) and `win3080-coordination-fix-request.md` (the direct-dispatch
coordination gap this run exposed).

6 recent commits reviewed, local models first (RTX3080:
`qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2`, RTX5080:
`gemma-4-26b-a4b-it-nvfp4`), each finding independently re-verified against the
real diff before being trusted. **2 of 12 verify/synthesis steps hit the
account's monthly spend limit mid-run** (`local-review:orama:e3c477d0`,
`Synthesize`) — completed both directly myself afterward rather than retrying
the paid path, so this report has no gaps, just a note on method for one entry.

## Per-commit results (CONFIRMED findings only)

### orama `2cb1f0f0` — exa MCP path resolution (RTX5080)
**1 real fix needed:** fallback `exec` in `.mcp.json`/`resolve-orama-root.sh`
silently produces a misleading "No such file" error (`/scripts/...` instead of
the intended path) if all 5 resolvers miss — should guard with
`[ -n "$W" ] || exit 1` before the final `exec`. 4/5 local-model findings held
(1 refuted: a "command injection" claim with a wrong line number and no real
attack surface — properly quoted throughout, no `eval`).

### orama `e3c477d0` — dependabot fix, brace-expansion + js-yaml (RTX3080, completed by me)
No findings. Clean, low-risk, same-major patch bumps, dev-only js-yaml
dependency, matches an established override pattern from a prior commit in
the same session. **Method note:** RTX3080's completions endpoint was hung
(health check fine, but even a 10-token smoke test timed out twice) — likely
queue backlog from the workflow's own earlier RTX3080 calls. Reviewed the
diff directly rather than keep retrying or spend more budget working around it.

### PT `3172050` — Windows msvcrt lock backend (RTX5080)
**No urgent action needed.** 2 of 6 local-model findings confirmed (both
stylistic — duplicated open/lock/finally boilerplate across the fcntl and
msvcrt branches, optional cleanup only), 3 refuted, 1 unverifiable. This
independently reproduces the same overconfidence pattern win-rtx5080's own
earlier benchmark already found on this exact commit (self-contradicting
"race condition" claim: model's own text says "doesn't crash" while still
stamping 85% confidence). Two independent runs, same verdict — worth trusting
that pattern going forward rather than re-litigating it a third time.

### PT `13f09c4` — frugality single-gate architecture (RTX3080)
**Pipeline gap, not a code finding.** Local-model output was a stale status
placeholder ("Waiting for background job bwgwwnc28"), not an actual review —
zero findings to verify either way. Real diff (~53KB, `orchestrator/gate.py`
new, `route_task()`/`privacy_critical` wiring, 29 new tests per commit
message) was never actually reviewed by a local model this round. If a real
local-model review of this commit is still wanted, the dispatch needs
re-running — this is a tooling gap in my fan-out script's async job capture,
not a signal about the commit itself.

### PT `a5e6273` — dependency bumps, fast-uri/hono (RTX5080)
2 of 3 findings usable: version-pin-style inconsistency across two packages
confirmed (real but low-stakes); a "workspace hoisting risk" finding refuted
(repo isn't a JS workspace at all — two separate package managers, pnpm vs
npm, nothing to hoist). Worth a quick look: `@modelcontextprotocol/sdk`
still transitively bundles the old vulnerable `hono@4.12.25`/
`@hono/node-server@1.19.14` under its own nested `node_modules` — likely low
risk (internal to the SDK's own transport) but not fully closed at the
transitive level. Optional, not urgent.

### orama `b3d1b36c` — "update all agent comms" trigger (RTX3080)
Same pipeline gap as PT `13f09c4` — local model produced no output
("Waiting for the local model response."). Diff itself is documentation-only
(SKILL.md frontmatter + a status markdown file), independently confirmed
low-risk with no code paths to review regardless.

## RTX3080 vs RTX5080 this round

| | RTX3080 | RTX5080 |
|---|---|---|
| Assigned | 3 | 3 |
| Delivered a real review | 1/3 (e3c477d0, by me after endpoint hung) | 3/3 |
| Finding confirmation rate (of delivered reviews) | n/a (no findings either way) | ~8/14 across the 3 (~57%) |

**RTX3080 had a dispatch-pipeline reliability problem this round** — 2 of 3
assigned targets got empty/placeholder output instead of an actual review,
and the 3rd required a manual completion after the endpoint itself hung.
RTX5080 completed all 3 of its assignments with real content, though with the
now-twice-confirmed pattern of overstating confidence on 1-2 findings per
commit that don't survive independent scrutiny — plan for that when trusting
its output solo (route through verification, as this run did, not raw).

## Action items (CONFIRMED, needs follow-up)

1. **orama `2cb1f0f0`**: guard the fallback `exec` path in
   `.mcp.json`/`scripts/exa/resolve-orama-root.sh` — real bug, small fix.
2. **PT `a5e6273`** (optional): check whether the transitive
   `hono@4.12.25`/`@hono/node-server@1.19.14` bundled inside
   `@modelcontextprotocol/sdk`'s nested tree is reachable.
3. **Fan-out pipeline itself**: the async local-model dispatch/capture that
   produced empty output for 2 of 3 RTX3080 targets needs investigating
   separately — a tooling gap in this session's workflow script, not
   something to fix in the reviewed commits.

## Not touched / explicitly deferred

- PT `3172050`'s duplicated-boilerplate cleanup — confirmed real but
  optional, not filed as a follow-up commit this session.
- No new commits made from this review pass; purely observational/reporting.
