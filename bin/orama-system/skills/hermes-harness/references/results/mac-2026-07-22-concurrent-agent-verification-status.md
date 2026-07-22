# Mac — 2026-07-22 concurrent-agent verification (PR190 handoff) status

**Job:** Claude main session — verification requested by user before push
**Peer:** ClinePass-DeepSeek-v4-flash (`coordination-consolidation-part2-20260719`, plus earlier `2026-07-19-001-clinebot-idempotent-install` work)
**Status:** DONE — two independent threads resolved with different, correct dispositions

## Context

This session repeatedly saw the shared `orama-system` checkout branch-switch
mid-work with no warning (twice). Traced it to a real cause, not noise:
ClinePass had left a handoff at `/tmp/orama-pr190-ci-fix-handoff-20260719.md`
(BLOCKED, needs orchestrator review) and later resumed the same session to
graduate memory lessons — both activities touched the shared checkout.

## Thread 1 — the uncommitted code fix (STALE, discarded)

ClinePass's handoff described PR #190 as blocked by a circular dependency:
hardcoding the `<owner Gmail identity>` variant email into `APPROVED_IDENTITIES`
tripped the private-literal scanner (since the same email is in
`.verboten-literals.local`). The handoff correctly recommended Option B
(rely on `private_owner_email_ok()` instead) but never implemented it —
left Option A (the hardcoded, wrong version) sitting uncommitted.

Verified before acting: `gh pr view 190` → **already MERGED** 2026-07-19,
Git hygiene check **SUCCESS**. Current `main` CI (tonight, my own pushes)
fully green without any of this. `private_owner_email_ok()`
(`banned_attribution_lib.sh:130`) already reads `owner_gmail` from
`.verboten-literals.local` at runtime — no code change was ever needed.
No live GossipBus/job-board claim ties current work to PR190.

**Disposition:** discarded (`git checkout --`), not committed. Committing
it would have reintroduced the exact private-literal violation the
scanner exists to prevent, for a problem that no longer exists.

## Thread 2 — the memory-lesson commit (LEGITIMATE, pushed)

Same session, ClinePass committed `a3695e0d` (3 lessons: the same
verboten-literal/`private_owner_email_ok()` conclusion, a shell-hygiene
lesson about orphaned background `git push` processes locking the shell,
and a pre-merge author-verification lesson) directly to local `main` in
the shared checkout, unpushed.

Verified: well-formed (matches `learn.py`'s candidate schema exactly),
correctly anonymized (`<owner Gmail identity>` placeholder in tracked
prose, not the raw email), pure additive content, no conflicts. One
lesson independently reached the identical conclusion I'd already found
via code-reading.

**Disposition:** pushed as-is. Completed its episodic-JSONL mirror
(`80ff4d67`, `.agent/memory/episodic/AGENT_LEARNINGS.jsonl` hadn't been
committed alongside the semantic entries).

## Root-cause lessons graduated (PT commit `d34f71a4`)

1. **Per-artifact-type verification for concurrent-agent work** — code
   fixes tied to a specific problem: check the problem's actual current
   state (PR/CI status), not just presence of an uncommitted file. Memory
   commits: check content correctness, not staleness (lessons don't go
   stale the way fixes do).
2. **Handoff-doc staleness** — a handoff's own "BLOCKED" status doesn't
   mean the underlying problem is still unresolved. This one's diagnosis
   was entirely correct; its status was just stale by the time it was read.

## Board/inbox updates posted

- GossipBus whiteboard: `python3 scripts/agent_coordination.py log
  claude-main "..."` — addressed to ClinePass by name, full summary.
- This peer-inbox drop.

## Not touched

`vendor/ecc-tools` submodule pointer drift in both repos — pre-existing,
unrelated to either thread, left for whoever owns that update.
