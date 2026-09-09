# Tripwire → Telos Canonical Restoration Handoff — 2026-09-10

## Purpose

This handoff records the completed restoration work that re-establishes the
accepted 2026-08-29 Tripwire/Telos architecture as canonical, corrects the
September semantic-only Telos implementation drift, transfers the reusable v2
endpoint-security implementation into Telos, restores Apache-2.0 governance for
Telos/Phylax, and creates durable PT `.agent` memory for future agents.

This document is current-state evidence, not merge authorization.

## Canonical decision

`oramasys/telos` is the sole reusable v2 endpoint-security authority succeeding
Tripwire.

Telos owns:

- canonical endpoint identity and IDNA hostname normalization;
- IP/CIDR, metadata, special-use and transition-network classification;
- SSRF policy;
- all-answer DNS validation and DNS-rebinding/TOCTOU defense;
- connection-time IP/socket pinning;
- post-connect peer-pin verification;
- redirect revalidation;
- proxy isolation;
- TLS destination identity and HTTP Host/SNI preservation;
- purpose-scoped semantic endpoint-use authorization;
- reusable safe transport/bridge primitives for v2 consumers.

Semantic endpoint permission and transport safety remain separate decisions, but
both are Telos responsibilities.

`oramasys/phylax` remains the generic security/safety/admission/monitorability
authority and explicitly excludes endpoint-specific security.

## v1 / v2 regime boundary

PT remains an independent v1 runtime authority. Its endpoint-policy,
`endpoint_policy_core.py`, `ssrf_fetch_policy.py`, `ssrf_pinned_adapter.py` and
associated tests are clean-room behavior/provenance evidence for v2 only.

- v1 MUST NOT import Telos or another v2 package;
- v2 MUST NOT import, execute, discover or silently fall back to PT runtime
  endpoint-security code;
- parity is behavioral/evidence comparison, not runtime reuse.

## Tasks 3–7 — Telos clean-room implementation

Repository: `oramasys/telos`  
PR: #1 — `feat(telos): restore full Tripwire endpoint-security authority`  
Branch: `2026-09-10-restore-tripwire-endpoint-authority`  
Verified head: `509d38299011d82f8df14e577169898bdebc344c`

Clean-room evidence revisions:

- `diazMelgarejo/Perpetua-Tools@a551da4fa97e5fbc6f908ad077c7b6d8030a3220`;
- `oramasys/Claude-Desktop-LLM@ba4f3910efc6496cd6476a274b93f4b877ba12b3`;
- `oramasys/oramasys@8ad2574010013d9f5b40b193d316516872462130`
  for additional Gateway transition-network parity vectors.

Implemented security vectors include:

1. canonical HTTP/HTTPS endpoint identity;
2. credential/userinfo rejection;
3. malformed scheme/port rejection;
4. IDNA normalization;
5. every A/AAAA answer checked before connection;
6. metadata, loopback/private-profile, link-local, multicast, unspecified,
   special-use and transition-network handling;
7. IPv4-mapped IPv6 normalization;
8. CGNAT `100.64.0.0/10` handling;
9. 6to4 relay anycast `192.88.99.0/24` denial;
10. Teredo `2001::/32` and 6to4 `2002::/16` denial;
11. pinned connection to the vetted IP;
12. post-connect peer equality verification;
13. canonical Host and TLS SNI preservation;
14. direct transport without environment-proxy bypass;
15. full redirect re-entry through identity, DNS, transport and semantic policy;
16. 301/302/303 → GET + body/body-header removal;
17. 307/308 method/body preservation;
18. cross-origin Authorization/Cookie/Proxy-Authorization stripping;
19. bounded redirects/socket deadlines;
20. cooperative cancellation boundaries;
21. JSONL bridge for non-Python consumers.

### Verification

GitHub Actions CI run `34407975637` passed at the exact head.

- Python 3.11: success;
- Python 3.12: success;
- Python 3.11 suite: **29 passed**;
- Python 3.11 total line coverage: **88.38%**;
- required coverage floor: **80%**;
- compile smoke: success;
- PR review-thread sweep: no review threads.

An earlier CI failure was isolated to an invalid TLS test double lacking the
stdlib `SSLContext.verify_mode` contract. Production TLS/pinning behavior was
not weakened; the test double was corrected and the matrix rerun passed.

## Task 8 — Phylax governance correction

Repository: `oramasys/phylax`  
PR: #1 — `fix(governance): restore Apache-2.0 and Telos boundary`  
Branch: `2026-09-10-restore-apache2-telos-boundary`  
Verified head: `9c5ad79e95c0400a0e24ef7c4f5d6fd90a9b27c5`

Changes:

- canonical full Apache License 2.0 text;
- package metadata changed to Apache-2.0;
- explicit Telos ownership of endpoint identity/SSRF/DNS/pinning/redirect/
  proxy/TLS/endpoint-use authorization;
- Phylax remains generic compile/runtime security/safety admission and
  monitorability substrate;
- >=80% coverage floor added, with stricter thresholds preserved.

Exact-head CI run `34407316622`: success. Review-thread sweep: none.

## Task 9 — Claude-Desktop-LLM transfer

Repository: `oramasys/Claude-Desktop-LLM`  
PR: #1 — `refactor(policy): transfer endpoint-security authority to Telos`  
Branch: `2026-09-10-transfer-endpoint-security-to-telos`  
Verified head: `6a602e8786708dbe62a112360ddde4ba63b8c3ad`

Result:

- the former TypeScript endpoint-policy implementation is no longer a permanent
  competing v2 authority;
- `endpoint-policy.ts` is a provider-facing compatibility facade;
- actual endpoint-security execution crosses the Telos JSONL bridge;
- there is no direct-fetch fallback;
- provider protocol/lifecycle remains with Claude-Desktop-LLM;
- provider tests inject a deterministic Telos transport double rather than
  duplicating policy semantics;
