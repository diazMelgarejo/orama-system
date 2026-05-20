# Agent Compatibility Matrix for openclaw-skills

This reference explains how each agent runtime discovers and executes the OpenClaw skill set.
It is intended for operators wiring multi-agent systems across mixed toolchains.

## Scope
- Skill package: `openclaw-skills`
- Master entrypoint: `SKILL.md`
- Subskills: `skills/openclaw-*/SKILL.md`
- Template assets: `templates/*.tpl`
- Reference docs: `references/*.md`

## Common Skill Contract
All runtimes should follow the same high-level flow:
1. Discover skill metadata.
2. Load `SKILL.md` and resolve the requested subskill.
3. Execute documented procedure.
4. Return Output Contract JSON.

## Claude
### Discovery
Claude uses the Skill tool with local skill roots and plugin-provided slash commands.

### Invocation
- Slash commands such as `/openclaw-new-agent` and `/openclaw-add-script` are exposed by plugin skill registration.
- A `.claude/skills/` symlink allows file-based fallback discovery when plugin metadata is unavailable.

### Notes
Claude behavior is highly deterministic when procedures in each `SKILL.md` are explicit.

## Hermes
### Discovery
Hermes performs native MCP discovery using the skill manifest exposed by the host.

### Invocation
Hermes maps command intent to manifest entries, then loads skill instructions and required assets.

### Notes
Manifest integrity is critical; broken metadata prevents command routing.

## Gemini
### Discovery
Gemini discovers skills via `gemini-mcp-tool` integration points.

### Invocation
Gemini activates skills through `activate_skill` API calls, passing arguments as structured JSON.

### Notes
Argument validation should happen before execution to avoid partial side effects.

## Codex
### Discovery
Codex uses `ai-cli-mcp` plus file-based skill discovery rooted in the workspace `workFolder`.

### Invocation
Codex resolves target skill files, reads `SKILL.md`, and runs the defined procedure with local tools.

### Notes
Codex can operate without remote manifests if local files are complete.

## Cursor
### Discovery
Cursor can consume skill rules through a `.cursor/rules/` symlink pointing to `SKILL.md`.

### Invocation
Prompted commands are interpreted against loaded rule files and local repository context.

### Notes
Ensure symlink targets are stable across machine restarts.

## WindSurf
### Discovery
WindSurf reads `.windsurfrules` for skill directives and behavioral policy.

### Invocation
When a directive matches an OpenClaw command, WindSurf loads corresponding instructions.

### Notes
Keep `.windsurfrules` minimal and specific to avoid ambiguous matches.

## Antigravity
### Discovery
Antigravity uses a `skill-load` directive in configuration.

### Invocation
Configured directives map to local skill paths and are loaded at session initialization.

### Notes
Invalid paths should hard-fail early to prevent silent fallback.

## OpenCode
### Discovery
OpenCode discovers skills from a manifest entry in `opencode.json`.

### Invocation
OpenCode resolves manifest entries to skill files, then executes associated procedures.

### Notes
Version the manifest alongside skill updates to prevent drift.

## 8gent.dev
### Discovery
8gent.dev discovers OpenClaw skills through HTTP MCP endpoint registration.

### Invocation
The runtime requests skill metadata from the MCP endpoint, then invokes selected skills remotely.

### Notes
Network reliability and endpoint auth are prerequisites for stable execution.

## Operational Recommendations
- Keep `SKILL.md` as the canonical source of procedure truth.
- Keep templates and references co-located with skills.
- Validate Output Contract JSON shape in CI.
- Pin manifest versions where supported.
- Test one happy path and one failure path per runtime.

## Compatibility Checklist
- Discovery path configured.
- Skill files reachable.
- Command routing verified.
- Structured output validated.
- Error propagation confirmed.
- Recursion controls tested.

## Change Management
When updating skills:
1. Update templates first.
2. Update references second.
3. Re-test runtime-specific discovery.
4. Publish migration notes for operators.
