# LLM Provider / Harness Failure Modes

> **Role:** a sourced lookup of failure modes that are specific to a model
> provider, agent harness, or connector — the ones agents keep falling for
> because the failure is invisible from inside the session. Read it before
> delegating to, or accepting work from, one of these channels.
> **Sourcing rule:** every row cites a Perpetua-Tools (PT) lesson id. The
> "claim" column paraphrases that lesson's own claim text; the lesson is the
> authority, this card is the index. Rows are not inferred from general
> knowledge of the vendors.
> **Status tags:** `main` = on PT `main`. `#441` = only in PT PR #441
> (head b63891c6) — **pending merge**; re-verify the id exists after that PR
> lands, and treat the row as provisional until then.
> **Why provider-keyed:** different providers fail differently, and a lesson
> learned about one reads as "a quirk" to an agent on another. Keying by
> provider lets the *delegating* agent look up its worker's traps.

---

## Claude Code / Agent tool / claude.ai sandboxes

| PT lesson | Status | Failure | Safeguard |
| --- | --- | --- | --- |
| `lesson_80225a223f41` | main | `Agent()` called again to "resume" a subagent spawns a fresh, unrelated agent with no prior context | Resume with `SendMessage(to=<agentId>)`; never re-spawn |
| `lesson_39b634f974c7` | main | A user message sent mid-turn appeared to reach a running background subagent directly, bypassing the main session | Do not assume subagent isolation; relay-sensitive instructions through the orchestrator and re-check what a subagent actually received |
| `lesson_a31e13420061` | main | A bare `cd dir && cmd` persists the cwd for every later command in the Bash tool | Use a subshell or absolute paths; never leave cwd in another worktree |
| `lesson_df682761347f` | main | claude.ai web/mobile ephemeral sandbox can be wiped between turns, losing uncommitted work | Commit and push as you go; the sandbox is not durable storage |
| `lesson_0f75262a1392` | main | Naive agents execute skill markdown literally, so imperative setup commands in a skill are an accidental prompt injection | Describe registration/env setup in prose, not as runnable commands |
| `lesson_9f9dec0d3314` | main | `git status` showing changes in a shared checkout may be a *live* sibling session's work | Check status before switching branches; never discard "stray" state in a shared checkout |

## Codex / ChatGPT Work (GitHub connector)

| PT lesson | Status | Failure | Safeguard |
| --- | --- | --- | --- |
| `lesson_51791f8ae4a1` | **#441** | Connector returns an empty or omitted `fetch_file` payload for an oversized tracked file; rebuilding from it silently publishes an empty/truncated file | Treat it as *unavailable data*, not an empty file; stream the verified local bytes and require remote blob SHA == local `git hash-object` |
| `lesson_d745015dde81` | **#441** | Capped tool channel mangles large UTF-8/JSONL when chunked arbitrarily; base64 groups split mid-quantum | Stream raw bytes as base64 chunks whose size is divisible by 3 (120000-byte chunks used), concatenate whole groups, verify final blob SHA |
| `lesson_590ae6342a41` | **#441** | A failed local reconstruction still moves a shared remote ref | Prove every tree entry by blob-SHA compare, then expected-head compare-and-set; a failed reconstruction must leave the ref unchanged |
| `lesson_4b650ec5b970` | main | Replaying review fixes from summaries/commit hashes that belong to a rewritten ancestry | Verify the live PR branch first; reapply only the missing behavioural delta |
| `lesson_24b4facd84d9` | **#441** | Catch-up merge/rebase when the PR head advances concurrently | Re-read head, reapply verified delta — see [`concurrent-head-reapply.md`](concurrent-head-reapply.md) |

The three **#441** safeguards compose: a guarded linear update is *expected-head
CAS + byte-aligned chunks + blob-SHA proof*. Any one alone leaves a hole.

## Review voices (Codex, Claude subagents, bots)

