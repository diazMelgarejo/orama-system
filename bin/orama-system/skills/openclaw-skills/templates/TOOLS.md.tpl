# TOOLS

## Available tools
{{tools_list}}

Tool usage principles:
- Prefer deterministic tools for deterministic workflows.
- Use networked tools only when local context is insufficient.
- Capture command intent before execution.
- Keep side effects scoped and reviewable.

## Scripts documentation
{{scripts_list}}

Script policy:
- Scripts should return machine-readable JSON to stdout.
- Human-readable logs should go to stderr.
- Scripts must fail fast on invalid inputs.
- Scripts should be idempotent when practical.

Operational note:
If a script and a tool overlap, prefer the script when behavior needs to stay stable.
