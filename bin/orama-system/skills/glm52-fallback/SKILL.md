---
name: glm52-fallback
description: GLM-5.2 fallback guidance for agents.
when_to_use: Activates for GLM-5.2 fallback setup or provider failover guidance.
disable-model-invocation: true
effort: medium
---

# GLM-5.2 Fallback

Use this skill for fallback configuration guidance only.

Tracked documentation must use placeholders only. Local runtime values belong outside git.

Required placeholder for examples: `<BigModel.API.key>`.

## Runtime contract

Operators configure local environment values outside the repository. Agents read those runtime values and must not print them in logs, PRs, docs, screenshots, or test output.

## Fallback order

1. Primary configured provider.
2. GLM-5.2 runtime configuration.
3. Local model fallback when available.
4. Ask the operator for explicit direction if all configured providers fail.
