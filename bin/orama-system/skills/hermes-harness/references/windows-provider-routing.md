# Windows Provider Routing Reference

> **Role:** provider fallback stack and routing rules for Hermes on Windows 11.  
> **Hard rule:** references-only — no executable logic. Thin wrappers read this; `start.ps1` exports env vars.

---

## Provider Priority Stack

| Priority | Provider | Model | Endpoint | Notes |
|---|---|---|---|---|
| 1 | LM Studio (local GGUF) | Live-resolved via `/v1/models` | `http://localhost:1234/v1` | Locality rule: always `localhost` on Windows |
| 2 | Nous Portal | `qwen/qwen3-coder:free` | `https://api.nousresearch.com/v1` | Requires `NOUS_API_KEY` |
| 3 | OpenRouter (free tier) | `qwen/qwen3-coder:free` | `https://openrouter.ai/api/v1` | Outer fallback; requires `OPENROUTER_API_KEY` |

Gemini CLI (`gemini -p`) — **retired 2026-06-18** (`IneligibleTierError`). Do not use.

---

## LM Studio Routing Rules

1. **Always `localhost:1234`** when running on Windows — the locality rule.
   Mac-orchestrator council calls to Windows use `$WIN_IP:1234` (set in Mac's `.env`).
2. **Model IDs must be live-resolved** — `GET http://localhost:1234/v1/models`.
   Never invent a model name. See `hermes-windows-partner-readiness.md` § LM Studio Model Resolution.
3. **Known working model ID (as of 2026-06-24):** `qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2`
   (lowercase, exact; loaded in LM Studio). Hardware: Windows RTX 3080, `gpu_offload=40`, `context 16384`.
4. **Timeout:** completion expected <180 s at `max_tokens≥2048`. Mark UNAVAILABLE if canary hangs >15 s.

---

## Nous Portal Configuration

```powershell
$env:NOUS_API_BASE = "https://api.nousresearch.com/v1"
$env:NOUS_DEFAULT_MODEL = "qwen/qwen3-coder:free"
# Never set NOUS_API_KEY inline — read from secure store only
```

Default coding model: `qwen/qwen3-coder:free`
Canary model: `nvidia/nemotron-3-ultra:free` (fast, reliable, used for `HERMES_READY` probe)

---

## OpenRouter Fallback

```powershell
$env:OPENROUTER_BASE = "https://openrouter.ai/api/v1"
$env:OPENROUTER_DEFAULT_MODEL = "qwen/qwen3-coder:free"
```

Use only when Nous quota is exhausted. Check quota: `GET https://api.nousresearch.com/v1/usage`.

---

## Cross-Machine Routing (Windows ↔ Mac)

| Caller | Target | Endpoint used |
|---|---|---|
| Windows (Hermes) | Windows LM Studio | `http://localhost:1234/v1` |
| Windows (Hermes) | Mac Ollama / LM Studio | `http://$env:MAC_IP:11434` or `http://$env:MAC_IP:1234` |
| Mac (OpenClaw) | Windows LM Studio | `http://$WIN_IP:1234/v1` (from Mac's `.env`) |

See `lan-endpoint-contract.md` for the full variable contract.

---

## Related

- [`windows-onboarding-config.md`](windows-onboarding-config.md) — env vars + toolchain
- [`hermes-windows-partner-readiness.md`](hermes-windows-partner-readiness.md) — canary + readiness matrix
- [`lan-endpoint-contract.md`](lan-endpoint-contract.md) — IP parametrization contract
- [`../commands/pt-hardware-policy/SKILL.md`](../commands/pt-hardware-policy/SKILL.md) — NEVER_MAC/NEVER_WIN affinity
