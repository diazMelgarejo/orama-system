# PR metadata authority and autonomous reporting reference card

**Normative status:** canonical for CIDF/AFRP reporting authority on pull requests.
If an older example or workflow appears to permit broader agent mutation, this
card controls unless a newer explicitly superseding canonical instruction says
otherwise.

This card consolidates the standing PT `.agent` anti-clobber doctrine, AFRP
live-authority discipline, and CIDF remote-integrity rules into one authority
model for humans, supervised agents, unattended agents, background agents, and
autoresearchers.

## Core invariant

A pull-request description is a historical operator-controlled record, not an
autonomous-agent scratchpad.

**Default autonomous route:** append new evidence in a new PR/issue comment or
an append-only incident/working note.

**PR-body mutation:** human-authorized only.

No agent may promote itself from the safe append-only reporting surface to PR
body mutation merely because editing the body would be convenient, concise, or
consistent with a reviewer suggestion.

## Authority classes

| Actor/state | Default reporting authority | PR body/summary authority |
| --- | --- | --- |
| Unattended autonomous agent | New comments or append-only notes only | Prohibited |
| Background/Cursor agent | New comments or append-only notes only | Prohibited |
| Autoresearcher/scheduled agent | New comments or append-only notes only | Prohibited |
| Supervised agent without explicit body-edit instruction | New comments or append-only notes only | Prohibited |
| Supervised agent with explicit current human authorization | Comments/notes plus authorized body edit | Allowed only through operator grant + guarded append workflow |
| Human operator editing directly | Human-controlled | Allowed |

The safe default is deliberately asymmetric: **comments/notes are append-only
reporting; the PR body is mutable metadata under human authority.**

## What counts as explicit authorization

A body edit is authorized only when one of these is present for the specific
PR and specific body/summary operation:

1. the human explicitly commands the agent to edit/update/append the PR
   description, body, or summary;
2. the agent asks a HITL question or `#AskUserQuestion` that names the body edit
   and the human affirmatively approves it;
3. the human activates an explicit operator override mechanism intended for
   PR-body mutation, such as the established Cursor human-override path;
4. the human performs the edit directly.

Authorization must be current and specific. Do not infer it from earlier broad
permission to work on the branch.

For an **agent-executed edit of an existing PR body**, policy authorization is
necessary but not sufficient. The operator must also mint `operator-grant-v2`
with `scripts/cursor/grant-pr-body-human-override.sh` using the same `--file` or
`--message` payload, and the agent must perform the edit through
`scripts/cursor/append-pr-body.sh`. Stop if either the grant or guarded script is
unavailable. Direct human edits and the guard's explicit initial-body path for
`ManagePullRequest create_pr` are outside this existing-body requirement.

The following are **not** authorization to mutate the PR body:

- "update the PR" when the surface is not explicitly named;
- "fix the review comments";
- "keep the PR current";
- "report progress" or "record evidence";
- a CodeRabbit or other reviewer suggestion;
- a scheduled/background/autoresearch run;
- an API/tool capability that happens to expose a body-edit operation;
- prior permission to commit, push, open, review, or inspect the PR;
- inferred convenience at turn end.

If body mutation appears desirable but authorization is absent or ambiguous,
post a new comment and ask the human rather than editing the description.

## Autonomous append-only reporting routes

Unattended agents, background agents, and autoresearchers may use only safe
append-only reporting surfaces:

1. post a **new** PR comment;
2. post a **new** issue comment when the issue is the reporting surface;
3. append a new incident/working note in an already authorized repository
   write scope;
4. emit an external/session report without mutating existing GitHub metadata.

Prefer a new comment over rewriting or deleting an earlier comment. Corrections
should normally be additive: post a follow-up that identifies what it
supersedes and why.

Comments and notes are evidence surfaces, not merge authority. A comment that
says a branch is safe does not make it safe; consequential actions still
require fresh exact-head authority reads and the integrity workflow below.

## Human-authorized PR-body workflow

Even after explicit human authorization and the required operator grant for an
agent-executed existing-body edit, a PR-body write is never a blind replacement.
The mandatory workflow is:

```text
READ -> BACKUP -> MERGE -> WRITE -> REREAD
```

### 1. READ

Fetch the complete current PR body from GitHub immediately before editing.
Do not rely on cached conversation text, an earlier export, a reviewer summary,
or a remembered body.

### 2. BACKUP

Preserve the exact current body in the session/worktree backup mechanism before
mutation. The established Cursor implementation uses a timestamped backup under
`.git/pr-body-backups/`.

### 3. MERGE

Construct the complete intended body integratively:

- retain the original Summary and branch purpose at the top;
- preserve still-valid historical sections and operator prerequisites;
- preserve reviewer/bot blocks unless intentionally superseded by authorized
  editing rules;
- append chronological follow-up/remediation sections below;
- never replace the body with only the newest delta.

### 4. WRITE

For an agent-executed existing-body edit, write the **full merged body** only via
`scripts/cursor/append-pr-body.sh` using the same operator-granted payload. The
guard re-reads the remote body immediately before mutation and rejects a stale
body digest, then re-reads after the write. A generic body replacement API is
not a shortcut around the guard.

