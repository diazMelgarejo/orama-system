# Agent Flow Standardization — Plan vs. Reality Reconciliation

> Retroactive checklist. The original plan (`00-agent-flow-standardization-plan.md` +
> `01-security-invariants-endpoint-policy.md`) called for this document to be written
> **before** execution. It wasn't — the work took a different real-time path (a parallel
> apprentice-integration task intervened, then a sandbox reset lost several hours of
> completed work and required a full redo). This reconciles the original intent against
> what was actually done, with commit-level evidence rather than restated intentions.

---

## The actual goal, stated explicitly

Everything documented below — the SSRF/transport-identity gap closure, the stale-test
cleanup, the parity checker, the NPM translation of PT's AlphaClaw controller — is a
means, not the end. The original plan's own I1/I2 name the real target directly:

> **I1 — Zero-config default:** every package runs with no required flags; all config
> has a sensible default. Config is *optional* refinement, never a precondition.
> **I2 — Consistent defaults across repos:** shared concepts (endpoint policy, config
> dir, log level, telemetry opt-in) resolve to identical defaults everywhere.

This reconciliation initially listed I1/I2 as "not addressed" alongside I3/I4/I5 as if
they were peer checklist items. They aren't peers — I1/I2 are the outcome the other
three exist to serve. A validator that's correct but not consistently packaged (I3), a
discovery mechanism that's sound but not zero-config by default (I4), errors that fail
closed but aren't uniformly typed (I5) — none of that adds up to "install and run great
together with sensible defaults" on its own. That composition work hasn't happened yet.
See **Next Steps** at the end of this document for what executing I1/I2 directly, rather
than assuming it falls out of the supporting work, actually requires.

---

## Scope note on evidence

All SHAs below are on branch `2026-08-12-endpoint-policy-standardization`, pushed to
both `diazMelgarejo/orama-system` and `diazMelgarejo/Perpetua-Tools` (same branch name,
deliberately reused across repos so the paired cross-repo work stays connected — see
PT `lesson_df682761347f`). Neither branch has a PR open yet; opening one requires a
token with PR-creation scope, which this session's git-push-only token doesn't have.

- orama-system range: `fde9d460..ae1e454a` (4 commits), plus this doc and its updates
- Perpetua-Tools range: `2cd0d894..ea104aee` (10 commits: the security work, the memory
  lessons, and the AlphaClaw-controller NPM translation)

---

## Part 1 — `01-security-invariants-endpoint-policy.md` (the security note)

