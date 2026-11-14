# Provider Auth

<!-- wandb-inference-working-config -->
## W&B inference

`invalid model ID` from the Cline CLI is stale provider metadata, not a
bad model id. `tokenSource` must be `manual` (or Cline's `oauth` or
`migration`) and `updatedAt` must be UTC with millisecond precision and a
trailing `Z`. Repair a shared entry with
`bin/orama-system/scripts/cline-provider-profiles/switch_cline_provider.py`.
When two routes run side by side, use
`bin/orama-system/skills/cline-wandb/scripts/launch_cline_wandb.py`.
Use the OpenAI client and Weave only if that error remains after the
metadata is current. Do not send a CoreWeave team/project string.
Shell-source the operator W&B env file before reading
`DEEPSEEK_V4_FLASH_WANDB`.

Cline providers are configured in `~/.cline/data/settings/providers.json`. Each
provider has a `settings` block with `provider`, auth (`apiKey` or `auth` OAuth
object), `model`, `timeout`, and `reasoning`.

## Providers

| Provider id | Default model | Auth type | Billing | Endpoint |
| --- | --- | --- | --- | --- |
| `cline` | `zai/glm-5.3-flash` | WorkOS OAuth | Cline Credits | `api.cline.bot` |
| `cline-pass` | `cline-pass/glm-5.3-flash` | WorkOS OAuth | Cline Credits | `api.cline.bot` |
| `anthropic` | `claude-fable-5` | API key (`sk-ant-...`) | Anthropic | `api.anthropic.com` |
| `openrouter` | `cohere/north-mini-code:free` | API key (`sk-or-v1-...`) | OpenRouter | `openrouter.ai` |
| `openai-compatible` | `gemini-3.8-flash` | API key | Google AI | `generativelanguage.googleapis.com` |
| `openai-codex` | — | OAuth | OpenAI | `api.openai.com` |
| `gemini` | Saved model (host-specific) | API key | Google AI | `generativelanguage.googleapis.com` |
| `sapaicore` | `gpt-5.5` | SAP AI Core | SAP | — |

## `cline` vs `cline-pass`

Selecting the `gemini` profile without a model override can retain its saved model;
inspect the active configuration before assuming a specific model.

Both carry the **identical** WorkOS OAuth token (`accessToken`, `refreshToken`,
`expiresAt`, `accountId` all match). They hit the same backend
(`https://api.cline.bot/api/v1/chat/completions`). The difference is naming:
`cline-pass` uses the `cline-pass/` model prefix (stripped upstream to
`zai/glm-5.3-flash`), while `cline` uses the bare `zai/glm-5.3-flash`. `cline-pass` is the
`lastUsedProvider` in the current config.

## WorkOS Token Lifecycle

The `auth.accessToken` is a `workos:eyJ...` JWT with:

- `expiresAt`: ~12 minutes from issuance
- `refreshToken`: used by the Cline CLI to rotate the access token
- Only the Cline CLI's auth loop knows how to refresh it

**Never copy this token into OpenClaw config or workspace files.** It will
expire within minutes and OpenClaw cannot refresh it. If you need OpenClaw to
call `api.cline.bot` directly, you need either a static Cline API key (if
issued) or a local token-refresh proxy.

## Authenticating a provider (interactive)

```bash
cline auth cline-pass     # re-authenticate the cline-pass provider
cline auth openrouter     # set OpenRouter API key
cline auth anthropic      # set Anthropic API key
```

`cline auth` requires a TTY. Never run in unattended automation.

## Checking credits

Cline Credits balance: `https://app.cline.bot/credits`

When credits are exhausted, `cline`/`cline-pass` calls return:

```json
{"error":{"code":"insufficient_credits","message":"Insufficient balance..."}}
```

(HTTP 402). Top up at the URL above.

## OpenClaw-side auth (for the `cline-agent` model)

The `cline-agent` uses `openrouter/z-ai/glm-5.3-flash` in OpenClaw, which authenticates
via the `OPENROUTER_API_KEY` environment variable. Verify with:

```bash
openclaw models status --agent cline-agent --probe
```

If `openrouter` is listed as missing, set `OPENROUTER_API_KEY` in
`~/.openclaw/openclaw.json` → `env` or in the shell environment and restart the
gateway.
