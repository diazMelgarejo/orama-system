# Hermes Universal Invocation Protocol

Cross-harness contract for `hermes-harness` operator dispatch. Harmonized with
[`openclaw-skills/references/universal-skill-protocol.md`](../../openclaw-skills/references/universal-skill-protocol.md)
(OpenClaw fabric skills use `openclaw_home`; Hermes operator skills use
`orama_system_root`).

Committed docs use **env placeholders only**. Runners expand to absolute paths
at runtime before file I/O. Never commit workstation absolute paths.

## Layer model (OSI-style)

| Layer | Name | Audience | Carries |
| ------- | ------ | ---------- | --------- |
| L3 | Intent | Human / orchestrator | Core trio + `harness` |
| L2 | Dispatch | Hermes harness | L3 + path placeholders + `executor_id` + optional `transport` |
| L1 | Transport | Partner CLI (internal) | Codex/AGY flags — not in committed skill docs |
| L0 | Result | All auditors | Canonical result envelope (this document) |

**v1 `transport` object (L2, audit/replay):** opaque dispatch intent for OTel and
Periscope. v2 may expand schema in `/docs/v2`.

```json
"transport": {
  "partner": "codex",
  "profile": "fanout"
}
```

## Layer dictionary (do not conflate)

These types serve different layers and must not be merged into one schema:

| Name | Layer | Owner | Purpose |
| ------ | ------- | ------- | --------- |
| **Hermes result** (this doc) | L0 | orama-system | Command/skill stdout contract: `status`, `data`, `error`, … |
| **JobSpec** / **JobStatus** | Control plane | Perpetua-Tools `/v1/jobs` | Durable job submission and lifecycle — not skill stdout |
| **TaskEnvelope** | Worker wire | Perpetua-Tools `contracts.py` | PT-owned worker dispatch contract — hot path uses JobSpec only |
| **SkillEnvelope** | L3 intent | Skill registry | Invocation intent (`skill_id`, `args`, `agent_id`) — not a result |

See also: [`docs/update-docs/2026-08-06-job-task-envelope-evolution.md`](../../../../../docs/update-docs/2026-08-06-job-task-envelope-evolution.md).

## Core envelope (required)

```json
{
  "skill_id": "pt-orama-council",
  "args": {},
  "agent_id": "hermes"
}
```

| Field | Required | Rule |
| ------- | ---------- | ------ |
| `skill_id` | yes | Registry slug; resolve via §Subskill Registry in `SKILL.md` |
| `args` | yes | Flat JSON object; `{}` when none |
| `agent_id` | yes | Audit owner: `hermes`, `claude`, `codex`, `openclaw`, `agy`, `orchestrator`, `relay-cursor` |
| `executor_id` | when delegating | Runner (`codex`, `agy`, `hermes`); defaults to `agent_id` |

## Harness extensions (optional)

| Field | When | Committed placeholder | Runtime expansion |
| ------- | ------ | ---------------------- | ------------------- |
| `harness` | Hermes dispatch | `"hermes"` | Echo only |
| `orama_system_root` | Operator skills | `"$ORAMA_SYSTEM_PATH"` | `git rev-parse --show-toplevel` or env |
| `openclaw_home` | Fabric skills | `"$OPENCLAW_HOME"` | User default `~/.openclaw` |
| `canonical_skill_root` | Path join | `"bin/orama-system/skills"` | Join with expanded root |
| `transport` | Partner dispatch | `{ "partner": "codex", "profile": "fanout" }` | Runner maps to CLI |

`repo_root` is a deprecated alias for `orama_system_root`.

## Core result (canonical — single source of truth)

All Hermes shell commands with `--json` emit this shape. Adapters normalize
legacy inbound shapes to this envelope before consumers read them.

```json
{
  "status": "ok",
  "skill_id": "hermes-spawn",
  "agent_id": "hermes",
  "executor_id": "hermes",
  "command": "hermes-spawn",
  "action": "status",
  "data": {},
  "files_modified": [],
  "follow_up_actions": [],
  "warnings": [],
  "error": null
}
```

| Field | Required | Rule |
| ------- | ---------- | ------ |
| `status` | yes | `ok`, `needs_input`, `partial`, `error`, or `blocked` |
| `skill_id` | when known | Registry slug for the emitting command |
| `agent_id` | when known | Audit owner |
| `executor_id` | when known | Runner that executed the command |
| `command` | when known | Thin-wrapper command name (e.g. `hermes-spawn`) |
| `action` | when known | Sub-action (e.g. `start`, `stop`, `status`) |
| `data` | yes | Command-specific payload; `{}` when none |
| `files_modified` | yes | Always an array; empty for read-only checks |
| `follow_up_actions` | yes | Always an array; required (non-empty) when `status` is `partial`, `needs_input`, `blocked`, or `error` |
| `warnings` | yes | Always an array; non-fatal information |
| `error` | yes | `null` on success, or `{ "code": "...", "message": "..." }` |

| `status` | Meaning |
| ---------- | --------- |
| `ok` | Completed |
| `needs_input` | Missing required input; no unsafe change |
| `partial` | Some work done; follow-up required |
| `error` | Failed; include safe `follow_up_actions` |
| `blocked` | Hermes alias for `needs_input` when preconditions fail |

