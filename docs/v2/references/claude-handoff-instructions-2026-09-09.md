# Claude handoff instructions: preserved source

Historical input, not current execution authority. Read the
[harmonization](migration-harmonization-2026-09-09.md) before using it.
The original text below is retained verbatim; its owner-tier claim describes the
source session, and its proposed decisions are reconciled in the harmonization.

```text
WHAT THIS ZIP IS
=================

Four Markdown documents produced by the 2026-09-09 instruction-debt audit and
the oramasys migration plan, already placed at the exact repo-relative path
they belong at:

    docs/v2/references/instruction-debt-audit-2026-09-09.md
    docs/v2/references/instruction-debt-remediation-plan.md
    docs/v2/references/oramasys-migration-execution-plan.md
    docs/v2/references/portable-memory-sanitization-runbook.md

They were written and validated against your own repo tooling inside a local
clone of diazMelgarejo/orama-system, at commit 0df2194 on branch main. They
are NOT yet committed or pushed anywhere. This session cannot push to
diazMelgarejo/orama-system (a cross-tier restriction — this session is tiered
to a different GitHub owner), so the files are handed to you here instead.

Validation already run against these exact files, in the real repo:
  - scripts/review/repo_hygiene.py .   -> "OK: repo hygiene checks passed" (exit 0)
  - LINT-013 (no raw LAN IP literals)  -> 0 hits
  - LINT-015 (every code fence labeled) -> 0 unlabeled fences, all balanced
  - MD013 (line length under the repo's 100-char cap outside code/tables) -> 0 violations
  - All internal cross-links between the four files resolve
  - No email / home-directory-path / RFC1918 literal in any of the four files

Nothing else in the repo was touched. `git status` on the clone this was
copied from shows only these four files as new/untracked.


HOW TO GET THIS INTO THE REPO
==============================

Option A — fastest, if you have local push access to diazMelgarejo/orama-system:

  1. Unzip this archive.
  2. From the root of your own local clone of diazMelgarejo/orama-system, copy
     the docs/v2/references/ folder from this zip on top of your repo's
     docs/v2/references/ folder (it only adds 4 new files; nothing existing
     is overwritten).
  3. Review the diff:
         git status
         git diff --stat
     You should see exactly 4 new files under docs/v2/references/, nothing
     else changed.
  4. Optionally re-run the repo's own guard before committing:
         python3 scripts/review/repo_hygiene.py .
     Expect: "OK: repo hygiene checks passed"
  5. Commit and push, e.g.:
         git checkout -b docs/instruction-debt-audit-2026-09-09
         git add docs/v2/references/instruction-debt-audit-2026-09-09.md \
                 docs/v2/references/instruction-debt-remediation-plan.md \
                 docs/v2/references/oramasys-migration-execution-plan.md \
                 docs/v2/references/portable-memory-sanitization-runbook.md
         git commit -m "docs(v2): add instruction-debt audit, remediation plan, migration plan, and memory sanitization runbook"
         git push -u origin docs/instruction-debt-audit-2026-09-09
  6. Open a PR against main in the normal way, or merge directly per your
     own workflow for this repo.

Option B — via GitHub's web UI, if you don't have a local clone handy:

  1. Unzip this archive.
  2. Go to https://github.com/diazMelgarejo/orama-system
  3. Navigate to docs/v2/references/
  4. Use "Add file" -> "Upload files" and drag in the 4 .md files from the
     unzipped docs/v2/references/ folder.
  5. Commit directly to a new branch and open a PR (GitHub's uploader offers
     this as an option), rather than committing straight to main.

Option C — hand this to a Claude Code session that IS tiered to the
diazMelgarejo owner (or ask a teammate with push access to run Option A).
That session can read the audit/plan content directly from these files and
commit them without needing this zip at all.


WHAT TO READ, IN ORDER
========================

1. instruction-debt-audit-2026-09-09.md
   The full audit: 9 findings (F1-F9), what's already well-scoped and should
   NOT be touched, coverage/access-gap inventory, and 5 scenario walkthroughs
   (typo fix, DB migration, UI visual-inspection change, failing test,
   deployment requiring approval).

2. instruction-debt-remediation-plan.md
   Exact fixes for the audit findings (R1-R7), with a called-out "smallest
   useful batch" of 4 items (R1-R4) to do first. Every fix states what it
   preserves, not just what it changes.

3. oramasys-migration-execution-plan.md
   The 6-wave plan (Wave 0-5) to migrate diazMelgarejo/orama-system and
   diazMelgarejo/Perpetua-Tools content into the oramasys/* org, copy-forward
   only, v1 untouched throughout. Includes a risk register and 4 open
   questions that need your decision before specific waves can proceed.

4. portable-memory-sanitization-runbook.md
   The detailed step-by-step procedure for finding F1 (Perpetua-Tools/.agent/
   carries live email + private-network-address leaks). This gates Wave 2 of
   the migration plan — do not skip it or copy .agent/ into any oramasys/*
   repo before running this.


DECISIONS YOU STILL NEED TO MAKE
===================================

These are called out inside oramasys-migration-execution-plan.md under
"Open questions," repeated here so you don't have to go find them:

1. Does oramasys/anamnesis get created to own portable memory in v2, or does
   memory land in oramasys/perpetua-core instead? This blocks Wave 2, step 5
   of the migration plan (and therefore the sanitization runbook's final
   migrate step).

2. Where do the ~62 canonical skills land in the target repos — one shared
   skills home, or split per-repo? Blocks Wave 4, step 3.

3. What is the intended end state for v1 (diazMelgarejo/orama-system and
   diazMelgarejo/Perpetua-Tools) once migration completes: archived read-only,
   or maintained indefinitely? Determines how Wave 5 finishes (remove legacy
   references outright vs. leave historical pointers).

4. How much of Wave 4 (skills consolidation) do you actually want done: all
   ~62 canonical skills migrated, or only the ones with live v2 triggers?
   This is the single largest unscoped piece of work in the whole plan.


ONE THING WORTH DOING BEFORE YOU COMMIT
==========================================

The remediation plan's R5 (generate skill wrappers instead of hand-copying
them) should land BEFORE migration Wave 4 runs, or you will carry 29 already-
drifted skill descriptions across the org boundary permanently. It's a small
script; see R5 in instruction-debt-remediation-plan.md for exactly what it
needs to do.


QUESTIONS OR CHANGES
=======================

These docs went into docs/v2/references/ because that's the existing
convention for exactly this kind of subordinate/derived planning document in
this repo (see agate-mvp-design.md and the phylax-monitorability-part-*.md
files already living there as the pattern). If you'd rather these live
somewhere else instead (e.g. staged directly in oramasys/alexandria instead
of v1's docs/v2/references/), say so and they can be regenerated at that
path — nothing about the content is tied to this specific location, only the
cross-links between the four files, which would need updating to match.
```
