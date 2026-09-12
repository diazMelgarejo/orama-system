# Remote content-integrity reference card

Use this card whenever a tracked file crosses an API, encoding, chunking, or
generated-content boundary. It complements CIDF's ordinary destination
verification; it does not replace AFRP live-authority checks.

## Required evidence

| Gate | Required evidence | Stop condition |
| --- | --- | --- |
| 1. Local pre-commit | Target parses/compiles; local path blob SHA and byte size captured | Parse failure, unknown encoding, or no local baseline |
| 2. Remote branch post-write | Fetched head SHA matches the expected source/base SHA; exact branch/ref has the same path blob SHA and byte size; fetched content has an expected marker and parses/compiles | Any mismatch, truncation, binary payload, or stale/moved branch head |
| 3. Pre-merge | Gate 2 repeated for the exact PR head SHA; PR base/head and tree delta re-read | Head moved, unresolved mismatch, or empty/unrelated tree delta |
| 4. Post-merge | Destination ref re-read; the same path blob/content evidence retained | Destination differs from reviewed PR result |

## Text transport rules

- Prefer an explicit UTF-8 text write for text files.
- Use Base64 only when the transport requires it; validate decoded byte count and
  remote blob SHA against the local Git blob.
- Never infer integrity from an API success response, a commit SHA, a local diff,
  or a visual GitHub rendering.
- Use the file's native validator after fetching the remote object: Python
  compilation for Python, JSON/YAML/TOML parsing for data, and project-specific
  tests for generated artifacts.

## Minimal evidence record

Record the target ref, local blob SHA, remote blob SHA, byte size, validator
command, and UTC timestamp in a PR comment (not the PR body -- some agent
environments, including Cursor background agents, cannot reliably edit an
existing PR body) or an incident note. Do not record credentials, local
workstation paths, or raw binary payloads.

## Why Base64 chunking corrupts silently (verified mechanism)

Base64 encodes input in 3-byte groups into 4-character output groups. When a
chunk boundary falls exactly on a multiple of 3 raw bytes, each chunk encodes
to a complete, padding-free group, and naive concatenation of the encoded
chunks decodes back to the exact original bytes. When a chunk boundary does
**not** land on a multiple of 3, the chunk's own encoding ends in `=` padding
(1 or 2 padding characters) even though more real data follows in the next
chunk. Padding characters are a decoder's end-of-stream signal: concatenating
padded, non-final chunks produces a byte stream a standards-conformant
decoder treats as complete at the first padding marker, silently discarding
everything after it — no error, no exception, just short, truncated output.

Reproduced directly before writing this: encoding 10,000 bytes of arbitrary
content in 12,288-byte chunks (12,288 = 4,096 × 3, so every chunk boundary
lands on a multiple of 3) produced zero mid-stream padding and decoded back
byte-for-byte correct. The same content chunked at 7,000 bytes (not a
multiple of 3) produced padding in the first chunk and decoded to exactly
7,000 bytes — silently dropping the remaining 3,000, the same class of
truncation symptom as the 79-byte incident below. This is why any chunked
Base64 transport must use a chunk size that is a multiple of 3 (12,288 is one
convenient, proven-safe choice, but any multiple of 3 works) — a chunk size
that isn't is not a minor inefficiency, it is a silent, undetected-by-the-API
corruption source, since the encode/decode calls themselves report success at
every step. This is precisely why gate 2 (remote branch post-write) and gate
3 (pre-merge) in this card exist: they are the only checks that would have
caught this, since local validation and the API's own write acknowledgment
both happen before the corruption is introduced by concatenation.

## The four integrity levels that must not be conflated

Reconstructed from a real incident: an agent verified level 1 and treated
level 2 as if it proved level 3, without ever separately checking 3 or 4.

1. **Local file validity** — the file on the local working copy parses,
   compiles, or otherwise validates.
2. **API write acknowledgment / returned SHA** — the remote API call that
   wrote the content returned success and a blob or commit SHA.
3. **Remote object integrity at the exact branch head** — the actual bytes
   stored at that ref, fetched independently and re-validated.
4. **Merged destination integrity** — the actual bytes at the merge
   destination, fetched and re-validated *after* the merge, since a merge
   is itself a write that can select the wrong tree or head.

None of these implies any of the others. An API can acknowledge a write of
corrupted bytes exactly as readily as it acknowledges a write of correct
ones — the acknowledgment proves the request was *received*, not that the
*content* was what the caller intended. The correct rule: local validation,
then remote branch fetch-and-parse, then an exact-head pre-merge recheck,
then a destination recheck after merge. Skipping any one of the four for a
single "it must be fine by now" assumption is how a 79-byte binary payload
reaches `main` while every logged step along the way reported success.

## Incident trigger

If a merged text file is unreadable, binary, truncated, or fails its native
parser, stop further merges. Open one focused repair PR from the known-good
source and complete all four gates before merging it.
