# Mac G1 frugality baseline — blocked (v1 scope)

**Date:** 2026-06-29  
**Host:** mac (OpenClaw)  
**Repo:** `orama-system` @ `main` (`d7e039c`)  
**Scope guard:** `docs/plans/2026-05-29-03-v1.1-definitive.md` §2 (tiers 0–2 local-first), §11 G1 (≥85% tier≤2)

## Search

| Path | Expected artifact | Found |
|------|-------------------|-------|
| `bin/orama-system/skills/code-review/scripts/frugality-report` | G1 telemetry dashboard (`--dry-run`, `--last 1h`) | **Missing** — only `crg-embed-mode` present |
| `tests/v1_1/test_realistic_session.py` | 100-call realistic session harness | **Missing** — `tests/v1_1/` directory does not exist |
| `tests/` (grep frugality/G1) | Related tests | No matches |
| `scripts/eval/oramasys_trigger_eval.py` | AC8 trigger eval (not G1) | Exists; unrelated to tier telemetry |

Git history on `main`: no commits ever touched `frugality-report` or `test_realistic_session.py`.

## Run attempts

```bash
cd orama-system
bash bin/orama-system/skills/code-review/scripts/frugality-report --dry-run
# → No such file or directory

python3 tests/v1_1/test_realistic_session.py
# → No such file or directory
```

Telemetry inputs (per plan §11): `.state/traces/*.jsonl` — **not present** on Mac (`~/.openclaw/state/traces/` also absent). No OTel `ot.tool.tier` spans to aggregate.

## G1 tier≤2 ratio

**Not measurable** — blocked by missing harness + missing trace sink.

| Blocker | Detail |
|---------|--------|
| P1 harness not shipped | `frugality-report` script never landed on `main` despite plan §11 AC |
| Session sim absent | `tests/v1_1/test_realistic_session.py` not in tree |
| No trace data | `frugality_router.py` + OTel exporter spec'd in PT (`orchestrator/`) — not present locally; no `.state/traces/` |
| v1 scope | Measurement would be tiers 0–2 only; tier≥3 out of scope for this baseline |

## Next unblock (v1 only)

1. Land `frugality-report` under `code-review/scripts/` (reads PT `.state/traces/*.jsonl`).
2. Land `tests/v1_1/test_realistic_session.py` (100 synthetic calls, assert ≥85% tier≤2).
3. Ensure PT `frugality_router.py` emits `ot.tool.tier` spans to trace JSONL.
4. Re-run: `frugality-report --dry-run` then `frugality-report --last 1h` for live G1.

**Status:** baseline **deferred** — infrastructure gap, not a measured ratio.
