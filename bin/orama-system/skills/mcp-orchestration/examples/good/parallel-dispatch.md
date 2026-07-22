# Golden Path: ai-cli-mcp Parallel Dispatch

> Extracted from `mcp-orchestration/SKILL.md` §5 during the 2026-07-22
> skill-trimming pass.

```text
Use ai-cli-mcp to run three workers in parallel:

1. model=sonnet
   workFolder=/absolute/path/project
   prompt="Review src/backend for risky refactors. Return findings only."

2. model=gpt-5.5
   workFolder=/absolute/path/project
   prompt="Write test suggestions for src/frontend. Do not edit files."

3. model=openrouter/nvidia/nemotron-3-super-120b-a12b:free
   workFolder=/absolute/path/project
   prompt="Read the repo and find stale docs. Return file list."

Then wait for all PIDs.
Merge outputs.
Do not modify files until I approve.
```

Why this is the golden shape: absolute `workFolder` on every worker, each
prompt scoped to read-only or explicitly-bounded output (no worker is told
to edit/commit), and an explicit human-approval gate before any file
changes land — matching `references/gemini-and-ai-cli-mcp-setup.md`'s
Worker Safety rules and `SKILL.md` §5 Rule 4.
