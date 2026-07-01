# Provider Auth

Cline providers are configured in `~/.cline/data/settings/providers.json`. Each
provider has a `settings` block with `provider`, auth (`apiKey` or `auth` OAuth
object), `model`, `timeout`, and `reasoning`.

## Providers

| Provider id | Default model | Auth type | Billing | Endpoint |
| --- | --- | --- | --- | --- |
| `cline` | `zai/glm-5.2` | WorkOS OAuth | Cline Credits | `api.cline.bot` |
| `cline-pass` | `cline-pass/glm-5.2` | WorkOS OAuth | Cline Credits | `api.cline.bot` |
| `anthropic` | `claude-fable-5` | API key (`sk-ant-...`) | Anthropic | `api.anthropic.com` |
| `openrouter` | `minimax/minimax-m2.5:free` | API key (`sk-or-v1-...`) | OpenRouter | `openrouter.ai` |
| `openai-compatible` | `google/gemini-3.1-pro-preview` | API key | Google AI | `generativelanguage.googleapis.com` |
| `openai-codex` | — | OAuth | OpenAI | `api.openai.com` |
| `gemini` | `gemini-3.5-flash` | API key | Google AI | `generativelanguage.googleapis.com` |
| `sapaicore` | `gpt-5.5` | SAP AI Core | SAP | — |

## `cline` vs `cline-pass`

Both carry the **identical** WorkOS OAuth token (`accessToken`, `refreshToken`,
`expiresAt`, `accountId` all match). They hit the same backend
(`https://api.cline.bot/api/v1/chat/completions`). The difference is naming:
`cline-pass` uses the `cline-pass/` model prefix (stripped upstream to
`zai/glm-5.2`), while `cline` uses the bare `zai/glm-5.2`. `cline-pass` is the
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

The `cline-agent` uses `openrouter/z-ai/glm-5.2` in OpenClaw, which authenticates
via the `OPENROUTER_API_KEY` environment variable. Verify with:

```bash
openclaw models status --agent cline-agent --probe
```

If `openrouter` is listed as missing, set `OPENROUTER_API_KEY` in
`~/.openclaw/openclaw.json` → `env` or in the shell environment and restart the
gateway.
