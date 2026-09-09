# Portable Memory Sanitization Runbook

> **Status:** approved 2026-09-09, blocked on Wave 0 registry and the anamnesis decision
> **Implements:** Wave 2 of
> [`oramasys-migration-execution-plan.md`](oramasys-migration-execution-plan.md)
> **Addresses:** finding F1 of
> [`instruction-debt-audit-2026-09-09.md`](instruction-debt-audit-2026-09-09.md)
> **Normative authority:**
> [doc 47 — portable-memory invariant](../47-portable-memory-local-topology-invariant.md).
> Doc 47 governs the invariant, the guard shape, and the registry contract; this runbook
> supplies the execution detail for one specific migration.

---

## Why this is a separate document

The rest of the migration moves files. This wave moves **the record of what the system has
learned**, and that record currently carries live private literals. Getting it wrong in
either direction is costly:

- Copy it as-is, and every successor repository is born violating doc 47.
- Delete the offending rows, and institutional memory is destroyed to fix a formatting
  problem.

The operating principle throughout, from the operator's standing invariant:

> **Do not amputate memory to fix a leak — sanitize it, do not stop recording it.**

Nothing in this runbook deletes a memory row.

---

## Baseline

Measured 2026-09-09 against `Perpetua-Tools/.agent/` (825 files):

| Category | Files | Lines |
| --- | --- | --- |
| Non-benign full email literals | 7 | 10 |
| RFC1918 `192.168/16` block literals | — | 15 |
| Link-local `169.254/16` block literals | — | 6 |
| API-key-shaped literals | 1 | 2 |
| Personal home-directory paths | 0 | 0 |

Benign synthetic hits — `anthropic.com` (8) and `example.com` (3) — are correctly excluded
and must remain excluded by the guard's allowlist.

**Zero home-directory path hits is a genuine pass.** Path hygiene is already working; the
failure is confined to identity and network-topology literals.

### Affected files

```text
.agent/memory/episodic/AGENT_LEARNINGS.jsonl       source row
.agent/memory/semantic/lessons.jsonl               source row
.agent/memory/candidates/graduated/<id>.json       source row
.agent/memory/semantic/LESSONS.md                  derived view
.agent/memory/semantic/DECISIONS.md                derived view
```

The split across source rows **and** derived views is the whole difficulty, and the reason
step order below is not negotiable.

---

## The rule that governs step order

From doc 47, and from the operator's standing invariant:

> **Supersession is not sanitization.** When a memory row leaks a private or
> local-topology literal, fix the source row or archived candidate, then regenerate every
> derived view. A struck-through rendered lesson, stale candidate, or old episodic row
> still counts as leaked portable memory until the source is scrubbed.

Two consequences that determine everything below:

1. **Sources before views.** Cleaning `LESSONS.md` while `lessons.jsonl` still carries the
   literal fixes nothing — the next regeneration re-leaks it.
2. **Regenerate, never hand-edit, a derived view.** A hand-edited view silently diverges
   from its source. It will look clean and re-leak on the next build.

---

## Preconditions

Do not start until all four hold:

- [ ] **Wave 0 registry exists** on the machine running the sanitization, with doc 47's
      keys populated: `owner_gmail`, `owner_name`, `forbidden_attribution`,
      `local_path_fragment`, `local_workspace_fragment`, `verboten_path_fragment`,
      `device_or_network_fragment`.
- [ ] **Wave 1 guard is live** in the destination repository and fails CI on a synthetic
      planted marker.
- [ ] **Destination decided** — `oramasys/anamnesis` (to be created) or `perpetua-core`.
      See the open question in the migration plan; this blocks step 7.
- [ ] **v1 write-protection confirmed.** The session must not hold push access to
      `diazMelgarejo/Perpetua-Tools`. Constraint 1 is enforced by tiering, not by
      discipline alone.

---

## Procedure

### Step 1 — Snapshot outside git

```bash
SNAP="$(mktemp -d)/agent-memory-snapshot"
cp -a /path/to/perpetua-tools/.agent "$SNAP"
```

Work exclusively on `$SNAP`. The v1 tree is read-only for the remainder of this runbook.

The snapshot location must be outside every git worktree — a working copy carrying
unsanitized literals must never be stageable.

### Step 2 — Establish the baseline with the real guard

```bash
python3 src/tools/repo_hygiene.py --scan "$SNAP" --report categories
```

