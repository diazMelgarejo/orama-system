# ECC Cross-Harness Skill Authoring

Use this reference when authoring an ECC/PT-orama skill that should be consumed
by multiple harnesses such as Codex, Hermes, Claude Code, OpenCode, Cursor,
Antigravity, or local model runners.

## Principle

Author the reusable workflow once in the repo skill tree, then adapt only
loading, event shape, command routing, or runtime permissions at each harness
edge. If a workflow requires editing three harness copies, the shared source is
in the wrong place.

Hermes is an operator shell that consumes ECC/orama assets; it is not the
canonical public runtime for those assets.

## ECC Shape

ECC-style skills are flat:

```text
skills/<skill-name>/SKILL.md
```

Recommended frontmatter:

```yaml
---
name: your-skill-name
description: Use when <trigger>. <one-line behavior>.
metadata:
  origin: ECC
  harnesses: [codex, hermes, antigravity, lmstudio, claude-code, opencode, cursor]
  tags: [tag1, tag2, tag3]
  related_skills: [council, hermes-imports, openclaw-persona-forge]
---
```

Do not mix this with Hermes in-repo frontmatter such as `metadata.hermes` or
category-nested Hermes skill paths.

## Harness Adapter Checklist

| Harness | Adapter rule |
|---|---|
| Codex | Keep local Codex skill installs as thin wrappers pointing to the canonical repo card |
| Hermes | Install or generate a thin local Hermes wrapper; do not paste canonical bodies into Hermes local state |
| Claude Code | Use project/plugin surfaces and hooks; keep reusable behavior in `skills/` |
| OpenCode | Adapt package/plugin/event handling only |
| Cursor | Translate to Cursor rule/hook layout without forking the workflow body |
| Local models | Verify chat-completions canary before selecting a model; use exact provider IDs |

## Authoring Workflow

1. Check existing skill families before adding a sibling.
2. Write the canonical skill under `skills/<skill-name>/SKILL.md`.
3. Add only harness-edge adapters needed to load or route the skill.
4. Keep secrets, OAuth state, personal memory, provider configs, and raw local
   runtime exports outside tracked files.
5. Verify at least one canonical read path and one harness adapter path.
6. Open a PR against the repo that owns the canonical skill.

## Windows Notes

- Prefer PowerShell or Python writes with explicit UTF-8.
- Avoid MSYS path doubling by using native Windows paths in write operations or
  verifying the final destination after any shell-based copy.
- Git Bash is useful for POSIX-style CLI tools, but tracked docs should use
  relative repo paths, GitHub URLs, or environment-variable placeholders.

## Do Not Import

- Opaque third-party runtime trees just because a private workflow used them.
- Raw Hermes hub cache, usage telemetry, lock files, or provider configuration.
- Invented local model names. Use live provider IDs and require a fast
  chat-completions canary before dispatch.
