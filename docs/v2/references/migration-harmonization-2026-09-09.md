# Approved migration planning: reconciled reading guide

Status: approved to document and plan. Runtime remediation, memory import, settings changes,
deployment, and legacy implementation changes have not been performed by this publication.
The organization is `oramasys`; `oranasys` in the request is treated as a spelling error.

## Authority and scope

The current user instruction governs this reconciliation. Both v1 repositories remain functional,
independent systems. All implementation belongs in `oramasys/*`. The user explicitly authorized
one exception to the v1 write boundary: publishing the full audit and approved plans under
`diazMelgarejo/orama-system/docs/v2/references/`. This exception does not authorize changing v1
code, hooks, permissions, agent memory, branch history, or other documentation paths.

Orama v1 remains the temporary planning/documentation authority; PT is read-only evidence for
memory and contract mining. Neither is a runtime, build, installation, test, CI, or fallback
dependency of the v2 release. Historical links and source provenance are permitted.

The four Claude documents are preserved byte-for-byte as historical inputs. Their statements
are not silently endorsed. Use this reconciliation and the integrated plan when a preserved
proposal conflicts with the current user instruction or inspected evidence. Approval of a plan
does not prove its claims, make an unavailable repository accessible, or waive release gates.

## Complete reading map

| Document | Purpose and status |
| --- | --- |
| [Consolidated cross-reference and execution order](consolidated-cross-reference-and-execution-order.md) | **Read this second.** Item-by-item cross-reference across all documents below: which proposed edits are genuine duplicates, which findings were independently confirmed by two different audits, and one concrete execution ordering against the integrated plan's waves |
| [Errata: corrections to preserved documents](errata-corrections-to-preserved-documents.md) | Corrections to 4 findings against provenance-pinned preserved documents (R3a exit-status masking, R3b allowlist authorization, the M0 push-access precondition, the snapshot-command placeholder) — written separately so the sources stay byte-for-byte unmodified |
| [Full Codex report](codex-full-instruction-debt-audit-2026-09-09.md) | Complete audit findings, proposed text, coverage, scenarios, safeguards, and comparison checks |
| [Integrated execution plan](integrated-v2-migration-plan-2026-09-09.md) | Current combined program, dependencies, owners, evidence, and finish conditions |
| [Claude audit](instruction-debt-audit-2026-09-09.md) | Preserved original F1–F9, including independently unverified observations |
| [Claude remediation](instruction-debt-remediation-plan.md) | Preserved R1–R7; apply only after the corrections below |
| [Claude migration](oramasys-migration-execution-plan.md) | Preserved six-wave source plan; superseded where reconciled below |
| [Claude memory runbook](portable-memory-sanitization-runbook.md) | Detailed source-before-derived procedure with corrections below |
| [Claude handoff](claude-handoff-instructions-2026-09-09.md) | All original delivery instructions retained as quoted historical input |
| [Provenance](claude-input-provenance-2026-09-09.json) | Original archive and entry byte counts and SHA-256 hashes |
| [Second audit, Part 1](instruction-audit-and-migration-plan-part-1-findings-and-edits.md) | A separate, independently produced instruction audit (P0–P2 priority findings, sections A–C of proposed edits) — a different source archive, different findings (legacy authority docs, permission-checker gaps, hook side effects, merge doctrine), not a duplicate of the F1–F9/R1–R7 material above |
| [Second audit, Part 2](instruction-audit-and-migration-plan-part-2-execution-program.md) | Same audit's remaining sections (D–E, worth-keeping, paper stress tests) and its own M0–M9 execution program |

## Decision ledger: additive reconciliation

