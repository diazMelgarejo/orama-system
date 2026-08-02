---
name: security
description: >
  Canonical entrypoint for portable-memory and secret-hygiene security work
  across the orama-system stack: category-only tracked policy, off-repo
  local-only registries, OpSec vs SecOps vocabulary, and routing to the right
  specialist reference (git-history-surgery for anything already leaked into
  history). Invoke when: "does this leak a secret", "am I about to hardcode a
  private value", "security review before commit", "OpSec review", "SecOps
  checklist", "portable memory hygiene", "private literal check", "check for
  forbidden identity/attribution/path fragments", or before writing any
  memory row, doc, skill, test fixture, or guard that touches sensitive
  categories.
---

# Security

One source of truth for keeping tracked content (memory, docs, skills, tests,
guards) free of concrete private/local values, while still fully documenting
*how* to detect and forbid them. Consolidates patterns that were scattered
across PT's `repo_hygiene.py`, PT's `.agent/memory/semantic/DOMAIN_KNOWLEDGE.md`,
and orama's `git-history-surgery` skill after the 2026-07-18 PT PR
#256/#258/#260 arc — where the first attempted fix for a leaked private
identity literal was itself wrong: it kept spelling the literal in the ban
rule, allowlist, tests, and docs while trying to forbid it.

## Prime invariant

Tracked policy names **categories**. It never spells the **concrete
fragment** it forbids — not in the ban rule, not in an allowlist, not in a
test fixture, not in memory. A negative rule that quotes the secret it exists
to ban is self-defeating.

Full statement, required guard shape, and acceptance criteria:
[`docs/v2/47-portable-memory-local-topology-invariant.md`](../../../../docs/v2/47-portable-memory-local-topology-invariant.md).
Read that doc before editing tracked memory, guards, skills, or multi-repo
security policy — this skill routes you there and to the other specialist
references; it does not restate their content.

## OpSec vs SecOps

Two related but distinct terms, both load-bearing in this stack:

- **OpSec (Operational Security)** — the *discipline*: what an agent does or
  doesn't do with its own output. Never grep for a forbidden literal and
  print the result. Never paste a real value into a commit message, PR body,
  board note, or shell history "just to explain what's being fixed." Never
  quote the secret inside the rule that bans it. OpSec is a behavior, checked
  every time an agent is about to write something.
- **SecOps (Security Operations)** — the *infrastructure* that enforces and
  verifies OpSec: the local-only registry loader, `repo_hygiene.py`'s
  `scan_private_verboten_literals`, the all-ref blob scanner, pre-commit
  hooks, CI gates. SecOps is tooling + process, checked by running it.

A clean SecOps scan is evidence that OpSec discipline held — but only for the
scope that scan actually covered. See "Verification gates are separate" below
before treating one clean scan as proof of another scope.

## Local-only registry pattern

Concrete forbidden identity, attribution, device, address, path, workspace,
and topology fragments live only in a local-only registry outside every git
worktree — never hardcoded in tracked files, even as a "banned example."

Reference implementation already in production (PT, reuse this shape rather
than inventing a parallel one):

- Loader: `scripts/review/repo_hygiene.py`'s `private_literal_values(root, key)`
  — reads `key=value` lines (`#` comments allowed) from a git-ignored
  `.verboten-literals.local` file at the OpenClaw workspace root, or from the
  path in `OPENCLAW_VERBOTEN_LITERALS` if set.
- Enforcement: `scan_private_verboten_literals()` (current tracked tree) and
  the all-ref blob scanner in
  [`../git-history-surgery/references/expunge-contaminated-history.md`](../git-history-surgery/references/expunge-contaminated-history.md)
  (every reachable blob, all refs) — both report category/path/count only,
  never the matched literal or matched line.
- Recommended abstract keys: `owner_gmail`, `owner_name`, `forbidden_attribution`,
  `local_path_fragment`, `local_workspace_fragment`, `verboten_path_fragment`,
  `device_or_network_fragment`. Tracked code must treat unknown keys as inert
  and must not hard-fail in CI if the registry is absent — fall back to
  generic secret/personal-path rules.

## Verification gates are separate

A pass on one gate is never evidence for another. Name the exact scope
verified, not an inferred "complete":

| Gate | What it proves | What it does NOT prove |
| --- | --- | --- |
| Current-tree scan | Tracked files at this commit are clean | History before this commit |
| Commit metadata/message scan | Author/committer/message text is clean | File contents are clean |
| PR-unique blob scan (`origin/main..HEAD`) | This branch's own contribution is clean | Inherited history from `main` |
| All-ref blob scan (`--all`) | Every reachable blob across every ref is clean | Nothing — this is the only scope that supports a repo-wide "clean" claim |

