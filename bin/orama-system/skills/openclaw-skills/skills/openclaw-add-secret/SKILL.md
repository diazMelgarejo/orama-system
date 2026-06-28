---
name: openclaw-add-secret
description: Store secrets in macOS Keychain and propagate them across runtime, shell, and provisioning files.
agent_compatibility: [Claude, Hermes, Gemini, Codex, Cursor, WindSurf, Antigravity, OpenCode, 8gent.dev]
model_routing: ollama-first-then-openrouter
version: "1.0"
layer: "1 — Operations (builds on Layer 0: v1/OpenRouter.md)"
upstream: https://github.com/rahulsub-be/cc-openclaw
upstream_license: MIT
extends: ../cc-openclaw/.claude/skills/openclaw-add-secret/SKILL.md
overlay_role: orama-normalized cross-harness extension
---

## Overlay Source

This Orama-normalized skill extends the upstream cc-openclaw skill at [`../cc-openclaw/.claude/skills/openclaw-add-secret/SKILL.md`](../cc-openclaw/.claude/skills/openclaw-add-secret/SKILL.md). Use the upstream file as the behavioral baseline and this file as the cross-harness overlay for Orama, Perpetua-Tools, Codex, Hermes, Gemini, and other agent runners.

## Purpose

Add credentials without exposing secret values in logs or files. This skill writes the secret to Keychain, then updates all required loaders so gateway, CLI, and disaster recovery stay aligned. Naming is enforced to prevent lookup mismatch.

## When to Use

- Adding API keys, bot tokens, app tokens, and service secrets
- Fixing missing env variable wiring for existing Keychain entries
- Standardizing secure secret onboarding

## Inputs

- Required:
  - `secret_name` (lowercase-hyphen)
  - `secret_value`
- Optional:
  - `env_var_name` (auto-derived when omitted)
  - `account_name` (defaults to `$USER` for keychain account field)

## Procedure

1. Derive service/env names and validate.

```bash
set -euo pipefail
printf '%s' "$secret_name" | grep -Eq '^[a-z0-9]+(-[a-z0-9]+)*$'
service="openclaw.$secret_name"
env_var="${env_var_name:-OPENCLAW_$(printf '%s' "$secret_name" | tr '[:lower:]-' '[:upper:]_')}"
printf '%s' "$env_var" | grep -Eq '^OPENCLAW_[A-Z0-9_]+$'
```
2. Collect secret without argv exposure, then store in Keychain.

Never pass the secret on the `security` command line or as a skill argument.
Disable shell history for this step, read silently from the terminal, pipe via
stdin to the helper (secret stays off the caller's argv):

```bash
set +o history
read -rs secret_value
printf '\n' >&2
printf '%s' "$secret_value" | bash "$REPO_ROOT/scripts/openclaw/store_keychain_secret.sh" "$service" "$USER"
unset secret_value
set -o history
```

The helper reads stdin only; callers must not substitute `$secret_value` into
`-w` flags. Provisioning scripts store key names and retrieval commands only,
never literal secret values.
3. Wire `openclaw-secrets.sh` (launchd/gateway source).

```bash
# Add export that reads from keychain service "$service" into "$env_var".
```
4. Sync `openclaw-env.sh` (shell source).

```bash
# Mirror the same export for CLI sessions.
```
5. Reflect the same export in provisioning `secrets.sh`.

```bash
# Add bootstrap logic to recreate "$service" and "$env_var" mapping on new machines.
```
6. Verify mapping and non-empty resolve.

```bash
security find-generic-password -s "$service" -w >/dev/null
```
7. Validate shell loaders reference the expected env var exactly once.

```bash
grep -n "$env_var" openclaw-secrets.sh openclaw-env.sh secrets.sh
```

8. Post-run scan: confirm the secret value does not appear in modified files or logs.

```bash
# After storing, verify no literal secret leaked into git-tracked files.
git diff --name-only | xargs -I{} grep -l "$env_var" {} 2>/dev/null || true
# env_var name is fine; literal secret value must not appear in any diff.
```

## Output Contract

```json
{
  "status": "ok|error",
  "files_modified": ["openclaw-secrets.sh", "openclaw-env.sh", "secrets.sh"],
  "follow_up_actions": ["openclaw-restart", "openclaw-status"]
}
```

## Naming Enforcement

- Keychain service must be `openclaw.<name>`.
- Service `<name>` must be lowercase with hyphens only.
- Environment variable must be `OPENCLAW_<NAME>` uppercase with underscores.
- Service suffix and env-var suffix must represent the same logical secret name.

## Gotchas

- Secret values must never be echoed to terminal or written to git-tracked files.
- Missing `openclaw-env.sh` update causes `MissingEnvVarError` in terminal usage.
- Missing `secrets.sh` update blocks disaster recovery reprovisioning.
- Reusing one env var for multiple services causes ambiguous runtime behavior.
- Copy-paste drift between `openclaw-secrets.sh` and `openclaw-env.sh` is a common source of mismatched values.

## See Also

- `../openclaw-add-channel/SKILL.md`
- `../openclaw-restart/SKILL.md`
- `../openclaw-status/SKILL.md`

## Notes

- Rotate compromised secrets by re-running this skill with the same `secret_name` and new value.
- Treat derived names as contract values; downstream config expects stable naming.

## References

- [`references/openrouter-defaults.md`](../../references/openrouter-defaults.md) — model routing source of truth
- [`references/universal-skill-protocol.md`](../../references/universal-skill-protocol.md) — invocation envelope standard
- [`references/pt-orama-weave.md`](../../references/pt-orama-weave.md) — how PT + orama-system cooperate
