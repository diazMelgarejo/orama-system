# Text-Metadata Integrity and Review-Completeness Reference Card

**Parent skill:** [`../SKILL.md`](../SKILL.md) (git-history-surgery), decision item 17.
**Companion:** [`../../../cidf/references/remote-content-integrity-reference-card.md`](../../../cidf/references/remote-content-integrity-reference-card.md)
covers byte-exact integrity for tracked files, Base64/chunked transport, and
Git blobs. This card covers the distinct case that reference card's own
"four integrity levels" work does not fully resolve on its own: **mutable
external text metadata** (a PR/issue body, a comment, any GitHub-API JSON
text field) has different transport semantics than a tracked file, and
applying blob-style exact-byte hashing to it produces false-positive
integrity failures on genuinely correct writes.

**Origin incident:** `diazMelgarejo/orama-system` PR #357, 2026-09-13. Full
narrative in PT `.agent/memory/working/ORAMA_PR357_PR_BODY_INTEGRITY_FALSE_POSITIVE_AND_RECOVERY_2026-09-13.md`
and `INDEPENDENT_VERIFICATION_METHODOLOGY_PR357_PR6_2026-09-13.md`.

## Rule 1 — choose the canonical representation before choosing a hash

| Target | Correct integrity relation |
| --- | --- |
| Git blob / tracked artifact / binary payload | exact bytes; cryptographic or Git blob hash |
| Encoded transport (Base64, chunked) reconstructed into a tracked file | exact decoded bytes + length/hash + parser |
| GitHub PR/issue text metadata (body, comment) | canonical logical text, with helper-added newline bytes normalized out before comparison |
| JSON object with schema semantics | schema/value equivalence, not incidental serialization bytes |

A cryptographic digest proves equality only of the exact bytes handed to it.
If two correct code paths produce semantically identical text with
different incidental bytes — most commonly, a locally-written file gaining
a trailing newline from `printf '%s\n'` that a JSON-field round-trip does
not preserve — raw digest comparison manufactures a false positive, not
stronger integrity.

**Concrete, verified failure shape:** writing a merged PR body locally with
`printf '%s\n' "$merged" >"$out"` (12 bytes for `"hello world"`) and then
re-reading the same content back through `gh pr view --json body --jq .body`
(11 bytes — the trailing newline does not survive a JSON string round-trip,
and does not survive shell command substitution `$(...)` either, which
strips trailing newlines by ordinary POSIX semantics) will never hash equal
under raw `sha256sum`, regardless of whether the write was correct. Verify
this directly before trusting any fix in this area:

```bash
out="$(mktemp)"; printf '%s\n' "hello world" >"$out"
rt="$(mktemp)"; printf '%s' "$(cat "$out")" >"$rt"   # simulates the round-trip
wc -c "$out" "$rt"        # 12 vs 11
sha256sum "$out" "$rt"    # different
```

The fix is to normalize before hashing — strip the trailing newline on
both sides, or otherwise canonicalize to the same logical representation,
before comparing:

```python
content = Path(path).read_bytes().rstrip(b"\n")
print(hashlib.sha256(content).hexdigest())
```

Do not casually change this normalization once it is proven green for a
given workflow — if a future requirement makes exact trailing-newline count
meaningful, redefine the canonicalization contract explicitly rather than
silently altering the hash function.

## Rule 2 — a new regression test passing is not TDD GREEN by itself

Run the whole neighboring test file, not just the new test:

```bash
pytest path/to/test_file.py -v
```

A fix aimed at one failure mode (e.g. closing a concurrent-write race) can
silently break an adjacent, established positive invariant (e.g. the normal
successful-write path) that the new test never exercises. The tell-tale
symptom, worth recognizing on sight: the new negative/regression test
passes, but a pre-existing positive/happy-path test in the same file fails
on the exact same head. That pattern means the new guard is either
over-restrictive or uses the wrong equivalence relation — it does not mean
the underlying design is wrong, only its implementation.

## Rule 3 — do not resolve a review thread while the affected head is CI-red

Canonical gate, all eight facts distinct, none proven by any of the others:

