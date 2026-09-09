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

## E2 — `instruction-debt-remediation-plan.md`, R3b: broad command-prefix allowlists are not a read-only authorization

**Source location:** R3b, "orama-system permission allowlist."

**The correction**: the proposed trailing-`*` command prefixes are not safe
read-only entries. `git branch`, `find`, `jq`, `sort`, and similar
commands have argument forms that can mutate state, write output, or cause
side effects. The absence of a mutating verb in the prefix is insufficient.
This correction supersedes the source proposal's broad allowlist and records
that the prior claimed authorization does not apply to it.

**Required implementation boundary**: define explicitly supported read-only
operations and validate their arguments and effects before allowing them.
Prefer structured read APIs where they exist. An unknown, malformed, or
mutating form follows the ordinary deny/approval path; it does not inherit a
command-family grant. Verify negative cases before side effects in the actual
successor adapter. This errata changes no real `.claude/settings.json` file.

This belongs with C1/C4's Phylax admission-adapter work in wave M4. It does
not authorize a legacy settings change, an allowlist widening, or an
unreviewed transfer of a shell policy into v2.

## E3 — `oramasys-migration-execution-plan.md`, "Recommended first move" — verify target-scoped access without probing writes

**Source location:** the document's closing "Recommended first move"
section.

**What the preserved document says**, verbatim: "Wave 0 plus Wave 1, in a
session tiered to `oramasys/perpetua-core` — it already has a CI
workflow, so the hygiene gate has somewhere to land immediately."

**The correction**: a target session needs verified authority for the actual
authorized change, not favorable-looking capability metadata. Do not create
empty branches, draft PRs, or other external state merely to probe access.
Those are writes with their own scope and notification effects.

Before Wave 0 begins, confirm repository access through an already-authorized,
meaningful scoped change or owner-provided access evidence. If neither exists,
treat target write access as unverified, request the required access or
direction, and continue only independent read-only planning. Do not silently
fall back to another target repository. Record the observed authorization and
the exact artifact/evidence in M0; never infer it from account metadata alone.

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
