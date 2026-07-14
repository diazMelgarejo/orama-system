# Review Remediation Crosslinks

This index tells future skills where to link when they need branch-local, pattern-level review remediation guidance.

Canonical card:

- [`branch-local-pattern-remediation.md`](branch-local-pattern-remediation.md)

## Recommended skill cross-reference targets

| Skill / surface | Relevant section to link |
|---|---|
| `oramasys-method` | Step 2 / integrative PR merge / verify-before-done sections. |
| `code-review` | Review findings triage and “do not checklist-patch” guidance. |
| `git-history-surgery` | Branch locality gate, reset-vs-revert discipline, and common-ancestor checks. |
| `gstack` | Multi-agent handoff and final verification gates. |
| `shell-hygiene` | Frugal inspection, explicit target branch, and avoiding stale full-file rewrites. |
| `agent-methodology` | Context immersion and multi-agent remediation kickoff. |
| `autoresearch` / fan-out worker skills | Use only after the owning branch and file lane are assigned; do not make autonomous branch/global changes. |

## Copy-paste link

```markdown
For multi-comment PR remediation, follow [Branch-Local Pattern Remediation](../../references/branch-local-pattern-remediation.md): work on the requested branch only, cluster findings by invariant, and fix the owning abstraction once.
```

## Why this exists

A CodeRabbit remediation pass on Perpetua-Tools PR #206 showed that isolated one-line review fixes cause conflicts and missed invariants. The successful pattern was to cluster similar comments into shared failure classes, inspect each owning file once, and repair the owning abstraction with regression coverage.
