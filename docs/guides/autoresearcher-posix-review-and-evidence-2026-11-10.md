# AutoResearcher POSIX Review and Evidence

Date: 2026-11-10. Scope: additive remediation in existing
[Orama PR 487](https://github.com/diazMelgarejo/orama-system/pull/487).
Companion memory: [PT PR 489](https://github.com/diazMelgarejo/Perpetua-Tools/pull/489),
`.agent/memory/semantic/MAC_POSIX_EVIDENCE_AND_LOCK_BOUNDARIES_2026-11-10.md`.
This is evidence and reusable operating guidance, not deployment approval.

## Attribution and Integration

Windows Claude Code, acting as `win-researcher`, authored the backend-lock
implementation and fixes through `9ba89cb9819967cca5c8f05aa7f21ccc0818ea48`.
Mac Codex's source-review sidecar identified the three findings below; the
primary Mac actor independently ran tests and synthetic fault injection.
Mac integration preserves the Windows commits and adds stricter outcome
classification, probe validation, regressions and this synthesis. All agent
identities are self-reported, `identity_verified=false`; attribution is not
cryptographic identity verification or operator endorsement. Scout is the
Mac research persona; Arthur remains OpenClaw-internal. A Windows identity
decision retained `win-researcher`, superseding the earlier shared-persona idea.

## Findings and Combined Contract

| Finding at `71ab3560` | Evidence | Resolution |
| --- | --- | --- |
| Usage substrings or a generic `subprocess.run` error could clear an in-flight record | Synthetic post-effect marker and I/O-error cases released to free | Preserve Windows' separate `Popen` launch boundary; every nonzero result after successful launch is unknown, regardless of text or speed |
| Permission refusal left an opened lock descriptor | Synthetic permission injection observed an unclosed descriptor | Preserve Windows' acquisition-exception cleanup and regression; verify all acquisition failure paths |
| Localhost rewrite trusted DNS, changed HTTPS identity and dropped userinfo | Source review and failing probe regressions | HTTP localhost uses literal IPv4 then IPv6 loopback without DNS; HTTPS retains hostname; unsupported userinfo and malformed URLs refuse before I/O |

An absent CLI or independently failed spawn can be `not-sent`. A timeout,
post-start I/O error or launched nonzero exit is `unknown`, never an automatic
retry or provider switch. Output shape and elapsed time are diagnostics, not
effect-boundary proof. A successful CLI exit means the CLI completed, not that
an operator approved effects. Plan mode and disabled tool auto-approval remain
the default; no real Cline or paid-provider dispatch was used for these tests.

Probe optimization applies only to plain HTTP localhost, not arbitrary peers
or HTTPS. It makes at most two literal-loopback attempts, splitting the I/O
timeout between them to retain IPv6-only backend reachability. The configured
HTTP read timeout is per I/O, not a whole-process
deadline; HTTPS and explicit peer names may still involve DNS. No TLS checks,
CA trust or bearer credentials are weakened. Tests use synthetic URLs/mocks,
not operator secrets. Explicit LAN endpoints retain their configured behavior.

## Native Baseline Receipts

Runtime: Python 3.13.18, SQLite 3.53.1; macOS 27.2 arm64. Tests ran with a
temporary home and credential-free environment through contained child runs.
These are native Mac software checks, not native Windows, Linux, service-user
ACL, physical-filesystem C6, serving or activation qualification.

| Source | Scope | Result |
| --- | --- | --- |
| Orama `71ab35601ac43c43a8538aff836bb47084cad7a4` | Seven lock/controller/probe/containment files | 154 passed, 13 Windows-only skips, one configuration warning |
| PT `b728015fc2b4462924c210c2292cba0b3f3ddf76` | State-authority-record tests | 20 passed, zero skips, two configuration warnings |
| Phylax `2c11d15820532f43e588a732f7b2b6509551a1f2` | Four portability/publication/retention files | 121 passed, one platform-specific skip |

Warnings were unknown pytest asyncio configuration keys with plugin autoload
disabled. Phylax's focused run disabled the full-suite coverage threshold;
it is not a coverage claim. Baseline tests passed despite the reproduced
defects: add adversarial regressions before treating a suite as sufficient.
Later-head regression results belong in the fixing commit/PR receipt, never
silently relabel this baseline as validation of a new head.

Baseline JUnit SHA-256 values, stored under the local `$MAC_POSIX_RESULTS`:

- `pr487-71ab3560.xml`:
  `200a32bd9a465953292c17b74912fc4ced5bd69ac1be71f6ee9c1c886b98b510`.
- `pt-state-authority.xml`:
  `a27aa985a0babb48f905bbeb2cfba48484606149a534e4686f77229a87b03fd7`.
- `phylax-posix.xml`:
  `626ddda41a281880ed500b6a95dbf4b909ceb661193b76bb1302bedd1e152077`.

`src/utils/win_exec.py` is byte-identical at Orama #481 contributor
`b16a6abe0802e9070337ee7473ecad201218b571`, Orama main `2537cefa`,
PR487 `71ab3560` and PT main `b728015f`. SHA-256:
`8a5e9a2b5fdf218a122683d117e1e6b3fd7047aa9224d0f2ace11bc21c988efb`.
No mirroring repair was required. Similar but intentionally different test
files do not establish source drift.

## Durable Lessons

1. Test the actual tool's version, help, install layout and dangerous defaults
   before building a controller. A shell shim, retired subcommand, inherited
   provider or auto-approval default is not a harmless detail. Never probe a
   real append-only ledger just to discover CLI syntax.
2. Bind every result to its exact source, runtime, host and test command.
   Re-read the live head before publication. Preserve concurrent fixes by
   integrating from their new tip, not overwriting from an older review base.
3. Separate process spawn from communication. Once launched, output cannot
   independently attest that a request was unsent. Persist ambiguity first;
   operator reconciliation, not a timed retry, clears unknown effects.
4. Cover exceptional acquisition and partial initialization, not just success
   and contention. An exception must not leak a descriptor or its OS lock.
5. Acquiring a lock proves availability, not prior-owner death or downstream
   completion. A temporary native flock experiment acquired after explicit
   unlock while the original holder remained alive. Its qualified receipt
   SHA-256 is `60e29666179c347e1a3cc5d4b905778cee66be14170a16daeab0105840d92f7a`.
6. Compare model routes only under matched endpoints, templates, sampling and
   thinking settings. Two unmatched timing samples describe observations,
   not a transport winner. Model loaded, tiny health response, research output,
   validator acceptance and tool-enabled worker completion are different gates.
7. Export sanitized derived views only. Raw ledgers and private histories stay
   node-local. Exact raw bytes/digests define delivery; LF-normalized digests
   are diagnostic, not substitutes for byte preservation. Server acceptance,
   authenticated readback, peer reading and individual consent are distinct.
8. Agent task IDs require a plan namespace: original Phylax P-W1/P-W2/P-W4 and
   later Windows WIN-W1/WIN-W2/WIN-W4 describe different deliverables. A GPU
   lock fix does not close an unrelated producer/authority porting task.

## Remaining Boundaries

The canonical sources remain `docs/v2` closure/governance/lifecycle plans.
Current Phylax main has a platform filesystem adapter: an old unconditional
`fcntl` observation is historical, not a current-main defect. Oramasys'
verify-only recovery pin is intentionally not a full producer installation;
missing producer modules do not alone prove a broken pin. Pin promotion is
separate authority. PT manual cleanup versus v2 Controller expiry/fencing
(D1), and the no-Doc69-retrofit boundary for legacy Core, are unchanged.

Windows native qualification of the final head, Linux execution, service-user
isolation and any outstanding item-level outbox ownership/independent receipts
remain separate. Previously accepted Mac C6 evidence does not qualify another
head or Windows host. No merge, generation promotion, deployment or v2 serving
activation follows from these tests. Existing v1 services remain in place.
Regular coordination is paused by operator instruction; substantive results may
be sent, but do not resume periodic dispatch or bulk-flush historical outboxes.

## Remediation Receipt and Handoff

Mac fixing commit `dc8ae1e37a72323a8c11089ec7c66d49cb158408` strengthens the
Windows fixes; merge `32d57051d2077967db77b8cab9a66903cc910b11` preserves the
concurrent `d15ebce5` inspect/recheck refusal and isolated scratch fixtures.
The trial merge was conflict-free. Seven dispatch/acquisition regressions
failed before remediation; the original probe regressions also failed before
their fix. The combined nine-file working-tree run passed 185 tests with
13 Windows-only skips and one disabled-plugin configuration warning. Its
child containment result was `contained`. Final clean-head execution is
recorded separately in the PR publication receipt, not inferred from ancestry.

Windows integration: review the actual published PR487 tip, preserving all
existing source commits. Run the same nine files natively on Windows and
report exact SHA/runtime/pass/skip counts; do not call Mac skips Windows proof.

Reproduction set (Windows-side note, added in orama PR 488). The receipt above does not enumerate
its nine files, so the Mac's exact set is unconfirmed. Windows reproduces with these explicit
files and the helper module `tests/_cline_fakes.py`:

```bash
python -X utf8 -m pytest -q -p no:cacheprovider \
  tests/test_autoresearcher_backend_lock.py tests/test_autoresearcher_backend_lock_review.py \
  tests/test_autoresearcher_backend_lock_followups.py tests/test_autoresearcher_review2.py \
  tests/test_autoresearcher_review3.py tests/test_autoresearcher_probe_loopback.py \
  tests/test_autoresearcher_ownership_integrity.py tests/test_cline_autoresearcher.py
```

Windows result at Mac head 69cb2ea7: 130 passed, 1 skipped.
Ask the Mac to name its ninth file.
PT memory stack remains PR487 then PR488 then PR489 by the previously
reported branch relationship; verify live heads and current mergeability
before each operator-authorized merge. Orama PR488 is separate Windows watcher
work: this review does not endorse it. Do not merge the historical Mac Cline
branch separately; its prompt correction is already incorporated in PR487.
No branch, PR or main should be force-updated to implement this handoff.

Final-review follow-up `03effcc8ae1ebc1fbf231f8d79f7cb8ebb44b013` closes
another integrity gap: recheck/mark/release verify the expected owner record
and held-file identity. If those change or cannot be verified, cleanup closes
its resources without replacing the evidence. An unchanged owner may still
release after an external prerequisite refuses. New regressions cover changed
nonce/state/resource/PID, malformed evidence, replacement inode and the real
dispatch refusal path. The real rename test is POSIX-only; portable identity
fault injection complements it. These checks coordinate participating writers;
an uncooperative process with file-write privileges can race any check/write
pair, so this is not a cryptographic integrity or hostile-filesystem guarantee.
The IPv6-only regression failed before the literal-loopback fallback was added.
Windows reference updates through `9ba89cb9` are retained, not overwritten.