| Item | Plan said | What actually happened | Status |
| --- | --- | --- | --- |
| Root cause: `urlparse().port` as unwrapped throwing boundary | Wrap all parsing so every failure becomes `ModelEndpointPolicyError` | Confirmed already implemented in both repos' `model_endpoint_url.py` before this session's work began — `validate_model_endpoint_url()` already wraps port/scheme/hostname resolution. Not something this session built; it predates this arc. | ✅ Already done (pre-existing) |
| Host classification: RFC1918, loopback, link-local, IPv4-mapped-IPv6 | Strengthen and keep consistent | Same as above — already present pre-session. What *was* new this session: finding and closing call sites that never routed through this classifier at all (see Part 3). | ✅ Already done (validator) / see Part 3 for call-site gaps |
| Keep API thin (domain error → HTTP 400) | Explicit requirement | `portal_server.py`'s `/api/peer-relay-probe` was the one FastAPI-facing endpoint found with an SSRF gap; fixed to catch `ModelEndpointPolicyError` and return 400 with a policy-attributed detail message, nothing more (orama-system `31639e78`). | ✅ Done, this session |
| Regression coverage: bare-host canonicalization, malformed port, out-of-range port, SSRF metadata IPs, IPv4-mapped-IPv6 bypass, skip-invalid list parsing | Add to both repos | Pre-existing in both repos' `test_model_endpoint_url.py`/`test_endpoint_policy_fuzz.py` (117 tests, untouched this session — already covered this ground). New coverage added this session was for the *call sites*, not the validator itself: 20+ new tests across both repos proving each previously-unvalidated site now rejects link-local/public targets. | ✅ Already done (validator-level) + ✅ done this session (call-site level) |
| **I3 — unify the validator into a shared `endpoint-policy` package** | Follow-up, feeds the standardization plan | **Partially done, deliberately.** Discovered mid-session that Perpetua-Tools already has a complete `packages/endpoint-policy/` (Apache-2.0, matches this exact proposed design) — built before this session, not by it. What this session added: `endpoint_policy_core.py` (a *second*, separately-owned shared module — transport-identity reconstruction, distinct from SSRF validation) synced into orama-system for the first time (orama-system `31639e78`). Per explicit instruction, actual *package dependency* wiring (orama-system depending on PT's package as a real import, deleting orama's local copy) is deferred to the v2 `oramasys/*` repo migration — both repos currently carry manually-synced mirror copies instead, with a bidirectional parity checker (Part 4) catching drift in the meantime. | ⚠️ Deferred by design, not forgotten — see v2 note below |
| Structured error taxonomy (`ERR_INVALID_URL`, `ERR_SSRF_BLOCKED`, `ERR_PUBLIC_ENDPOINT_BLOCKED`) | Follow-up | Not done. `ModelEndpointPolicyError` remains a single exception type with a message, not a coded taxonomy. | ❌ Not done, not attempted this session |
| Fuzz + property tests for the URL parser | Follow-up | Pre-existing (`test_endpoint_policy_fuzz.py`, both repos), predates this session. | ✅ Already done (pre-existing) |
| Isolate parsing in a hardened module | Follow-up | This *is* what `packages/endpoint-policy/` already is on the PT side. Not separately re-done. | ✅ Already done (pre-existing) |

---

## Part 2 — `00-agent-flow-standardization-plan.md` (the overarching plan)

### Invariants (I1–I5)

| Invariant | Plan | Reality | Status |
| --- | --- | --- | --- |
| I1 — Zero-config default | Every package runs with no required flags | **This is the actual target, not a peer checklist item** — see "The actual goal" section above. Not evaluated this session as its own audit; no packaging/CLI-defaults inventory was performed on either repo's actual entrypoints. | 🎯 Target — execution plan in Next Steps |
| I2 — Consistent defaults across repos | Shared concepts resolve identically everywhere | Same reframing as I1. Narrow progress exists (the endpoint-policy validator now agrees between repos via I3), but broader config-dir/log-level/telemetry defaults were never inventoried, so "consistent" isn't yet a verified property of the whole system. | 🎯 Target — execution plan in Next Steps |
| I3 — Single source of truth for shared logic | Endpoint/URL policy lives in ONE package | See Part 1 — real progress, deliberately incomplete pending v2. | ⚠️ Partial, deferred |
| I4 — Predictable discovery (env → config → default, never hardcoded) | — | Directly relevant to the actual bugs found this session: `MAC_IP`/`WIN_IP`/`LLAMA_SERVER_BASE_URL`/discovery-file-sourced hosts *were* already following an env→file→default resolution order in both repos. The gap wasn't discovery mechanism, it was that the *resolved* value skipped SSRF validation before use. Fixed at 5 call sites (Part 3). | ✅ Mechanism was already sound; validation gap fixed |
| I5 — Fail closed, explain clearly | One typed, actionable error, never a raw trace or 500 | This is exactly what the call-site fixes in Part 3 deliver: each rejected endpoint now fails via `ModelEndpointPolicyError` with an explanation, caught and handled locally (warn-and-fallback for internal resolvers, HTTP 400 for the one FastAPI endpoint) rather than crashing or silently misrouting. | ✅ Done, this session |

### Stage 0 — Method ("eat our own dog food")

