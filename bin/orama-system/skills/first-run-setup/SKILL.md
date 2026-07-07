---
name: first-run-setup
description: >-
  Idempotent first-run bootstrap for the orama-system toolchain: Node, Python 3.13,
  Ollama models, code-review-graph, gbrain, unified embeddings, Claude Code profiles,
  and PreCompact hook.
when_to_use: >-
  Activates when setting up a new machine, after fresh clone, or when the user asks
  for first-run install, bootstrap, or §0 checklist.
disable-model-invocation: true
effort: medium
argument-hint: "[status|install|mcp]"
arguments: [action]
paths:
  - "bin/orama-system/scripts/**"
  - "scripts/**"
---

# First-Run Setup

> **Canonical:** [`../../references/first-run-install.md`](../../references/first-run-install.md)
> **Script:** [`../../scripts/first-run-install.sh`](../../scripts/first-run-install.sh)

## When to use

- New machine or fresh OpenClaw checkout
- User asks to "run first-run", "bootstrap orama", or "install §0"
- Before heavy agentic work when `~/.orama-system/first-run.done` is missing

## Workflow

1. **Status** (fast, read-only):

   ```bash
   bash bin/orama-system/scripts/first-run-install.sh status
   ```

2. **Install** (idempotent install / validate):

   ```bash
   bash bin/orama-system/scripts/first-run-install.sh install
   ```

3. **MCP workers** (separate — not part of first-run.done):

   ```bash
   bash bin/orama-system/scripts/install-mcp-stack.sh
   ```

4. Confirm marker: `~/.orama-system/first-run.done`

## Flags

| Flag | Effect |
|------|--------|
| `--dry-run` | Print actions without executing writes |
| `--force` | Re-validate every component; repair config only — never reinstall satisfied binaries/models |

## Error Resilience

For gstack/gbrain/CRG error handling during bootstrap, source the shared
ADR-045 safety framework:

```bash
source bin/orama-system/scripts/lib/gstack-gbrain-crg-safe.sh
```

Run `_detect_errors` before first external gbrain or CRG call. Use
`_retry_with_backoff` for idempotent bootstrap steps. Report failures with
`_err_actionable` for clear diagnostics.

See: `docs/adr/ADR-045-gstack-gbrain-crg-error-resilience.md`

## Environment

| Variable | Purpose |
| ---------- | --------- |
| `OPENCLAW_ROOT` | OpenClaw tree (auto-detected if unset) |
| `NVM_NODE_BIN` | Preferred Node bin dir (default `~/.nvm/versions/node/v22.22.2/bin`) |
| `ORAMA_STATE_DIR` | Override `~/.orama-system` state directory |

## OmniRoute

Optional appendix only — first-run **probes** OmniRoute when `OMNIROUTE_TOKEN` is set; never fails closed. Do not install OmniRoute from this skill.

## See also

- [`../../../docs/how-to/first-run-and-code-review.md`](../../../docs/how-to/first-run-and-code-review.md) — full E2E path through MCP stack and first review
- [`../../mcp-install/SKILL.md`](../../mcp-install/SKILL.md) — ai-cli-mcp, optional Gemini
- [`../code-review/SKILL.md`](../code-review/SKILL.md) — graph-first review after CRG is up