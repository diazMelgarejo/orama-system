# Hermes Universal Invocation Protocol

Cross-harness contract for `hermes-harness` operator dispatch. Harmonized with
[`openclaw-skills/references/universal-skill-protocol.md`](../../openclaw-skills/references/universal-skill-protocol.md)
(OpenClaw fabric skills use `openclaw_home`; Hermes operator skills use
`orama_system_root`).

Committed docs use **env placeholders only**. Runners expand to absolute paths
at runtime before file I/O. Never commit workstation absolute paths.

## Layer model (OSI-style)

| Layer | Name | Audience | Carries |
|-------|------|----------|---------|
| L3 | Intent | Human / orchestrator | Core trio + `harness` |
| L2 | Dispatch | Hermes harness | L3 + path placeholders + `executor_id` + optional `transport` |
| L1 | Transport | Partner CLI (internal) | Codex/AGY flags — not in committed skill docs |
| L0 | Result | All auditors | Core result superset |

**v1 `transport` object (L2, audit/replay):** opaque dispatch intent for OTel and
Periscope. v2 may expand schema in `/docs/v2`.

```json
"transport": {
  "partner": "codex",
  "profile": "fanout"
}
```

## Core envelope (required)

```json
{
  "skill_id": "pt-orama-council",
  "args": {},
  "agent_id": "hermes"
}
```

| Field | Required | Rule |
|-------|----------|------|
| `skill_id` | yes | Registry slug; resolve via §Subskill Registry in `SKILL.md` |
| `args` | yes | Flat JSON object; `{}` when none |
| `agent_id` | yes | Audit owner: `hermes`, `claude`, `codex`, `openclaw`, `agy`, `orchestrator` |
| `executor_id` | when delegating | Runner (`codex`, `agy`, `hermes`); defaults to `agent_id` |

## Harness extensions (optional)

| Field | When | Committed placeholder | Runtime expansion |
|-------|------|----------------------|-------------------|
| `harness` | Hermes dispatch | `"hermes"` | Echo only |
| `orama_system_root` | Operator skills | `"$ORAMA_SYSTEM_PATH"` | `git rev-parse --show-toplevel` or env |
| `openclaw_home` | Fabric skills | `"$OPENCLAW_HOME"` | User default `~/.openclaw` |
| `canonical_skill_root` | Path join | `"bin/orama-system/skills"` | Join with expanded root |
| `transport` | Partner dispatch | `{ "partner": "codex", "profile": "fanout" }` | Runner maps to CLI |

`repo_root` is a deprecated alias for `orama_system_root`.

## Core result (required — OpenClaw-compatible)

```json
{
  "status": "ok",
  "files_modified": [],
  "follow_up_actions": []
}
```

| `status` | Meaning |
|----------|---------|
| `ok` | Completed |
| `needs_input` | Missing required input; no unsafe change |
| `partial` | Some work done; follow-up required |
| `error` | Failed; include safe `follow_up_actions` |
| `blocked` | Hermes alias for `needs_input` when preconditions fail |

## Hermes extensions (optional)

`harness`, `skill_id`, `agent_id`, `executor_id`, `output`, `warnings`, `errors`, `checks`

Path casing mismatch on expansion → `warnings[]`, not `blocked` (Windows-safe).

## Path expansion (runtime only)

1. Read placeholder from envelope (`$ORAMA_SYSTEM_PATH`, `$OPENCLAW_HOME`).
2. Expand via env or `git rev-parse --show-toplevel`.
3. Join `canonical_skill_root` + registry-relative path.
4. `git fetch origin --prune`; `git pull --ff-only` when clean and tracking.

## Chaining

Child calls inherit parent-expanded paths. Cross-harness orchestrators may carry
both `orama_system_root` and `openclaw_home`. OpenClaw fabric skills must use
`openclaw-skills` protocol, not Hermes inline procedures.
