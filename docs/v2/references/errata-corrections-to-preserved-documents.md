# Errata — Corrections to Preserved Historical Documents

> **Status:** corrections only. The 4 source documents named below remain
> byte-for-byte unmodified, per their explicit provenance guarantee
> (SHA-256-pinned in
> [claude-input-provenance-2026-09-09.json](claude-input-provenance-2026-09-09.json)).
> This document states what's wrong and what the correct version is; it
> does not edit the sources. Anyone implementing a correction below should
> apply it directly to the real target file/system, not to the preserved
> document that first proposed it.
> **Provenance:** written in response to
> [pullrequestreview-5148933700](https://github.com/diazMelgarejo/orama-system/pull/351#pullrequestreview-5148933700)
> on PR #351, whose findings against these 4 documents this file resolves
> without breaking their preservation guarantee — the same pattern already
> used for the runbook CLI clarification in
> [docs/wiki/08-git-hygiene-and-branching.md](../../wiki/08-git-hygiene-and-branching.md).

---

## E1 — `instruction-debt-remediation-plan.md`, R3a: the proposed ruff-hook command masks the real exit status

**Source location:** R3a, "Ruff hook (both repos)."

**What the preserved document proposes**, verbatim:

```json
"command": "payload=$(cat); file=$(printf '%s' \"$payload\" | python3 -c \"import sys,json;print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))\" 2>/dev/null); [ -z \"$file\" ] && file=$(python3 -c \"import os,json;print(json.loads(os.environ.get('CLAUDE_TOOL_INPUT','{}')).get('file_path',''))\" 2>/dev/null); [[ \"$file\" == *.py ]] && ruff check \"$file\" 2>&1 | head -10 || true"
```

**The correction**: `... | head -10 || true` masks `ruff check`'s real
exit status in two ways — the pipeline's reported exit code is `head`'s,
not `ruff`'s, and the trailing `|| true` unconditionally overrides
whatever exit code does survive. A hook meant to surface lint failures
this way will never actually report one as a failure, regardless of
whether ruff found anything. Corrected form, preserving output
truncation while keeping ruff's real exit status:

```json
"command": "payload=$(cat); file=$(printf '%s' \"$payload\" | python3 -c \"import sys,json;print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))\" 2>/dev/null); [ -z \"$file\" ] && file=$(python3 -c \"import os,json;print(json.loads(os.environ.get('CLAUDE_TOOL_INPUT','{}')).get('file_path',''))\" 2>/dev/null); if [[ \"$file\" == *.py ]]; then out=$(ruff check \"$file\" 2>&1); status=$?; printf '%s\\n' \"$out\" | head -10; exit \"$status\"; fi; exit 0"
```

Captures ruff's status before truncating output, then exits with that
captured status rather than truncation's or a hardcoded `true`. The same
fix applies to R2's analogous pytest command (same document, `tail -30`
in place of `head -10`) for the identical reason — status is captured
before truncation, not read from the truncation command's own exit code.

## E2 — `instruction-debt-remediation-plan.md`, R3b: allowlist widening — authorized by direct human decision

**Source location:** R3b, "orama-system permission allowlist." The
preserved document's own text already states this correctly and needs no
technical correction — it explicitly instructs "obtain security review
before applying," which review 5148933700 repeated as its own finding.

**Disposition, recorded here rather than silently assumed**: reviewed and
explicitly authorized. The 12 proposed entries (`git status`, `git log`,
`git diff`, `git show`, `git branch`, `git rev-parse`, `grep`, `rg`,
`find`, `jq`, `sort`, `uniq`, each with a trailing `*`) are read-only
commands; none introduces a mutating verb (no `push`, `commit`, `rm`,
`merge`, or deploy command), matching the preserved document's own stated
scope exactly. **This authorization applies to the proposal as written in
the preserved document — it does not itself modify any real
`.claude/settings.json` file**, which is outside this docs-only PR's
scope and was not independently inspected as part of this authorization.
Whoever implements this (matching the ownership map in
[consolidated-cross-reference-and-execution-order.md](consolidated-cross-reference-and-execution-order.md),
likely alongside C1/C4's Phylax admission-adapter work in wave M4) should
treat this record as the sign-off, not re-request it, but should still
verify the target file's current state before applying — this
authorization was granted against the proposal's text, not a live diff
against an inspected target file.

## E3 — `oramasys-migration-execution-plan.md`, "Recommended first move" — add an explicit push-access precondition

**Source location:** the document's closing "Recommended first move"
section.

**What the preserved document says**, verbatim: "Wave 0 plus Wave 1, in a
session tiered to `oramasys/perpetua-core` — it already has a CI
workflow, so the hygiene gate has somewhere to land immediately."

**The correction**: this recommendation assumes the executing session
already has verified push access to `oramasys/perpetua-core`. This
session's own experience is the concrete counter-example: its GitHub
token has repo-level `push`/`admin` reported in capability metadata for
`diazMelgarejo/orama-system`, yet PR creation on that same repo returned
403 — confirmed directly, not assumed, earlier in this document
directory's own history. Reported capability metadata is not
authorization, a principle this same PR's own audit content (Part 1,
§"Loading, scope, and precedence") already states independently.
Corrected precondition, to run before Wave 0 begins on any target
repository, not assumed from account-level permission fields:

1. Attempt a trivial, reversible write against the actual target
   repository and branch (e.g., a branch creation, or a draft PR against
   a scratch branch) before relying on that repository for Wave 0/M2
   foundational work.
2. If the write fails despite favorable-looking capability metadata,
   treat the session as read-only for that repository regardless of what
   `permissions` fields report, and escalate for a token/scope fix before
   proceeding — do not silently fall back to a different target
   repository as a workaround, which would be an undocumented scope
   change to the plan.
3. Record the verified result (not the reported capability) in the M0
   baseline evidence this same plan already requires.

## E4 — `portable-memory-sanitization-runbook.md`, Step 1: snapshot-copy placeholder path

**Source location:** the runbook's snapshot-creation step, immediately
before "Step 2 — Establish the baseline with the real guard."

**What the preserved document shows**, verbatim:

```bash
SNAP="$(mktemp -d)/agent-memory-snapshot"
cp -a /path/to/perpetua-tools/.agent "$SNAP"
```

**The correction**: `/path/to/perpetua-tools` is a placeholder, not a
runnable path, and the runbook's own later steps already reference a
`$PERPETUA_TOOLS_ROOT`-shaped variable convention for exactly this
purpose (matching this repository's own
[git-hygiene wiki doc](../../wiki/08-git-hygiene-and-branching.md)'s
established "no workstation-specific literal paths in tracked files"
discipline, which this specific line does not follow). Corrected form:

```bash
SNAP="$(mktemp -d)/agent-memory-snapshot"
cp -a "$PERPETUA_TOOLS_ROOT/.agent" "$SNAP"
```

Whoever executes this runbook should set `PERPETUA_TOOLS_ROOT` to their
actual local Perpetua-Tools checkout path before running Step 1, matching
this repository's existing variable-substitution convention rather than
hand-editing a literal path into the command each time.