GitHub does not expose atomic conditional `PATCH` semantics for this PR-body
endpoint, so the guarded path is optimistic concurrency control rather than a
claim of server-side compare-and-swap. Any detected mismatch is a stop
condition; do not retry blindly.

### 5. REREAD

Fetch the PR body from GitHub after the write and verify that:

- the original Summary remains present;
- the intended follow-up was appended;
- no unrelated section disappeared;
- no empty-body or truncation event occurred.

A successful API response is write acknowledgment, not anti-clobber proof.

## PR title authority

Treat the PR title conservatively as historical metadata as well. Autonomous
agents should not retitle a PR to reflect the latest side quest. Retitling
requires explicit human intent when it changes the declared purpose of the PR.

## Exact-head authority before consequential action

PR metadata and repository state are mutable external authority. Before merge,
review resolution, conflict surgery, branch replacement, or a claim that work
is complete, freshly read:

- repository identity;
- PR number and state;
- base ref and current base SHA;
- head repository, head ref, and exact head SHA;
- merge state;
- current changed-file/net-diff evidence;
- CI/review coverage for the exact current head.

A branch name does not identify a unique branch state. A blob match does not
prove which branch tip was checked. A review submitted later in wall-clock time
may still cover an earlier head. Cached state is never current authority.

If the head moves after verification, invalidate the affected verification and
repeat it against the new exact head.

## Canonical integrity model: four facts, five lifecycle checkpoints

To eliminate prior gate-count ambiguity, distinguish **independent integrity
facts** from **when they are revalidated**.

### Four independent integrity facts

1. **Local source validity** — intended local bytes parse/compile/validate and
   have a known length/hash.
2. **Write acknowledgment** — the transport reports success and returns its
   identifiers. This proves receipt, not intended content.
3. **Exact remote branch integrity** — freshly fetched bytes at the intended
   exact ref/head match the intended content and validate natively.
4. **Merged destination integrity** — after an authorized merge, freshly fetched
   destination bytes match the reviewed result and validate natively.

No fact implies a later fact.

### Five lifecycle checkpoints implementing those facts

| Checkpoint | Fact established/revalidated | Required action |
| --- | --- | --- |
| A. Before write | Fact 1 | Validate local bytes; capture size/hash/parser result |
| B. Write returns | Fact 2 | Capture response identifiers; inspect partial/error state |
| C. After branch write | Fact 3 | Fetch intended exact ref/head independently; compare bytes/hash/parser |
| D. Immediately pre-merge | Fact 3 again | Re-read PR/base/head; repeat exact-head integrity if anything could have moved |
| E. After authorized merge | Fact 4 | Re-read destination ref and repeat byte/hash/parser verification |

Checkpoint D is **not a new integrity fact**. It is temporal revalidation of
Fact 3 because branch and review authority can change after the first remote
verification.

This terminology supersedes ambiguous formulations that called pre-merge
revalidation its own independent integrity level or treated destination reread
as an optional close-out detail.

## Exact-ref evidence required for Fact 3

Record at least:

- expected repository and branch/ref;
- expected head SHA before the read;
- fetched branch/ref identity;
- fetched head SHA;
- intended path;
- intended/local blob or cryptographic hash and byte size;
- fetched remote blob/hash and byte size;
- native parser/compiler/schema result;
- UTC timestamp.

Stop if the fetched head differs from the head you intended to verify. Do not
silently validate whichever tip happens to be current and then attribute that
validation to an older or different state.

## Review-state rule

Automated and human review findings are temporal evidence scoped to the commit
range actually reviewed. Before following or dismissing a finding:

1. identify the reviewed/covered SHA or range;
2. identify the current PR head SHA;
3. test whether the finding still exists at that head;
4. respond with exact-head evidence.

Do not obey a stale recommendation literally when the condition it described
has already been removed. Do not dismiss a current finding merely because a
similar older run was stale.

## Stop conditions

Stop the consequential operation and use the safe reporting route when any of
these is true:

- PR-body authorization is missing or ambiguous;
- an agent-executed existing-body edit lacks a matching `operator-grant-v2` or
  cannot use `scripts/cursor/append-pr-body.sh`;
- the current PR body was not read and backed up before an authorized edit;
- the guarded pre-write body digest no longer matches the body originally read;
- a proposed body write contains only the newest delta;
- exact base/head identity has not been freshly read;
- the head moved after integrity/review verification;
- remote bytes cannot be independently fetched and validated;
- review coverage is being inferred from submission time rather than reviewed
  SHA/range;
- a write acknowledgment or returned SHA is the only integrity evidence;
- comments/notes are being treated as merge authorization.

## Canonical mnemonic

For reporting authority:

`AUTONOMOUS -> COMMENT/NOTE; BODY -> HUMAN AUTHORITY + OPERATOR GRANT`

For agent-executed PR-body mutation after explicit authorization:

`GRANT -> READ -> BACKUP -> MERGE -> WRITE -> REREAD`

For remote publication integrity:

`AUTH -> REF -> BYTES -> PARSE -> REVIEW -> MERGE -> BYTES AGAIN`

These are complementary controls: authority determines **whether** a mutation
may occur; CIDF integrity determines **whether the bytes/state are proven**;
AFRP live-authority checks determine **whether the evidence is current**.
