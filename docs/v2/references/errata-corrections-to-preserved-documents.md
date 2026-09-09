# Errata — Corrections to Preserved Historical Documents

**Status:** corrections only. The provenance-pinned source documents remain
byte-for-byte unchanged. Apply these corrections through the current integrated
plan and successor implementation, not by rewriting the historical inputs.

See `claude-input-provenance-2026-09-09.json` for source hashes.

## E1 — checker pipelines must preserve the checker exit status

The preserved remediation plan includes examples where output truncation can
replace the real `pytest`/`ruff` exit code and where `|| true` can turn failure
into apparent success.

Correct pattern:

```bash
out_file="$(mktemp)"
if checker-command >"$out_file" 2>&1; then
  status=0
else
  status=$?
fi
tail -30 "$out_file"
rm -f "$out_file"
exit "$status"
```

The concrete successor hook may use a different implementation, but its
observable contract is the same: output truncation is presentation; it does not
change the checker result. Advisory hooks must be labelled advisory rather than
masquerading as passing tests.

## E2 — command-family wildcard rules are not read-only authorization

A trailing wildcard on command names such as `git branch`, `find`, `jq` or
`sort` does not prove read-only behavior. Some argument forms mutate refs,
delete files, write output or execute callbacks.

Required successor rule:

- prefer structured read APIs;
- where shell admission is necessary, validate supported argument/effect forms;
- unknown, malformed or mutating forms take the ordinary deny/approval path;
- negative tests prove rejection before side effects;
- no legacy `.claude/settings.json` change is authorized by this errata.

This maps to the M3/M4 admission contract and Phylax/runtime-policy work.

## E3 — target access is verified through authorized work, not probe writes

The preserved migration plan assumed a target-scoped session could begin on a
particular successor repository.

Correction:

- favorable-looking capability metadata is not permission to manufacture a
  write probe;
- do not create empty branches, commits, draft PRs or other external state just
  to test access;
- verify target access through an already-authorized meaningful operation or
  owner-provided evidence;
- if required access is unavailable, record the exact blocker and continue
  independent read-only planning rather than silently changing target scope.

M0 records the observed authorization/evidence for every selected write target.

## E4 — memory snapshot creation must fail closed

The preserved runbook's literal `/path/to/perpetua-tools` is a placeholder. A
replacement that blindly expands an unset `$PERPETUA_TOOLS_ROOT` is also unsafe:
it can become `/.agent` and copy unrelated data if such a directory exists.

Corrected runnable boundary:

```bash
: "${PERPETUA_TOOLS_ROOT:?Set PERPETUA_TOOLS_ROOT before running Step 1}"
test -d "$PERPETUA_TOOLS_ROOT/.agent" || {
  printf '%s\n' "Missing Perpetua-Tools .agent directory" >&2
  exit 1
}
SNAP="$(mktemp -d)/agent-memory-snapshot"
cp -a "$PERPETUA_TOOLS_ROOT/.agent" "$SNAP"
```

The snapshot stays outside worktrees and preserves bytes. Subsequent sanitation
operates on the migration copy, never on the v1 source.

## E5 — the old MiniGraph R0–R2 implementation plan is historical

Any preserved/synthesized passage that still schedules these as future work is
superseded by live successor evidence:

- returned-value awaitability;
- strict dict deltas;
- END-only/validated routing including unknown targets;
- detached compile semantics;
- exact max-step diagnostics;
- optional interrupt payload;
- `_run()` as sole scheduler;
- `aobserve()` rich and `asteps()` sanitized projections;
- generic observer fan-out and per-listener payload isolation.

Current future work begins at R3 reducers/joins, R4 durable deterministic
resume, and R5 GraphSpec/application validation.

## E6 — old corrective-branch status language is stale

Canonical Orama docs 57/59 preserve historical wording that the unknown-route
and per-listener-isolation corrections were only on a post-merge branch. Live
`oramasys/perpetua-core` now contains both behaviors and dedicated regression
coverage.

Do not use the stale branch-status sentence to reopen those fixes. Repair the
legacy canonical docs in a separately scoped documentation parity change if
they are modified; PR #351 records the current truth for migration planning.

## E7 — release dependency checks must not ban legitimate target subprocesses

A previous synthesized M8 statement rejected all `runtime shell calls`. That is
overbroad because approved provider/platform/tool adapters can legitimately use
subprocesses.

The actual forbidden boundary is legacy dependence:

- no shell/subprocess invocation of v1 scripts, binaries, policy authorities,
  memory writers or provider paths;
- no implicit sibling checkout discovery/fallback.

Target-owned subprocess adapters remain allowed when explicitly declared,
argument/effect validated, lifecycle/cancellation tested, and independent of
v1.

## E8 — workstation-specific plugin cache paths are non-portable

Tracked planning documentation must not embed a path such as a specific
`/root/.../superpowers/6.3.0/` cache location.

Use `$SUPERPOWERS_ROOT` as a neutral report locator after defining it as the
installed Superpowers package root. This does not promise that every harness
exports that environment variable; it is a portable documentation convention.
