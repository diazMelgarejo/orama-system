# LAN Endpoint Contract

> **Role:** canonical variable contract for all machine IPs and service endpoints across orama-system + PT.  
> **Decision (2026-06-24):** every machine IP is an environment variable resolved at runtime.  
> No tracked IP literals in skills, plans, or docs — only code-fallback defaults inside resolution modules.  
> **Hard rule:** references-only. `start.sh` / `start.ps1` export these; code reads `os.getenv(...)`.

---

## Canonical Variable Set

| Variable | Meaning | Code-fallback default | Set in |
|---|---|---|---|
| `MAC_IP` | Mac host LAN IP | `192.168.254.110` | `.env` / `start.sh` |
| `WIN_IP` | Windows host LAN IP | `192.168.254.108` | `.env` / `start.ps1` |
| `LM_STUDIO_MAC_ENDPOINT` | Full Mac LM Studio URL | `http://{MAC_IP}:1234` | `.env` |
| `LM_STUDIO_WIN_ENDPOINTS` | Comma-list of Win LM Studio URLs | `http://{WIN_IP}:1234` | `.env` |
| `MAC_LMS_HOST` / `MAC_LMS_PORT` | Mac LM Studio host + port parts | from `LM_STUDIO_MAC_ENDPOINT` | `.env` |
| `WINDOWS_IP` / `WINDOWS_PORT` | Win LM Studio/Ollama host + port | from `LM_STUDIO_WIN_ENDPOINTS` | `.env` |
| `OLLAMA_MAC_ENDPOINT` | Mac Ollama URL | `http://localhost:11434` (Mac) / `http://{MAC_IP}:11434` (other) | `.env` |
| `OLLAMA_WINDOWS_ENDPOINT` | Win Ollama URL | `http://localhost:11434` (Win) / `http://{WIN_IP}:11434` (other) | `.env` |
| `LM_STUDIO_API_TOKEN` | LM Studio bearer token | `lm-studio` (dev) | `.env.local` |
| `ORAMA_PLATFORM` | Override platform detection | *(empty)* | CI / test env |

---

## Locality Rule

> When code runs **on** a machine, it reaches that machine's own services via `localhost`.  
> The LAN IP (`$WIN_IP` / `$MAC_IP`) is used **only** for genuine cross-machine calls.

| Caller | Target | Resolves to |
|---|---|---|
| Mac process | Mac LM Studio / Ollama | `localhost` |
| Mac process | Windows LM Studio / Ollama | `$WIN_IP` |
| Windows process | Windows LM Studio / Ollama | `localhost` |
| Windows process | Mac LM Studio / Ollama | `$MAC_IP` |

**Implementation:** `src/perpetua_tools/agent_launcher.py::resolve_local_or_remote()`  
**Gap (2026-06-24):** `alphaclaw_bootstrap.py` now mirrors this rule — see PT commit.

---

## Hygiene Rules

- `grep -rn '192\.168\.' src/ scripts/ bin/ docs/` must return only fallback-default
  lines inside resolution code (with a comment). Never a bare IP in a skill, plan, or doc.
- `start.sh` and `start.ps1` export `MAC_IP` / `WIN_IP` so child processes inherit them.
- `.env.local` overrides `.env` (machine-local settings take precedence). Neither is tracked.

---

## Self-Heal Behaviour

`agent_launcher.py` logs a warning and normalizes to `localhost` if a non-loopback endpoint
is configured for the local machine (e.g. a stale DHCP IP left in `.env`):

```text
WARNING: OLLAMA_MAC_ENDPOINT=http://192.168.x.x:11434 is non-loopback;
PT runs on the Mac so its ollama is localhost — normalizing to http://localhost:11434
```

This "live/canonical localhost beats stale LAN config" self-heal is present for Mac Ollama
and Win LM Studio in `agent_launcher.py`. `alphaclaw_bootstrap.py` now applies the same rule.

---

## Related

- [`windows-provider-routing.md`](windows-provider-routing.md) — Win provider stack
- [`windows-onboarding-config.md`](windows-onboarding-config.md) — Win env vars + toolchain
- `PT src/perpetua_tools/agent_launcher.py::resolve_local_or_remote()` — shared helper
- `PT src/perpetua_tools/alphaclaw_bootstrap.py` — locality rule applied
