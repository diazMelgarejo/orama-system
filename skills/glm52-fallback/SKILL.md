---
name: "glm52-fallback"
description: "GLM-5.2 fallback setup guidance"
trigger: "bash setup-glm52.sh"
---

# GLM-5.2 Fallback

Canonical location: `skills/glm52-fallback`.

Tracked files must not contain runtime credential values. Use environment variables or placeholders only.

## Setup

Export the runtime value locally, then run the setup script:

```bash
export GLM52_API_KEY="<BigModel.API.key>"
bash skills/glm52-fallback/setup-glm52.sh
```

## Runtime contract

- `GLM52_API_KEY` is read from the operator environment.
- Runtime values belong in local-only files under `~/.openclaw/`.
- Logs, docs, PR text, screenshots, and tests must not print credential values.

## Fallback order

1. Primary configured provider.
2. GLM-5.2 runtime configuration.
3. Local model fallback when available.
4. Ask the operator for explicit direction if all configured providers fail.
