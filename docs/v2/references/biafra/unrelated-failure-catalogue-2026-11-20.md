# Biafra unrelated-failure catalogue — 2026-11-20

Status: deferred investigation, not fixes, waivers or qualification evidence.
This catalogue preserves the November 17–18 run observations for later work.
No new full-suite run is implied by this document's November 20 date.

Fresh November 20 publication checks passed: 48 PT provider/worker tests and
400 Orama dispatch/Biafra tests, with 10 Orama skips. The paired run used
published PT `32cfd077dabf90530afe3e44a04f2f4f3fa3316b`, now selected by
`.github/pt-dispatch-test-ref`. These focused passes do not close the unrelated
failures or native-platform qualification gaps catalogued below.

## Evidence boundary

| Run | Revision / scope | Observed result |
| --- | --- | --- |
| PT full candidate | Prepared source subsequently committed as `bbad6111`; final source unchanged by documentation commits | 3700 passed, 12 skipped, 15 warnings |
| Orama full candidate | Prepared source subsequently committed as `5e7e3212`; doc-only finalization `dbc58fd4` | 4310 passed, 145 skipped, 7 failed, 4 warnings, 24 subtests passed |
| Orama unchanged PR head | `9e50b2896c781229228de46a2a3e79710f4c0d57`; four implicated test files | 83 passed, 12 skipped, the same 7 failed |
| Orama affected Biafra tests | Integrated candidate, including baseline/security checks | 353 passed, 16 skipped |

The PT full run preceded annotation-only finalization of its new process tests;
an AST comparison removed those annotations/imports and matched the baseline.
The final focused worker suite passed 48 tests with ResourceWarnings as errors.
These qualifications matter: neither historical full count is described as a
fresh full run on the eventual publication commit.

Saved log names in the downloadable evidence bundle:
`biafra-pt-final.log`, `biafra-orama-final.log`,
`biafra-orama-base-residuals.log`. Runtime: Linux, Python 3.12.14, pytest 9.0.3.
No native Windows/macOS result is established by these logs.

## Active failure inventory: seven cases, two investigation groups

### UF-TLS — peer trust isolation (three cases)

Classification: baseline-reproducible, security-sensitive TLS/runtime interaction.
Priority: P1 investigation. Owner: Orama peer transport/TLS maintainer.
Root cause: **unconfirmed**; the observed extra trust anchor is established, not
the reason it was added. Do not call these harmless or environment-only.

1. `tests/test_peer_tls_trust.py::test_fingerprinted_ca_is_loaded_from_the_verified_bytes`
2. `tests/test_peer_tls_trust.py::test_a_file_swapped_after_the_fingerprint_check_is_never_trusted`
3. `tests/test_peer_tls_trusted_bundle_regression.py::test_real_openssl_trusted_bundle_cannot_expand_pinned_ca_trust`

The first two expected only the synthetic approved CA but observed another CA.
The third observed an extra anchor even in a direct OpenSSL context constructed
from its fixture bundle. This suggests the runtime's trust-loading path must be
isolated before assigning the defect to the application's pinning code.

Next slice:

- Trace `src/utils/peer_tls.py`, SSL context creation, fixture setup and any
  installed runtime trust hooks. Compare clean interpreter and managed runtime.
- Capture redacted SSL/OpenSSL/module provenance without exporting credentials
  or operator certificate stores. Keep TLS verification enabled throughout.
- Preserve exact pinned-CA-only semantics and the replacement-race regression.
  Do not add the unexpected anchor to expected results to make tests green.
- Acceptance: all three pass under a documented supported runtime and explicit
  negative trust checks still reject unapproved anchors and changed file bytes.

### UF-PROC — process containment proof (four cases)

Classification: baseline-reproducible, security-sensitive lifecycle/ownership proof.
Priority: P1 investigation. Owner: Orama process-runtime maintainer.
Root cause: **unconfirmed**. The Linux run returned `unknown` instead of
`contained`; that result alone proves neither successful containment nor escape.

1. `tests/test_win_exec.py::test_terminate_tree_kills_grandchild`
2. `tests/test_win_exec.py::test_reparented_orphan_is_killed_and_contained`
3. `tests/test_win_exec.py::test_orphan_after_root_exit_is_contained_by_the_job`
4. `tests/test_win_exec.py::test_run_tree_returns_when_a_descendant_keeps_the_pipe_open`

Despite the filename, these four ran through the POSIX path on Linux, not native
Windows. The last test's timing/return assertions passed before the containment
assertion failed. Preserve that distinction when triaging pipe handling.

Next slice:

