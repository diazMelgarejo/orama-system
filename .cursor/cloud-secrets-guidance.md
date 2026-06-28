# Cursor Cloud secrets — loopback / bind guidance

Loopback addresses and bind-all interfaces are **configuration**, not credentials.
Do **not** register them as Cursor Cloud secrets (especially not as **Redacted** secrets).

## Remove from the Secrets tab

Delete or un-redact entries whose value is only loopback or bind-all:

| Variable | Use instead |
|----------|-------------|
| `LOCAL_MAC_HOST` | `OLLAMA_MAC_ENDPOINT=http://localhost:11434` (see `.env.example`) |
| `OLLAMA_HOST` | `OLLAMA_MAC_ENDPOINT` |
| `OPENCLAW_GATEWAY_URL` | `.cursor/environment.json` + `OPENCLAW_GATEWAY` in `.env.example` |
| `LM_STUDIO_URL` / `LM_STUDIO_MAC_ENDPOINT` | `.cursor/environment.json` + `.env.local` for LAN |
| Host-only secrets (loopback or bind-all) | Use `localhost` in committed config; set `ORAMA_LAN_BIND_HOST` only when you truly need LAN bind |

When host addresses are stored as **Redacted** secrets, Cursor's commit scanner blocks staged
files containing those strings and agents may write scanner placeholders into source.

## Safe pattern

- **Secrets tab:** API keys, tokens, passwords, `SETUP_PASSWORD`, `ORAMA_CONTROL_PLANE_TOKEN`
- **`.cursor/environment.json`:** non-secret `localhost` URLs
- **`.env.local`:** LAN IPs and machine-specific endpoints only
- **LAN bind:** `PT_BIND_LAN=1` / `ORAMA_BIND_LAN=1` / `PORTAL_BIND_LAN=1` (optional `ORAMA_LAN_BIND_HOST`)