| PT lesson | Status | Failure | Safeguard |
| --- | --- | --- | --- |
| `lesson_a36cfa62ffb9` | main | Independent reviewers disagree, or one carries a verified-false claim, and the synthesis silently "corrects" it | Save each voice verbatim in its own file with inline `[FALSE …]` / `[CORRECTION …]` annotations |
| `lesson_9e9515189f99` | main | A finding deferred as "pre-existing, not in this PR's diff" from memory or a generic scan | Verify with `git log --oneline <base>..HEAD -- <file>` against the PR's real base |

## Kimi CLI

| PT lesson | Status | Failure | Safeguard |
| --- | --- | --- | --- |
| `lesson_3e67d96a87f5` | main | `kimi -p` combined with `--yolo` is a hard error | `-p` is already non-interactive; drop `--yolo` when scripting |

## Cline / ClinePass

| PT lesson | Status | Failure | Safeguard |
| --- | --- | --- | --- |
| `lesson_58ec2dc24e62` | main | Fan-out routed by model slug alone; model reached through a different provider than intended | Verify provider auth, not only the slug; stop and repair rather than silently switching models |
| `lesson_49e8701ba9e9` | main | Writing a provider config into the tool's settings store does not make the CLI use it | Check for a separate top-level provider-selection default before assuming the write took effect |
| `lesson_40b554e8fb35` | main | A rate-limited peer's stale job-board claim blocks re-claim | `queue fail <task_id> --notes <reason>` to release, then claim under your own id |
| `lesson_4b5e00553026` | main | Heartbeat cleanup of DEAD agents does *not* release their stale job-queue claims | Release job-queue claims explicitly; do not rely on heartbeat cleanup |

## Antigravity / Gemini-style headless agents

| PT lesson | Status | Failure | Safeguard |
| --- | --- | --- | --- |
| `lesson_78b0efde1631` | main | Sandboxed/headless treated as sufficient approval to edit or fan out | Run a read-only plan pass first; require explicit human confirmation before accept-edits or background edit fan-out |

## PR-management connectors

| PT lesson | Status | Failure | Safeguard |
| --- | --- | --- | --- |
| `lesson_4a38f0e95fcf` | main | `ManagePullRequest update_pr` replaces the *entire* PR body; passing only the newest follow-up erases the rest | Read the live body, back it up, reconstruct original summary plus chronological follow-ups, then write the integrative body |

## OpenAI-compatible third-party APIs

| PT lesson | Status | Failure | Safeguard |
| --- | --- | --- | --- |
| `lesson_3c85823ef46f` | main | A vendor doc's exact sample call is not guaranteed correct; an optional-looking parameter (project header / SDK kwarg) can silently break auth with a 401 despite a valid key | Test the minimal call; if auth fails with a valid key, remove optional parameters before suspecting the key |
| `lesson_ad340c4ee7cb` | main, *provisional* | HTTP libraries/SDKs follow redirects by default, a control surface separate from URL/DNS validation | Disable or validate redirects explicitly; do not treat host validation as redirect safety |

---

## How to use this card

1. **Delegating:** find your worker's section; put its safeguards in the
   dispatch prompt as constraints, not hopes.
2. **Accepting work:** a clean-looking result from a channel with a row here
   needs the matching verification (blob SHA, live-branch read, base-ref log),
   not a skim.
3. **New failure:** capture it in PT through `learn.py`
   (stage → graduate → render), then add one row here with the lesson id. This
   card never carries a claim that has no lesson behind it.

## See also

- [`concurrent-head-reapply.md`](concurrent-head-reapply.md) — publishing a
  delta onto an advanced head.
- [`post-review-micro-remediation.md`](post-review-micro-remediation.md) —
  Phase 1 verification of review claims (never apply reviewer patches blindly).
- [`multi-agent-collaboration-protocol.md`](multi-agent-collaboration-protocol.md)
  — shared-checkout and claim-collision invariants.