Expect the counts in the baseline table. **If the numbers differ, stop** — either the
memory changed since the audit, or the guard's category definitions disagree with the
audit's. Reconcile before proceeding; a guard that under-reports will certify a dirty tree
as clean.

Record the baseline. It is the before-figure for the acceptance check.

### Step 3 — Classify every hit before changing anything

For each hit, decide which of three treatments applies:

| Treatment | When | Result |
| --- | --- | --- |
| **Registry key** | The literal identifies the operator, a device, or local topology | Replace with the doc 47 key |
| **Synthetic** | The literal is illustrative — an example in a lesson body | Replace with a synthetic marker |
| **Structural drop** | The literal is an incidental artifact with no semantic role | Remove the field, keep the row |

**Classification is a judgement call and must precede editing.** Rewriting a lesson's
meaning while sanitizing it is the failure mode to avoid: the point is to keep the lesson
and lose the literal.

Record the classification per hit. It becomes the audit trail for this wave.

### Step 4 — Sanitize source rows only

Edit, in this order:

```text
.agent/memory/episodic/AGENT_LEARNINGS.jsonl
.agent/memory/semantic/lessons.jsonl
.agent/memory/candidates/graduated/<id>.json
```

Preserve every row. Preserve row identity — ids, timestamps, ordering, and provenance
fields — so downstream consumers and any existing embeddings stay valid.

**Do not touch `LESSONS.md` or `DECISIONS.md` in this step.** They are outputs.

### Step 5 — Regenerate derived views

Rebuild `LESSONS.md` and `DECISIONS.md` from the sanitized sources using the repository's
own renderer. Do not hand-edit them.

If no renderer exists, **that is itself a finding** — it means the views have been
maintained by hand, and doc 47's regeneration requirement cannot be satisfied. In that
case build the renderer first; a view that cannot be regenerated cannot be certified
clean.

### Step 6 — Verify to zero, and verify idempotence

```bash
python3 src/tools/repo_hygiene.py --scan "$SNAP" --report categories
```

Two conditions, both required:

- [ ] The scan reports **zero** in every non-benign category.
- [ ] A second regeneration of the derived views produces **no diff** — proving the views
      genuinely derive from the sanitized sources rather than having been edited into
      looking clean.

The second check is the one that catches the failure mode in step 5. Do not skip it.

### Step 7 — Migrate

Copy the sanitized tree into the destination decided in the preconditions. Run the
destination's CI guard as the gate — the same guard, now enforcing on arrival.

### Step 8 — Close the loop with write-time redaction

Per doc 47's acceptance criterion 4, memory tools must **redact at write time**, before
candidate, episodic, or semantic records are persisted.

Without this step the tree is clean exactly once and drifts thereafter. This is the
difference between a cleanup and a fix, and it is the point of the operator's mnemonic:

> *Secure persistent memory equals persistently secure memory* — memory that lasts across
> sessions is only as trustworthy as the discipline that keeps it clean on every write,
> not a one-time cleanup.

---

## Acceptance criteria

Mapped directly to doc 47's acceptance list:

- [ ] A whole-tree portable-memory scan reports zero hits.
- [ ] The portable-brain guard is enforced in the destination's CI.
- [ ] Tests prove local-only registry loading **with synthetic values only**.
- [ ] Memory tools redact at write time before records are persisted.
- [ ] Rendered memory files are regenerated from sanitized source records.

Two added for this specific migration:

- [ ] Row count is unchanged between snapshot and migrated tree — **nothing was amputated.**
- [ ] The v1 `.agent/` tree is byte-identical to its pre-runbook state.

---

## Failure modes to watch for

| Failure | Symptom | Prevention |
| --- | --- | --- |
| View cleaned, source left dirty | Scan passes, next regeneration re-leaks | Step order: sources first (step 4 before 5) |
| View hand-edited | Scan passes, regeneration produces a diff | Idempotence check (step 6) |
| Rows deleted to clear hits | Scan passes, memory is poorer | Row-count check in acceptance |
| Guard under-reports | Dirty tree certified clean | Baseline reconciliation (step 2) |
| Literal pasted into this runbook or a test | The invariant violated by its own remediation | Categories only; synthetic fixtures only |
| Clean once, drifts after | Scan passes today, fails in a month | Write-time redaction (step 8) |

The fifth row deserves emphasis. Every artifact produced by this wave — this runbook, the
guard's tests, the classification record from step 3 — is itself tracked content and is
bound by doc 47. Test fixtures use synthetic markers loaded from a temporary local-only
fixture, never a real literal. A remediation that leaks while remediating has failed.
