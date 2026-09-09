# OramaSys Migration Execution Plan — `diazMelgarejo/*` to `oramasys/*`

> **Status:** approved 2026-09-09, pending Wave 0 provisioning
> **Derived from:** [`instruction-debt-audit-2026-09-09.md`](instruction-debt-audit-2026-09-09.md)
> **Companion plans:**
> [`instruction-debt-remediation-plan.md`](instruction-debt-remediation-plan.md) ·
> [`portable-memory-sanitization-runbook.md`](portable-memory-sanitization-runbook.md)
> **Supersedes in practice:** the forward-looking sections of
> [`18-master-alignment-v2-migration-plan.md`](../18-master-alignment-v2-migration-plan.md),
> which predates the existence of the six `oramasys/*` repos.
> **Standards applied:** [doc 46 — repository standard](../46-repository-standard.md) ·
> [doc 47 — portable-memory invariant](../47-portable-memory-local-topology-invariant.md)

---

## Governing constraints

Restated from the operator's brief, because every wave below is shaped by them:

1. **No changes to v1.** `diazMelgarejo/Perpetua-Tools` and `diazMelgarejo/orama-system`
   are working as intended. Every wave is **copy-forward, never cut.** v1 is read-only
   throughout.
2. **No cross-org mixing.** v2 repos represent a different regime, not a stepped evolution
   of v1. All `oramasys/*` repos must work together from the start without depending on
   `diazMelgarejo/*`.
3. **v1 remains authority during transition.** `orama-system` is the docs and planning
   authority, and `Perpetua-Tools` the `.agent` memory and contract-surface source, until
   migration completes.

Constraints 2 and 3 are in tension by design — that is what makes this a transition rather
than a switch. Wave 5 exists to resolve it, and nothing before Wave 5 should try to.

---

## Prerequisite: session tiering blocks execution

Measured during the audit:

```text
add_repo(oramasys/oramasys,      access=push) -> REFUSED: cross-tier adds not supported
add_repo(oramasys/perpetua-core, access=push) -> REFUSED: cross-tier adds not supported
add_repo(diazMelgarejo/orama-system, access=push) -> REFUSED: cross-tier adds not supported
```

A session is tiered to a single repository owner. Read access to public repos works across
owners; **write access does not.**

**Consequence:** each wave must run in a session opened with its target repository as the
*initial source*. A single session cannot migrate from `diazMelgarejo/*` into
`oramasys/*` — it can only read one and write the other, never both.

**Working pattern:** clone the legacy source read-only into a session tiered to the
target repo. Read access is unrestricted, so the source material is available; the write
side is correctly scoped to one destination.

---

## Correcting one premise

The brief describes migrating "all now." The repositories disagree, and the repositories
should be trusted here. `oramasys/alexandria/README.md` states:

> **not yet in active use** … `orama-system/docs/v2/` remains the canonical, actively-
> maintained specification tree until a real migration is explicitly scheduled.
> **Not scheduled:** the full `docs/v2/` to `alexandria` migration. When it happens,
> `orama-system/docs/v2/` is expected to remain fully intact as historical source — this
> repo receives copies, not a destructive move.

This matches constraint 3 exactly. This plan therefore **schedules** that migration rather
than assuming it already applies, and holds every move to copy-forward semantics.

---

## Current state: the migration is roughly 40 percent complete

Measured by cloning all six targets:

| Repo | Files | State |
| --- | --- | --- |
| `perpetua-core` | 68 | Real MiniGraph engine, 11 graph plugins, 30 test files, CI workflow |
| `oramasys` | 27 | Gateway lifecycle, FastAPI surface, dialer, 5 test files |
| `telos` | 10 | Complete vertical slice: contracts, policy, authorizer, boundary doc |
| `phylax` | 9 | Complete vertical slice: contracts, authorizer, boundary doc |
| `agate` | 8 | Spec, JSON Schema, two worked examples |
| `alexandria` | 2 | Scaffold only, by explicit design |

**What remains is docs, skills, and memory — not core code.** This substantially reduces
risk and reorders priorities: the code migration people usually fear most is largely done.

Every target already conforms to doc 46 (`src/<pkg>/` plus `src/tests/`, hatchling
src-layout). Both legacy repos do not (audit F8). **This asymmetry is the central
structural fact of the migration** and the reason no wave below is a directory copy.

---

## Cross-org coupling: better than feared

Checked across all six targets:

| Target | References to legacy org | Kind |
| --- | --- | --- |
| `oramasys` | 27 in 4 files | prose plus 1 docstring |
| `perpetua-core` | 7 in 3 files | prose plus 1 docstring |
| `agate` / `telos` / `phylax` / `alexandria` | 2-7 each | prose only |

**No `pyproject.toml` or `Makefile` in any target references the legacy org.** There is no
build-level cross-org dependency to unwind — only prose and two docstrings, in
`perpetua-core/src/perpetua_core/discovery/__init__.py` and
`oramasys/src/orama/gateway/compat.py`. Constraint 2 is a Wave 5 text pass, not an
architectural problem.