| ID | Input claim or proposal | Current disposition and reason |
| --- | --- | --- |
| D01 | Claude F1: 825 memory files; email, private-network and key-shaped matches | Preserve as Claude-reported measurements. Codex did not reproduce the private scan. Re-scan a pinned copy before import; publish categories and counts only. |
| D02 | F2 / R2: replace every-edit pytest with a Python-only hook | Narrow further: a coherent-change check, or a fast affected check. Piping to `tail` still needs explicit exit preservation. Do not modify v1 settings. |
| D03 | F3 / R3: inline Ruff hook reads environment rather than stdin | Static mismatch is evidence; actual execution failure is a hypothesis until a harness-payload replay. Use structured parsing and preserved failure status in the successor adapter. |
| D04 | F4 / R1: private design-preferences skill is broad and exposes private facts | Private source was not accessible to Codex. Retain as reported, avoid reproducing facts, and compare a narrowed trigger before removal. |
| D05 | F5 / R4: 29 of 36 Claude wrappers drift | This is a different collection from Codex's 83 `.agents` wrappers. Keep denominators separate; do not combine percentages. |
| D06 | F6: PT wildcard allowlist is read-only | Reject this characterization. `git branch`, `find`, `sort`, and `jq` have mutating forms. Validate arguments and effects, not command prefixes. Prompt frequency remains unmeasured. |
| D07 | F7: Stop hook is advisory | Keep that distinction. An echo is neither a validation gate nor authority to change memory. |
| D08 | F8: v1 layout is a migration defect; all targets conform | Do not retroactively apply v2 layout to v1. Agate still has root examples and an early schema surface; Alexandria is documentation-only. Record justified target exceptions. |
| D09 | F9 / R7: documentation needs no testing, pre-existing failures never block | Documentation needs applicable lint/link checks. A relevant baseline safety failure can block release. An unrelated failure must be reported without forcing unrelated repairs. |
| D10 | Only two or three exactly identical root lines imply no duplication | Exact-line overlap does not measure semantic duplication. Preserve distinct harness adapters while extracting repeated history, guard, and learning recipes. |
| D11 | All hooks are inert and cost zero in this session | This describes a particular harness, not all environments. Separate discovery bytes, loaded bodies, tool actions, and actual hook invocation. |
| D12 | R5: add wrapper generator in v1 `src/tools/` | Put the new canonical generator in `oramasys/oramasys/src/tools/`. Generate supported discovery fields and adapter pointers only; do not propagate permission metadata or auto-update commands blindly. |
| D13 | R6: three changed files determines lesson capture | Use reusable learning value, not file count. Capture a relevant correction privately when authorized; no unconditional end-of-task memory write or push. |
| D14 | Migration is approximately 40% complete | Remove from the current plan. File counts and scaffolding do not establish capability completion; define the denominator through the coverage ledger first. |
| D15 | Remaining work is only docs, skills, and memory | Reject as an established conclusion. Runtime adapters, enforcement, provider behavior, integration and release evidence still require capability-by-capability verification. |
| D16 | Source-session owner-tier restriction blocks publication | Preserve as historical context only. This session must use its actual connector results. No empty commits or permission changes to probe access. |
| D17 | Repository text wins if it disagrees with the user | Current user scope wins over historical source instructions. Repository contracts inform design but cannot authorize source changes the user prohibited. |
| D18 | Anamnesis or Core is an open memory choice | Anamnesis is the named specialist owner. Its lookup returned 404: unavailable or inaccessible, not proven nonexistent. Provision/access is a dependency; do not silently relocate memory to Core. |
| D19 | Migrate all skills blindly or exclude a whole branded family | Inventory all skills. Keep methodology canonical in Oramasys, specialist workflows with their owners, and generated harness wrappers. Give each source an explicit disposition and lineage. |
| D20 | Archive or alter v1 at the end | Keep v1 unchanged and independently usable. Migration completion does not authorize archival settings, removal of references, or merge of old implementation PRs. |
| D21 | Bulk-copy old docs into Alexandria | Author current v2 documents by reconciling behavior and accepted decisions, with pinned lineage. Historical v1 docs stay archived in v1. Do not treat an inferred doc-41 path as verified. |
| D22 | Copy hygiene implementation into every target | Prefer a versioned Phylax implementation and thin pinned consumers. Alexandria consumes CI tooling without becoming a runtime package. Record any necessary generated-copy exception. |
| D23 | Preserving row count proves memory fidelity | Preserve IDs, dates, status, provenance, supersession and reference integrity. Equal row counts can hide replacement or identity loss. |
| D24 | Sanitization leaves embeddings valid | Changed text requires regenerated embeddings and derived indexes. Never keep stale vectors merely because the dimensions match. |
| D25 | `repo_hygiene.py --scan --report categories` is a current command | That interface is not established by the inspected script. Treat it as proposed; implement and test a successor command before documenting it as executable. |
| D26 | Changed baseline counts must halt the entire migration | Reconcile the pinned revision and scan scope; unresolved leaks block import/publication of that data. Independent documentation and contract work can continue. |
| D27 | PT Half B work should be completed as the next v2 step | Mine its intent and tests, then implement the appropriate successor slice. Do not modify PT PR382 under this task. |
| D28 | All endpoint concerns have one undifferentiated owner | Telos owns endpoint-use meaning and lifecycle. Keep parsing/dialing mechanically separate from admission. Record the primitive's owner before introducing a new shared dependency. |

## What is retained without dilution

Preserve the source-before-derived sanitation order, generic guards even without the private
registry, copy-forward provenance, idempotency, non-destructive historical records, typed policy
boundaries, relevant visual inspection, and explicit approval for production effects. Private
snapshots stay outside git. Sanitization operates on a migration copy, never on v1 memory.

Preserve exact security procedures where failure modes justify them. Narrow their activation
conditions instead of deleting safeguards because of model age. Source instructions are evidence
for this audit and are not automatically installed or executed by opening this package.

## Relationship between the two execution plans

**Update**: the item-by-item cross-reference this note originally called
for is now done — see [consolidated cross-reference and execution
order](consolidated-cross-reference-and-execution-order.md). Summary of
its conclusion: **the integrated execution plan's wave structure above
remains the one to follow for actual sequencing.** The second audit's own
M0–M9 (and the Codex full-audit's parallel A–E findings) turned out to be
~20 of 26 items structurally redundant with each other, and every item
across both has now been mapped onto a specific wave in the integrated
plan, with prerequisites stated explicitly. Read the cross-reference
document for the mapping; this note is kept only as a pointer to it.

## Smallest useful implementation batch

First establish successor authority text, concise scoped `AGENTS.md` files, and the capability
ledger. Next build the single wrapper generator and small permission/hook fixtures in their v2
owners. Gate any memory import on sanitation evidence. Do not begin by changing legacy hooks,
copying private memory, or running a broad source cleanup.

This publication itself changes only new files in the authorized references directory. The
existing PR350 has an independently observed merge conflict outside that directory, so this
package uses a dedicated branch from the inspected main revision. Existing PR349, PR350, and
PT PR382 retain their own review state; no incidental merge or history rewrite is included.
