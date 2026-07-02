# Lessons — 2026-07-02 pilot (Fable-5 orchestrator session)

1. **Partial merge restores are a CI regression class.** `033737c` deleted a
   workflow AND its checker script; a later commit restored only the workflow.
   Every main push then failed with `[Errno 2] can't open file` exit 2. Rule:
   when restoring any CI workflow, grep it for every path it invokes and restore
   those in the same commit. One `gh run view --log-failed` beat two external
   root-cause analyses that lacked log access.

2. **Verify before rebuild — again.** Two polished external deliverables
   hypothesized (a) validator-test failure and (b) contract-drift failure. The
   actual failure was a missing file. Authenticated `gh` log access (10 seconds)
   refuted both. Never act on deduced CI root causes when logs are one command away.

3. **Filename collision ≠ mirror drift.** PT `src/utils/endpoint_policy_core.py`
   (transport identity: scheme+host+port reconstruction) and orama
   `src/utils/endpoint_policy_core.py` (SSRF/security validator) are different
   modules. A raw `diff` screamed DRIFT; reading 20 lines of each showed
   different-purpose. Check module docstrings before declaring drift.

4. **The hardened validator already landed in orama.** Wrapped `parsed.port`
   (throwing boundary), `ipv4_mapped` unwrap (CVE-2026-26324 class), link-local
   block, hypothesis fuzz suite — all present; 1019 tests green. PT still needs
   the shared `packages/endpoint-policy/` extraction (delegated to Win, coord-023).

5. **Local-model coordination costs zero frontier tokens.** The Win 27B
   co-orchestrator ACCEPTed the division of labor via one LM Studio
   `chat/completions` call with a forced `VERDICT: | REASON: | BLOCKERS:` format.
   Structured-reply constraints make small local models reliable coordinators.

6. **Claude subagent limits are an availability class, not an error.** All 5
   workflow subagents died on session-limit simultaneously. The fallback ladder
   that worked: inline main-loop execution + local models. Encode: when
   delegation fails on limits, degrade to (a) local LM Studio/Ollama for
   reasoning-light subtasks, (b) inline for verification, never retry-storm.

7. **H6 validated.** Win 27B beats Mac 9B on real `autoresearch_bridge` work
   (3 vs 5 iterations, 45s vs 70s; 38/38 rubric in 10.77s single-pass) —
   dual-path orchestration prioritizing the Win peer when reachable is correct.

8. **Git push can hang silently after a clean rebase.** Two foreground timeouts,
   then `run_in_background` succeeded. Pushes belong in background jobs with
   completion notification, per the hard-deadlines discipline.