One real coupling does exist: `oramasys/README.md` documents `make dev-install` depending
on a **sibling `../perpetua-core` checkout** (pre-release, unpublished). `telos` is already
resolved properly through a pinned `oramasys-telos` dependency. That is the pattern
`perpetua-core` should follow — see Wave 5.4.

---

## The waves

Each wave runs in its own session, tiered to its target. Waves 1 and 2 gate everything
after them.

### Wave 0 — Provisioning

No code. Removes the blockers that would otherwise stall every later wave.

1. Confirm the operator can open sessions tiered to each `oramasys/*` repository.
2. Confirm push rights on all six targets.
3. Stand up the **local-only registry** on every machine that will run a migration
   session, using doc 47's recommended keys: `owner_gmail`, `owner_name`,
   `forbidden_attribution`, `local_path_fragment`, `local_workspace_fragment`,
   `verboten_path_fragment`, `device_or_network_fragment`.

**Wave 2 cannot start without step 3.** The sanitization runbook resolves literals to
registry keys; without a registry there is nothing to resolve to.

**Exit criterion:** a session can push a trivial commit to each of the six targets, and
the registry loads on each machine.

---

### Wave 1 — Port the hygiene gate to v2

Before content moves, the destination must be able to reject bad content. This wave exists
because of audit F1: without it, Wave 2 would import leaks into clean repositories.

1. Port `Perpetua-Tools/scripts/review/repo_hygiene.py` and `repo_hygiene_core.py` into
   each target as `src/tools/repo_hygiene.py`. **Note the path** — `src/`, per doc 46. Do
   not reproduce the root-level `scripts/` violation from audit F8.
2. Extend it to the full doc 47 guard shape:
   - exact configured private literals from the local-only registry
   - private or unclassified full email literals in portable memory
   - personal home-directory paths
   - local workspace and topology fragments from the registry
   - local temporary paths from the registry
   - secret and API-key patterns
   - **derived views as well as source rows**
3. Enforce doc 47's reporting rule: the guard reports **path, line, and category only**,
   and never prints the matched literal.
4. Carry `LINT-013` forward — no dotted-quad LAN literals in tracked non-Python files.
   Affinity slugs such as hardware tier categories remain permitted; only address literals
   are expunged.
5. Wire into CI. `perpetua-core` already has `.github/workflows/test.yml` to extend; the
   other five need a workflow created.

**Exit criterion:** CI on all six targets fails a commit containing a synthetic planted
marker, and passes on a clean tree. Test with synthetic values only — never a real literal.

---

### Wave 2 — Sanitize and migrate portable memory

Gated by Wave 1. This is audit F1, and the wave most likely to go wrong.

Full procedure:
[`portable-memory-sanitization-runbook.md`](portable-memory-sanitization-runbook.md).

Summary: snapshot `.agent/` outside git, sanitize **source rows first**, **regenerate**
derived views from the sanitized sources, re-scan to zero, then migrate. Add write-time
redaction so new records are sanitized before persistence.

The v1 `.agent/` tree is **not modified** — this is a copy-forward, per constraint 1.

**Blocking decision:** which repository owns portable memory in v2?
[`56-anamnesis-runtime-memory-migration.md`](../56-anamnesis-runtime-memory-migration.md)
names `anamnesis`, but **no `oramasys/anamnesis` repository exists** — verified during the
audit. Either create it, or land memory in `perpetua-core`. This blocks the runbook's final
step and should be settled during Wave 0.

**Exit criterion:** the guard reports zero on the migrated tree, and a round-trip
regeneration of derived views is a no-op.

---

### Wave 3 — Documentation to `alexandria`

Formally schedules what `alexandria/README.md` records as unscheduled.

1. Copy `orama-system/docs/v2/` — 68 numbered documents plus `plans/` and `references/` —
   into `alexandria/`. **`orama-system/docs/v2/` stays fully intact.** The target README
   commits to this and so does constraint 1.
2. **Preserve the numbering.** The tree is densely cross-linked by number (46 to 47 to 50,
   60 to its three parts). Renumbering would break every reference.
3. De-duplicate `41-alexandria-repository.md`, which currently exists in **both**
   `orama-system/docs/v2/` and `oramasys/oramasys/docs/v2/`. `alexandria` becomes its
   single home; leave pointers behind.
4. Add a status header to each copied document distinguishing canonical-in-alexandria from
   historical.
5. Only after the copy verifies: flip `alexandria/README.md` from "not yet in active use"
   to active, and mark `orama-system/docs/v2/` historical **in alexandria's own docs** —
   not by editing v1.

**Exit criterion:** every internal link resolves within `alexandria`, and v1 `docs/v2/` is
byte-identical to its pre-wave state.

---

### Wave 4 — Skills consolidation

