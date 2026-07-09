# Interactive Provider Setup — canonical doctrine

> **Role:** single reusable pattern for LLM-provider auth/API-key onboarding,
> referenced by any skill that needs credentials. Do not duplicate this logic
> into individual skills — link here.
> **Precedent:** matches vanilla OpenClaw/Hermes onboarding behavior — see
> `openclaw-skills/SKILL.md` § "ALWAYS: AskUserQuestion for decisions."

---

## Three execution modes (detect, don't assume)

| Mode | Detection | Behavior |
|---|---|---|
| **Agent-mediated** | Claude/Codex/other tool-using agent runs the skill | Use the `AskUserQuestion` tool — never a shell prompt. One question: pick primary provider; already-configured providers are pre-listed as automatic fallback. |
| **Human terminal** | `[ -t 0 ]` true (stdin is a TTY) and no agent tool context | Run `scripts/interactive-provider-setup.sh` — a 60s-timeboxed `read` prompt. |
| **Non-interactive** | CI, cron, subagent, piped stdin, or 60s timeout elapses | Skip prompting entirely. Use whatever is already configured; write `null` placeholders for the rest. Never block. |

**Idempotency rule:** every provider check reads existing env vars / secret
files FIRST. Already-configured providers are never re-prompted — they are
automatically added to the fallback chain. Only genuinely unset providers
trigger a prompt, and only in interactive mode.

---

## Provider table (canonical env var contract)

| Provider | Primary env var | Alt env var(s) | Placeholder file |
|---|---|---|---|
| Claude (Anthropic) | `ANTHROPIC_API_KEY` | — | `~/.openclaw/secrets/anthropic-api-key` |
| Codex (OpenAI) | `OPENAI_API_KEY` | `CODEX_API_KEY` | `~/.openclaw/secrets/openai-api-key` |
| Antigravity / Gemini (Google) | `GEMINI_API_KEY` | `GOOGLE_API_KEY` | `~/.openclaw/secrets/gemini-api-key` |
| Cline (ClinePass) | `CLINE_API_KEY` | `CLINEPASS_TOKEN` | `~/.openclaw/secrets/cline-api-key` |
| BigModel (GLM-5.2) | `GLM52_API_KEY` | `OPENCLAW_MODELS_PROVIDERS_BIGMODEL_APIKEY` | `~/.openclaw/secrets/glm52-api-key` |
| Perplexity API | `PERPLEXITY_API_KEY` | — | `~/.openclaw/secrets/perplexity-api-key` |

A provider is **configured** when its primary or any alt env var is
non-empty, OR its placeholder file exists and is non-empty.

---

## Flow

1. Scan the provider table. Build two lists: `configured` and `unconfigured`.
2. If `configured` is non-empty and nothing has explicitly asked for a
   primary yet: configured providers become the fallback chain in the order
   found; the first one found is the default primary unless overridden.
3. If mode is agent-mediated or human-terminal AND `unconfigured` is
   non-empty: ask ONE question — "Which provider should be primary?"
   listing configured providers plus "skip / configure later" for each
   unconfigured one. 60s timeout in human-terminal mode; no timeout needed
   in agent-mediated mode (the agent owns pacing).
4. Write results:
   - Configured/chosen providers → their env files, unchanged if already set.
   - Still-unconfigured providers → `null` placeholder written to their env
     file / `.env` entry (e.g. `PERPLEXITY_API_KEY=null`) so downstream
     tooling can distinguish "asked and declined" from "never asked."
5. Never print, log, or echo actual credential values at any step.

---

## Env/placeholder file contract

`~/.openclaw/.env.providers` (mode 600), one line per provider:

```bash
# Written by interactive-provider-setup.sh — do not hand-edit values here.
# null = not yet configured (opt-in prompt was skipped or declined).
ANTHROPIC_API_KEY=null
OPENAI_API_KEY=null
GEMINI_API_KEY=null
CLINE_API_KEY=null
GLM52_API_KEY=null
PERPLEXITY_API_KEY=null
ORAMA_PRIMARY_PROVIDER=null
```

`null` (not empty string, not unset) is the explicit "asked, not yet
provided" marker — distinct from a var that was never even scanned.

---

## Invocation

```bash
bash bin/orama-system/scripts/interactive-provider-setup.sh
```

Flags: `--non-interactive` (force skip mode regardless of TTY),
`--timeout N` (override the default 60s), `--primary <provider>` (set
without prompting).

## Related

- [`openclaw-skills/SKILL.md`](../skills/openclaw-skills/SKILL.md) § AskUserQuestion rule
- [`glm52-fallback/SKILL.md`](../skills/glm52-fallback/SKILL.md) — first consumer of this pattern
- [`hermes-harness/references/partner-prompt-contract.md`](../skills/hermes-harness/references/partner-prompt-contract.md) — non-TTY flag precedent
