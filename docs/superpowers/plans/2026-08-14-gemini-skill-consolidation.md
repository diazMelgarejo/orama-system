# Gemini Skill Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconcile the thirteen divergent Gemini skills with their canonical owners while preserving valid harness metadata, then classify the nine Gemini-only skills against Claude, Codex, and Orama before changing them.

**Architecture:** Canonical behavior stays with Orama, Perpetua, or gstack. Gemini is a distribution root: metadata-free skills become symlinks, skills with verified Gemini metadata become minimal adapters, and external-owner collisions remain untouched. Every mutation is manifest-authorized and archive-first.

**Tech Stack:** Python 3 standard library, JSON, Markdown `SKILL.md` cards, relative symlinks with generated-wrapper fallback, `pytest`.

**Spec:** `bin/orama-system/SKILL.md`, `bin/orama-system/skills/oramasys-method/SKILL.md`, `bin/orama-system/cidf/SKILL.md`, and `bin/orama-system/skills/skillify/references/codex-thin-wrapper-installs.md`.

## Global Constraints

- Keep ownership singular: Orama owns methodology, Perpetua owns runtime/configuration cards, and gstack retains its independently installed cards.
- No tracked file may contain local paths, identities, credentials, archives, or global-root contents.
- Archive a pre-existing Gemini regular directory before replacement and record source/archive SHA-256 digests with logical root labels only.
- Preserve Gemini frontmatter only after validating it against current official Gemini CLI documentation; unknown keys block reconciliation. (See Task 2, Step 3's `gemini-frontmatter-contract.md` — P2-1, 2026-08-14 gate correction — for the local, versioned validation contract that makes this reproducible across runs.)
- Every write requires `--reconcile-gemini`, `--only`, and `--archive-root`. Existing `--install` must not mutate the Gemini root.
- Never replace gstack `skillify` or `gstack-upgrade`. Orama's creator remains `oramasys-skillify`.
- Antigravity must resolve to the shared agent root; audit it rather than writing to it.
- The nine Gemini-only candidates are analysis-only until a later approved implementation plan selects their disposition.

---

## Disposition Matrix

| Slug | Owner | End state | Rule |
| --- | --- | --- | --- |
| `agent-methodology` | Orama | adapter | Preserve supported Gemini discovery metadata only. |
| `code-review`, `git-history-surgery`, `orama-afrp` | Orama | link or generated wrapper | Drop the unrelated local GLM fallback snippet. |
| `orama-gstack` | Orama | adapter | Target `bin/orama-system/gstack-gbrain/SKILL.md`, not stale `gstack`. |
| `orama-system`, `oramasys-method` | Orama | adapter | Current canonical cards subsume historical full bodies. |
| `perpetua-tools`, `perpetua-config`, `perpetua-hardware`, `perpetua-startup-intelligence` | Perpetua | cross-repo adapter | Resolve declared `PERPETUA_TOOLS_PATH` only. |
| `gstack-upgrade`, `skillify` | gstack | preserve-external | Record ownership and protect against overwrite. |

Review-only candidates: `autoplan`, `autoresearch`, `codex`, `deep-research`, `diagram`, `kimi-webbridge`, `oramasys-skillify`, `setup-gbrain`, and `sync-gbrain`.

---

## Gate Status — Review Synthesis Corrections (2026-08-14)

Three independent reviews evaluated this plan:
- `gemini-skill-consolidation-review-synthesis-codex-reviewer-2026-08-14.md` (synthesis, authoritative)
- `gemini-skill-consolidation-plan-review-codex-reviewer-2026-08-14.md` (codex-reviewer)
- `review-gemini-skill-consolidation-2026-08-14-antigravity-gemini.md` (AntiGravity-Gemini)

The synthesis set an **Implementation Gate**: implementation may not proceed past
Task 1 until (1) all six P1 corrections below are applied, (2) the duplicate lock
priority is removed, (3) the plan is committed from a clean worktree, and (4) both
review checklists are re-run against that committed SHA.

**This revision applies all six P1 corrections and both P2 corrections.** They are
folded directly into the affected task bodies below (Task 0, Task 1, Task 2, Task
5, Task 7, and Implementation Tasks) rather than listed only here, so an
implementer inherits the corrected requirement without cross-referencing this
table. This table exists so the gate's status is auditable in one place.

| # | Correction | Applied in | Required test(s) |
| --- | --- | --- | --- |
| P1-1 | `--verify` must inspect the Gemini INBOUND root, not only outbound `TARGET_ROOTS`; failure exits nonzero | Task 0, Fix 1 | unreconciled-root verify FAILs |
| P1-2 | Verification must prove recoverability (archive receipt), not just final symlink shape | Task 0, Fix 1; Task 2, Step 4 | missing receipt; mismatched receipt |
| P1-3 | Resolve Task 5 / Task 7 deadlock — `missing`/`divergent` are audited outcomes, not failures; shared-root creation deferred to a separate human-approved task | Task 5, Step 2; Task 7, Step 1; new Task 5a (deferred) | `verify_antigravity_root` states `missing`/`divergent` each produce a `RootFinding` with an operator next action; Task 7 asserts no Antigravity root mutation |
| P1-4 | Archive-first must preserve a usable live skill if activation fails after archive succeeds | Task 2, Step 4 | forced post-archive replacement failure leaves original live directory usable |
| P1-5 | Lock needs atomic acquisition (O_EXCL) + bounded, guarded recovery contract; unify duplicate P1/P2 lock task | Task 0, Fix 3 (sole P1 lock task); Implementation Tasks T8 marked superseded-by | contention; terminated-owner recovery; sequential idempotence |
| P1-6 | Execution must start from a reviewed branch state | Task 1, Preconditions | manual: `git show --stat HEAD`, `git status --short --branch` output recorded; abort on unexpected staged/unstaged edits |
| P2-1 | Accepted Gemini frontmatter needs a local, versioned validation contract | Task 2, Step 3 (metadata_policy); new `gemini-frontmatter-contract.md` reference | every preserved key tested against the local contract; unknown key errors report the exact offending key |
| P2-2 | T3/T4/T5 in Implementation Tasks are already incorporated into the plan body — move to completed history, don't leave as open work | Implementation Tasks → Completed Review History table | manual read |

**Task 1 status: COMPLETE.** Commit `da32cccb` — "feat(skills): read-only Gemini
inventory audit (Task 1)" — 29 tests green, `docs/reference/gemini-skill-consolidation-inventory.md`
generated. The gate's remaining scope is Task 0's three fixes (this revision
strengthens Fix 1 and Fix 3 per P1-1/P1-2/P1-5 above) plus Tasks 2 through 7.

---

### Task 0: P1 Review Fixes (prerequisite)

**Status:** Required before Task 1 begins. This task folds the appended
/autoplan Eng review's CRITICAL GAPs — Implementation Tasks T1, T2, and T8
below — into concrete interface requirements so every downstream task builds
on the corrected contract from the start, instead of patching it in later.

**Files:**
- Modify: `bin/orama-system/skills/skillify/scripts/install_thin_skill_wrappers.py`
  (or the split module introduced later by Implementation Task T6, if that
  refactor lands first)
- Modify: `tests/test_install_thin_skill_wrappers.py`

**Fix 1 — Gemini-aware verification path (Implementation Task T1, CRITICAL GAP).**
The existing `verify(only: set[str] | None = None) -> list[str]` (line
399-451) iterates `TARGET_ROOTS` only — Codex/Agents roots — and has no
parameter or hook for a Gemini root, so a `--verify` call after Task 7 prints
`"verification passed"` regardless of whether Gemini reconciliation ran,
partially ran, or did nothing. Add a distinct, explicitly named function:

~~~python
def verify_gemini(root: Path, only: set[str] | None = None) -> list[RootFinding]:
    ...
~~~

Task 7's `--verify --only <gemini slugs>` invocation MUST route every Gemini
slug to `verify_gemini`, never to the existing `TARGET_ROOTS`-scoped
`verify()`. The two verification paths may share helpers but must stay
structurally separate so a Gemini-only verify run cannot silently fall
through to the wrong root list and pass by accident.

Required failing test (write first): a verify run against a Gemini root where
reconciliation did **not** happen (regular directory still present, no
archive receipt, no symlink) must have `verify_gemini` return a non-empty
`list[RootFinding]` reporting failure — the CLI must exit non-zero, not print
"verification passed".

**Fix 1 — strengthened per synthesis P1-1 and P1-2 (2026-08-14 gate correction).**
The `verify_gemini` signature above is superseded by the signature below — kept
above for its rationale, but the implementer must build the corrected interface,
not the one shown above:

~~~python
def verify_gemini(
    root: Path,
    archive_root: Path,
    only: set[str] | None = None,
) -> list[RootFinding]:
    ...
~~~

Two requirements, both from the review synthesis:

1. **P1-1 — inbound root, nonzero exit.** `verify_gemini` inspects the Gemini
   **inbound** root (`~/.gemini/skills`, the foreign root this plan writes
   *into*) — never the existing outbound `TARGET_ROOTS` list `verify()`
   already covers. When `verify_gemini` returns any non-empty
   `list[RootFinding]`, the CLI's `--verify` exit code MUST be non-zero. A
   Gemini-only verify run that silently falls through to `verify()`'s
   `TARGET_ROOTS` scope and reports `"verification passed"` is exactly the
   false-pass this fix exists to close.

2. **P1-2 — prove recoverability, not just final shape.** The original
   signature (`root`, `only` — no archive root, no receipt location) cannot
   identify which archive to validate, so it can accept a correct-looking
   symlink even when the matching archive is missing, corrupt, or belongs to
   a different slug. `verify_gemini` MUST take an `archive_root` argument
   that resolves to the archive tree used at reconciliation time. Because
   this plan's tasks batch reconciliation in multiple timestamped runs
   (Task 3's 7 slugs and Task 4's 4 slugs each get their own
   `$(date -u +%Y%m%dT%H%M%SZ)` subdirectory — see Task 2 Step 4's receipt
   contract), `archive_root` for `--verify` is the **parent** archive
   directory (e.g. `$HOME/.gemini/skills-archive/`), not one specific batch
   timestamp. `reconcile_gemini` maintains a persistent per-slug index file
   at `<archive_root_parent>/index.json` (mapping `slug -> most recent batch
   subdirectory`), so `verify_gemini` can resolve, for any requested slug,
   which batch's receipt to validate without the operator tracking
   timestamps by hand. For every slug under verification, confirm a receipt
   exists under the resolved batch directory containing: `slug`, `source
   digest` (sha256), `archive digest` (sha256), `final target kind`
   (`symlink` | `generated-wrapper`), and `canonical target`. A finding with
   `status="failed"` and a `detail` naming the slug is required when the
   receipt is absent or when any receipt field does not match the live
   filesystem state (e.g. the live symlink's resolved target no longer
   equals the receipt's `canonical target`).

Required tests (write first, in addition to the unreconciled-root test above):
- **missing receipt** — a slug whose live state is a correct symlink but whose
  archive root has no receipt file must fail verification.
- **mismatched receipt** — a slug whose receipt exists but whose recorded
  `canonical target` (or digest) does not match the live filesystem state must
  fail verification, with the slug named in the finding's `detail`.

**Fix 2 — narrow the OSError catch-all (Implementation Task T2, CRITICAL GAP).**
The symlink-fallback path in Task 2 Step 4 (exercised by Step 5's
`test_reconcile_falls_back_to_wrapper_when_symlink_fails`) must NOT catch
`OSError` generically. Catch only the specific errno values that indicate
"this platform/filesystem does not support symlinks" —
`errno.EPERM`, `errno.ENOSYS`, and `errno.EOPNOTSUPP` (check availability per
platform; not all three are defined everywhere) — and re-raise every other
`OSError` unchanged.

Required test: an `OSError` raised with an unrelated errno (e.g.
`errno.ENOSPC`, disk full) from `create_relative_link` must propagate out of
`reconcile_gemini` unmodified — it must NOT be caught and must NOT produce a
generated wrapper.

**Fix 3 — concurrency guard on `reconcile_gemini` (Implementation Task T8;
Eng verdict treats this as P-critical for this plan despite its P2 label in
the Implementation Tasks list below, because this plan's own execution model
— "fresh agent per task," see Execution Handoff — makes racing invocations of
`reconcile_gemini` over the same slug reachable, not theoretical).**
Add a lightweight sentinel lock (e.g. an `<archive_root>/.reconcile.lock`
file, held for the duration of one `reconcile_gemini` call and released on
exit including on error) plus a source-revalidation check immediately before
the archive-then-symlink commit.

Required test: an idempotence test that invokes `reconcile_gemini` twice in a
row over the same slug and asserts the second call is a no-op — it must not
raise, must not create a second archive copy, and must not leave a stale lock
artifact.

**Fix 3 — strengthened per synthesis P1-5 (2026-08-14 gate correction): atomic
acquisition + bounded, guarded recovery.** The lightweight sentinel lock
described above is superseded by the contract below — a check-then-create
sentinel still races (two processes can both observe "no lock" before either
creates one), and a bare `finally`-release does not run when the owning
process is killed (`kill -9`, OOM, host reboot), so the next fresh-agent task
in this plan's own "fresh agent per task" model can block permanently on a
lock nobody will ever release.

Required lock contract:
- **Atomic acquisition** — create the lock file with `os.open(path,
  O_CREAT | O_EXCL | O_WRONLY)` (or equivalent exclusive-create primitive),
  never check-then-create. `O_EXCL` fails atomically if the file already
  exists; treat that as "lock held," not a race to resolve with a retry loop
  that itself re-introduces the race.
- **Ownership payload** — on successful acquisition, write a minimal JSON
  payload into the lock file: owning PID, start timestamp (UTC), and the
  source directory's SHA-256 digest at acquisition time. This is what makes
  recovery *bounded* rather than guesswork.
- **Guarded stale-lock recovery, not automatic deletion.** A lock is only a
  *candidate* for stale-lock recovery when the recorded PID is no longer a
  live process on this host. Recovery must not delete-and-retry silently: it
  must be an explicit, logged, separately invoked operator action (e.g. a
  `--reconcile-gemini --force-unlock <slug>` flag or equivalent) that reports
  the stale payload (PID, start time, source SHA) before removing the lock.
  Automatic silent deletion of any lock file — live-owner or not — is exactly
  the failure mode this fix exists to close.
- **Release on the normal path** — release (delete) the lock file when
  `reconcile_gemini` completes successfully or raises a handled exception; a
  `finally` block covers in-process exceptions but, per the point above, is
  not relied on for the killed-process case.

Required tests (write first, in addition to the idempotence test above):
- **contention** — two sequential (or, if the test harness supports it,
  concurrent) `reconcile_gemini` invocations attempting to acquire the same
  slug's lock: the second acquisition attempt must fail cleanly (raise a
  named exception, not hang or corrupt state) while the first holds the lock.
- **terminated-owner recovery** — a lock file written with a PID that is not
  a live process on the host must be identified as stale by the guarded
  recovery path (not silently deleted by normal `reconcile_gemini` calls) and
  must require the explicit operator recovery action above to clear.
- **sequential idempotence** — retained from the original Fix 3: invoking
  `reconcile_gemini` twice in a row over the same slug is a no-op on the
  second call, does not create a second archive copy, and does not leave a
  stale lock artifact.

**Duplicate priority resolved:** this is the single P1 lock task for the
plan. Implementation Tasks T8 (below, in the appended `/autoplan` review)
originally carried a P2 label for the same requirement — it is retained
verbatim there for its rationale and evidence trail, but is now marked
**superseded-by Task 0 Fix 3** rather than treated as separate remaining
work. See Completed Review History for the cross-reference.

- [ ] **Step 1: Write the failing tests above** — expanded per the 2026-08-14
  gate corrections (P1-1, P1-2, P1-5) to seven tests; the original three names
  are retained below, plus four added by the strengthened Fix 1 and Fix 3:
  Gemini-verify-reports-failure-when-not-reconciled,
  Gemini-verify-fails-on-missing-receipt (P1-2, new),
  Gemini-verify-fails-on-mismatched-receipt (P1-2, new),
  OSError-with-unrelated-errno-propagates,
  lock-contention-fails-cleanly (P1-5, new),
  lock-terminated-owner-requires-guarded-recovery (P1-5, new),
  second-run-over-same-slug-is-a-no-op

- [ ] **Step 2: Run the tests to confirm failure**

Run: `pytest tests/test_install_thin_skill_wrappers.py -q`
Expected: FAIL — `verify_gemini` does not exist yet, the narrow errno check
does not exist yet, and there is no lock.

- [ ] **Step 3: Implement `verify_gemini` (strengthened signature — archive_root
  and receipt contract, per P1-1/P1-2), the narrow errno check, and the
  atomically-acquired, guarded-recovery sentinel lock (per P1-5)** exactly as
  specified above. These three interfaces are prerequisites for Task 2 (Step
  4's symlink-fallback and archive-stage-commit logic must use the narrow
  errno check and the lock from the start, not a bare `except OSError`) and
  for Task 7 (the `--verify` call must route Gemini slugs to `verify_gemini`).
  Later tasks build directly on these corrected interfaces rather than
  re-deriving equivalent logic.

- [ ] **Step 4: Verify and commit**

~~~bash
pytest tests/test_install_thin_skill_wrappers.py -q
git add bin/orama-system/skills/skillify/scripts/install_thin_skill_wrappers.py tests/test_install_thin_skill_wrappers.py
git commit -m "fix(skills): add Gemini-aware verify, narrow OSError catch, reconcile lock (P1 review fixes)"
~~~

### Task 1: Add A Read-Only Cross-Root Inventory

**Files:**
- Create: `docs/reference/gemini-skill-consolidation-inventory.md`
- Modify: `bin/orama-system/skills/skillify/scripts/install_thin_skill_wrappers.py`
- Modify: `tests/test_install_thin_skill_wrappers.py`

**Interfaces:**
- `SkillInventory(slug, root_id, entry_kind, sha256, frontmatter_keys)`
- `inventory_root(root_id: str, root: Path) -> list[SkillInventory]`
- `inventory_all_roots() -> list[SkillInventory]`
- `render_inventory(rows: list[SkillInventory], home: Path) -> str`

**Preconditions (P1-6, synthesis correction from the AntiGravity-Gemini
review — "Commit-Stat Review Before Replay"):** before Step 1 begins, the
implementer records:

~~~bash
git show --stat HEAD
git status --short --branch
~~~

and captures the resulting source SHA in the task's commit message or PR
evidence. Abort and escalate to the human operator instead of proceeding if
either command shows unexpected staged or unstaged edits (i.e. any change not
attributable to this plan's own prior committed tasks). This precondition
guards against replaying or building on top of an unreviewed, partially-dirty
branch state.

**Satisfied for the actual Task 1 run:** commit `da32cccb` — "feat(skills):
read-only Gemini inventory audit (Task 1)" — landed from a clean worktree on
top of base `c25b3dee`; 29 tests green. See Gate Status above.

- [ ] **Step 1: Write the failing inventory test**

~~~python
def test_render_inventory_is_sorted_and_portable(mod, tmp_path: Path) -> None:
    rows = [
        mod.SkillInventory("zeta", "gemini", "regular", "a" * 64, ("name",)),
        mod.SkillInventory("alpha", "agents", "symlink", "b" * 64, ("description", "name")),
    ]
    rendered = mod.render_inventory(rows, home=tmp_path)
    assert rendered.index("alpha") < rendered.index("zeta")
    assert str(tmp_path) not in rendered
    assert "agents" in rendered
~~~

- [ ] **Step 2: Run the test to prove the helper is absent**

Run: `pytest tests/test_install_thin_skill_wrappers.py -q`  
Expected: FAIL because the inventory interfaces do not exist.

- [ ] **Step 3: Implement `--audit-gemini`**

Use `hashlib.sha256` and conservative frontmatter parsing. Audit Gemini, Claude, Codex, shared-agent, and Antigravity roots without calling an install, archive, or symlink function.

~~~python
if args.audit_gemini:
    print(render_inventory(inventory_all_roots(), home=HOME))
    return 0
~~~

- [ ] **Step 4: Capture the baseline**

Create the inventory document from the audit. Include source tree SHA, logical root labels, entry kind, digest, frontmatter keys, and the Disposition Matrix. Do not include a home directory.

- [ ] **Step 5: Verify and commit**

~~~bash
pytest tests/test_install_thin_skill_wrappers.py -q
python3 bin/orama-system/skills/skillify/scripts/install_thin_skill_wrappers.py --audit-gemini
python3 scripts/review/check_orama_skills.py --mode strict .
git add bin/orama-system/skills/skillify/scripts/install_thin_skill_wrappers.py tests/test_install_thin_skill_wrappers.py docs/reference/gemini-skill-consolidation-inventory.md
git commit -m "feat(skills): add read-only Gemini inventory audit"
~~~

### Task 2: Add Manifest-Gated Archive-First Reconciliation

**Files:**
- Create: `bin/orama-system/skills/skillify/references/gemini-skill-ownership.json`
- Modify: `bin/orama-system/skills/skillify/scripts/install_thin_skill_wrappers.py`
- Modify: `tests/test_install_thin_skill_wrappers.py`

**Interfaces:**
- `GeminiOwnership(slug, owner, action, canonical_slug, canonical_path, metadata_policy)`
- `load_gemini_ownership(path: Path) -> dict[str, GeminiOwnership]`
- `ownership_for(slug: str) -> GeminiOwnership`
- `reconcile_gemini(root: Path, archive_root: Path, only: set[str]) -> list[Path]`
- `validate_reconciliation_request(only: set[str]) -> None`
- `create_relative_link(target: Path, source: Path) -> None`

- [ ] **Step 1: Write archive-first and external-owner failure tests**

~~~python
def test_reconcile_archives_before_replacing_regular_skill(mod, tmp_path: Path) -> None:
    root, archive = tmp_path / "gemini", tmp_path / "archive"
    old = root / "code-review" / "SKILL.md"
    old.parent.mkdir(parents=True)
    old.write_text("old Gemini body\\n", encoding="utf-8")

    changed = mod.reconcile_gemini(root, archive, {"code-review"})

    assert (archive / "code-review" / "SKILL.md").read_text(encoding="utf-8") == "old Gemini body\\n"
    assert root / "code-review" in changed
    assert (root / "code-review").is_symlink()

def test_reconcile_refuses_gstack_owned_skill(mod, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="preserve-external"):
        mod.reconcile_gemini(tmp_path / "gemini", tmp_path / "archive", {"skillify"})
~~~

- [ ] **Step 2: Run the tests to confirm failure**

Run: `pytest tests/test_install_thin_skill_wrappers.py -q`  
Expected: FAIL because reconciliation interfaces do not exist.

- [ ] **Step 3: Create the ownership manifest**

Every record contains `owner`, `action`, `canonical_slug`, `canonical_path`, and `metadata_policy`. Only `link`, `adapter`, and `preserve-external` are allowed actions.

~~~json
{
  "schema_version": 1,
  "skills": {
    "code-review": {
      "owner": "orama",
      "action": "link",
      "canonical_slug": "code-review",
      "canonical_path": "bin/orama-system/skills/code-review/SKILL.md",
      "metadata_policy": "none"
    },
    "skillify": {
      "owner": "gstack",
      "action": "preserve-external",
      "canonical_slug": "skillify",
      "canonical_path": "",
      "metadata_policy": "external"
    }
  }
}
~~~

**`metadata_policy` enum (complete set — Implementation Task T4).** Every
`GeminiOwnership` record's `metadata_policy` must be one of exactly these
three values; no other value is permitted:

| Value | Meaning | Applies to (action) | Example |
| --- | --- | --- | --- |
| `none` | No Gemini frontmatter is preserved — the slug becomes a plain symlink to the canonical `SKILL.md`, so there is nothing Gemini-specific left to validate. | `link` | `code-review`, `git-history-surgery`, `orama-afrp` |
| `validated` | The adapter keeps only frontmatter keys that were checked against current official Gemini CLI documentation at implementation time; any other key found in the source card is an `unsupported frontmatter` error (Task 2 Step 5) and blocks reconciliation for that slug. | `adapter` | `agent-methodology` retains `user-invocable: false` only after that key is confirmed current; `orama-gstack`, `orama-system`, `oramasys-method`, and the Perpetua cross-repo adapters (Task 4) all use `validated` |
| `external` | Orama does not read, validate, or manage the slug's frontmatter at all — ownership and metadata both belong to the external project. | `preserve-external` | `skillify`, `gstack-upgrade` |

Populate the remaining records from the Disposition Matrix, giving every
`link` row `metadata_policy: "none"`, every `adapter` row (including the four
Perpetua cross-repo adapters in Task 4) `metadata_policy: "validated"`, and
every `preserve-external` row `metadata_policy: "external"`. Do not include
absolute paths.

- [ ] **Step 4: Implement safe reconciliation**

For each requested slug: reject unknown, unapproved, and external records; copy the complete existing directory into `archive_root/<slug>`; compare source/archive digest; create a relative link for `link`; generate a minimal adapter for `adapter`; return changed paths. If symlink creation fails, write a generated thin wrapper and report the fallback.

**Strengthened per synthesis P1-4 (2026-08-14 gate correction) — archive-first
must not leave the live skill missing or partial.** The sequence above, read
literally ("copy... compare... create a relative link... generate a minimal
adapter"), archives the source and then removes/replaces the foreign-root
directory in place. If both link creation and generated-wrapper creation fail
*after* the source directory has already been cleared, the archive exists but
`~/.gemini/skills/<slug>` is left missing or partial — a regression versus the
Gemini-owned skill's state before this plan ran. Narrowing the `OSError` catch
(Fix 2 above) does not by itself restore a source that was already removed.

Corrected sequence (stage-validate-commit, not archive-then-mutate-in-place):

1. Archive the complete existing directory into `archive_root/<slug>` and
   verify the archive digest matches the source digest (as today).
2. **Stage** the replacement (symlink or generated adapter/wrapper) at a
   temporary path alongside the live directory — do not touch
   `~/.gemini/skills/<slug>` yet.
3. **Validate** the staged replacement (symlink resolves, or generated
   adapter file is well-formed and non-empty).
4. **Commit atomically** — where the filesystem supports it, `os.rename()`
   the validated staged replacement over the live path (POSIX rename is
   atomic within the same filesystem). Only after the commit succeeds is the
   original live directory considered replaced.
5. **On any staging or validation failure**, the live directory must still be
   the original, untouched source — nothing has been removed yet, because
   step 2 staged beside it rather than clearing it first. If a filesystem
   constraint ever forces clearing the source before staging (e.g. a
   filesystem that cannot hold both paths at once), the implementer MUST
   restore the archived copy back to the live path before raising, so the
   failure surfaces with the Gemini skill still usable, never missing.

**Receipt contract (P1-2).** On a successful commit, write a receipt file
under `archive_root/<slug>/` (e.g. `archive_root/<slug>/.receipt.json`)
containing: `slug`, `source_digest` (sha256, pre-archive), `archive_digest`
(sha256, post-copy), `final_target_kind` (`"symlink"` or
`"generated-wrapper"`), and `canonical_target` (the resolved path or adapter
target). `reconcile_gemini` also creates or updates a persistent index file
one level above the per-batch timestamped directory
(`<archive_root>/../index.json`), mapping `slug -> this batch's archive_root`
and overwriting only that slug's entry so other slugs' historical batch
entries are preserved. `verify_gemini` (Task 0, Fix 1, strengthened) reads
this index and receipt to prove recoverability, not just inspect the final
symlink shape.

Required test (P1-4, write first): force replacement creation (both symlink
and generated-wrapper paths) to fail after a successful archive; assert the
original live directory at `~/.gemini/skills/<slug>` still exists and is
usable (not partially removed, not empty) after `reconcile_gemini` raises.

- [ ] **Step 5: Add collision and metadata regression tests**

~~~python
def test_reconcile_never_replaces_gstack_upgrade(mod, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="preserve-external"):
        mod.reconcile_gemini(tmp_path / "gemini", tmp_path / "archive", {"gstack-upgrade"})

def test_reconcile_rejects_unknown_frontmatter_key_for_adapter(mod, tmp_path: Path) -> None:
    root = tmp_path / "gemini"
    skill = root / "orama-system" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\\nname: orama-system\\nunsupported: true\\n---\\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported frontmatter"):
        mod.reconcile_gemini(root, tmp_path / "archive", {"orama-system"})

def test_reconcile_falls_back_to_wrapper_when_symlink_fails(mod, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(mod, "create_relative_link", lambda target, source: (_ for _ in ()).throw(OSError("links disabled")))
    changed = mod.reconcile_gemini(tmp_path / "gemini", tmp_path / "archive", {"code-review"})
    assert changed == [tmp_path / "gemini" / "code-review"]
    assert (tmp_path / "gemini" / "code-review" / "SKILL.md").is_file()
~~~
~~~

- [ ] **Step 6: Verify and commit**

~~~bash
pytest tests/test_install_thin_skill_wrappers.py -q
python3 bin/orama-system/skills/skillify/scripts/install_thin_skill_wrappers.py --audit-gemini
git add bin/orama-system/skills/skillify/references/gemini-skill-ownership.json bin/orama-system/skills/skillify/scripts/install_thin_skill_wrappers.py tests/test_install_thin_skill_wrappers.py
git commit -m "feat(skills): add safe Gemini reconciliation manifest"
~~~

### Task 3: Consolidate The Seven Orama-Owned Cards

**Files:**
- Modify: `bin/orama-system/skills/skillify/references/gemini-skill-ownership.json`
- Modify: `bin/orama-system/skills/skillify/scripts/install_thin_skill_wrappers.py`
- Modify: `tests/test_install_thin_skill_wrappers.py`
- Modify: `docs/reference/gemini-skill-consolidation-inventory.md`

**Mapping:**

~~~text
link:    code-review, git-history-surgery, orama-afrp
adapter: agent-methodology, orama-gstack, orama-system, oramasys-method
~~~

**Additional interface:** `gemini_adapter(ownership: GeminiOwnership) -> str`

- [ ] **Step 1: Write target-specific failing tests**

~~~python
def test_orama_gstack_adapter_targets_gstack_gbrain(mod) -> None:
    text = mod.gemini_adapter(mod.ownership_for("orama-gstack"))
    assert "bin/orama-system/gstack-gbrain/SKILL.md" in text
    assert "bin/orama-system/gstack/SKILL.md" not in text

def test_code_review_reconciliation_drops_glm_fallback(mod, tmp_path: Path) -> None:
    changed = mod.reconcile_gemini(tmp_path / "gemini", tmp_path / "archive", {"code-review"})
    assert all("GLM-5.2 Fallback" not in p.read_text(encoding="utf-8") for p in changed if p.is_file())
~~~

- [ ] **Step 2: Verify failure, then implement adapters**

Run: `pytest tests/test_install_thin_skill_wrappers.py -q`  
Expected: FAIL until `gemini_adapter` and the canonical `gstack-gbrain` target exist.

Verify current official Gemini frontmatter before retaining `user-invocable: false` for `agent-methodology`. Adapters may keep validated discovery metadata but cannot retain full behavior, local GLM fallbacks, absolute paths, or Claude-only tool declarations.

- [ ] **Step 3: Reconcile the explicit Orama set**

~~~bash
python3 bin/orama-system/skills/skillify/scripts/install_thin_skill_wrappers.py \
  --reconcile-gemini \
  --only agent-methodology,code-review,git-history-surgery,orama-afrp,orama-gstack,orama-system,oramasys-method \
  --archive-root "$HOME/.gemini/skills-archive/$(date -u +%Y%m%dT%H%M%SZ)"
~~~

- [ ] **Step 4: Regenerate the inventory doc (Implementation Task T5)**

Re-run the audit and update `docs/reference/gemini-skill-consolidation-inventory.md`'s
"Latest audit snapshot" section with the fresh `--audit-gemini` output —
replace the previous snapshot but keep the Disposition Matrix and narrative
context above it (Task 1 Step 4) intact. Do not skip this step; it is what
keeps the inventory doc from silently going stale after each reconciliation
batch.

- [ ] **Step 5: Verify and commit**

~~~bash
pytest tests/test_install_thin_skill_wrappers.py -q
python3 bin/orama-system/skills/skillify/scripts/install_thin_skill_wrappers.py --audit-gemini
python3 scripts/review/check_orama_skills.py --mode strict .
python3 scripts/review/repo_hygiene.py .
git diff --check
git add bin/orama-system/skills/skillify/references/gemini-skill-ownership.json bin/orama-system/skills/skillify/scripts/install_thin_skill_wrappers.py tests/test_install_thin_skill_wrappers.py docs/reference/gemini-skill-consolidation-inventory.md
git commit -m "feat(skills): consolidate Gemini Orama skill adapters"
~~~

### Task 4: Make Perpetua Global Adapters Portable

**Files:**
- Modify: `bin/orama-system/skills/skillify/scripts/install_thin_skill_wrappers.py`
- Modify: `bin/orama-system/skills/skillify/references/gemini-skill-ownership.json`
- Modify: `tests/test_install_thin_skill_wrappers.py`

**Interface:** `cross_repo_wrapper(ownership: GeminiOwnership) -> str`

- [ ] **Step 1: Write failing resolver tests**

~~~python
def test_perpetua_wrapper_uses_environment_root_not_caller_repo(mod) -> None:
    text = mod.cross_repo_wrapper(mod.ownership_for("perpetua-config"))
    assert '"$PERPETUA_TOOLS_PATH/config/SKILL.md"' in text
    assert "git rev-parse --show-toplevel" not in text

def test_perpetua_wrapper_explains_missing_root(mod) -> None:
    assert "PERPETUA_TOOLS_PATH is not set" in mod.cross_repo_wrapper(mod.ownership_for("perpetua-tools"))
~~~

- [ ] **Step 2: Implement and reconcile**

The adapter validates `PERPETUA_TOOLS_PATH` and the expected repository-relative skill file, then stops with a clear remediation when either is absent. It never searches arbitrary parents or assumes a sibling directory name.

~~~bash
python3 bin/orama-system/skills/skillify/scripts/install_thin_skill_wrappers.py \
  --reconcile-gemini \
  --only perpetua-tools,perpetua-config,perpetua-hardware,perpetua-startup-intelligence \
  --archive-root "$HOME/.gemini/skills-archive/$(date -u +%Y%m%dT%H%M%SZ)"
~~~

- [ ] **Step 3: Regenerate the inventory doc (Implementation Task T5)**

Re-run the audit and update `docs/reference/gemini-skill-consolidation-inventory.md`'s
"Latest audit snapshot" section with the fresh `--audit-gemini` output,
keeping the Disposition Matrix and narrative context above it intact.

- [ ] **Step 4: Verify and commit**

~~~bash
pytest tests/test_install_thin_skill_wrappers.py -q
python3 bin/orama-system/skills/skillify/scripts/install_thin_skill_wrappers.py --audit-gemini
python3 scripts/review/check_orama_skills.py --mode strict .
python3 scripts/review/repo_hygiene.py .
git diff --check
git add bin/orama-system/skills/skillify/scripts/install_thin_skill_wrappers.py bin/orama-system/skills/skillify/references/gemini-skill-ownership.json tests/test_install_thin_skill_wrappers.py docs/reference/gemini-skill-consolidation-inventory.md
git commit -m "fix(skills): make global Perpetua wrappers portable"
~~~

### Task 5: Verify Antigravity And Preserve gstack Namespace Ownership

**Files:**
- Modify: `bin/orama-system/skills/skillify/scripts/install_thin_skill_wrappers.py`
- Modify: `tests/test_install_thin_skill_wrappers.py`
- Modify: `bin/orama-system/skills/skillify/references/codex-thin-wrapper-installs.md`

**Interfaces:**
- `RootFinding(status: str, detail: str)`
- `verify_antigravity_root(shared_agents_root: Path, antigravity_root: Path) -> RootFinding`

- [ ] **Step 1: Write failing protection tests**

~~~python
def test_audit_reports_antigravity_shared_root(mod, tmp_path: Path) -> None:
    agents, antigravity = tmp_path / "agents", tmp_path / "antigravity"
    agents.mkdir()
    antigravity.symlink_to(agents, target_is_directory=True)
    assert mod.verify_antigravity_root(agents, antigravity).status == "shared-root"

def test_manifest_rejects_skillify_collision(mod) -> None:
    with pytest.raises(ValueError, match="external owner"):
        mod.validate_reconciliation_request({"skillify"})
~~~

- [ ] **Step 2: Implement checks and update operator guidance**

The root check returns `shared-root`, `missing`, or `divergent`; only `shared-root` passes. Document: run manifest audit first, retain gstack `skillify`, invoke Orama creator as `oramasys-skillify`, and never bulk-install the Orama manifest into a gstack-populated root.

- [ ] **Step 3: Verify and commit**

~~~bash
pytest tests/test_install_thin_skill_wrappers.py -q
python3 bin/orama-system/skills/skillify/scripts/install_thin_skill_wrappers.py --audit-gemini
python3 scripts/review/check_orama_skills.py --mode strict .
git add bin/orama-system/skills/skillify/scripts/install_thin_skill_wrappers.py tests/test_install_thin_skill_wrappers.py bin/orama-system/skills/skillify/references/codex-thin-wrapper-installs.md
git commit -m "test(skills): guard Gemini gstack namespace collisions"
~~~

### Task 6: Review Gemini-Only Candidates Without Mutating Them

**Files:**
- Create: `docs/reference/gemini-only-skill-comparison.md`
- Modify: `docs/reference/gemini-skill-consolidation-inventory.md`
- Modify: `tests/test_install_thin_skill_wrappers.py`

- [ ] **Step 1: Capture evidence**

For each candidate, record digest, availability and entry type in Gemini/Claude/Codex/shared-agent roots, frontmatter keys, executable dependencies, declared upstream owner, closest Orama capability, and collision risk.

~~~text
autoplan
autoresearch
codex
deep-research
diagram
kimi-webbridge
oramasys-skillify
setup-gbrain
sync-gbrain
~~~

- [ ] **Step 2: Apply the ownership rubric**

For every candidate answer:

~~~text
1. Is current behavior already owned by an Orama or Perpetua card?
2. Is it owned by an upstream project, CLI, or vendor?
3. Is its remaining delta portable across Claude, Codex, and Gemini?
4. Does its slug collide with a global or upstream namespace?
5. Can its proposed end state pass frontmatter and hygiene validation?
~~~

Validate Gemini schema fields against current official documentation. Compare `autoplan`, `diagram`, `setup-gbrain`, and `sync-gbrain` with gstack; `autoresearch` with experiment guidance; `codex` with `codex-mcp-debugging` and `codex-openclaw-agent`; `deep-research` with verified EXA/Firecrawl guidance; `kimi-webbridge` with its upstream owner; and `oramasys-skillify` with the canonical skillify package and collision policy.

- [ ] **Step 3: Block candidate reconciliation**

~~~python
def test_gemini_only_candidates_are_not_reconcilable_without_approval(mod) -> None:
    candidates = {"autoplan", "autoresearch", "codex", "deep-research", "diagram", "kimi-webbridge", "oramasys-skillify", "setup-gbrain", "sync-gbrain"}
    for slug in candidates:
        with pytest.raises(ValueError, match="not approved"):
            mod.validate_reconciliation_request({slug})
~~~

- [ ] **Step 4: Regenerate the inventory doc (Implementation Task T5)**

Re-run `--audit-gemini` and update `docs/reference/gemini-skill-consolidation-inventory.md`'s
"Latest audit snapshot" section with the fresh output, keeping the
Disposition Matrix and narrative context above it intact.

- [ ] **Step 5: Verify and commit the analysis-only batch**

~~~bash
pytest tests/test_install_thin_skill_wrappers.py -q
python3 bin/orama-system/skills/skillify/scripts/install_thin_skill_wrappers.py --audit-gemini
python3 scripts/review/check_orama_skills.py --mode strict .
python3 scripts/review/repo_hygiene.py .
git diff --check
git add docs/reference/gemini-only-skill-comparison.md docs/reference/gemini-skill-consolidation-inventory.md tests/test_install_thin_skill_wrappers.py
git commit -m "docs(skills): classify Gemini-only integration candidates"
~~~

### Task 7: Final Verification And Handoff

**Files:**
- Modify: `docs/reference/gemini-skill-consolidation-inventory.md`
- Modify: `docs/reference/gemini-only-skill-comparison.md`

- [ ] **Step 1: Run the full gate**

~~~bash
pytest tests/test_install_thin_skill_wrappers.py -q
python3 bin/orama-system/skills/skillify/scripts/install_thin_skill_wrappers.py --audit-gemini
python3 bin/orama-system/skills/skillify/scripts/install_thin_skill_wrappers.py --verify --only agent-methodology,code-review,git-history-surgery,orama-afrp,orama-gstack,orama-system,oramasys-method,perpetua-tools,perpetua-config,perpetua-hardware,perpetua-startup-intelligence
python3 scripts/review/check_orama_skills.py --mode strict .
python3 scripts/review/repo_hygiene.py .
git diff --check
git status --short
~~~

Expected: all tests pass; Antigravity is `shared-root`; `skillify` and `gstack-upgrade` remain `preserve-external`; candidates are `not changed by this plan`.

- [ ] **Step 2: Record final evidence**

Add this table to both reference documents:

~~~text
slug | previous digest | archive digest | owner | canonical target | final state | verification | result
~~~

- [ ] **Step 3: Commit the verification record**

~~~bash
git add docs/reference/gemini-skill-consolidation-inventory.md docs/reference/gemini-only-skill-comparison.md
git commit -m "docs(skills): record Gemini consolidation verification"
~~~

## Self-Review

| Requirement | Plan coverage |
| --- | --- |
| Gemini-aware verify, narrow OSError catch, reconcile lock (P1 review CRITICAL GAPs T1/T2/T8) | Task 0 |
| Reconcile thirteen divergent cards without destructive overwrite | Tasks 2 through 5 |
| Promote behavior only into its true owner | Disposition Matrix, Tasks 3 and 4 |
| Preserve gstack collision boundary | Task 5 |
| Compare nine candidates across Gemini, Claude, Codex, and Orama | Task 6 |
| Preserve valid metadata and portable tracked content | Global Constraints, Tasks 1 and 2 |
| Validate with focused tests and hygiene gates | Every task and Task 7 |

No task bulk-replaces a global root or changes a Gemini-only candidate.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-14-gemini-skill-consolidation.md`.

1. **Subagent-Driven (recommended):** fresh agent per task with review before each reconciliation batch.
2. **Inline Execution:** checkpoints after Tasks 2, 4, and 6.

---

## AUTOPLAN REVIEW — CEO / ENG / DX (Design phase skipped: no UI scope)

Run 2026-08-14 via `/autoplan` (single-agent stand-in: CODEX SAYS = actual `codex exec`
adversarial pass; CLAUDE INDEPENDENT VOICE = second, independent read of this file,
ignoring the first pass, per the autoplan skill's dual-voice requirement under the
single-agent constraint — see task preamble). Mode: **HOLD SCOPE** (this is
infra/tooling hygiene extending an existing script, not a greenfield feature —
matches the CEO skill's own default for "refactor" and "enhancement of existing
system"; Mechanical decision, no genuine ambiguity).

### What Already Exists

- `bin/orama-system/skills/skillify/scripts/install_thin_skill_wrappers.py` (490
  lines) already exists and already runs a thin-wrapper-publishing pipeline
  (`--install`/`--verify`/`--dry-run`/`--only`) targeting **five roots**:
  `~/.codex/skills`, `~/.agents/skills`, `.agents/skills`,
  `orama-system/.agents/skills`, `perplexity-api/Perpetua-Tools/.agents/skills`.
  Grepped this file and `tests/test_install_thin_skill_wrappers.py` (19 existing
  tests, all scoped to `workspace_candidates`/`repo_relative`/`wrapper` rendering)
  and `bin/orama-system/skills/skillify/references/codex-thin-wrapper-installs.md`
  for the string "gemini" (case-insensitive): **zero hits in all three files.**
  Confirms the task brief's framing — Task 1 genuinely modifies an existing file,
  but the Gemini-specific surface (`SkillInventory`, `GeminiOwnership`,
  `reconcile_gemini`, `verify_antigravity_root`, the whole manifest) is 100%
  net-new. There is no partial Gemini-reconciliation code to reuse.
- The file's own top-of-file comment (lines 90–100) documents a **real prior
  incident**: a 2026-07-22 change added `~/.claude/skills` as a target root and
  silently overwrote gstack's own `skillify` card — recovered from gstack's
  source copy. This is direct, in-repo evidence for why the plan's "manifest-gated,
  never overwrite gstack `skillify`/`gstack-upgrade`" constraint is not
  over-engineering — it is a documented recurrence-prevention measure for an
  incident that already happened once in this exact file's blast radius.
- GossipBus context (relayed by the task, not independently visible to this
  agent) reports a *separate*, narrower piece of work completed earlier the same
  day: "Antigravity native global skills resolving through one canonical shared
  skill tree, 121 SKILL.md files validated." **This maps at most to Task 5's
  `verify_antigravity_root` check and does not cover Tasks 1–4, 6–7** (manifest,
  inventory, reconciliation engine, candidate classification) — confirmed by
  grep above: none of that machinery exists on disk. Ground-truth check on this
  actual machine found **no evidence to corroborate the Antigravity-shared-root
  claim either**: `~/.gemini/antigravity`, `~/.antigravity`, `~/.antigravity-ide`,
  and `~/.antigravitycli` are all private Antigravity IDE state directories (chat
  history, MCP config, installation ID) — none is a symlink to a shared skills
  root, and none contains a `skills/` tree at all. `~/.gemini/skills/` itself is a
  mix of real directories and symlinks pointing at `.agents/skills/...`, unrelated
  to Antigravity. **Recommendation: do not assume Task 5's audit will report
  `shared-root` on first run** — the state it's meant to detect may not exist yet
  on a given machine, and CODEX independently confirms below that
  `verify_antigravity_root` is *not* redundant work (see Eng Pass 1).
- Codex independently confirmed (Pass 1, read-only inspection of the same file):
  "there is no Antigravity handling today, and `TARGET_ROOTS` has no Antigravity
  root" — cross-model agreement that Task 5 is required, net-new work, not a
  rerun of already-completed work.

### NOT in Scope

- Disposition for the 9 Gemini-only candidates (`autoplan`, `autoresearch`,
  `codex`, `deep-research`, `diagram`, `kimi-webbridge`, `oramasys-skillify`,
  `setup-gbrain`, `sync-gbrain`) — Task 6 is explicitly analysis-only per the
  plan's own Global Constraints; a disposition decision needs a separate,
  later approved plan. Correctly deferred, not silently dropped.
- A generic multi-root drift-monitoring system (Codex Pass 1: "A permanent
  five-root inventory plus generic reconciliation engine is disproportionate
  unless recurring drift is established"). This review does not fold that
  expansion in — see Decision Audit Trail D1 below for the taste call on
  right-sizing Task 1's inventory scope instead of building a permanent monitor.
- CI/CD or scheduled-drift-detection wiring for the new inventory audit. Nothing
  in the plan proposes running `--audit-gemini` on a cadence; this review does
  not add that scope either (no stated recurring-drift problem to justify it —
  Principle 6, bias to action, argues against inventing infrastructure nobody
  asked for).
- Migrating `~/.claude/skills` (the Claude root) into this reconciliation
  system. The plan is explicitly scoped to `~/.gemini/skills`; the Claude root's
  own protection (the July 2026 incident) is already handled by
  `TARGET_ROOTS` deliberately excluding it (see the file's own comment). Out of
  scope by design, not an oversight.

### Dream State Delta

```
CURRENT STATE                         THIS PLAN                              12-MONTH IDEAL
13 Gemini skill cards drift           7 tasks: audit -> manifest ->          One shared skill source
independently of their Orama/         reconcile 11 slugs -> verify           of truth per canonical
Perpetua/gstack canonical             Antigravity shared-root -> classify    owner, symlinked/adapted
sources; 0% reconciled; no            9 analysis-only candidates             into every AI CLI root
audit trail; the file that            ------------------------------->      (Claude/Codex/Gemini/
would do this reconciliation                                                Antigravity/future CLIs),
does not yet contain any                                                    each with a manifest-
Gemini-aware code at all.                                                   gated, archive-first,
                                                                             auditable reconciliation
                                                                             path — no more silent
                                                                             overwrites (root cause
                                                                             of the 2026-07-22
                                                                             gstack-skillify incident).
```

This plan moves cleanly toward the ideal: it generalizes the exact pattern
(manifest-gated, archive-first) that already protects the Codex/Agents roots
from repeating the July incident, and applies it to the one remaining
unprotected root (Gemini). It does not solve the "N roots, N reconciliation
engines" duplication Codex flags in Eng Pass 2 (T1/T5 root-discovery overlap) —
that's the honest gap between this plan and the ideal, tracked in the
Decision Audit Trail and Implementation Tasks below.

### System Architecture Diagram

```
                         install_thin_skill_wrappers.py  (490 lines today)
                         ================================================
                         EXISTING RESPONSIBILITY (unchanged by this plan)
                         ┌──────────────────────────────────────────────┐
                         │  CANONICAL_SKILLS (Orama/Perpetua sources)    │
                         │        │                                     │
                         │        ▼                                     │
                         │   build_specs() ── wrapper() ── install()    │
                         │        │                                     │
                         │        ▼                                     │
                         │   TARGET_ROOTS (OUTBOUND, this repo's own    │
                         │   content published OUT):                   │
                         │     ~/.codex/skills                          │
                         │     ~/.agents/skills                         │
                         │     .agents/skills                           │
                         │     orama-system/.agents/skills              │
                         │     perplexity-api/.../.agents/skills        │
                         └──────────────────────────────────────────────┘

                         NEW RESPONSIBILITY (Tasks 1-6, this plan)
                         ┌──────────────────────────────────────────────┐
                         │  gemini-skill-ownership.json (NEW manifest)   │
                         │        │                                     │
                         │        ▼                                     │
                         │  load_gemini_ownership() -> ownership_for()  │
                         │        │                                     │
                         │        ▼                                     │
                         │  validate_reconciliation_request()           │
                         │   ├─ unknown slug ────────► reject           │
                         │   ├─ preserve-external ────► reject          │
                         │   └─ not-approved candidate ► reject         │
                         │        │ (approved: link | adapter)          │
                         │        ▼                                     │
                         │  reconcile_gemini(root, archive_root, only)  │
                         │   1. archive existing dir (SHA-256 compare)  │
                         │   2. create_relative_link() ──fails──┐       │
                         │        │ succeeds                    ▼       │
                         │        ▼                        write thin   │
                         │   symlink in place              wrapper      │
                         │                                  (fallback)  │
                         │        │                                     │
                         │        ▼                                     │
                         │  INBOUND target: ~/.gemini/skills/<slug>     │
                         │  (a FOREIGN root this repo does NOT own      │
                         │   the content of — the opposite direction    │
                         │   from every existing TARGET_ROOTS write)    │
                         └──────────────────────────────────────────────┘

                         ORTHOGONAL: verify_antigravity_root()
                         ┌──────────────────────────────────────────────┐
                         │  compares ~/.gemini/antigravity (or wherever │
                         │  Antigravity resolves) against the shared    │
                         │  agents root -> shared-root | missing |      │
                         │  divergent. Read-only. No writes.            │
                         └──────────────────────────────────────────────┘
```

**Coupling finding (Eng Pass, both voices independently flagged this):** the new
Gemini-reconciliation responsibility writes INTO a foreign root
(`~/.gemini/skills`), while every existing responsibility in this file writes
OUT of this repo's own canonical sources. That is a fundamentally different
risk class (Codex Pass 1: "The existing installer destructively cleans target
directories and rewrites canonical docs; that is a materially different risk
model") sharing one file, one CLI arg-parser, and — critically — one `verify()`
function that was written for the outbound case only (see Error & Rescue
Registry, `verify()` row, CRITICAL GAP).

### Error & Rescue Registry

```
METHOD/CODEPATH                    | WHAT CAN GO WRONG                        | EXCEPTION CLASS
------------------------------------|-------------------------------------------|---------------------------
load_gemini_ownership(path)        | manifest file missing                    | FileNotFoundError
                                    | manifest is malformed JSON                | json.JSONDecodeError
                                    | manifest has unknown schema_version       | (unnamed — no version gate specified)
ownership_for(slug)                | slug not in manifest                     | KeyError / (unnamed — plan doesn't specify)
reconcile_gemini(root, archive, only)| slug is preserve-external              | ValueError("preserve-external")
                                    | source dir mutated between archive+link  | (unnamed — TOCTOU, no test)
                                    | archive_root/<slug> already exists       | (unnamed — no test, no defined behavior)
                                    | second invocation on same slug (racing)  | (unnamed — no lock, no test)
                                    | frontmatter has unsupported key           | ValueError("unsupported frontmatter")
                                    | filesystem doesn't support symlinks       | OSError (caught, falls back to wrapper)
                                    | filesystem raises OSError for OTHER reason| OSError (same catch — CRITICAL GAP, see below)
                                    | interrupted mid-write (crash/kill -9)     | (unnamed — no journal, no recovery test)
verify_antigravity_root(a, b)      | neither path exists                      | RootFinding(status="missing")
                                    | paths exist but resolve differently      | RootFinding(status="divergent")
                                    | paths exist and match                    | RootFinding(status="shared-root")
                                    | ONLY the shared-root case has a test     | (Task 5 Step 1 tests one of three states)
existing verify() (line 399-451)   | called against post-reconciliation state | returns FALSE PASS — see below

EXCEPTION CLASS                        | RESCUED? | RESCUE ACTION                          | USER SEES
----------------------------------------|----------|-----------------------------------------|------------------
ValueError("preserve-external")        | Y        | pytest.raises in tests; CLI: unhandled  | raw traceback, no remediation text ← GAP (DX)
ValueError("not approved")             | Y        | same as above                           | raw traceback, no remediation text ← GAP (DX)
ValueError("unsupported frontmatter")  | Y        | reconciliation aborts for that slug     | raw traceback, doesn't list which key ← GAP (DX)
OSError (symlink-unsupported)          | Y        | falls back to generated thin wrapper    | silent success — but see below
OSError (permission denied / disk full)| N ← GAP  | same catch as above — WRONG              | silent "fallback succeeded" when it actually masked a real failure ← CRITICAL GAP
FileNotFoundError (manifest missing)   | N ← GAP  | —                                        | raw traceback ← GAP
json.JSONDecodeError (manifest corrupt)| N ← GAP  | —                                        | raw traceback, no line/col context surfaced ← GAP
```

**CRITICAL GAP — `verify()` silently validates the wrong thing after Gemini
reconciliation runs.** Both CODEX and the independent Claude pass found this
identically without seeing each other's output (cross-model consensus, high
confidence). `verify()` (existing function, `install_thin_skill_wrappers.py:399`)
iterates `TARGET_ROOTS` — which is Codex/Agents/etc., **not** the Gemini root —
and asserts each target directory contains only `SKILL.md` plus the literal
strings `"git fetch origin --prune"` and `"git pull --ff-only"`. Task 7 Step 1
runs `... --verify --only agent-methodology,code-review,...` expecting it to
confirm "Antigravity is shared-root; skillify and gstack-upgrade remain
preserve-external; candidates are not changed by this plan" — **none of that is
what `verify()` actually checks.** As written, Task 7 will print
`"verification passed"` regardless of whether the Gemini reconciliation
succeeded, partially succeeded, or did nothing at all. This is the single
highest-value fix in this review (Implementation Task T1 below).

### Test Diagram (Section 6 — maps every new codepath to its test)

```
NEW CODEPATHS INTRODUCED (Tasks 1-6):
  SkillInventory / inventory_root / inventory_all_roots / render_inventory
  GeminiOwnership / load_gemini_ownership / ownership_for
  reconcile_gemini / validate_reconciliation_request / create_relative_link
  gemini_adapter / cross_repo_wrapper
  RootFinding / verify_antigravity_root
  (MISSING, not in any task's interface list) a Gemini-aware verify path

NEW DATA FLOWS:
  manifest JSON -> ownership_for() -> reconcile_gemini() -> filesystem mutation
  Gemini root scan -> inventory_root() -> render_inventory() -> markdown doc
  PERPETUA_TOOLS_PATH env var -> cross_repo_wrapper() -> written SKILL.md text

NEW ERROR/RESCUE PATHS: (see Error & Rescue Registry above — 5 unnamed/unrescued rows)

CODEPATH                          | TYPE            | TEST IN PLAN?          | HAPPY PATH | FAILURE PATH        | EDGE CASE
------------------------------------|-----------------|--------------------------|------------|----------------------|------------------------------
render_inventory (sort+portability) | Unit            | YES (Task 1 Step 1)     | YES        | NO                   | NO (home-leak tested; ROOT-leak not tested)
--audit-gemini CLI wiring           | Integration     | NO explicit test        | manual run only (Task 1 Step 5) | NO | NO
reconcile_gemini (archive+symlink)  | Unit            | YES (Task 2 Step 1)     | YES        | NO                   | NO
reconcile_gemini (external-owner)   | Unit            | YES (Task 2 Step 1)     | n/a        | YES                  | n/a
reconcile_gemini (unsupported FM)   | Unit            | YES (Task 2 Step 5)     | n/a        | YES                  | n/a
reconcile_gemini (symlink fallback) | Unit            | YES (Task 2 Step 5)     | n/a        | YES                  | NO (only OSError generically, not scoped)
reconcile_gemini (concurrent/TOCTOU)| Unit/Integration| NO                       | n/a        | NO ← GAP             | NO ← GAP
reconcile_gemini (partial-batch fail)| Integration    | NO                       | n/a        | NO ← GAP             | NO ← GAP
load_gemini_ownership (malformed)   | Unit            | NO                       | n/a        | NO ← GAP             | NO ← GAP
gemini_adapter (orama-gstack target)| Unit            | YES (Task 3 Step 1)     | YES        | NO                   | NO
gemini_adapter (frontmatter policy) | Unit            | Partial (agent-methodology only) | YES | NO           | NO (other metadata_policy values untested)
cross_repo_wrapper (env var used)   | Unit            | YES (Task 4 Step 1)     | YES        | NO                   | NO
cross_repo_wrapper (missing root)   | Unit            | YES (Task 4 Step 1)     | n/a        | YES (string-only)    | NO (no path-escape/quoting test — Codex Pass 2)
verify_antigravity_root(shared-root)| Unit            | YES (Task 5 Step 1)     | YES        | n/a                  | NO
verify_antigravity_root(missing)    | Unit            | NO ← GAP                | n/a        | NO ← GAP             | n/a
verify_antigravity_root(divergent)  | Unit            | NO ← GAP                | n/a        | NO ← GAP             | n/a
validate_reconciliation_request(collision)| Unit      | YES (Task 5 Step 1)     | n/a        | YES                  | NO
candidate-block (9 slugs)           | Unit            | YES (Task 6 Step 3)     | n/a        | YES                  | NO
Task-7 full-gate verify             | Integration     | Expected but NOT WIRED ← CRITICAL GAP (see Error & Rescue Registry)
```

**Test ambition check:** the 2am-Friday test ("what test would make you confident
shipping this at 2am on a Friday?") is the concurrent-invocation / partial-batch
test — neither exists. The hostile-QA test ("kill -9 the process mid-archive,
then re-run") also doesn't exist. Given this is a local single-operator CLI (not
a service under concurrent multi-tenant load), full chaos-engineering coverage is
disproportionate (Principle 3, pragmatic) — but a single idempotence test
("re-running reconcile_gemini on an already-reconciled slug is a no-op, not an
error") is cheap and directly protects the plan's own "Subagent-Driven /
fresh-agent-per-task" execution model from Codex's flagged risk ("Task 3 can leave
global state changed while its follow-on task runs in a different context").
Added to Implementation Tasks below.

### Failure Modes Registry

```
CODEPATH                          | FAILURE MODE                    | RESCUED? | TEST? | USER SEES?        | LOGGED?
------------------------------------|----------------------------------|----------|-------|---------------------|--------
verify() post-reconciliation        | validates wrong root entirely    | N        | N     | "verification passed" (WRONG) | N — CRITICAL GAP
reconcile_gemini OSError catch-all  | masks real disk/permission errors| N (mis-rescued as fallback) | N | Silent "fallback succeeded" | N — CRITICAL GAP
reconcile_gemini concurrent run     | two agents race the same slug    | N        | N     | Silent (undefined) | N — CRITICAL GAP
load_gemini_ownership malformed JSON| manifest corrupt / hand-edited   | N        | N     | Raw traceback       | N — GAP
--archive-root literal placeholder  | operator copy-pastes `<timestamp>`| N       | N     | Directory named "<timestamp>" created | N — GAP (DX, Codex catch)
ValueError messages (3 kinds)       | no remediation text, only keyword| Partial (tests pass on keyword) | Y (keyword only) | Raw traceback, no next-step | N — GAP (DX)
inventory doc not regenerated       | Tasks 3/4/6 list doc as "Modify" but never redirect `--audit-gemini` output into it | N | N | Stale "previous digest" in evidence doc | N — GAP (Codex catch, DX)
```

Rows with RESCUED=N, TEST=N, USER SEES=Silent are marked **CRITICAL GAP** above
per this skill's own rule. Three qualify: the `verify()` false-pass, the
OSError catch-all masking real failures, and concurrent/racing invocations.
All three are addressed in Implementation Tasks below.

### DX: Developer Journey Map (implementer of this plan, not an end-user)

```
STAGE                | IMPLEMENTER DOES                          | FRICTION POINT                              | STATUS
----------------------|--------------------------------------------|----------------------------------------------|--------
1. Read the plan      | Opens this file, reads Global Constraints  | "Every write requires --reconcile-gemini,   | GAP — Codex Pass 2: false-as-written, `--install`
                       |                                            | --only, --archive-root" (line 19)            | still writes all TARGET_ROOTS unconditionally.
2. Run Task 1         | pytest -q, then --audit-gemini             | Output format unspecified beyond "sorted,   | GAP — not decision-tool quality (Codex Pass 3)
                       |                                            | portable" — no root-status/drift/next-action |
3. Run Task 2         | Write manifest JSON by hand                 | metadata_policy enum values not fully named | GAP — "none"/"external" shown, adapter values aren't
4. Run Task 3         | --reconcile-gemini --only <7 slugs>         | Copy-pastes `<timestamp>` literal            | GAP — Codex Pass 3, creates a bad dir name
5. Hit an error       | ValueError raised for e.g. preserve-external| Message is a bare classification keyword,   | GAP — both voices, no remediation text
                       |                                            | not "what do I do now"                       |
6. Run Task 7         | --verify --only <11 slugs>                  | Passes even if Gemini state is wrong         | CRITICAL GAP (see above) — false confidence
7. Hand off to next   | "fresh agent per task" (Execution Handoff)  | No persisted receipt of what Task 3 actually | GAP — Codex Pass 3, state loss across agent handoff
   task's fresh agent |                                              | did if Task 4's agent starts fresh           |
```

### DX Scorecard (0-10, gap-to-10 method)

```
DIMENSION                    | SCORE | WHAT A 10 LOOKS LIKE FOR THIS TOOL
-------------------------------|-------|-------------------------------------------------------------
Usable (install/setup)        | 7/10  | TDD steps are copy-runnable as written; a 10 adds a single
                               |       | `--dry-run` preview of the Gemini root diff before any write.
Credible (predictable)        | 5/10  | A 10 has verify() actually check what Task 7 claims it checks,
                               |       | and idempotent re-runs are explicitly tested and documented.
Findable (errors self-explain) | 4/10  | A 10's ValueErrors read like "code-review is gstack-owned
                               |       | (preserve-external) — no mutation performed; managed by gstack,
                               |       | not this manifest" instead of a bare keyword.
Useful (solves the real problem)| 8/10 | Already strong — correctly scopes to the 13 known-divergent
                               |       | cards and defers the 9 unknowns instead of guessing.
Accessible (any implementer)  | 6/10  | A 10 has the audit output in both human-table and `--json` form
                               |       | so a fresh agent-per-task handoff can machine-parse prior state.
```

### Decision Audit Trail (auto-decided using the 6 principles; Mechanical vs Taste vs User Challenge)

| # | Decision | Classification | Reasoning (principle) | Auto-decided outcome |
|---|----------|-----------------|------------------------|------------------------|
| D1 | Manifest-gated architecture vs. flatter 11-slug migration list (Codex Pass 1 preference) | **Taste** — reasonable people disagree; Codex leans flatter, this review leans manifest-first given the documented July incident | P1 completeness + P4 DRY (the manifest generalizes a pattern the file already needs) | Keep manifest-gated design; fold in Codex's scoping critique (one shared root-resolver for T1+T5, don't build a permanent 5-root drift monitor) |
| D2 | Mode = HOLD SCOPE vs SELECTIVE EXPANSION | **Mechanical** | CEO skill's own default for "refactor / enhancement of existing system" | HOLD SCOPE |
| D3 | `verify()` false-pass on Gemini state — fix now vs defer to TODOS | **Mechanical** — cross-model consensus (Codex + independent Claude found it separately), CRITICAL GAP, directly contradicts Task 7's own "Expected" claims | P1 completeness — a review gate that doesn't gate is worse than no gate | Add a Gemini-aware verify path; P1 in Implementation Tasks |
| D4 | OSError catch-all in symlink fallback — narrow now vs defer | **Mechanical** — matches the user's own explicit Section 2 rule ("catch-all is always a smell") plus Codex's independent finding | P5 explicit over clever | Narrow to recognized symlink-unsupported errno values; re-raise others; P1 |
| D5 | Concurrent/racing `reconcile_gemini` invocations — full distributed lock+journal (Codex's ask) vs lightweight sentinel lock | **Taste** | P3 pragmatic — this is a single-operator local CLI, not a multi-tenant service; a `.reconcile.lock` sentinel + re-check-before-commit is proportionate, a "durable recovery journal" is not | Lightweight lock + idempotence test; P2 |
| D6 | Split Gemini reconciliation into its own module vs keep in `install_thin_skill_wrappers.py` | **Taste** leaning **Mechanical** — the repo's own coding-style rule caps files at 800 lines / 200-400 typical; this file will cross that line by the end of Task 6 | P5 explicit, P4 DRY (avoid one file doing 4 unrelated jobs) | Extract Gemini reconciliation to a new sibling module in Task 2, imported by the existing CLI; P2 |
| D7 | `--archive-root` literal `<timestamp>` placeholder in Tasks 3-5 commands | **Mechanical** — objectively a copy-paste bug, Codex catch | P5 explicit | Replace with `"$(date -u +%Y%m%dT%H%M%SZ)"` in the plan text; P1, trivial |
| D8 | `metadata_policy` enum values incomplete ("none"/"external" shown, adapter values unnamed) | **Mechanical** — both voices independently flagged, objectively underspecified | P5 explicit | Name every value in Task 2's manifest schema; P1 |
| D9 | Error message content (keyword-only vs slug+remediation) | **Mechanical** — both voices agree, DX principle "every error = problem + cause + fix" | P1 completeness | Require slug + remediation text in every raised ValueError; test on substring is fine, message content should be richer than the tested substring; P2 |
| D10 | `--audit-gemini` output richness (root-status/drift-state/JSON mode) | **Taste** — real value but not blocking; in blast radius, <1 day CC effort | P2 boil lakes (auto-approve: in blast radius + <1 day CC effort) | Add root-status/drift/next-action columns + `--json` flag; P2 |
| D11 | Inventory doc regeneration after reconciliation — wire `--audit-gemini` output into the doc | **Mechanical** — Codex catch, plan lists doc as "Modify" in 3 tasks but never states the redirect | P1 completeness | Add explicit "regenerate inventory doc from fresh --audit-gemini output" sub-step to Tasks 3/4/6; P1 |
| D12 | GossipBus "Antigravity already validated" claim — trust as covering Task 5 or not | **User Challenge (informational, not auto-decidable)** — this is a factual claim about prior work, not a design preference; ground-truth check on this machine found no corroborating evidence | n/a — flagged, not decided | Surfaced in "What Already Exists" above; recommend the human confirm which environment that validation ran in before treating Task 5 as lower-priority |

No decision in this review reached the **User Challenge** bar as defined by the
autoplan skill (both models recommending the user's stated *direction* change,
e.g. drop a task or merge tasks) — D1 and D6 are architecture-shape taste calls
within the plan's existing direction, not a recommendation to abandon it. D12 is
an informational flag, not an auto-decidable design question.

## Implementation Tasks

Synthesized from this review's findings. Each task derives from a specific
finding above. P1 blocks ship (fold into Tasks 2/5/7 before implementation
starts); P2 should land same branch; P3 is a follow-up TODO.

- [ ] **T1 (P1, human: ~3h / CC: ~30min)** — reconciliation-verify — Add a
  Gemini-aware verification path distinct from the existing `verify()`
  - Surfaced by: Error & Rescue Registry — `verify()` CRITICAL GAP; cross-model
    consensus (Codex Pass 2 + independent Claude pass, found separately)
  - Files: `bin/orama-system/skills/skillify/scripts/install_thin_skill_wrappers.py`
    (or the new split module, see T6), `tests/test_install_thin_skill_wrappers.py`
  - Verify: `pytest tests/test_install_thin_skill_wrappers.py -q` includes a test
    asserting Task 7's `--verify --only <gemini slugs>` actually inspects
    `~/.gemini/skills` symlink targets, archive receipts, and calls
    `verify_antigravity_root`, not just `TARGET_ROOTS`

- [ ] **T2 (P1, human: ~1h / CC: ~10min)** — narrow-oserror-catch — Replace the
  generic `except OSError` symlink fallback with a narrow catch on recognized
  symlink-unsupported conditions; re-raise everything else
  - Surfaced by: Error & Rescue Registry, Failure Modes Registry — OSError
    catch-all CRITICAL GAP; Codex Pass 2 independently flagged the same line
  - Files: `install_thin_skill_wrappers.py` (Task 2 Step 4's `create_relative_link`
    caller), `tests/test_install_thin_skill_wrappers.py`
  - Verify: a new test asserting a permission-denied `OSError` propagates instead
    of silently falling back to a generated wrapper

- [ ] **T3 (P1, human: ~15min / CC: ~5min)** — fix-timestamp-placeholder — Replace
  the literal `<timestamp>` in Tasks 3, 4, 5's `--archive-root` example commands
  with a concrete, safe expression
  - Surfaced by: Codex Pass 3 (DX), "copy-paste bait"
  - Files: this plan file (`docs/superpowers/plans/2026-08-14-gemini-skill-consolidation.md`)
  - Verify: manual read — `--archive-root "$HOME/.gemini/skills-archive/$(date -u +%Y%m%dT%H%M%SZ)"`

- [ ] **T4 (P1, human: ~30min / CC: ~10min)** — name-metadata-policy-values —
  Enumerate every `metadata_policy` value (not just "none"/"external") in Task
  2's manifest schema, with one example input/output pair per value
  - Surfaced by: Decision Audit Trail D8, both voices independently
  - Files: this plan file, `bin/orama-system/skills/skillify/references/gemini-skill-ownership.json`
  - Verify: manual read — every value referenced by the Disposition Matrix's
    "adapter" rows has a named `metadata_policy`

- [ ] **T5 (P1, human: ~30min / CC: ~10min)** — wire-inventory-regeneration —
  Add an explicit sub-step to Tasks 3, 4, 6 that redirects fresh `--audit-gemini`
  output into `docs/reference/gemini-skill-consolidation-inventory.md` after
  each reconciliation batch
  - Surfaced by: Decision Audit Trail D11, Codex Pass 3
  - Files: this plan file
  - Verify: manual read — each task's "Verify and commit" block includes the
    redirect, not just a bare `--audit-gemini` invocation

- [ ] **T6 (P2, human: ~2h / CC: ~20min)** — split-gemini-module — Extract the
  Gemini reconciliation surface (Task 1-5 interfaces) into a new sibling module
  under `bin/orama-system/skills/skillify/scripts/`, imported by the existing
  CLI dispatch in `install_thin_skill_wrappers.py`
  - Surfaced by: Decision Audit Trail D6 — repo's own 800-line file ceiling,
    SRP (outbound-publish vs inbound-foreign-root-reconciliation are different
    risk classes per Codex Pass 1)
  - Files: new module (e.g. `gemini_reconcile.py`), `install_thin_skill_wrappers.py`,
    `tests/test_install_thin_skill_wrappers.py` (or a new test file alongside it)
  - Verify: `wc -l` on both files stays under the repo's 800-line ceiling

- [ ] **T7 (P2, human: ~1h / CC: ~15min)** — actionable-error-messages — Every
  `ValueError` raised by `reconcile_gemini`/`validate_reconciliation_request`
  includes the slug, the observed state, and a one-line remediation, not just
  the classification keyword the tests match on
  - Surfaced by: Decision Audit Trail D9, both voices
  - Files: install script/new module, `tests/test_install_thin_skill_wrappers.py`
  - Verify: manual read of exception message templates against the DX skill's
    "problem + cause + fix" bar

- [ ] **T8 (P2, human: ~2h / CC: ~20min)** — lightweight-reconcile-lock — Add a
  sentinel lock file (or equivalent) around `reconcile_gemini` plus a
  source-revalidation check immediately before the archive-then-symlink commit,
  and one idempotence test (re-running on an already-reconciled slug is a no-op)
  - Surfaced by: Decision Audit Trail D5, Codex Pass 2 (transactionality),
    Test Diagram gap
  - Files: install script/new module, `tests/test_install_thin_skill_wrappers.py`
  - Verify: new test simulates two sequential `reconcile_gemini` calls on the
    same slug and asserts the second is a no-op, not an error or a duplicate archive

- [ ] **T9 (P3, human: ~2h / CC: ~20min)** — richer-audit-output — Add
  root-availability, resolved-root status, drift-state, and next-action columns
  to `--audit-gemini`'s human output, plus a `--json` flag for machine parsing
  - Surfaced by: Decision Audit Trail D10, Codex Pass 3
  - Files: install script/new module
  - Verify: `--audit-gemini --json | jq .` round-trips cleanly

- [ ] **T10 (P3, human: ~1h / CC: ~10min)** — untested-verify-antigravity-states —
  Add tests for `verify_antigravity_root`'s `missing` and `divergent` states,
  not just `shared-root`
  - Surfaced by: Test Diagram gap, Codex Pass 2 ("one symlink equality test is
    insufficient")
  - Files: `tests/test_install_thin_skill_wrappers.py`
  - Verify: `pytest -k verify_antigravity -v` shows 3 passing cases

### JSONL artifact

Written to `~/.gstack/projects/diazMelgarejo-orama-system/tasks-autoplan-review-20260814.jsonl`
(one line per T1-T10 above, `phase` field set per originating review: T1/T2/T8/T10
= `eng-review`, T3/T4/T5/T7/T9 = `devex-review`, T6 = `eng-review`).

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/autoplan` (CEO phase) | Scope & strategy | 1 | issues_open | Mode=HOLD SCOPE; scope proportionality tension (D1, taste); Antigravity "already done" claim not corroborated on this machine (D12, informational) |
| Codex Review | `codex exec` (adversarial, all 3 phases combined) | Independent 2nd opinion | 1 | issues_found | 14 findings across CEO/Eng/DX passes; high overlap with independent Claude pass (verify() gap, catch-all OSError, metadata_policy, error messages found by both) |
| Eng Review | `/autoplan` (Eng phase) | Architecture & tests (required) | 1 | issues_found | 3 CRITICAL GAPs (verify() false-pass, OSError catch-all, concurrent/racing invocations), 7 additional test/architecture gaps, SRP/file-size concern (D6) |
| Design Review | N/A | UI/UX gaps | 0 | SKIPPED | No UI scope — CLI/manifest tool only, confirmed by plan content (no endpoints, screens, or user-visible interaction flows) |
| DX Review | `/autoplan` (DX phase) | Developer experience gaps | 1 | issues_found | Scorecard: Usable 7/10, Credible 5/10, Findable 4/10, Useful 8/10, Accessible 6/10; 7 journey-stage friction points, `<timestamp>` copy-paste bug (Codex catch) |

- **CODEX:** Ran `codex exec -s read-only --enable web_search_cached -c 'model_reasoning_effort="high"'` against the plan with the filesystem-boundary instruction prefixed; returned 14 tagged findings across all 3 passes, none in disagreement with the independent Claude pass — pure additive coverage (Codex caught the `<timestamp>` bug and the inventory-doc-regeneration gap that the independent pass missed; the independent pass caught the same `verify()` false-pass and OSError catch-all Codex also found).
- **CROSS-MODEL:** Full agreement on the three CRITICAL GAPs (`verify()` false-pass, OSError catch-all, no concurrency guard) and on `metadata_policy`/error-message underspecification. Codex additionally flagged manifest schema-version handling and PERPETUA_TOOLS_PATH path-escape validation (folded into T4/T7 above at P2/P3, not separately CRITICAL). No cross-model tension requiring a user tiebreak — see Decision Audit Trail, zero User Challenges.
- **VERDICT:** CEO + DX reviewed, no blockers to continued planning. **ENG REVIEW: NOT CLEARED** — 3 CRITICAL GAPs (T1, T2, T8 above) must land before Task 2 of the underlying plan begins implementation, per this skill's Prime Directive #1 (zero silent failures) and Directive #2 (catch-all error handling is a defect). Re-run `/plan-eng-review` (or this pipeline) after T1/T2/T3/T4/T5 land to clear the gate.

**UNRESOLVED DECISIONS:**
- D1 (manifest-gated architecture vs. flatter migration list) — taste call, auto-decided to keep manifest-gated with scope-tightening (D1 outcome above); human may override before implementation starts.
- D12 (GossipBus "Antigravity already validated" claim) — informational only; recommend confirming which environment/session that validation ran in, since this machine shows no corroborating symlink evidence, before deprioritizing Task 5.
