# OpenClaw pattern graft registry (living)

> **Wave 0** — taxonomy + lane tags. Wave 1+ JSON envelope and lifecycle commands
> tracked here additively. Plan:
> `docs/plans/2026-08-03-hermes-openclaw-graft-audit-plan.md`

## Lane key

| Lane | Runtime | orama examples |
| ---- | ------- | -------------- |
| **L-H1** | Native `delegate_task` children | Interactive Hermes only (future `hermes-native-delegate` card) |
| **L-PT** | PT `spawn_hermes_agent()` / `hermes_harness.py` | `hermes-orama`, `hermes-delegate`, `hermes-spawn` |
| **L-Fleet** | `coord_pulse` → `cursor-agent` | Win coder/autoresearcher queues; `subagent/win-*` git branches |

Canonical detail: [`hermes-dispatch-taxonomy.md`](hermes-dispatch-taxonomy.md)

## Graft matrix (Wave 0 locked)

| OpenClaw pattern | Target lane | Action | Status |
| ---------------- | ----------- | ------ | ------ |
| `recursive-spawn-protocol` → `hermes-delegate` | L-PT | **SKIP** until rename (`hermes-pt-parallel`) | Wave 0 |
| Universal JSON envelope | L-PT + L-Fleet shells | **ADOPT** | Wave 1 |
| `openclaw-status` pre-flight | L-PT + L-Fleet | **ADAPT** → `hermes-status` | Wave 2 |
| `openclaw-restart` sequence | L-Fleet Task Scheduler | **ADAPT** (no launchd on Win) | Wave 2 |
| `openclaw-dream-setup` | L-PT lesson mining | **MERGE** | Wave 3 |
| Agent directive templates | `bin/agents` staging | **VERIFY** (already absorbed) | Done |
| Path prose `$OPENCLAW_ROOT` | All harness refs | **REJECT** — use path doctrine | Wave 0 |

## SKILL wording (Wave 0)

| Command | Lane tag applied | NOT `delegate_task` callout |
| ------- | ---------------- | --------------------------- |
| `hermes-delegate` | L-PT | Yes |
| `hermes-orama` | L-PT | Yes |
| `hermes-spawn` | L-PT | Yes |
| Root `hermes-harness/SKILL.md` | All three lanes | Yes |