Rules:

1. `status` is authoritative. The legacy `ok: true|false` boolean is compatibility
   input only and must not be used by new callers.
2. `warnings` contains non-fatal information. Distrust the result only when
   `status` is not `ok` or `error` is non-null.
3. `error.message` states the problem, cause, and next safe action without secrets
   or workstation paths.
4. Health reports put subsystem results under `data.subsystems`.
5. Canary probes keep `PASS|FAIL|UNAVAILABLE|SKIPPED` inside `data.canaries[]`.

## Compatibility mapping (four existing shapes)

| Existing shape | Reconciliation |
| --- | --- |
| Hermes protocol `{status, files_modified, follow_up_actions}` | Canonical baseline; add optional metadata and `error: null` on success. |
| OpenClaw `{status, data}` / `{status, message}` | Map `data` to `data`; map `message` to `error.message`; derive an error code from the command when absent. |
| Draft `{ok, command, action, data, warnings, error}` | Replace `ok` with canonical `status` (`true`→`ok`, `false`→`error`); retain other fields as optional metadata. |
| Canary `{canaries: [{status: PASS\|FAIL\|UNAVAILABLE\|SKIPPED}]}` | Keep canary vocabulary inside `data.canaries`; map required FAIL/UNAVAILABLE to top-level `error`/`blocked`, optional failures to `partial`, SKIPPED to a warning plus `follow_up_actions` when required. |

Canary records keep `name`, `status`, `detail`, and `required`. They do not
become a second top-level protocol.

## Bidirectional adapter mapping

Emitters always produce the canonical shape. Inbound legacy payloads normalize
before consumption.

| Direction | Source field | Canonical field | Rule |
| ----------- | -------------- | ----------------- | ------ |
| → canonical | `ok: true` | `status: "ok"` | Boolean success |
| → canonical | `ok: false` | `status: "error"` | Boolean failure |
| → canonical | `message` | `error.message` or `data`/`warnings` | Map to `error` only on non-success; preserve successful messages |
| → canonical | `data` (OpenClaw) | `data` | Passthrough object |
| → canonical | `canaries[]` | `data.canaries[]` | Nested; derive top-level `status` per canary rules |
| → canonical | (missing) | `files_modified: []` | Default empty array |
| → canonical | (missing) | `follow_up_actions: []` | Default empty array |
| → canonical | (missing) | `warnings: []` | Default empty array |
| → canonical | (missing) | `error: null` | On success |
| ← legacy | `status` | `status` | Passthrough enum |
| ← legacy | `data` | `data` | Passthrough |
| ← legacy | `error` | `error` | Passthrough or omit when null |
| ← OpenClaw | `status` + `data` | `{status, data}` | Strip Hermes-only fields when caller expects OpenClaw |
| ← canary-only | `data.canaries` | `{canaries: [...]}` | Flatten for legacy canary consumers |

### Adapter pseudocode (normalize inbound)

```text
function normalize_result(raw, command, action):
  if raw has "ok" and not raw has "status":
    raw.status = raw.ok ? "ok" : "error"
  if raw has "message" and not raw.error:
    if raw.status is non-success (not "ok"):
      raw.error = {code: command + "_error", message: raw.message}
    else:
      # Preserve successful legacy messages outside error
      raw.data = raw.data ?? {}
      raw.data.message = raw.data.message ?? raw.message
      raw.warnings = raw.warnings ?? []
      if raw.message not in raw.warnings:
        raw.warnings.append(raw.message)
  if raw has "canaries":
    raw.data = raw.data ?? {}
    existing = raw.data.canaries ?? []
    top_level = raw.canaries ?? []
    raw.data.canaries = existing.concat(top_level)
    delete raw.canaries
  raw.files_modified = raw.files_modified ?? []
  raw.follow_up_actions = raw.follow_up_actions ?? []
  raw.warnings = raw.warnings ?? []
  if raw.status == "ok" and raw.error is missing:
    raw.error = null
  raw.command = raw.command ?? command
  raw.action = raw.action ?? action
  return raw
```

## Hermes extensions (optional, legacy)

`harness`, `output`, `errors`, `checks` — prefer `warnings` and `error` in new code.

Path casing mismatch on expansion → `warnings[]`, not `blocked` (Windows-safe).

## Optional extensions

`pt-orama-lesson-mining` is an **optional** command card. It is not installed by
default, is not required for bootstrap or partner dispatch, and does not introduce a
Perpetua-Tools dependency. Install only with
`install_hermes_thin_skills.py --include-optional`.

## Path expansion (runtime only)

1. Read placeholder from envelope (`$ORAMA_SYSTEM_PATH`, `$OPENCLAW_HOME`).
2. Expand via env or `git rev-parse --show-toplevel`.
3. Join `canonical_skill_root` + registry-relative path.
4. `git fetch origin --prune`; `git pull --ff-only` when clean and tracking.

## Chaining

Child calls inherit parent-expanded paths. Cross-harness orchestrators may carry
both `orama_system_root` and `openclaw_home`. OpenClaw fabric skills must use
`openclaw-skills` protocol, not Hermes inline procedures.
