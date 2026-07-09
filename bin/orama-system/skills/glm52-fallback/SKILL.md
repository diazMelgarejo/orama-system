---
name: glm52-fallback
description: GLM-5.2 fallback setup guidance for agents when ClinePass is unavailable.
when_to_use: Activates for GLM-5.2 fallback setup, provider failover guidance, or verifying BigModel fallback configuration.
disable-model-invocation: true
effort: medium
paths:
  - "bin/orama-system/skills/glm52-fallback/**"
---

# GLM-5.2 Fallback

Use this skill for fallback configuration guidance only. The canonical folder is:

```text
bin/orama-system/skills/glm52-fallback/
```

## Credential rule

Tracked files must never contain runtime credential values. Use environment variables or placeholders only.

Required documentation placeholder:

```text
<BigModel.API.key>
```

Runtime input contract:

```text
GLM52_API_KEY
```

## Setup

Export the runtime value locally, then run the setup script:

```bash
export GLM52_API_KEY="<BigModel.API.key>"
bash bin/orama-system/skills/glm52-fallback/setup-glm52.sh
```

The setup script reads `GLM52_API_KEY` from the caller environment and writes local-only files under `~/.openclaw/`.

## Runtime contract

- `GLM52_API_KEY` is supplied by the operator environment.
- `GLM52_ENDPOINT` is written to the local env file for the BigModel chat-completions endpoint.
- Runtime values belong in local-only files under `~/.openclaw/`.
- Logs, docs, PR text, screenshots, and tests must not print credential values.

## Fallback order

1. Primary configured provider.
2. GLM-5.2 runtime configuration.
3. Local model fallback when available.
4. Ask the operator for explicit direction if all configured providers fail.

## Verification

```bash
test -n "${GLM52_API_KEY:-}" && echo "GLM52_API_KEY is set"
bash bin/orama-system/skills/glm52-fallback/setup-glm52.sh
```

Report only setup status. Do not print the credential value.
