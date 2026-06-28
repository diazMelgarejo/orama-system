<!-- lint-ignore LINT-013 -->
# Local API Fallback — Full Reference

> **Rule:** When OmniRoute is disabled OR no external API responds (Anthropic, OpenRouter, etc.),
> fall back to local inference in this fixed priority order. Never leave the session broken.

## Priority 1 — Ollama (Mac, always-on)

```bash
# Verify reachability:
curl -s --max-time 3 http://localhost:11434/api/tags \
  | python3 -c "import json,sys; m=json.load(sys.stdin).get('models',[]); print('MODELS:', [x['name'] for x in m])"
```

Preferred inference model: `qwen3.5:9b-nvfp4` — required per § 0 hard requirements.
Embeddings model: `bge-m3` — required for gbrain + CRG semantic search.

Use Ollama first: always running locally (Mac hard requirement), zero-cost, works offline.

## Priority 2 — LM Studio (Windows GPU coder pool)

```bash
# Endpoint pool:
echo "$LM_STUDIO_WIN_ENDPOINTS"    # e.g. 192.168.254.103:1234
# Verify:
curl -s --max-time 3 "http://${LM_STUDIO_WIN_ENDPOINTS%%,*}/v1/models" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('MODELS:', [m['id'] for m in d.get('data',[])])"
```

OpenAI-compatible API on Windows GPU. **Fail loudly if the variable is set but host is unreachable.**
If `$LM_STUDIO_WIN_ENDPOINTS` is unset, skip this tier silently.

## Fallback decision table

| External API | Ollama | LM Studio | → Use |
|---|---|---|---|
| OK | any | any | External API (normal path) |
| DOWN | running | any | Ollama |
| DOWN | DOWN | running | LM Studio |
| DOWN | DOWN | DOWN | Surface outage; do not hallucinate |

**Every tier check must have a ≤3s timeout. Never hang silently.**
