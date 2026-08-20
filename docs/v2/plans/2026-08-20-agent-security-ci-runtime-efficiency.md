# Agent Security CI: runtime efficiency + supply-chain pinning

> Companion to [`32-agentic-security-controls.md`](../32-agentic-security-controls.md) § 6/8/9.
> Source: live run inspection, `diazMelgarejo/orama-system` run `32363347703` (jobs `96407477061`
> "gitleaks", `96407476872` "aguara / agent-audit / skill-scanner / mcp-scanner / Ramparts"),
> 2026-08-20, triggered by PR #321.

## Status: implemented (PR #321)

The runtime-shape fix described below has landed. `.github/workflows/agent-security.yml` now runs
`gitleaks`, `aguara`, `agent-audit`, `skill-scanner`, `mcp-scanner`, and `ramparts` as 6 separate
parallel jobs (plus a fast smoke-test job for the dispatcher script's own exit-code propagation),
each with the caching described in the Recommendation section. `aguara` is pinned to a commit SHA
(not `@latest`); `agent-audit`'s clone is cached at a stable path matching what `actions/cache`
restores, keyed on its pinned ref.

## Baseline (before this PR)

`.github/workflows/agent-security.yml` ran two jobs on every push/PR to `main`/`develop`:

| Job             | Tools                                                                         | Runtime (baseline run, 32363347703) |
| --------------- | ----------------------------------------------------------------------------- | ----------------------------------- |
| `gitleaks`      | gitleaks (secrets)                                                            | **7s**                              |
| `agent-surface` | aguara, agent-audit, skill-scanner (per-SKILL.md loop), mcp-scanner, Ramparts | **~13m26s**                         |

`gitleaks` was already the right shape: one focused tool, its own job, fast. `agent-surface` was
not: 5 distinct scanners bundled sequentially in one job (`scripts/ci/run_agent_security_scans.sh`),
each contributing setup + install time that dominated actual scan time.

## Findings

1. **Unpinned supply-chain dependency in a security scanner.** `run_agent_security_scans.sh` does
   `go install github.com/garagon/aguara/cmd/aguara@latest` — floating `@latest` in a tool whose
   entire job is catching supply-chain/agent-surface risk. A compromised or behavior-changed release
   of aguara would be pulled silently on the next CI run with no diff to review. Pin to a commit SHA
   (matches this repo's own convention for every `actions/*` step in the same workflow file, which
   are all pinned to SHAs).
2. **No pip cache.** `pip install cisco-ai-skill-scanner cisco-ai-mcp-scanner` and the editable
   install of `agent-audit` run fresh every job. `actions/setup-python` supports `cache: pip`
   directly; not set here.
3. **`agent-audit` is git-cloned fresh every run**, not pinned via a cached/vendored install — the
   script does pin the ref (`AGENT_AUDIT_REF`, good), but re-clones over the network each run
   instead of caching the clone keyed on that ref.
4. **Sequential, not parallel.** The skill-scanner loop invokes once per `SKILL.md` directory found
   under `bin/agents` and `bin/orama-system/skills` — currently serial. These are independent
   per-directory scans with no shared state; a matrix job or simple backgrounding would cut
   wall-clock roughly proportional to skill-dir count.
5. **One job, one failure domain.** Bundling 5 tools in one job step means a single tool's failure
   or hang blocks visibility into the other 4 until the whole step exits — and retries re-run
   everything, including tools that already passed. `gitleaks`'s own job split in this same file is
   the counter-example already in the codebase.

## Recommendation (implemented; do not restructure the security _logic_, only its runtime shape)

This is a CI-efficiency pass, not a scanner-coverage change — every existing check stays, same
severity gates, same baseline files (with one exception noted below: Ramparts moved from non-fatal
`warn_run` to blocking `run`, tightened during implementation review, not part of the original
runtime-shape scope). Scope:

1. **Done.** Pin `aguara` to a commit SHA via `AGUARA_REF` (same pattern as `AGENT_AUDIT_REF`
   already in the script), not `@latest`.
2. **Done.** Add `cache: pip` to `actions/setup-python` in every Python-based scanner job.
3. **Done.** Cache the `agent-audit` clone keyed on `AGENT_AUDIT_REF` (actions/cache, path =
   `CACHE_DIR/agent-audit`, a stable path outside the per-run scratch dir so the cache step's
   `path:` can actually match it between runs; key includes the ref so a ref bump invalidates
   automatically).
4. **Done.** Split `agent-surface` into per-tool jobs (aguara, agent-audit, skill-scanner,
   mcp-scanner, Ramparts) running in parallel, mirroring the existing `gitleaks` job shape.
   Skill-scanner's per-directory loop stays a single job; not worth a `strategy: matrix` at current
   scale.
5. **Revised during implementation review:** Ramparts scan calls moved from non-fatal `warn_run` to
   blocking `run`, and unavailability in CI now sets `FAIL=1` instead of only warning — a Ramparts
   finding is a real scan result like any other tool's, not an install/availability warning. This is
   a policy tightening, not part of the original runtime-shape-only scope, called out explicitly per
   this doc's own original framing.

## Explicitly out of scope here

- Changing which findings are fatal vs. warn-only (that's a §6/§9 policy decision, not a runtime one
  — see `32-agentic-security-controls.md`).
- Adding new scanners.
- Touching the `TOXIC_CROSS_002` baseline suppression for skills scans (documented, intentional,
  unrelated to runtime).