- Inspect `src/utils/win_exec.py` and `tests/posix_containment_fixtures.py` for
  process ownership, non-reaping observation, group membership and orphan reaping.
- Reproduce standalone and under the supported CI/subreaper launcher; distinguish
  fixture or runtime capability gaps from actual runtime cleanup defects.
- Use deterministic process barriers and real child trees; retain cleanup of
  test-owned processes only. Do not signal unrelated processes or weaken `unknown`.
- Acceptance: prove all owned descendants exit and ownership evidence justifies
  `contained`; unknown evidence must continue to fail closed. Qualify native
  Windows job behavior and macOS behavior separately.

## Reproduction entrypoints

From an isolated checkout of each stated revision, using the same installed
environment and the repository's native interpreter/fixture prerequisites:

```bash
python -m pytest -q tests/test_peer_tls_trust.py \
  tests/test_peer_tls_trusted_bundle_regression.py tests/test_win_exec.py
```

The baseline evidence also included `tests/test_markdown_lint_gate.py`.
That gate passed after its local dependency was supplied. Fresh counts may vary
with runtime/platform selection; always record exact revision, command, skips
and diagnostics instead of copying this historical count.

## Non-active reports: do not count them again as current failures

| Report | Classification and disposition |
| --- | --- |
| Two Markdown gate failures | Resolved local setup: required markdownlint-cli2 0.17.2 was absent at the repo-local path. Four Markdown gate tests subsequently passed. No lint guard was weakened. |
| Earlier Orama report of 24 failures | Historical handoff report: 13 dispatch/governance, 9 portal dispatch and 2 Markdown setup failures. The old editable PT checkout ownership problem was not present in the integrated run; none of those 24 is a current failing case in the final logs. |
| Earlier PT report of five Git state failures | Historical handoff report, not reproduced in the recorded 3700-pass full run. Linked-worktree tests need explicit isolated state authority; do not disable that guard. |
| Intermediate PT worker-path errors | In-progress integration, not unrelated debt: a running suite observed the old worker path while it moved under `src`. The final full run passed and the final focused worker suite passed 48 tests. |
| Generated bytecode Aguara finding | Resolved scan hygiene: an untracked generated bytecode file duplicated an existing sandbox-rule match. It was moved outside the scan tree; final scan had zero new findings. Baseline unchanged. |
| Skipped platform/optional tests | Unexecuted evidence, not passing qualification and not failed cases. Keep native platform gates open. |

## Warning debt, separate from the seven failures

| ID | Observation | Priority / owner / next proof |
| --- | --- | --- |
| UW-ASYNC | Two PT RuntimeWarnings: unawaited `connect_tcp` helper and the GBrain timeout test's `communicate` coroutine; warning surfaced during later tests/GC | P2, PT async/test owner. Locate allocation with tracemalloc and isolated ordering; the warning's reporting test is not necessarily its source. Prove all started coroutines are awaited or explicitly cancelled. |
| UW-CERT | Four PT warnings for deprecated naive certificate validity access | P2, PT TLS owner. Migrate to timezone-aware API with expiry-boundary tests. |
| UW-LEGACY | Nine PT deprecated legacy orchestrator import warnings | P3, PT compatibility owner. Inventory remaining callers; preserve retained shims until migration is explicitly complete. |
| UW-WS | Three Orama legacy websockets/uvicorn warnings and one legacy orchestrator import warning | P3, transport/compatibility owners. Review the supported dependency matrix and regress upgrade/auth flows; do not silently remove compatibility. |

Warnings have no separate unchanged-base reproduction in this evidence set;
they are observed investigation candidates, not established new regressions.

## Other publication diagnostics

The November 20 PT push reported three moderate vulnerabilities on PT's default
branch. This is an untriaged GitHub dependency-security notice, not a failed
Biafra test or a newly established regression. Advisory IDs, affected versions
and remediation are not verified here. Owner: PT dependency/security maintainer;
P2 triage through the repository's existing vulnerability workflow. Inspect the
[Dependabot queue](https://github.com/diazMelgarejo/Perpetua-Tools/security/dependabot)
before assigning fixes; publication neither waives nor resolves those alerts.

## Repair order and publication meaning

Investigate UF-TLS and UF-PROC in separate bounded source slices, then UW-ASYNC,
certificate API migration and compatibility warning cleanup. Before any fix,
write a failing reproducer, inventory the full contract/caller lifecycle and
retain privacy and failure semantics. Catalogue entries remain open until a
fixing commit and actual verification are linked additively.

The November 20 publication instruction releases the earlier push hold for
existing PT #516 and Orama #519 only. It does not waive these failures, accept
security risk, complete native qualification or authorize a merge/activation.