If the all-ref scan timed out, was deferred, or wasn't run, say so explicitly
and keep the gap tracked. Do not round it down to "complete."

## Decision flow

1. **About to write a memory row, doc, skill, test fixture, or guard that
   touches a sensitive category?** Name the category, load real values from
   the local-only registry, never hardcode. Use synthetic values in tests.
2. **A private/local-topology literal already landed in tracked history?**
   Do not fix it here — this is history surgery. Go to
   [`../git-history-surgery/references/expunge-contaminated-history.md`](../git-history-surgery/references/expunge-contaminated-history.md).
3. **A memory row was superseded by a cleaner-looking later entry, but the
   old row might still contain a leak?** Supersession is not sanitization —
   fix the source row (or archived candidate) directly and regenerate every
   derived/rendered view. Never assume a newer entry cleans an older one.
4. **Someone suggests "just stop recording that kind of memory" as the
   fix for a leak?** Wrong response. Sanitize the memory (write-time
   redaction, category-only wording); don't amputate it. Under-recording
   relocates the risk to institutional memory loss instead of removing it.
5. **Closing out a security/privacy session?** Scan, test, commit, push,
   fetch, verify branch state, inventory dirty worktrees — then state the
   exact gates verified (table above), not a blanket "complete."

## Non-Negotiables

- Never print a matched literal or matched line from any scanner — labels,
  paths, and counts only.
- Never paste a real forbidden value into a commit message, PR body, board
  note, memory row, or shell history, even to explain what's being fixed.
- Never treat "current-tree clean" as "history clean," or "PR-unique clean"
  as "all-ref clean." Name the scope.
- Never let "don't leak this value" collapse into "stop recording memory."
  Sanitize, don't amputate.
- Never invent a new local-only pattern-file format per incident — reuse
  `private_literal_values()` / `.verboten-literals.local` (or the equivalent
  already established in the repo you're in) so registries stay singular and
  loaders stay consistent across PT, orama-system, and future v2 repos.

## Mnemonic

**"Secure persistent memory = persistently secure memory."** Memory that
lasts across sessions is only as trustworthy as the discipline that keeps it
clean on every single write — not a one-time cleanup.

## Related skills

- [cursor-pr-body](../cursor-pr-body) — Layer 0 comment-only + operator-grant-v2 append path;
  same-user Keychain boundary and replay state machine (`reserve` → `mark-applied` → `consume`)
- [git-history-surgery](../git-history-surgery) — the specialist for anything that already leaked
  into committed history: expunge, reanchor, tree-twin, clean-replacement-PR.
  This skill is upstream of that one — use `security` to keep a leak from
  happening; use `git-history-surgery` once one already has.

## References

- [`docs/v2/47-portable-memory-local-topology-invariant.md`](../../../../docs/v2/47-portable-memory-local-topology-invariant.md) — the prime invariant, full guard shape, and acceptance criteria
- [`docs/plans/2026-08-02-pr-body-grant-security-remediation.md`](../../../../docs/plans/2026-08-02-pr-body-grant-security-remediation.md) — PR-body operator grant v2 (HMAC capability, not human identity)
- [`references/pr-body-human-grant-security-gap-research.md`](../../references/pr-body-human-grant-security-gap-research.md) — TTY/HITL gap research
- [`../cursor-pr-body/SKILL.md`](../cursor-pr-body/SKILL.md) — operator + agent append workflow
- [`docs/v2/23-security-preconditions.md`](../../../../docs/v2/23-security-preconditions.md) — v2 security gate preconditions
- [`docs/v2/24-security-first-platform.md`](../../../../docs/v2/24-security-first-platform.md) — security-first platform design baseline
- [`docs/v2/32-agentic-security-controls.md`](../../../../docs/v2/32-agentic-security-controls.md) — authentication, LAN-bind hardening, and agentic security controls
- [`../git-history-surgery/references/expunge-contaminated-history.md`](../git-history-surgery/references/expunge-contaminated-history.md) — remediation once a leak already landed in history, plus the runnable all-ref blob scanner
- PT companion: [`scripts/review/repo_hygiene.py`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/scripts/review/repo_hygiene.py) (the reference `private_literal_values()` loader implementation) and [`.agent/memory/semantic/DOMAIN_KNOWLEDGE.md`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/.agent/memory/semantic/DOMAIN_KNOWLEDGE.md) § Cybersecurity / OpSec / SecOps
