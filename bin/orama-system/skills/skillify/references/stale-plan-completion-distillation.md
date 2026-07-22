# Stale-Plan Completion — Decision-Process Distillation (Fable 5 → smaller models)

Distilled 2026-07-19 from the live fleet-mesh completion run (mother plan:
`docs/next/fleet-mesh/2026-07-08-self-healing-mesh-degradation-modes.md`),
written so a smaller model (Sonnet 5 Medium, qwen3.5:9b, gemma-4-26b) can
execute the same class of task — "make plan X work flawlessly out of the box"
— without a frontier model's judgment. Follow the steps in order; every rule
here was load-bearing in the real run.

## The core insight (memorize this one)

**A plan document's own status section is evidence about the past, not the
present.** The fleet-mesh plan said, in bold, verified-by-grep language:
"NONE of the 6 phases have been started; all 10 success criteria unchecked."
That was true when written — and 9 days later ~95% of it was BUILT, by other
agents, without the doc being updated. An agent that trusted the doc would
have re-implemented everything (wasted days, duplicate-implementation
conflicts). An agent that trusted nothing would have audited forever.

The rule: **re-verify the plan's own named symbols against the CURRENT code
before writing anything.** Every named symbol/endpoint/flag in a plan is a
grep probe. Run them all, cheaply, first.

## Step-by-step procedure

1. **Read the plan fully.** Extract: (a) every named symbol, file, endpoint,
   CLI flag; (b) the success-criteria checklist; (c) which repo owns each
   piece. Do not skim — the criteria list IS your work plan.
2. **Sync to latest origin/main first** (`git fetch && git pull --ff-only` on
   a clean checkout; stash-with-tag anything dirty that isn't yours and
   record the stash SHA on the coordination board). Concurrent agents move
   main *while you work* — a plan audited against a stale main is a stale
   audit.
3. **Grep-audit every criterion** against the synced tip:
   `git grep -l "SymbolA\|SymbolB\|flag-c" origin/main -- '*.py' '*.sh'`.
   Sort criteria into: BUILT (symbol exists), MISSING (no match), UNKNOWN
   (needs a runtime check, not a grep).
4. **Run the tests the plan names, don't just confirm files exist.** A test
   FILE existing proves nothing — run it. In the real run this is what
   exposed the two genuine gaps a grep audit alone missed:
   - an import-time crash (FastAPI 204-with-body assertion) that no grep
     would flag, and
   - a truncated module (`ip_resolver.py`) whose functions were still
     *imported* by other files (grep says "exists") but no longer *defined*.
5. **For each genuine gap, find root cause in git history before writing:**
   `git log --oneline -- <file>` then `git log -S '<deleted symbol>'`. In
   the real run this revealed the truncation was ONE bad commit that
   replaced a 324-line file with its 98-line patch fragment — so the fix is
   *recovery + graft* (restore last-good version, re-apply the bad commit's
   one legitimate change on top), NOT rewriting the module from memory.
   Never re-implement what git history already contains.
6. **After any recovery, add a contract test that would have caught the
   damage.** The truncation went unnoticed because nothing asserted the
   public API surface existed. A 10-line parametrized "every public name is
   callable" test converts silent deletion into loud failure, forever.
7. **Implement only the genuinely-MISSING criteria**, reusing the file's own
   conventions (in the real run: the `--relay` client reused the target
   script's existing discovery/token/timeout helpers rather than inventing
   new ones — read the file's other functions first, then match them).
8. **Verify fixes two ways: synthetic AND real.** Unit tests with mocks
   prove logic; then run against real state (the real resolver returned the
   real current Win IP from live discovery). A fix verified only
   synthetically is half-verified (see PT lesson_7155c5157bd4).
9. **Full-suite gate before the end-to-end run.** Your targeted tests
   passing says nothing about collateral damage. Run the whole suite, then
   the plan's own E2E path (here: `start.sh` roundtrip) LAST — E2E on top
   of a red suite wastes the expensive step.
10. **Report criteria as a table with evidence per row** — "BUILT (by
    others, commit X)", "FIXED here (commit Y)", "verified: test/command Z".
    Never collapse to "done". The next agent inherits your table the way
    you inherited the stale plan — make yours trustworthy longer.

## Anti-patterns this procedure exists to prevent

| Anti-pattern | What it caused / would have caused |
|---|---|
| Trusting the plan's status block | Full re-implementation of ~95%-built work |
| Grep-only audit (no test runs) | Missing both real bugs (import crash, truncation) |
| Rewriting a damaged module from memory | Losing the P1-P6 chain's accumulated edge cases |
| Patching without `git log -S` root-cause | Treating one destructive commit as N unrelated bugs |
| "Tests exist" = "tests pass" | Shipping a suite that fails at collection |
| E2E before full-suite gate | Burning the expensive roundtrip on a known-red tree |
| Inventing facts a task brief asserts (e.g. a constant name) | Fabricated docs; violates "ground every claim in the repo" |

## Delegation notes (for the orchestrator dispatching this)

- This procedure is mechanical enough for a mid-tier model EXCEPT steps 5
  and 7 (root-cause judgment, convention-matching). Dispatch those to the
  strongest available non-frontier tier; steps 1-4 and 9-10 are safe for
  local 9B-27B models with the exact commands given.
- Coordination hygiene while running: register on the board, pulse ~60s,
  drop status markdown to the peer inbox at phase boundaries, and record
  any stash SHAs on the board (peers cannot see your terminal).

## Provenance / re-verification

- Source run: orama branch `2026-07-19-002-fleet-mesh-oob-fixes`
  (ip_resolver recovery commit + relay client commit), PT board agent
  `claude-fable5-fleet-mesh`.
- Re-verify volatile claims:
  `git log --oneline -3 -- src/utils/ip_resolver.py`
  `python3 -m pytest tests/test_ip_resolver_contract.py tests/test_probe_lan_peer_relay.py -q`
  `bash start.sh --fleet-status`

AUDIT: 2026-07-19 skillify reference create — distills the fleet-mesh
completion run's decision process for smaller models; verified against the
run's own commits and test results.