The plan asked for this document *before* execution (Context Immersion → Visionary
Architecture → Ruthless Refinement → Execution → Crystallization, in that order, with
the plan written first). That didn't happen — Context Immersion and the divergence
matrix below were reconstructed *after* Execution, not before it. Worth naming plainly
rather than glossing over: the actual sequence was Execution → (interruption: apprentice
PR review/merge task, unrelated to this plan) → (sandbox reset, full redo) → Execution
(redo) → this Crystallization document. The oramasys 5-stage method's own ordering
wasn't followed for this task; noting that as a real process finding, not just a content
gap.

### Divergence matrix (reconstructed from actual audit findings, not the original's `⟨FILL⟩` placeholders)

| Dimension | orama-system | Perpetua-Tools | Divergence found |
| --- | --- | --- | --- |
| SSRF validator (`model_endpoint_url.py`) | Mirror copy, now synced | Canonical | Was drifted (docstrings/comments only, logic already identical) — reconciled `31639e78` |
| Transport-identity module (`endpoint_policy_core.py`) | Did not exist before this session | Canonical, actively used in `orchestrator/model_registry.py` + `fastapi_app.py` | Total absence on orama-system side, not drift — closed `31639e78` |
| Call sites using resolved-but-unvalidated hosts | 4 real gaps found and fixed (`portal_server.py`, `discover.py`, `lan_peer_channel.py`, `lm_link_watch.py`) | 5 real gaps found and fixed (`alphaclaw_bootstrap.py`, `agent_launcher.py`, `lan_discovery.py`, `autoresearch_bridge.py`, `perpetua/discovery/registry.py`) | Same underlying pattern independently present in both repos — each fixed with its own RED-first test, not a shared patch, since the call sites themselves aren't shared code |
| Parity/drift detection | `verify_model_endpoint_policy_parity.py` existed for `model_endpoint_url.py` only | Same | Extended on both sides to also cover `endpoint_policy_core.py` (`ae1e454a` / `74779e00`), verified live bidirectionally — PT→orama and orama→PT both report PASS |
| License metadata | README claimed Apache-2.0; actual `LICENSE` file (and GitHub's own detection) was MIT, with an unfilled placeholder copyright | N/A (not audited — out of this plan's original scope, found incidentally) | Real, unrelated bug found and fixed (`fde9d460`, pre-dates the branch's main security work) — resolved by aligning to MIT (confirmed via search: LangChain and LangGraph, the stated compatibility target, are both MIT) |

### Execution Strategy table (original vs. actual)

| Repo | Plan said | Actual |
| --- | --- | --- |
| Perpetua-Tools | Adopt shared endpoint-policy package; align defaults; regression tests | Package already existed pre-session (not "adopted," discovered already-adopted). Regression tests: yes, extensively — 5 new SSRF-gap fixes + parity checker extension, all RED-first. Defaults alignment: not done (I1/I2 not addressed). |
| orama-system | Host the shared config schema + endpoint-policy primitive; fix 2 failing CI runs; docs under `docs/` | Did not "host" the primitive (PT remains canonical, per explicit v2-deferral instruction) — synced a *mirror* instead. The 2 originally-cited CI runs (`28520664897`, `28523352731`) are both from `2026-07-01`, over a month stale relative to when this work happened; current `main` passes cleanly, so these were resolved by being outdated, not by direct action. This `docs/` document is the first plan-related doc actually written under `orama-system/docs/` for this effort. |
| AlphaClaw | Align macOS post-install defaults | Not touched — explicit hard exclusion from all implementation work on this repo, held throughout. Deferred pending a follow-up ask now that PT/orama-system work is done (see Open Questions). |

---

## Part 3 — What actually got fixed this session (not in either original doc, found via direct audit)

Neither original document anticipated these specific call sites — they were found by
tracing variable origins for every `f"http://..."` construction in both repos, not
predicted in advance. Listed here because the reconciliation would be incomplete
without them; this is the majority of the actual delivered work.

| Repo | File | Gap | Severity note |
| --- | --- | --- | --- |
| orama-system | `portal_server.py` (`/api/peer-relay-probe`) | Authenticated-peer-supplied `target_ip`/`target_port`, zero SSRF check | Most severe orama-system finding — network-facing, user-controlled |
| orama-system | `discover.py` (`probe_models`) | `MAC_IP` env var + cached/scanned IPs, zero validation | Single choke point fixed protects ~10 call sites at once |
| orama-system | `lan_peer_channel.py` + `lm_link_watch.py` | Discovery-file `"ip"` field trusted verbatim, double-scheme risk | Two independent readers of the same file, fixed separately |
| Perpetua-Tools | `autoresearch_bridge.py` (`_lm_studio_base_url`) | `LLAMA_SERVER_BASE_URL`/`LM_STUDIO_WIN_ENDPOINTS`, zero SSRF check | Most severe PT finding — leaks `Authorization: Bearer` token to whatever host the env var names |
| Perpetua-Tools | `alphaclaw_bootstrap.py` + `agent_launcher.py` | `MAC_IP`/`WIN_IP`-driven resolution, locality-checked but not SSRF-checked | Same pattern as orama's `discover.py` finding, independently present |
| Perpetua-Tools | `lan_discovery.py` (`_read_discovery_win_url`) | Discovery-file `"ip"` field, same class as orama's finding | |
| Perpetua-Tools | `registry.py` (`register_by_ip`) | Caller-supplied `ip`/`port`, zero validation | No current production caller — fixed anyway as a public-API landmine |

Every fix above shipped with a RED-first regression test (test written and confirmed
failing against live, unmodified code before any implementation change), per
`docs/TDD.md`. Two real mistakes were caught mid-work rather than shipped: a false-positive
test for `probe_models` (passed regardless of the fix, because a real network failure in
this sandbox produced the same observable result as a genuine SSRF rejection — caught by
asserting the network call was never attempted, not just checking the return value) and
the same false-positive pattern recurring independently in PT's `register_by_ip` test.

---

## Part 4 — PyPI / npm publishing (the plan's own unresolved open question)

Investigated directly rather than left as a standing question:

**PyPI.** `perpetua-endpoint-policy` (the exact name already set in
`packages/endpoint-policy/pyproject.toml`) is confirmed **available** — `pypi.org/pypi/perpetua-endpoint-policy/json`
returns 404. The package **builds cleanly** (`python -m build`, verified directly, not
assumed from the `pyproject.toml` looking correct) and the resulting wheel **installs and
imports correctly** (`from endpoint_policy import validate_model_endpoint_url` works
against the actual built artifact). Nothing technical blocks publishing today — this is
now purely a decision (do you want it public, versioning/release-process ownership),
not an unresolved technical readiness question.

**npm — endpoint-policy validator specifically.** Confirmed **no JavaScript/TypeScript
port of the SSRF validator exists anywhere in either repo** — it has only ever been
implemented in Python. `perpetua-endpoint-policy` is also available as an npm package
name (registry.npmjs.org returns 404), but there is nothing to publish yet. AlphaClaw
is the only JS-side codebase in this three-repo ecosystem and is under this session's
hard exclusion, so publishing *this specific validator* to npm remains blocked on the
AlphaClaw follow-up.

**npm — the AlphaClaw controller, a different and separate npm question.** Not blocked
the same way. Perpetua-Tools already contains its own TS/JS controller
(`packages/alphaclaw-adapter/`, `packages/alphaclaw-mcp/`) that steers a running
AlphaClaw process via `child_process.spawn` + HTTP — never a git/repo-level operation
against AlphaClaw's own repository (verified directly, recorded as PT
`lesson_a5b40efe18d5`, before doing any further work on it). This is PT's own code and
was in scope. Given `// @ts-ignore` was required to even import
`@diazmelgarejo/alphaclaw-adapter` from the TypeScript controller (no `.d.ts` existed),
added real TypeScript type declarations (hand-written, diffed function-by-function
against the actual `module.exports` keys to confirm an exact match) plus a dual
CJS/ESM entry point, RED-first: wrote a type-contract fixture before the `.d.ts`
existed, confirmed genuine RED via `tsc --noEmit` (`TS2307: cannot find module`, and
the deliberately-invalid test calls reported as "unused `@ts-expect-error`" because
untyped code resolves everything to `any`), then implemented. Verified the fix against
the real consumer, not a synthetic stand-in: removed the actual `// @ts-ignore` from
`packages/alphaclaw-mcp/src/index.ts` and ran that package's own real `tsc` build
clean, plus both packages' full existing test suites (40/40, 6/6) with zero regressions
(PT `ea104aee`).