- >=80% line/function/branch coverage gate is enforced.

The first transfer CI exposed a real composition bug: provider-contract tests
created providers directly and bypassed the server path that supplied
`allowedEndpoints`. The provider/Telos seam was corrected rather than weakening
Telos.

Exact-head CI run `34407097945`: success. Review-thread sweep: none.

## Task 10 — ADR 62 and PR #351 reconciliation

Repository: `diazMelgarejo/orama-system`  
PR: #351 — `docs(v2): harmonize full instruction audit and migration plans`  
Branch: `docs/v2-audit-migration-harmonization-20260909`

Key documentation commits:

- ADR 62 canonical restoration:
  `42bef136120eaadd311ab2e21a7f17d2db1017ba`;
- ownership-versus-enforcement clarification:
  `b33da9908f0aa33ffeb760ec7742c7016b12c0bf`.

ADR 62 now records:

- the 2026-08-29 design was never superseded;
- semantic-only September Telos was implementation drift;
- Telos owns all endpoint-specific security;
- PT is v1-only and clean-room evidence for v2;
- Claude becomes a Telos consumer;
- Phylax is generic security only;
- Oramasys Gateway's dedicated dialer is transitional implementation evidence,
  not a second steady-state authority;
- Telos/Phylax are Apache-2.0;
- >=80% coverage floor, with stricter component thresholds never lowered;
- citation-contaminated secondary synthesis is not architecture evidence.

CodeRabbit correctly identified that canonical ownership must not be confused
with complete migration enforcement. E10 was corrected: direct historical/current
`curl`, `urllib`, `httpx`, and Gateway paths are not considered Telos-enforced
until individually migrated and verified. The review thread was resolved.

## Tasks 12–13 — PT `.agent` memory and coordination

Repository: `diazMelgarejo/Perpetua-Tools`  
PR: #382 — `Gate 4 Half B: agent_launcher.py adopts dedicated-dialer discipline`  
Branch: `gate4/halfb-dialer-adoption-20260907`

Human-readable semantic memory:

`.agent/memory/semantic/TRIPWIRE_TELOS_ENDPOINT_SECURITY_AUTHORITY_2026-09-10.md`

Working coordination board:

`.agent/memory/working/2026-09-10-tripwire-telos-restoration-coordination-board.md`

Canonical machine-retrievable lesson:

**`lesson_5efb8cefb8af`**

The canonical PT memory pipeline was executed through the real
`.agent/tools/learn.py` → `graduate.py` path after all v2 heads were verified.
Workflow run `34408305625` completed successfully and produced commit
`6a8bc5faf8abf274932e9ee5b80d45781935a9d8`.

The pipeline:

- appended an episodic evidence record;
- appended the accepted lesson to `semantic/lessons.jsonl`;
- regenerated `semantic/LESSONS.md` through tooling;
- moved the candidate to
  `memory/candidates/graduated/5efb8cefb8af.json`;
- validated semantic and episodic JSONL;
- committed and pushed the generated memory.

The temporary one-shot workflow used to execute the repository-native memory
pipeline was removed immediately afterward. Rendered memory was never hand-edited.

## Citation-contamination correction

The Telos/Phylax evolution writeup referred to as “Document 7” is quarantined as
untrusted secondary synthesis because unrelated external citations were used as
if they established repository-specific facts.

Future agents MUST ground project-specific architectural claims in repository
files, commits, PR/review records, PT `.agent` memory, or explicit approved
architecture decisions. Do not invent Document 7's author/date/tool provenance
without actual artifact metadata.

## License doctrine

```text
oramasys/telos           Apache-2.0
oramasys/phylax          Apache-2.0
PT endpoint-policy       Apache-2.0 (v1 runtime/evidence)
oramasys/oramasys        MIT
oramasys/perpetua-core   MIT
Claude-Desktop-LLM       MIT consumer
```

## Coverage doctrine

Every project maintains at least **80% test coverage**. If a component already
defines a higher threshold, the higher threshold remains binding and MUST NOT be
lowered.

## Remaining migration boundary

The canonical authority restoration and the explicitly requested Tasks 3–13 are
implemented/verified as described above. One broader v2 consumer-migration
dependency remains outside those completed task boundaries:

`oramasys/oramasys/src/orama/gateway/dialer.py` still contains transitional
DNS/classification/connector behavior from the semantic-only Telos era.

Its useful vectors have been absorbed into Telos parity evidence, but the
Gateway consumer contract must still be deliberately rewritten so Oramasys
keeps application/provider purpose/port policy while Telos owns endpoint
identity, DNS/address classification and secure transport. Do not perform a
cosmetic dependency bump or recreate endpoint security locally.

This remaining consumer migration does **not** change the canonical ownership
decision; it means global enforcement is not claimed until that path and other
direct outbound paths are migrated individually.

## Hard rules for receiving agents

1. Read PT `lesson_5efb8cefb8af` and the semantic memory before endpoint-security
   work.
2. Never create a permanent v2 secure connector outside Telos.
3. Never add a direct-network fallback around Telos denial/unavailability.
4. Never restore caller-trusted `is_public` as security evidence.
5. Never make PT v1 depend on v2 packages.
6. Never make Telos depend on PT v1 at runtime.
7. Maintain >=80% coverage and preserve all stricter existing thresholds.
8. Re-fetch exact PR heads, CI and review threads after every push or concurrent
   agent update.
9. Treat preserved historical source documents as evidence, not current
   implementation status.
10. Never merge without explicit owner authorization.

## Merge state

No PR referenced by this handoff was merged by this work. Merge remains a
separate explicit owner decision.
