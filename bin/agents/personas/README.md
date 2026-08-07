# Raft persona catalog (canonical staging copy)

Tracked copy of EDITED-03 → MERGE-10 persona YAML. Live hub mirror:
`${HOME}/.alphaclaw/.openclaw/workspace/docs/oramasys/personas/`

**SSoT for git/install:** this directory. Hub copies are operator-runtime mirrors —
refresh from here after `git pull`.

| Persona file | openclaw_id | Display | Staging folder |
| -------------- | ------------- | --------- | ---------------- |
| `cole.yaml` | `cole-agent` | Cole | `cole/` |
| `hermes.yaml` | `hermes-agent` | Hermes | `hermes-monitor/` |
| `sage.yaml` | `gemini-coder` | Sage | `sage/` |
| `penn.yaml` | `coder` | Penn (alias on Rourke) | `executor/` |
| `arthur.yaml` | `mac-researcher` | Arthur | `mac-researcher/` |
| `nova.yaml` | `kimi-agent` | Nova | `nova/` |
| `rex.yaml` | `grok-agent` | Rex | `rex/` |
| `relay-cursor.yaml` | `relay-cursor` | Relay Cursor Agent | `relay-cursor/` |

Pipeline agents (Cass, Aria, Sena, Rourke, Vera, Crystal, Glen) use `bin/agents/*/SOUL.md` + hub `REGISTRY.yml`.

Binding table: [`../REGISTRY.yml`](../REGISTRY.yml)
