# orama-system — Codex Agent Guide

Skills are auto-loaded from `.agents/skills/`.

## ultrathink System Skill

- Path: `.agents/skills/orama-system/SKILL.md`
- Mother skill: `bin/orama-system/SKILL.md` (v1.1.0.0)
- AFRP gate: `bin/orama-system/afrp/SKILL.md`
- CIDF: `bin/orama-system/cidf/SKILL.md`

## Agent Roles

See `.codex/agents/` for role configs (explorer, reviewer, docs-researcher).

## Coordination Provenance

For any handoff, board publication, review, or takeover, follow
`bin/orama-system/skills/gossip-bus/references/author-actor-takeover-policy.md`.
Record the original author separately from the current actor; report identity
verification honestly; and do not claim endorsement, authorization, or
completion beyond independently checked evidence.

## API

`POST /ultrathink` on port 8001 — see `api_server.py`.
