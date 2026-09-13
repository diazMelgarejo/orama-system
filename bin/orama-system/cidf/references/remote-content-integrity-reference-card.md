# Remote content-integrity reference card

Use this card whenever a tracked file crosses an API, encoding, chunking, or
generated-content boundary. It complements CIDF destination verification and
AFRP live-authority checks.

For PR reporting/mutation authority, the normative companion is
[`pr-metadata-authority-and-reporting-reference-card.md`](pr-metadata-authority-and-reporting-reference-card.md).
If older examples appear broader, that authority card controls.

## Canonical model: four integrity facts, five lifecycle checkpoints

Do not confuse an integrity fact with a later revalidation of the same fact.
The canonical model contains four independent facts:

1. **Local source validity** — intended local bytes validate and have a known
   size/hash.
2. **Write acknowledgment** — the transport reports success and returns its
   identifiers. This proves receipt, not intended content.
3. **Exact remote branch integrity** — independently fetched bytes at the
   intended exact ref/head match the intended content and validate natively.
4. **Merged destination integrity** — after an authorized merge, independently
   fetched destination bytes match the reviewed result and validate natively.

These facts are implemented through five lifecycle checkpoints because Fact 3
must be revalidated immediately before merge whenever branch state could have
changed.

| Checkpoint | Fact | Required evidence | Stop condition |
| --- | --- | --- | --- |
| A. Local pre-write | 1 | Target parses/compiles; local blob/hash and byte size captured | Parse failure, unknown encoding, or no local baseline |
| B. Write acknowledgment | 2 | API/Git write reports success; returned commit/blob/ref identifiers captured | Error, partial failure, or ambiguous write result |
| C. Remote post-write | 3 | Intended repo/ref fetched independently; fetched head SHA equals expected head SHA; path blob/hash, byte size, source marker, and parser/compiler match | Any mismatch, truncation, binary payload, or stale/moved head |
| D. Exact-head pre-merge | 3 again | PR/base/head re-read live; checkpoint C repeated for exact current PR head when anything could have moved | Head/base moved, unresolved mismatch, stale review, or unrelated/empty delta |
| E. Post-merge destination | 4 | Destination ref re-read; resulting path blob/hash, byte size, and parser/compiler match reviewed result | Destination differs from reviewed PR result |

Checkpoint D is temporal revalidation of Fact 3, **not a fifth integrity fact**.
Checkpoint E is mandatory destination integrity, not an optional reporting
close-out.

## Exact-ref identity is mandatory

Blob equality proves content equality, not which branch tip was checked. For
Fact 3, record and compare:

- expected repository and branch/ref;
- expected head SHA;
- fetched repository and branch/ref;
- fetched head SHA;
- intended path;
- local/intended blob or cryptographic hash and byte size;
- fetched remote blob/hash and byte size;
- native validator result;
- UTC timestamp.

Stop if the fetched head SHA differs from the head you intended to verify. Do
not validate whichever branch tip happens to be current and attribute that
proof to an older or different tip.

## Text transport rules

- Prefer an explicit UTF-8 text write for text files.
- Use Base64 only when the transport requires it; validate decoded byte count
  and remote blob SHA against the intended Git blob.
- Never infer integrity from an API success response, a returned SHA, a local
  diff, or a visual GitHub rendering.
- Use the file's native validator after fetching the remote object: Python
  compilation for Python, JSON/YAML/TOML parsing for data, and project-specific
  tests for generated artifacts.

## Evidence reporting authority

Routine integrity evidence from unattended/autonomous/background agents or
autoresearchers belongs in a **new PR/issue comment** or an append-only incident
or working note. These are the safe autonomous reporting surfaces.

Do **not** edit the PR body merely to record evidence. A PR description is
human-controlled historical metadata. Editing it requires explicit current
human authorization for that specific body/summary operation.

For an **agent-executed edit of an existing PR body**, that human authorization
must be followed by `operator-grant-v2`: the operator runs
`scripts/cursor/grant-pr-body-human-override.sh` with the same `--file` or
`--message`, and the agent must use `scripts/cursor/append-pr-body.sh` for
`READ -> BACKUP -> MERGE -> WRITE -> REREAD`. Stop if either the matching grant
or guarded path is unavailable. Direct human edits are a separate allowed path.

The write must contain the complete integratively merged body, preserving the
original Summary and valid historical sections. A delta-only body replacement
is prohibited even after authorization.

Generic instructions such as "update the PR", "report progress", "fix review
comments", or an automated reviewer suggestion do not authorize PR-body
mutation. Without explicit authorization, post a new comment/note and ask the
human if a description edit is actually needed.

Do not record credentials, personal workstation paths, or raw binary payloads
in comments, notes, or PR metadata.

## Why Base64 chunking can corrupt silently

Base64 encodes input in 3-byte groups into 4-character output groups. When a
chunk boundary falls on a multiple of 3 raw bytes, that independently encoded
chunk can be padding-free. When a non-final independently encoded chunk does
not end on a multiple-of-3 boundary, its encoding ends in `=` padding.
Concatenating such padded chunks into one Base64 stream before a single decode
creates interior padding and an ambiguous/invalid transport contract.

The safe rule is not "always use 12,288 bytes". The safe rule is to define the
producer/decoder contract explicitly:

- encode the complete payload once; or
- if independently encoded chunks must be concatenated before one decode, make
  every non-final raw chunk length divisible by 3; or
- decode each encoded part independently and concatenate decoded bytes.

`12,288 = 4,096 × 3` remains a useful worked example because a full 12,288-byte
raw chunk encodes to exactly 16,384 Base64 characters without padding. It is a
convenient example, not a universal magic size.

After reconstruction, always verify the exact remote byte count/hash and native
parser result. Alignment is transport hygiene, not integrity proof.

## Integrity levels must not be collapsed

The incident family showed why these statements are all different:

- "the local file parsed";
- "the API accepted the write";
- "the intended exact remote branch head contains the intended bytes";
- "the merged destination contains the reviewed bytes".

None implies the next. The correct workflow is local validation, write
acknowledgment, exact remote fetch-and-validate, exact-head pre-merge
revalidation, then destination revalidation after an authorized merge.

## Review-state rule

Review findings are temporal evidence scoped to the SHA/range actually
reviewed. Submission time alone does not prove the latest head was examined.
Before following or dismissing a review finding:

1. read the reviewed/covered SHA or range;
2. read the current PR head SHA;
3. test whether the condition still exists at that head;
4. reply with exact-head evidence.

A stale recommendation should not be followed literally after its condition
has been removed, and a current failure must not be dismissed merely because a
similar older run was stale.

## Incident trigger

If a merged text file is unreadable, binary, truncated, or fails its native
parser, stop further merges. Open one focused repair PR from independently
verified known-good source material and complete Facts 1–3, including the
pre-merge revalidation of Fact 3, before any authorized merge. Complete Fact 4
only after the merge by re-reading and validating the destination.

## Compact mnemonics

Reporting authority:

`AUTONOMOUS -> COMMENT/NOTE; BODY -> HUMAN AUTHORITY + OPERATOR GRANT`

Authorized agent PR-body edit:

`GRANT -> READ -> BACKUP -> MERGE -> WRITE -> REREAD`

Remote publication integrity:

`AUTH -> REF -> BYTES -> PARSE -> REVIEW -> MERGE -> BYTES AGAIN`
