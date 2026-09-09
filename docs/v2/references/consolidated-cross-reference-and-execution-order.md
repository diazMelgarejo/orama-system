# v2 Migration Planning — Consolidated Cross-Reference and Execution Order

> **Status:** planning reference, not yet implemented. This document does
> what [migration-harmonization-2026-09-09.md](migration-harmonization-2026-09-09.md)'s
> reading map alone did not: an actual item-by-item cross-reference across
> every document in this directory, a real redundancy/parallel/prerequisite
> map, and one concrete execution ordering. Read the harmonization doc
> first for authority, scope, and the 28-item decision ledger — this
> document builds on it rather than restating it.
> **This document changes no proposal's content.** It maps what already
> exists across the other eight documents in this directory. Where two
> documents propose materially the same thing in different words, this
> document says so and picks one to carry forward — it does not invent a
> third wording.

---

## 1. The two tracks, and why they exist

Reading all nine documents in this directory in full (not just the
reading-map index) surfaces something the index alone doesn't state
explicitly: **there are two structurally independent audit tracks**,
produced separately, that were never cross-referenced against each other
before this document.

**Track A — the "Claude" F/R track**: `instruction-debt-audit-2026-09-09.md`
(F1–F9), `instruction-debt-remediation-plan.md` (R1–R7),
`oramasys-migration-execution-plan.md` (the original six-wave plan),
`portable-memory-sanitization-runbook.md`. Findings are specific measured
facts — 825 memory files, 29-of-36 wrapper drift, a Ruff hook reading
environment instead of stdin. **Already reconciled** against current
evidence via the harmonization doc's 28-item decision ledger (D01–D28) and
folded into `integrated-v2-migration-plan-2026-09-09.md`'s wave structure.

**Track B — the "Codex/Claude second audit" track**:
`codex-full-instruction-debt-audit-2026-09-09.md` (this repo's Codex
session) and this session's own two-part audit
([Part 1](instruction-audit-and-migration-plan-part-1-findings-and-edits.md),
[Part 2](instruction-audit-and-migration-plan-part-2-execution-program.md)).
**These two were never reconciled against each other before this
document, and neither was reconciled against Track A.**

Confirmed directly, not assumed, before writing anything below: both
Track B documents use the identical P0/P1/P2 priority taxonomy, the
identical A–E proposed-edit section structure, cite the identical
repository snapshot commits, and propose edits to the identical files
(`oramasys/perpetua-core/README.md`'s authority language,
`oramasys/alexandria/README.md`'s migration posture, the same Superpowers
plugin skill files) — with different specific wording for the same
proposals. This is not two complementary audits; it is two independent
syntheses of the same underlying source material.

---

## 2. Track B cross-reference: redundant pairs

Every A–E item in both Track B documents, checked directly against its
counterpart. "Substantively identical" means: same target file, same
underlying finding, different wording only. Where one side has content
the other lacks, that's noted rather than treated as a conflict.

