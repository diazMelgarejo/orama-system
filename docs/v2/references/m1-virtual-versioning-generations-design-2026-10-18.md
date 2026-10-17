# Virtual versioning for oramasys: generations, an active pointer and a state machine

Status: design, G0 approved by the operator on 2026-10-18 with the design reviewer's
clarifications; only G1 (data-only) is authorized. Author: a coding agent. It authorizes nothing
beyond that and changes no code. It builds on `2026-10-17-m1-pin-promotion-design.md` and the
graduation ceremony in PT `.agent/references/graduation-ceremony-mutation-approvals.md`.

## 1. The idea, and why it fits what we built

M1 generation 2 showed that a promotion is mostly data: pins, a manifest, a registry snapshot,
digests, an approval, a receipt. Generation 1 is still archived byte for byte, with its own
frozen identities, and tests prove it can be rebuilt exactly. So a **generation** can be treated as
an immutable, named version of the whole compatibility contract, and **rollback can be a move
between generations** instead of a repository revert or a package downgrade. That is the same
trick as Internet Explorer's compatibility modes.

### The Internet Explorer comparison (checked against Microsoft's compatibility guidance)

| IE compatibility | Our equivalent |
| --- | --- |
| A document mode (IE5, IE7, IE8, edge) is an emulated behaviour of an older engine, selected without shipping the old browser | A **generation** names the older contract (pins, manifest, registry) without reverting the repository |
| A site or page opts in: `X-UA-Compatible` per page, or an administrator's Enterprise Mode site list maps a site to the mode in which it works | A **consumer declares the generation it needs**; an `ACTIVE` pointer is the default; `edge` means "follow the active generation" |
| The mapping is controlled by someone accountable (developer plus IT administrator) and kept as a list | The pointer and each consumer mapping are **reviewed records**, moved only by the operator |
| Emulation has fidelity levels: "IE8 Enterprise Mode provides higher-fidelity emulation ... using the original user agent string"; IE7 Enterprise Mode adds Compatibility View | We say how real a rollback is (section 4); a declared generation is not the same as a verified one |
| Without a DOCTYPE a page falls back to IE5 mode; with one, IE7 mode: defaults decide when nothing is declared | A missing declaration in production, CI or an installer must refuse, never fall through to "latest" by accident |
| Modes piled up as compatibility debt and were eventually retired | Every generation carries a **sunset rule**, so old generations are archived, not run forever |

**Limit that matters most.** In IE the newest engine runs and imitates the old one. Imitation is
never perfect. For us, pins decide what a fresh install gets; an environment that is already
installed keeps its packages until someone reinstalls. A pointer move therefore changes what we
*declare and verify*, not what is already running. Real rollback of a running system still needs a
reinstall, or one environment per generation with a switch. Say which one you mean every time.

## 2. What exists and what does not

| Exists | Missing |
| --- | --- |
| Gen-1 archive, byte-exact, tested against independent frozen identities | One source for pins: today pins repeat in the package file, lane files, CI, manifest and recipe, and tests keep them equal |
| Approval, evidence run, receipt and rollback block per generation | An `ACTIVE` pointer that names the live generation |
| Installed-identity verifier script | A state machine: `status` is free text and nothing enforces transitions |
| Record of promoted pins and a rollback target | A rule that live labels match what main installs (found after the M1 merge: the record said `proposed` while the package file already installed the new pins) |

## 3. Design

**Generation.** An immutable folder `requirements/generations/<id>/` holding pins, manifest,
coverage, install plan, registry snapshot reference, approval reference, evidence digests, receipt
reference and a sunset rule. Immutable means one canonical inventory with content digests per
generation: a later change creates a new generation and never edits an accepted folder.
Generations `m1-gen1` and `m1-gen2` are migrated as data first, byte for byte, with no
behaviour change.

**Pointer.** One file `requirements/ACTIVE-GENERATION.json` naming a generation and the record that
moved it. Package pins, lane files and CI install checks are **generated from, or checked
against,** the active generation. A check fails if any repetition disagrees.

**Consumers.** A consumer (a CI lane, a deployment, an installer) declares `generation: <id>` or
`edge`. **An undeclared production, CI or installer consumer refuses**; it never silently follows
`ACTIVE`. Any diagnostic default must be explicit and non-production.

**State machine** (one live status per generation; a transition is a reviewed record):

| From | To | Needs |
| --- | --- | --- |
| candidate | proposed | scope record; history archived; checks that can fail |
| proposed | approved | operator approval binding exact digests |
| approved | evidenced | hosted evidence sealed; independent recompute |
| evidenced | accepted | operator acceptance and receipt |
| accepted | pins-merged | merge of the pin change; labels updated in the same change |
| pins-merged | active | pointer moved by a reviewed record; installed set verified against it |
| active | superseded | a later generation is active; this one stays archived and rollback-eligible |
| any | retired | sunset reached; archive only. **Forbidden while the generation is ACTIVE or declared by any consumer** |

