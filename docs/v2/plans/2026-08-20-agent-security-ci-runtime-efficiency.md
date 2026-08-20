# Agent Security CI: runtime efficiency + supply-chain pinning

> Companion to [`32-agentic-security-controls.md`](../32-agentic-security-controls.md) § 6/8/9.
> Source: live run inspection, `diazMelgarejo/orama-system` run `32363347703`
> (jobs `96407477061` "gitleaks", `96407476872` "aguara / agent-audit / skill-scanner /
> mcp-scanner / Ramparts"), 2026-08-20, triggered by PR #321.

## Current state

`.github/workflows/agent-security.yml` runs two jobs on every push/PR to `main`/`develop`:

| Job | Tools | Runtime (this run) |
|---|---|---|
| `gitleaks` | gitleaks (secrets) | **7s** |
| `agent-surface` | aguara, agent-audit, skill-scanner (per-SKILL.md loop), mcp-scanner, Ramparts | **~13m26s** |

`gitleaks` is the right shape: one focused tool, its own job, fast. `agent-surface` is not:
5 distinct scanners bundled sequentially in one job (`scripts/ci/run_agent_security_scans.sh`),
each contributing setup + install time that dominates actual scan time.

## Findings

1. **Unpinned supply-chain dependency in a security scanner.** `run_agent_security_scans.sh`
   does `go install github.com/garagon/aguara/cmd/aguara@latest` — floating `@latest` in a
   tool whose entire job is catching supply-chain/agent-surface risk. A compromised or
   behavior-changed release of aguara would be pulled silently on the next CI run with no
   diff to review. Pin to a commit SHA (matches this repo's own convention for every
   `actions/*` step in the same workflow file, which are all pinned to SHAs).
2. **No pip cache.** `pip install cisco-ai-skill-scanner cisco-ai-mcp-scanner` and the
   editable install of `agent-audit` run fresh every job. `actions/setup-python` supports
   `cache: pip` directly; not set here.
3. **`agent-audit` is git-cloned fresh every run**, not pinned via a cached/vendored
   install — the script does pin the ref (`AGENT_AUDIT_REF`, good), but re-clones over
   the network each run instead of caching the clone keyed on that ref.
4. **Sequential, not parallel.** The skill-scanner loop invokes once per `SKILL.md`
   directory found under `bin/agents` and `bin/orama-system/skills` — currently serial.
   These are independent per-directory scans with no shared state; a matrix job or
   simple backgrounding would cut wall-clock roughly proportional to skill-dir count.
5. **One job, one failure domain.** Bundling 5 tools in one job step means a single tool's
   failure or hang blocks visibility into the other 4 until the whole step exits — and
   retries re-run everything, including tools that already passed. `gitleaks`'s own job
   split in this same file is the counter-example already in the codebase.

## Recommendation (do not restructure the security *logic*, only its runtime shape)

This is a CI-efficiency pass, not a scanner-coverage change — every existing check stays,
same severity gates, same baseline files. Scope:

1. Pin `aguara` to a commit SHA via `AGUARA_REF` (same pattern as `AGENT_AUDIT_REF` already
   in the script), not `@latest`.
2. Add `cache: pip` to `actions/setup-python` in `agent-surface`.
3. Cache the `agent-audit` clone keyed on `AGENT_AUDIT_REF` (actions/cache, path = the
   clone dir, key includes the ref so a ref bump invalidates automatically).
4. Split `agent-surface` into per-tool jobs (aguara, agent-audit, skill-scanner, mcp-scanner,
   Ramparts) running in parallel, mirroring the existing `gitleaks` job shape. Skill-scanner's
   per-directory loop can stay a single job with a `strategy: matrix` over discovered
   `SKILL.md` directories if directory count grows enough to matter; not required at
   current scale.
5. Keep `FAIL`/`WARN` semantics unchanged (`run` = blocking, `warn_run` = non-fatal) —
   this is a scheduling change, not a policy change.

## Explicitly out of scope here

- Changing which findings are fatal vs. warn-only (that's a §6/§9 policy decision, not a
  runtime one — see `32-agentic-security-controls.md`).
- Adding new scanners.
- Touching the `TOXIC_CROSS_002` baseline suppression for skills scans (documented,
  intentional, unrelated to runtime).
