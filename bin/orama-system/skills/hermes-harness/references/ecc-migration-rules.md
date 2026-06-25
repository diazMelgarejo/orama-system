# ECC Migration Rules

Distilled from [`ecc-hermes-cross-harness.md`](ecc-hermes-cross-harness.md)
§ "Migration Decision Map" for use when triaging Hermes/OpenClaw artifacts.

## Decision Map

Treat any Hermes or OpenClaw artifact as a source. Distill it into the smallest
safe PT-orama/ECC surface:

| Source artifact | Durable target |
|---|---|
| Reusable workflow knowledge | **Skill** (`bin/orama-system/skills/<slug>/SKILL.md`) |
| Procedural action | **Command or hook** (`commands/<slug>/SKILL.md`) |
| Runtime/session routing | **Adapter or control-plane issue** |
| Generic setup instructions | **Doc or example** (`docs/` or `references/`) |
| Private memory, tokens, account state | **Do not ship** |

## Triage Questions (run for every candidate artifact)

1. Is it reusable across operators, or personal to one workspace?
2. Is the asset mainly knowledge, procedure, or runtime behavior?
3. Should it become a skill, command, hook, doc/example, or issue?
4. Does publishing it leak secrets, private datasets, local paths, or personal state?

## Migration Checklist

- [ ] Artifact triaged to one of: skill / command / doc / do-not-ship
- [ ] No workstation paths in tracked files — use env vars
- [ ] No credentials, OAuth tokens, or account state included
- [ ] Redirect stub created for absorbed entry point (see [`../perpetua-hardware/SKILL.md`](../perpetua-hardware/SKILL.md) as example)
- [ ] New file referenced from `hermes-harness/SKILL.md § References` (if skill/command)
- [ ] Verification step documented

## Redirect Stub Format

When an old entry point is absorbed:

```markdown
---
name: <slug>
description: >-
  REDIRECT → <target>. [What was absorbed and where it went].
---

# <Title>

> **Redirected:** [description] — see [`../<target>/SKILL.md`](../<target>/SKILL.md).
> This stub has no procedure.
```

No procedure, no script path, no secret, no machine path in a redirect stub.
