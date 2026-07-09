# GLM52 Clean Remediation Replay Record

Date: 2026-07-09

## Scope

This branch was created from current `main` to replay only GLM52 fallback remediation into a clean, separate PR.

## Backup policy

Do not commit credential-bearing backup copies. This record preserves only sanitized path and blob metadata from the clean branch before replacement.

## Pre-replacement inventory

| Path | State on clean main | Pre-replacement blob SHA |
|---|---|---|
| `skills/glm52-fallback/SKILL.md` | absent | n/a |
| `skills/glm52-fallback/setup-glm52.sh` | absent | n/a |
| `bin/orama-system/skills/cline-openclaw-agent/glm52-fallback/SKILL.md` | absent | n/a |
| `bin/orama-system/skills/cline-openclaw-agent/glm52-fallback/setup-glm52.sh` | absent | n/a |
| `bin/orama-system/skills/glm52-fallback/SKILL.md` | present | `527330f50e5c62916a57130f45458826658940c8` |
| `bin/orama-system/skills/glm52-fallback/setup-glm52.sh` | present | `e6d479bd45f0f58a255f4e681299e99afc77e199` |

## Replay decisions

- Keep one consolidated canonical folder: `bin/orama-system/skills/glm52-fallback/`.
- Delete old live GLM52 files first, then recreate sanitized replacements at the consolidated folder.
- Use `$GLM52_API_KEY` as the runtime input contract.
- Do not print, quote, or store runtime credential values in docs, scripts, logs, PR bodies, or tests.
- Keep Cline backlinks pointed at the sibling consolidated GLM52 skill.

## Out of scope

- Git history rewrite.
- Provider key rotation.
- PR #142 cleanup.