`rolled-back` is not a permanent generation state. A rollback is a reviewed **pointer-transition
receipt** that moves `ACTIVE` to an earlier accepted generation; the generations themselves keep
their states (`superseded`, `active`).

Serving activation, T3 and other capabilities are **separate switches**, listed in the record's
`still_off`, never implied by a generation state.

**Rollback tiers.** A rollback to a generation whose evidence is already accepted is a lighter
ceremony: operator approves the pointer move; no new evidence run is required if the target's
pins, manifest and registry are byte-identical to the accepted ones. If anything in the target
differs, it is a new generation and takes the full ceremony.

**Fidelity classes** for a rollback claim: `declared` (pointer and records say so),
`verified-installed` (installed set matches the generation's pins), `reproduced` (a fresh
environment built from the generation's pins passed the generation's evidence suite). Reports say
which class they have.

**Optimizer candidates.** AutoResearcher or optimizer output enters as a `candidate` generation.
The evaluator, safety policy and acceptance tests are fixed inputs, held outside the mutator, and
bound by digest. Promotion beyond `candidate` is the operator's.

## 3a. Where the pins live today, and the choice that decides everything

Inventory on `main` (2026-10-18): the production Core pin repeats in 13 files (the package file, two
workflows, the production lane file, both manifests, the install plan, the promotion record, the
registry fixture and three tests plus the oracle README); Telos and Agate repeat in 7 and 9
files; the consumer commit and the registry ref repeat in 8 and 9. Tests keep them equal; nothing
generates them.

The harness drift guard forbids `pyproject.toml` and `src/orama/` changes between a consumer
commit and its harness. So **a rollback that edits the package pins is always a new consumer commit
and the full ceremony.** Two ways out:

| Option | How rollback works | Cost | Real virtual rollback? |
| --- | --- | --- | --- |
| A. Pointer as a check | Pins stay in the package file. The pointer is validated against them. Rollback = new consumer commit that restores the old pins | Low. Fits the existing ceremony | No. It only makes the live label and checks honest |
| B. Constraints indirection | The package declares unpinned or range dependencies. Installs run `pip install -c <active generation>/constraints.txt` (or the lock equivalent). Rollback = move the pointer; the consumer commit does not change | Medium. CI, the production-install verifier and the installed-identity gate must all read the same constraints file | Yes, for fresh installs. Running environments still need a reinstall |

Recommendation: build A first (G2), because it removes the repeated-pin drift risk with no
packaging change; then decide B (G2b) on its own evidence. B changes how oramasys is installed, so
it is the operator's call and needs its own design review.

## 4. Staged plan (each stage is its own reviewed PR; the ceremony applies to each)

| Stage | Change | Gate |
| --- | --- | --- |
| G0 | This design, reviewed; fix the record label now | Codex design review; operator approves the record label PR |
| G1 | Migrate gen-1 and gen-2 evidence into immutable generation folders **as data only**: canonical inventory and content digests, historical sources retained, no `ACTIVE` consumption | Byte-identity tests; no production dependency or pin change; zero runtime, install or CI behaviour change; the existing suite unchanged; explicit proof that historical bytes are unchanged |
| G2 | Option A: `ACTIVE-GENERATION.json` plus checks that every one of the repeated pins and refs agrees with it | Mutation tests: a wrong pointer, a drifted pin and a missing declaration are each refused |
| G2b | Option B (only if the operator chooses it): constraints-file indirection for installs | Own design review; CI, production-install verifier and identity gate read one constraints file; fresh-environment drill on both interpreters |
| G3 | State-machine validator and transition records | Illegal transitions refused; the history of gen-1 and gen-2 replays cleanly |
| G4 | Installed-set gate: fail closed when the installed set does not match the active generation | Fresh-environment drill on both interpreters |
| G5 | Rollback drill to gen-1 on a throwaway branch, all three fidelity classes | Receipt with the independence table |
| G6 | Optimizer candidate generations | Locked-evaluator rules from doc 57 section 14 satisfied first |

## 5. Risks and non-goals

- Emulating an old contract is not running it. Do not report a pointer move as a downgrade.
- A pointer that anyone can move is a back door: moves are operator-owned records, and CI refuses an
  unreviewed move.
- A frozen manifest keeps its own labels (the gen-2 manifest still lists `production-pin-promotion`
  as disabled because it was frozen before the merge). The live status record supersedes the label;
  the frozen bytes are never edited.
- Not in scope: serving activation, T3, a runtime plug-in system, and automatic optimization.

## 6. Decisions for the operator

Resolved 2026-10-18 (operator approval of G0, with the design reviewer's clarifications):

1. G0 is approved and the record label (`pins-merged`, `still_off`) is merged.
2. Undeclared production, CI and installer consumers fail closed.
3. Retirement is forbidden while a generation is active or declared; a rollback is a reviewed
   pointer-transition receipt.
4. Only G1 is authorized (data-only, as above).

Still open:

1. Real rollback semantics for running systems: reinstall on demand, or one environment per
   generation with a switch.
2. Option A (pointer as a check) before any G2 work; Option B (constraints indirection) is a
   separate G2b design, approval and evidence path.