| This session's item | Codex full-audit item | Relationship | Disposition |
| --- | --- | --- | --- |
| A1 — `perpetua-core/README.md` authority | A1 — same file, same finding | Substantively identical | Carry forward this session's wording — states the read-only-evidence framing with an explicit "not a runtime/build/installation/test/CI dependency" list; Codex's version is shorter but equivalent |
| A2 — `alexandria/README.md` migration posture | A2 — same file, same finding | Substantively identical | Either wording works; Codex's is slightly more concise. No material difference to reconcile |
| A3 — Telos/Phylax boundary docs | A3 — same two files, same finding | Substantively identical | Carry forward either; both state "no fallback to v1" and "contract needs owner/version/tests" |
| A4 — new `alexandria/migration/regime-boundary.md` | *(no direct counterpart)* | Unique to this session | Genuinely new — Codex's audit doesn't propose this specific new file. Keep |
| B1 — skill wrapper "Before Use" fetch/pull | B1 — same finding, same 83-file/68-fetch/65-block measurement | Substantively identical | Same underlying measurement cited in both — confirms the number is real, not restated independently. Carry forward either wording |
| B2 — skill description table (12 skills) | B2 — skill description table (12 skills, slightly different skill list) | **Partial overlap, not identical** | Codex merges `orama-afrp`/`orama-cidf` into one `cidf` entry; this session keeps them separate. Neither is obviously wrong — depends on whether AFRP and CIDF are actually one skill or two in the real installed set, which neither audit independently confirmed. **Open item**, not silently resolved here |
| B3 — entry-file splitting by workflow | B3 — same finding, notes a missing security-enforcer workflow path | Substantively identical, Codex has more detail | Carry forward Codex's version — it additionally flags a broken reference this session's version didn't catch |
| B4 — memory-trigger successor adaptation | B4 — same finding | Substantively identical | Either wording works |
| C1 — Phylax enforcement gap + contract | C1 — same finding (PT permission checker) | Substantively identical finding; this session's proposed contract text is more detailed | Carry forward this session's version — it names the specific `check_tool_call()` behaviors (returns allow for unknown schemas, doesn't evaluate `blocked_patterns`, not registered as a `PreToolUse` hook) that Codex's version references more generally |
| C2 — shared permissions policy | *(folded into Codex's C1 discussion)* | Overlapping scope, not a clean 1:1 pair | Both cover approval-boundary conflicts; this session's is a standalone policy proposal, Codex's is embedded in the C1 discussion. Carry forward this session's standalone version for clarity |
| C3 — hook configuration | *(folded into Codex's C1 discussion)* | Same relationship as C2 | Same disposition as C2 |
| C4 — command-permission allowlist (`git branch`, `find`, `jq`) | **Track A's D06**, not Track B | **Cross-track match, not Track B redundancy** | See §3 below — this is the more important finding: two *independently reconciled* sources (this session's audit, and Track A's F6/D06) agree on the same real gap |
| C5 — `oramasys/oramasys/Makefile` test-target diff | *(no direct counterpart in Codex's audit)* | Unique to this session | Genuinely new, concrete, and small. Keep |
| D1 — verification standard (Cursor rules) | D-series, same finding | Substantively identical | Either wording works |
| D2 — `oramasys-method` "never visual" wording conflict | D-series, same finding | Substantively identical | Either wording works |
| D3 — merge doctrine (10-minute wait, "simulate" mutates) | D-series, same finding | Substantively identical | Either wording works |
| D4 — rewritten-history section | D-series, same finding | Substantively identical | Either wording works |
| D5 — orchestrator/verifier elegance-score conflict | D-series, same finding | Substantively identical | Either wording works |
| E — Superpowers plugin proposals (10 files) | E-series, same plugin path, overlapping file list | Substantively identical | This session's table is organized file-by-file with exact replacement text per section; Codex's covers the same ground. Carry forward this session's version — it's the more complete of the two on this specific section |

**Net result of this cross-reference**: roughly 20 of 26 Track B items are
genuine duplicates needing no further reconciliation beyond picking one
wording. Four (A4, C5, and the C4 cross-track match, and B2's open
sub-item) need explicit handling, not silent merging. This is a
substantially smaller actual finding set than "two audits' worth of
items" suggested before this cross-reference.

---

## 3. Cross-track matches: where Track A and Track B independently agree

The genuinely valuable finding from doing this cross-reference: a small
number of items were found **independently by both tracks**, using
different methods, on different dates. Independent agreement is stronger
evidence than either audit alone.

| Finding | Track A reference | Track B reference | Why this matters |
| --- | --- | --- | --- |
| Command-name-prefix allowlists (`git branch *`, `find *`, `jq *`) don't establish read-only behavior | F6/D06: "Reject this characterization... `git branch`, `find`, `sort`, and `jq` have mutating forms" | This session's C4: same three example commands, same core claim | Two independent audits, different dates, same specific example commands. This is the single strongest-evidence finding in either track — carry forward with high confidence, D06's decision-ledger disposition already stands |
| PT's permission/enforcement layer claims more than it enforces | F3/D03 (Ruff hook environment-vs-stdin mismatch, PreToolUse registration) | This session's C1 (`check_tool_call()` returns allow for unknown schemas, doesn't evaluate `blocked_patterns`/`requires_approval_patterns`) | Same category of finding (declared enforcement exceeds actual enforcement), different specific mechanisms. Complementary, not redundant — both should be fixed, they're different code paths |
| Legacy Gate 4 / Doc 66 still directs PT-side implementation | D27: "PT Half B work... Do not modify PT PR382 under this task" | This session's own corroboration (§1 of Part 1): Doc 66's stale paragraph found and fixed separately in PR #347, PT PR #382's real work verified this session | This is the one item where this session has *first-hand, current* evidence beyond either audit's own inspection — the PT PR #382 work is real, tested, and merged as of this writing, not a hypothesis |
| Skill wrapper synchronization commands (`git fetch`/`pull`) run during read-only skill selection | R5, F5 (29-of-36 `.claude` wrapper drift, different denominator) | B1 in both Track B documents (83-file/68-fetch measurement) | **Different denominators, confirmed different collections** — the decision ledger's D05 already correctly keeps these separate. This document does not combine them either |

---

## 4. Where each track's proposed edits land in the authoritative execution plan

`integrated-v2-migration-plan-2026-09-09.md`'s wave structure (M0–M9) is
the one to execute against — restating its own dependency ordering here
only to map specific items onto it, not to propose a competing sequence.

| Wave | Items from this cross-reference that land here | Why this wave, not earlier or later |
| --- | --- | --- |
| M0 (baseline) | A4 (new `regime-boundary.md`) | It *is* a baseline-authority document; nothing else can proceed coherently until the write boundary is recorded in Alexandria, not just in these reference docs |
| M1 (coverage) | None directly — this wave is the capability ledger itself | Every disposition below assumes M1's ledger exists first, per the integrated plan's own "M0 precedes M1" note |
| M2 (foundations) | A1, A2, A3, B1, B2 (once the open AFRP/CIDF sub-item is resolved), B3, B4 | These are all "governance/authority text + skill-loading discipline" — the integrated plan's own M2 definition ("v2 owner guides... governed adapter discovery") |
| M3 (contracts) | C1's contract text (the Phylax enforcement contract specifically, not the whole C1 finding) | The proposed replacement text in C1 *is* a contract specification — "declares required behavior... each supported harness must register and test its admission adapter" belongs with M3's other contract work, not M4's implementation |
| M4 (specialists) | C1's actual implementation (Phylax admission adapters), C4's cross-track-confirmed allowlist fix (implemented wherever the successor permission adapter lives, likely also Phylax-owned) | This is real code, not policy text — matches M4's "Implement Agate, Telos, Phylax... Independently testable packages" |
| M5 (Core) | C5 (`oramasys/oramasys/Makefile` diff) | Small, mechanical, build-system scoped — fits M5/M2 boundary; listed here since the integrated plan's own M2 already covers "declared commands" |
| M6 (Oramasys) | D1–D5 (verification/merge/history doctrine), the PT PR #382 dialer work per the integrated plan's own note ("Mine the intent and fixtures behind legacy Gate 4 and PT PR382 into a v2 slice") | D-series items are operational doctrine for whoever does M6's implementation work, not separate deliverables — they should be adopted as working practice before M6 starts, not produced as M6 artifacts |
| M7 (knowledge) | E-series (Superpowers plugin fixes), C2/C3 (permission policy, hook configuration) | E-series is skill/documentation-adjacent, matching M7's "skill and documentation procedure." C2/C3 are agent-behavior policy, closest to M7's Alexandria authorship work |
| M8/M9 | Nothing from this cross-reference directly — these waves consume the outputs of the above, they don't have their own new proposed edits | Confirms the integrated plan's own scoping: M8/M9 are release-process waves, not places new instruction fixes land |

---

## 5. Prerequisites, stated explicitly

Reading across all documents, four real prerequisite chains exist that no
single document states end-to-end:

1. **A4 (regime-boundary.md) blocks nothing else technically, but should
   land first anyway** — every other item's disposition assumes "the
   write boundary is Alexandria-recorded," and right now that's still
   only true across scattered reference documents, not a canonical
   Alexandria record. Cheap to do first; expensive to discover missing
   later.
2. **B2's open AFRP/CIDF question blocks the skill-wrapper generator
   (Track A's R5/D12, "put the new canonical generator in
   `oramasys/oramasys/src/tools/`")** — the generator needs a settled
   skill list to generate wrappers *for*. Either resolve whether AFRP and
   CIDF are one skill or two before building the generator, or build the
   generator to handle both shapes and defer the question — but don't
   silently pick one, which is what happens if the generator is built
   against only one Track B document's table.
3. **C1's contract text (M3) must exist before C1's implementation (M4)
   — this is true within a single finding, not just across tracks.**
   Both Track B documents describe this as one finding with one proposed
   fix; this cross-reference is the first place that's split into "the
   contract" (M3) and "the adapter that implements it" (M4) as genuinely
   separate, ordered deliverables.
4. **Anamnesis provisioning (Track A's D18, still "Blocked: lookup
   returned 404" per the integrated plan's own execution ledger) blocks
   all of M7's memory-import sub-procedure, but blocks none of M7's
   documentation sub-procedure.** The integrated plan already states this
   ("memory import waits for sanitation and Anamnesis access... M7
   documentation... can proceed early") — repeated here because it's the
   single most consequential "don't block unrelated work on this" case
   across every document in this directory.

---

## 6. What this document does not resolve

Honest about scope, matching this whole directory's own stated discipline:

- **B2's AFRP/CIDF skill-count question** is flagged, not resolved — it
  needs inspection of the actual installed skill directory, which neither
  Track B document independently confirmed.
- **This cross-reference covers the A–E/P0–P2 items in both Track B
  documents exhaustively, and the highest-confidence Track A/B matches
  (§3) — it does not re-derive or re-verify every one of Track A's 28
  decision-ledger items against Track B.** That would be a second,
  comparably-sized pass; nothing found while building this document
  suggested it would change any of the 28 dispositions already recorded,
  but that's an expectation, not a checked fact.
- **No item's proposed replacement wording was independently re-verified
  against live `oramasys/*` repository content** — this session's GitHub
  token remains blocked from that org (confirmed directly, unrelated PR,
  earlier this session). Every disposition above is a reconciliation
  between documents, not a re-audit of the underlying repositories.
