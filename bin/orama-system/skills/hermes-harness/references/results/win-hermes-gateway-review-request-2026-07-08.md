---
source: win
topic: coord/hermes-gateway-review-request
priority: normal
requested_by: cyre (Win RTX 3080)
---

# Hermes Gateway independent work — flagged for review

This session's work is marked **Hermes Gateway independent work** and
queued for independent review by the Mac co-orchestrator and any other
Windows AutoResearcher/coder node (including the incoming 3rd node / 2nd
Windows, RTX 5080) before being treated as final. Nothing below is
self-certified — flagging it here is the request for that second look.

## What to review

1. **`win_job_queue.py` code review + fix** — commit
   [`e9d3fa9`](https://github.com/diazMelgarejo/orama-system/commit/e9d3fa93040bca6708c01f45cf53652ce52c5c9a)
   on orama-system. An uncommitted, unauthored stashed WIP to
   `is_actionable_assignment()` was proven unsafe by running the existing
   test suite directly (broke 2/6 tests), replaced with a narrow
   `mac-*-hypothesis-*-real-task*` allowlist. Origin of the original stash
   was never conclusively identified — **if this was your in-progress
   work, please compare against your intent**, since it was independently
   rewritten rather than continued from your stash.
2. **`coord_pulse.ps1` `-Args` → `-LanArgs` fix** — applied the same
   PowerShell automatic-variable-collision fix already landed in
   `start.ps1` to its sibling `coord_pulse.ps1`.
3. **`check_commit_message.sh` — added `fable` to the approved co-author
   marker list** — please confirm this reads correctly on your platform;
   a CRLF-contamination bug was found and fixed in this same file during
   the same session (Linux CI `set -euo pipefail` broke on `\r` inside an
   option name) — worth a second confirmation the fix is clean end-to-end.
4. **3rd fleet node onboarding** —
   [`windows-node-onboarding.md`](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/first-run-setup/references/windows-node-onboarding.md)
   is new and untested against a real fresh machine. First actual use will
   be the RTX 5080 node — please flag anything that doesn't match reality
   on your own node's history.
5. **PT `.agent/tools` UTF-8 stdout fix** — commit
   [`900ce04`](https://github.com/diazMelgarejo/Perpetua-Tools/commit/900ce04)
   on Perpetua-Tools. `graduate.py`/`learn.py`/`recall.py`/`show.py` were
   crashing on Windows cp1252 console encoding when printing unicode
   arrows; fixed via `sys.stdout.reconfigure(encoding="utf-8")`. Worth
   confirming this doesn't regress anything on macOS (should be a no-op —
   macOS Terminal is already UTF-8 — but flagging since it's a shared file).

## Both repos are resynced

`orama-system` and `Perpetua-Tools` `main` are both pushed and current as
of this drop. `orama-system/main` went through a history rewrite this
session (confirmed via `scripts/git/reanchor_scan.sh`) — if your local
clone still shows large ahead/behind counts against a stale ref, that's
expected; don't force-push over it, just re-fetch and compare content via
`git show <sha>:<path>` rather than commit-graph position.

## No action required to unblock

This is a review flag, not a blocking gate — the work above is already
merged to `main` on both repos. Push back here (or drop a reply doc back
to this machine's inbox) only if review surfaces something that needs
correcting.
