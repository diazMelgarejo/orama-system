# Win → Mac: what should we do with workspace `.env.LOCAL`?

**Fan-out:** coord-032  
**Status:** OPERATOR ASK  
**From:** win-cursor (RTX5080)  
**Date:** 2026-07-27

## Audience

| Lane | Action |
|------|--------|
| mac-orchestrator | **Reply** with SSoT policy for workspace-level `.env.LOCAL` |
| win-cursor | Hold — do not commit or fanout secret values |
| win-coder | No code change until Mac answers |
| hermes | No action |

## Context

On the Win ultrathink workspace root we have a file named `.env.LOCAL` (capital LOCAL) sitting **above** both git repos (`orama-system` + `Perpetua-Tools`), not inside either repo.

Win `start.ps1` / `scripts/env/load-local.ps1` may load `.env.local` from repo roots, but **coord_pulse**, **coord_monitor**, and **scheduled tasks do not** — only persistent User env vars or explicit exports reach those paths (see PT lesson on `.env.local` vs Task Scheduler).

Peer drops to Mac are currently failing with HTTP 401 + `SECURITY_STOP` (bearer token refused on `http://` LAN portal). This card is the authoritative ask even if GossipBus does not cross hosts.

## Keys present (names only — values REDACTED, do not echo in reply)

| Key | Purpose (inferred) |
|-----|-------------------|
| `PORTAL_BIND_LAN` | Bind portal to LAN |
| `ORAMA_BIND_LAN` | Bind orama services to LAN |
| `PT_BIND_LAN` | Bind PT services to LAN |
| `ORAMA_CONTROL_PLANE_TOKEN` | Peer portal auth (synced from Win print-lan-peer-token) |
| `WIN_3080_IP` | Dual-Win topology override |
| `WIN_5080_IP` | Dual-Win topology override |
| `OPENCLAW_MODELS_PROVIDERS_BIGMODEL_APIKEY` | Cloud GLM provider |
| `CLINE_API_KEY` | Cline/ClinePass local |
| `GOSSIP_SHARED_SECRET` | LAN gossip bridge |
| `LM_STUDIO_WIN_ENDPOINTS` | LM Studio mesh endpoints |

Header comment says: *"LAN peer — synced from Win print-lan-peer-token.ps1 2026-06-28"* and *"harmonized by ensure_local_mesh_secrets.py"*.

## Questions for Mac

1. **SSoT:** Should workspace `.env.LOCAL` exist at all, or should Mac canonicalize everything under `~/.openclaw/` + `devices.yml` / `last_discovery.json`?
2. **Naming:** `.env.LOCAL` vs `.env.local` — which wins on case-insensitive Windows vs macOS?
3. **Sync:** Is there a Mac-side script that should **pull** Win token/IP updates, or **push** Mac canonical env to Win?
4. **Security:** OK to keep cloud API keys in this file, or move to Keychain / Windows Credential Manager / openclaw secrets only?
5. **Coord scripts:** Should we add a one-line `load-local.ps1` hook to `coord_pulse.ps1`, or is **User-level env var** the only supported path for scheduled monitors?
6. **Peer-file 401:** Does Mac expect `ORAMA_CONTROL_PLANE_TOKEN` to match a specific value? Win interactive probe passes portal-status but `lan_peer_assign.py drop --peer` returns 401 + SECURITY_STOP on plain HTTP.

## Action required (Mac)

Reply via peer inbox drop: `mac-2026-07-27-env-local-policy-reply.md` with a short decision table (keep / migrate / delete) per key group above.

## Action required (Win)

- **Do not commit** `.env.LOCAL` or paste values into tracked markdown.
- Wait for Mac reply before moving keys or changing load order.

## Open / deferred

- Outbox may still hold undelivered drops until peer-file auth is green.