`FINDING -> CURRENT HEAD -> RED PROOF -> MINIMAL FIX -> FOCUSED GREEN -> FULL GREEN -> RE-READ FINDING -> RESOLVE`

Thread UI state is not proof of correctness. Never describe an intended
validation step as if it were completed evidence — either run it and record
the actual result, or state plainly that it remains unverified.

Related, less explicit: the CIDF card's "Remote publication integrity"
compact mnemonic (`AUTH -> REF -> BYTES -> PARSE -> REVIEW -> MERGE ->
BYTES AGAIN`) includes review as one step in a broader publication
sequence; this rule is the specific, actionable expansion of what that
step actually requires before resolving a thread.

## Rule 4 — an automated review finding is scoped to the commit range it actually reviewed

Already covered in full by the CIDF card's own "Review-state rule" section
— [`../../../cidf/references/remote-content-integrity-reference-card.md`](../../../cidf/references/remote-content-integrity-reference-card.md#review-state-rule).
Do not restate it here; load that section directly. It applied precisely
to this incident: CodeRabbit's finding on the dependency-declaration
contradiction was correct for the commit it reviewed, but that commit was
a deliberate RED state superseded by a later GREEN fix the review hadn't
yet seen.

## Rule 5 — a CI-only compatibility dependency is not package metadata

If a dependency exists only to exercise cross-package compatibility in
tests, do not publish it through any package metadata — not
`dependencies`, and not any `[project.optional-dependencies]` extra, since
an optional extra is still published metadata that advertises a dependency
relationship the package does not architecturally own. Install it from a
separate requirements file in its own CI step instead:

```bash
python -m pip install -e '.[dev]'
python -m pip install -r requirements/test-<fixture-name>.txt
```

Add a dedicated test asserting the package's own metadata never re-declares
the dependency, so a future change cannot quietly reintroduce it after
removing it from required dependencies.

## Rule 6 — a relayed incident report is a claim to verify, not a fact to inherit

Before building on or citing another agent/session's incident or recovery
report:

- [ ] Reproduce its central technical claim directly, in isolation, before
  treating it as established — a byte-count mismatch, a race condition, a
  chunk-size boundary.
- [ ] Resolve every cited commit SHA, PR number, and CI run ID against the
  live API and confirm it says what the report claims.
- [ ] Distinguish, in whatever you write next, what you personally verified
  from what you are relaying on the strength of the report alone.

A well-written, internally consistent retrospective is still a claim about
the world, not a substitute for checking the world.

## Durable future-agent checklist

Before changing an integrity guard on external text metadata:

- [ ] Identify whether the target is bytes, structured values, or text
  metadata — they have different correct equality relations.
- [ ] Trace every serialization/deserialization boundary end to end
  (variable → `printf` → temp file → CLI/API → JSON field → readback).
- [ ] Define the canonical equality relation before selecting a
  hash/checksum.
- [ ] Read existing success-path tests before writing a new failure-path
  regression.
- [ ] Write a RED regression that proves the defect; run it and record the
  actual failure, not an inferred one.
- [ ] Implement the smallest fix; prefer one canonical normalization
  helper reused by both the pre-write and post-write checks.
- [ ] Run the whole neighboring test file — both old and new invariants
  must pass.
- [ ] Test representation edge cases explicitly: empty value, one trailing
  newline, multiple trailing newlines, CRLF vs LF where relevant.
- [ ] Run the full relevant suite or inspect exact-head CI before claiming
  completion.
- [ ] Do not resolve review threads while affected CI is red on the exact
  current head.
- [ ] Re-read the exact remote head and review coverage before claiming
  completion.

## Related skills

- [[git-history-surgery]] — parent skill; decision item 17 links here.
- [[git-file-deletion-guard]] — the sibling exact-byte discipline for
  tracked-file deletions and Git data-API tree publication; this card is
  the mutable-text-metadata counterpart to that tracked-file doctrine.
- CIDF `remote-content-integrity-reference-card.md` — the four-gate model
  (local pre-commit, remote branch post-write, pre-merge, post-merge) this
  card's Rule 1 refines for the specific case of text metadata rather than
  tracked file content.
