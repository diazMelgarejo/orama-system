# Sites readiness r2 implementation — 2026-10-06 UTC

AFRP: Type C | Expert | Mode 2. Implements the approved six-task readiness plan in
the legacy v1 regime. No clean-room v2 dependency, new model provider or agent-network
inference is introduced. Concrete Site IDs, account identifiers, URLs and local paths
remain in the private operator runbook.

## Ownership and implementation map

| Task | Implementation and acceptance | Status |
| --- | --- | --- |
| 1: opt-in preview | `local-preview.mjs`, runtime containment, dependency/preload resolution, child environment, exit/signal tests and real Wrangler reproduction | Implemented; synthetic-home failure and isolated readiness observed |
| 2: reviewed assembly | Shared `overlay.mjs`; `verify-assembled.mjs` independently checks raw bytes, provenance, manifest, migration order/schema/constraints/query plans | Implemented; current candidate verified |
| 2: Site migration | Generated index-only follow-up; initial migration and journal entry preserved | Generated and locally verified; production migration requires deployment |
| 3: built Worker | `tests/local-worker-smoke.mjs`, real HTTP and disposable D1, owner isolation, retries/conflicts, same-time pagination, archive/restarts, cancellation cleanup | Passed locally; not hosted identity evidence |
| 4: private deployment | Exact source/version/deployment via native Sites; anonymous access denial; compatible prior version retained | Earlier private publication succeeded; follow-up publication recorded in private runbook |
| 5: connected dogfood | Native generated plugin, real `oramasys_prepare_prompt`, exact original/result verification | Blocked until platform installation and owner OAuth succeed |
| 6: handoff/lessons | This sanitized map, additive lessons in both repos, PT working-memory incident; concrete evidence in private runbook | Implemented documentation; hosted UI and two-user evidence remain outstanding |

## Corrections to prior claims

The first publication predates approval of revision 2 and did not establish a supported
first-publication reversal. No unpublish operation is exposed here. Its successful
deployment does not prove owner sign-in or MCP installation. The revised gate cannot
be applied retroactively. Subsequent updates retain the earlier compatible saved version.

The already-published candidate lacked the history-index migration. The r2 verifier
found this despite byte-identical source and a passing build. The generated migration
changes only indexes and is semantically verified against the canonical PT schema.

The UI parsed non-JSON gateway failures as JSON. Plain-text authorization errors can
therefore produce browser parser wording instead of the real status. The shared client
decoder now checks authentication and HTTP failures first. This is an observed code
defect with a regression test; it does not establish the cause of an owner OAuth denial.

The supported Site policy already granted the owner access. Reapplying the same owner
allowlist changed its revision without widening access. Anonymous root and MCP history
were denied; sign-in redirected to the platform OAuth endpoint. No application error
events were returned during the reported failed login. Owner access remains unverified.

## Final review fixes

A single fresh reviewer found runtime symlink containment, falsy JSON metadata,
partial request-key uniqueness and interrupted detached-Worker cleanup gaps. Each was
reproduced and repaired with regression tests. An additional author-side test prevents
candidate migration SQL from attaching a disk database during read-only verification.

The launcher validates resolved runtime and D1/config destinations. The verifier requires
JSON objects, compares partial-index semantics and probes duplicate active keys. The
smoke runner handles cancellation, stops its owned process group and preserves the signal.

## Release gate discipline

Do not merge before CodeRabbit. PT runtime/compiler is unchanged; Orama consumes the
existing reviewed bytes. If a future canonical fix is required, merge PT first, then
re-pin Orama. Push order remains Orama before PT when both change.

No local fixture header or platform service token may count as hosted owner evidence.
Do not make the Site public to work around login. Do not run the optional forged-header
probe without its separate authorization. Before future sharing, use two actual approved
identities to test cross-owner read/list/archive; owner-private smoke cannot prove that.

Once platform login/installation works, invoke Appendix A of the approved plan through
the connected tool. Verify `isError:false`, mode/version, source equality/hash and the
role/goal/constraints/output sections. Optional storage uses a fixed retry key and a
durable `prompts_get` read-back. Preparation is deterministic formatting, not inference.

## Status update after publication (appended 2026-10-06)

This section supersedes the "blocked" and "unverified" wording above where the two conflict.
Earlier text stays as the record of what was known when it was written. The facts below come from
the implementation agent's handoff; a reviewer has not independently re-run them against the
hosted Site.

- The r2 candidate was published as a new private Site version. The owner-only allowlist was
  reapplied without widening access.
- Anonymous root, MCP and history requests were denied with 401 and returned no records.
- The installed generated plugin made authenticated native calls: Appendix A prepared
  (`structured-contract`, version 1.0.0, original preserved byte for byte), history listed, and a
  long plan was saved in two records, read back, retried idempotently and rejected on changed
  content. Task 5 is therefore passed for the owner's plugin session.
- Still not verified: owner browser sign-in, two real accounts (hosted isolation), and the optional
  forged-header probe, which needs its own authorization.
- The first-publication reversal gate was not met. No unpublish or suspend operation is exposed,
  and no explicit owner acceptance of a one-way publication is recorded. An earlier compatible
  version is retained; code rollback does not reverse D1 migrations.
- Concrete identifiers, hashes and record IDs stay in the private operator runbook.