101 skill directories: 62 canonical plus 39 wrappers. The largest unknown in this plan.

1. **Land remediation R5 first** — the wrapper sync script. Migrating 29 drifted
   descriptions (audit F5) would carry the drift across the org boundary permanently.
   This is a hard ordering dependency.
2. Triage all 62 canonical skills into three buckets:
   - **migrate** — harness-neutral, works as-is
   - **rewrite** — v1-coupled; anything referencing `bin/orama-system/`, `openclaw`,
     `gbrain`, or `gstack` paths
   - **archive** — v1-only, notably the `openclaw-*` family
3. Apply doc 46: canonical skills land under `src/`, not `bin/`. Doc 18 already anticipates
   this — *"In v2, `bin/` is largely deprecated in favor of proper Python modules or
   dedicated plugin boundaries."*
4. Re-audit each migrated skill's description against audit F5's criteria — no catch-all
   triggers, no self-arguing activation clauses — **at migration time.** Auditing during
   the move is far cheaper than a second pass afterwards.

**Scope warning.** This wave could not be sized from metadata alone. 62 bodies at roughly
200 lines each is a genuine multi-session effort. Budget accordingly, and do not let it
block Waves 1 through 3, which are independent of it.

**Exit criterion:** every migrated skill activates on its intended trigger and none on the
catch-all pattern; the wrapper sync check is green in CI.

---

### Wave 5 — Cut the v1 authority references

Last. Only once Waves 1 through 4 have landed. This wave resolves the tension between
constraints 2 and 3.

1. `perpetua-core/README.md` — the authority-split table names
   `diazMelgarejo/orama-system` as owner of GraphSpec, evaluation, workflow, and
   effect-policy semantics. Repoint to the v2 owner.
2. Rewrite the two docstrings in `perpetua_core/discovery/__init__.py` and
   `orama/gateway/compat.py`.
3. `alexandria/README.md` — the governance table lists `orama-system` as the live L3
   methodology layer and `Perpetua-Tools` as L2 runtime. Repoint once superseded.
4. Resolve `oramasys`'s sibling-checkout dependency on `../perpetua-core`: pin a reviewed
   commit, mirroring the existing `oramasys-telos` pin, so a clean `pip install` resolves
   without a sibling checkout.
5. Final sweep: a case-insensitive search for the legacy org across `oramasys/*` returns
   only historical-provenance notes, never a current-authority claim.

**Exit criterion:** no v2 repository names a v1 repository as a current authority.
Constraint 2 holds in the end state.

---

## Sequencing

```text
Wave 0 ──> Wave 1 ──┬──> Wave 2  (memory, gated by Wave 1)
                    ├──> Wave 3  (docs)      ──┐
                    └──> Wave 4  (skills)    ──┼──> Wave 5
                                               ┘
```

Waves 2, 3, and 4 are independent of each other once Wave 1 lands and can run in parallel
sessions. Wave 5 is strictly last.

---

## Risk register

| Risk | Likelihood | Mitigation |
| --- | --- | --- |
| Memory leak crosses into a clean-room repo | **high** if Wave 1 skipped | Wave 1 gates Wave 2. Non-negotiable. |
| Doc renumbering breaks 68 cross-linked documents | medium | Preserve numbering (Wave 3.2) |
| Description drift becomes permanent across the org boundary | **high** | R5 sync script before Wave 4 (Wave 4.1) |
| Root-level `scripts/`/`tests/` imported into conforming targets | medium | Doc 46 as acceptance criterion (audit F8) |
| `anamnesis` never created; memory lands in the wrong repo | medium | Settle during Wave 0; blocks Wave 2 |
| Wave 4 scope overruns and stalls the programme | medium | Waves 1-3 are independent; do not serialise behind it |
| v1 destabilised | **low** | Every wave is copy-forward; v1 is read-only throughout |

---

## Open questions

These four require an operator decision. Each blocks the wave named.

1. **`anamnesis`** — create the repository, or land portable memory in `perpetua-core`?
   *Blocks Wave 2, step 5.*
2. **Skills destination** — one shared home, or per-repo skill trees? Doc 46 says `src/`;
   doc 18 says `bin/` is deprecated; neither names the owning repository.
   *Blocks Wave 4, step 3.*
3. **v1 end state** — archived read-only, or maintained indefinitely? Determines whether
   Wave 5 leaves pointers or removes references outright. *Blocks Wave 5, step 5.*
4. **Wave 4 appetite** — migrate all 62 canonical skills, or only those with live v2
   triggers? *Determines Wave 4 sizing.*

---

## Recommended first move

Wave 0 plus Wave 1, in a session tiered to `oramasys/perpetua-core` — it already has a CI
workflow, so the hygiene gate has somewhere to land immediately.

That unblocks everything downstream and puts the guard in place **before any content
crosses the org boundary**, which is the one ordering mistake in this plan that would be
genuinely expensive to undo.
