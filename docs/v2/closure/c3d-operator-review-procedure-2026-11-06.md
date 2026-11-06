# C3d operator review procedure (2026-11-06)

## Current decision

The operator directly approved operator-only human review for this closure.
A second human reviewer is not required. This narrows reviewer composition,
not the review's contents, exact-revision binding or operational evidence.
It does not waive the separate Release R6 review or R4/R5 host qualification.

Source: direct operator messages and the operator-decisions section of the
Claude review-fix proposal dated 2026-11-06. Agent announcements are provenance
pointers, not substitutes for the operator's decision.

## Sequence and evidence

1. Implement and review K1-K3, including all remaining inline findings. Commit
   locally, rehearse the combined checks, and freeze the exact code heads.
2. Publish once per affected repository under the operator's explicit authority.
   Obtain final hosted CI results for those exact heads. No merge or deployment.
3. The operator performs a fresh interactive `gh auth login` on their own
   account, not through an agent. Existing tokens or `gh auth status` alone do
   not establish a fresh authentication ceremony. Never record device codes,
   tokens, credential files or authentication transcripts in review artifacts.
4. The operator explicitly accepts the exact final code heads and the security,
   legacy-job disposition, rollback and operational runbook evidence. Record
   non-secret account identity, UTC authentication/acceptance times, exact
   revisions and the bounded acceptance statement. An agent may prepare the
   packet but cannot act as the human or manufacture their acceptance.
5. Run C6 last on the accepted final code and named physical target filesystem.
   Retain workload, dependencies, test results and limitations. A fresh login
   proves account control procedurally, not review quality, independent review,
   a task-bound OTP attestation or benchmark compliance.

There must be no code change after acceptance without renewed review of the
new head. A later evidence-only receipt must identify the measured code head
explicitly; its own commit does not retroactively qualify different code.

## Current boundaries

The operator authorized the Mac APFS data volume for C6; native Windows
qualification remains separate. Serving stays off, `ORAMA_GRANT_SERVING` stays
unset, and the library default remains `governed=False`. Benchmark effects are
synthetic inert fixtures, not permission for real effects or live deployment.
PT coordination remains manual. Nothing here authorizes a merge, rewrites
Doc 68, changes controller authority or creates a serving approval record.

## Future policy option

Backlog, not implemented by this closure: introduce an explicit
`independent_reviewer_required` policy option, initially defaulting to the
ratified operator-only setting. A later reviewed contract must define policy
ownership, authenticated reviewer identity, exact-revision binding, evidence
validation and fail-closed malformed/unavailable behavior. Do not add a flag
that falsely implies existing code enforces an unimplemented review policy.
