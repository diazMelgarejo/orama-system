---
name: shell-hygiene
description: "Safe shell command execution for agents in this environment. Covers two enforced gotchas: (1) sleep N && <command> chains are blocked — wait on background processes, file growth, or conditions with Monitor until-loops / run_in_background…"
---

<!-- THIN-WRAPPER: canonical skill lives in orama-system/bin/orama-system -->

# shell-hygiene (thin wrapper)

Canonical, permanent implementation: `../../../bin/orama-system/skills/shell-hygiene/`.
**Read it before proceeding** — this wrapper only carries discovery metadata.

Pre-wrapper body preserved at `SKILL.md.premerge-20260628.bak`.
