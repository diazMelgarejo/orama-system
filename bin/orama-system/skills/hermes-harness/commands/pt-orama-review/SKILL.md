---
name: pt-orama-review
description: >-
  Review PT-orama plans or deliveries with findings-first critique and
  harness-readiness checks.
version: 1.1.0.0
license: Apache 2.0
compatibility: hermes, codex, windows
parent_skill: hermes-harness
triggers:
  - pt-orama-review
  - hermes review
  - findings-first harness review
allowed-tools: bash, file-operations
---

# PT-orama Review

Use this command to review a PT-orama plan, branch, diff, or handoff package.
Be strict and evidence-first.

## Review Priorities

1. P0/P1 defects, security risks, bad assumptions, and broken verification.
2. Duplicated canonical knowledge that should remain in `orama-system`.
3. False claims about installed tools, models, branches, commits, or PRs.
4. Windows readiness gaps: Hermes launcher path, `HERMES_GIT_BASH_PATH`,
   LM Studio chat canary, AGY install, and AGY visible-output canary.
5. Missing tests, stale links, mojibake, or absolute workstation paths in
   tracked content.

## Required Shape

```text
FINDINGS:
- [severity] file/path or claim: issue, evidence, fix

OPEN QUESTIONS:

VERIFICATION NEEDED:

APPROVAL:
CLEAN or NEEDS_REVISION
```

Do not rewrite the user's work unless explicitly asked. Do not commit.
