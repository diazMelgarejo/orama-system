# Remote content-integrity reference card

Use this card whenever a tracked file crosses an API, encoding, chunking, or
generated-content boundary. It complements CIDF's ordinary destination
verification; it does not replace AFRP live-authority checks.

## Required evidence

| Gate | Required evidence | Stop condition |
| --- | --- | --- |
| Local pre-commit | Target parses/compiles; local path blob SHA and byte size captured | Parse failure, unknown encoding, or no local baseline |
| Remote branch post-write | Exact branch/ref has the same path blob SHA and byte size; fetched content has an expected marker and parses/compiles | Any mismatch, truncation, binary payload, or stale branch head |
| Pre-merge | Gate 2 repeated for the exact PR head SHA; PR base/head and tree delta re-read | Head moved, unresolved mismatch, or empty/unrelated tree delta |
| Post-merge | Destination ref re-read; the same path blob/content evidence retained | Destination differs from reviewed PR result |

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
command, and UTC timestamp in the PR body or incident note. Do not record
credentials, local workstation paths, or raw binary payloads.

## Incident trigger

If a merged text file is unreadable, binary, truncated, or fails its native
parser, stop further merges. Open one focused repair PR from the known-good
source and complete all four gates before merging it.