Version note, also recorded to memory: the adapter package's version (`0.9.9.9`) was
never valid semver — 4 components, `npm publish` would reject it outright — but the fix
isn't an arbitrary clean bump. It now tracks the real relationship this PT-side
controller has to the upstream `chrysb/alphaclaw` release line the AlphaClaw soft-fork's
`feature/*` branch bumps against (operator-stated baseline ~0.9.34), landing on
`0.9.39`. This corrects an earlier uncommitted step in this same session that bumped to
`0.10.0` — semver-valid but disconnected from the soft-fork's actual lineage — and
explicitly supersedes the AlphaClaw-adapter-specific portion of a previously *locked*
versioning decision (PT `lesson_292b1558dde2`, "do not re-debate without human
override"), by direct human override, not a unilateral change (PT `lesson_9bcca08eefa4`).
This version bump is for the PT-side package only; it does not touch or imply a bump to
AlphaClaw's own `feature/*` branch, which remains under the standing exclusion and can
catch up to this numbering separately, later.

---

## Open questions, still genuinely open

1. **AlphaClaw.** PT/orama-system work is now done; this is the point you said to ask again.
2. **PyPI publish decision.** Technically ready; needs an actual yes/no and, if yes,
   a release-process owner.
3. **npm — the endpoint-policy validator.** Still blocked on AlphaClaw (whether to
   port the validator to JS at all, and where it would live). The AlphaClaw
   *controller* (a separate npm question) is no longer blocked — see Part 4.
4. **Structured error taxonomy** (`ERR_INVALID_URL` etc.) — flagged in the original
   security note as a follow-up, never attempted.

---

## Next Steps — executing I1/I2 directly

Per "The actual goal" section above: I1 and I2 are the target, not a checklist item to
mark done alongside the others. None of the work above directly executes them. What
would:

1. **Entrypoint inventory (Context Immersion the original plan asked for, still not
   done).** For each of the three repos: every console_script / CLI entrypoint / MCP
   server start command, and for each one, does it run with zero required flags and
   zero required env vars on a clean checkout? Where it doesn't, what's the minimum
   viable default?
2. **A single `DEFAULTS.md` or equivalent**, per the original plan's own
   Crystallization stage — one place enumerating every cross-repo shared default
   (config dir, log level, telemetry opt-in, endpoint policy, discovery ordering) and
   its rationale, so I2 becomes a checkable property instead of an assumption.
3. **A CI check that fails on default drift**, mirroring the parity-checker pattern
   already built and proven for the endpoint-policy modules (Part 3.5) — extend the
   same AST-comparison approach, or a simpler config-schema diff, to whatever the
   `DEFAULTS.md` inventory identifies as actually shared.
4. **Re-run the divergence matrix** (Part 2) once 1–3 exist, this time actually filling
   the I1/I2 rows with verified findings instead of "never evaluated."

None of this is started. Named here so the next pass has a concrete starting point
instead of re-deriving the target from scratch.
