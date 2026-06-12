---
name: orama-system
description: >-
  Elegant problem-solving methodology with 5-stage process, AFRP pre-router gate,
  CIDF v1.2 content insertion framework, and 7-agent execution network. Activates
  for architectural thinking, systematic verification, content insertion decisions,
  complex multi-step tasks, code quality reviews, and self-improvement workflows.
  Triggers on: "ultrathink", "think deeply", "5-stage", "systematic approach",
  "elegant solution", "verify before done", "content insertion", "AFRP", "CIDF".
  Treat legacy "ultrathink" prompts as oramasys invocations.
version: 0.9.9.7
license: Apache 2.0
compatibility: claude-code, claude-desktop
allowed-tools: bash, file-operations, web-search, subagent-creation, mcp-oramasys
sub_skills:
  - path: afrp/SKILL.md
    trigger: "Query is non-trivial, audience-dependent, or open-ended (Type B/C/D)"
  - path: cidf/SKILL.md
    trigger: "Any content insertion, file write, paste, upload, or scripted output"
---

<!-- THIN-WRAPPER: canonical skill lives in bin/orama-system -->

# orama-system (thin wrapper)

The canonical, permanent implementation lives in the repo at
`../../../bin/orama-system/` (under `bin/orama-system/`). **Read it before proceeding** —
this wrapper only carries discovery metadata; the substance is canonical there.

Original pre-wrapper body preserved at `SKILL.md.premerge---stamp.bak`.
