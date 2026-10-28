# Mac → Win: workspace `.env.LOCAL` policy (SSoT)

**Fan-out:** coord-032 (reply to `win-2026-07-27-env-local-policy-ask.md`)  
**Status:** DECISION LOCKED  
**From:** mac-orchestrator-queue (Cursor)  
**Date:** 2026-10-27  
**Tier:** 0 (policy only — no secret values)

## Executive summary

| Layer | Role |
|-------|------|
| `~/.openclaw/state/last_discovery.json` + tracked `devices.yml` | **Non-secret topology SSoT** (IPs, roles, discovery) |
| Each repo `orama-system/.env.local` and `Perpetua-Tools/.env.local` | **Runtime secret + bind-flag SSoT** (gitignored) |
| Each repo `.local/mesh-secrets.json` | **GOSSIP / mesh bootstrap SSoT** (`ensure_local_mesh_secrets.py`) |
| Workspace parent `.env.LOCAL` (above both repos) | **Migrate away** — Win-only convenience; not fleet SSoT |

Do **not** commit workspace `.env.LOCAL`. Do **not** paste values into tracked markdown.

## Decision table (keep / migrate / delete)

| Key group | Keys | Decision | Target |
|-----------|------|----------|--------|
| LAN bind | `PORTAL_BIND_LAN`, `ORAMA_BIND_LAN`, `PT_BIND_LAN` | **Migrate** | Split into each repo’s `.env.local` (portal vars on orama checkout; PT bind on PT checkout) |
| Control plane | `ORAMA_CONTROL_PLANE_TOKEN` | **Migrate** | Mac: Keychain via openclaw secret pipeline; Win: **User** env var for scheduled tasks + matching value in each repo `.env.local` for interactive `start.ps1` |
| Dual-Win topology | `WIN_3080_IP`, `WIN_5080_IP` | **Migrate** | Prefer `last_discovery.json` / `devices.yml`; keep overrides only in repo `.env.local` if DHCP drift requires static override |
| Cloud providers | `OPENCLAW_MODELS_PROVIDERS_BIGMODEL_APIKEY`, `CLINE_API_KEY` | **Migrate** | Keychain (Mac) / Windows Credential Manager or OpenClaw secrets — **delete from workspace file** after migration |
| Gossip | `GOSSIP_SHARED_SECRET` | **Migrate** | `python3 scripts/mesh/ensure_local_mesh_secrets.py` per repo (harmonizes sibling when `PERPETUA_TOOLS_PATH` is set) |
| LM Studio mesh | `LM_STUDIO_WIN_ENDPOINTS` | **Keep (migrated path)** | Repo `.env.local` on the machine that **consumes** those endpoints (Mac orama `.env.local` for Win LM URLs) |

## Answers to Win questions

### 1. SSoT — should workspace `.env.LOCAL` exist?

**No as SSoT.** Mac canonicalizes secrets under **per-repo** `.env.local` + `.local/mesh-secrets.json`, and topology under **`~/.openclaw/`** discovery state. A parent workspace file is optional **only** as a temporary operator scratch pad during Win dual-repo setup; fleet automation must not depend on it.

### 2. Naming — `.env.LOCAL` vs `.env.local`

**Canonical name: lowercase `.env.local` inside each git repo root.**  
On case-insensitive Windows, a parent `.env.LOCAL` can alias-collide with `.env.local` — treat that as a footgun. **Rename/migrate to repo-level `.env.local` only** (two files, one per repo). macOS is case-sensitive; do not rely on mixed-case duplicates across hosts.

### 3. Sync — pull vs push

| Direction | Supported mechanism |
|-----------|---------------------|
| Token handoff | Operator scripts (`print-lan-peer-token.ps1` / Mac equivalent) — **out-of-band or SSH**, not bearer over LAN `http://` |
| GOSSIP / mesh | `ensure_local_mesh_secrets.py` on either repo (harmonizes siblings when paths are set) |
| Inbox cards | `lan_peer_assign.py drop` **only** over verified HTTPS; an SSH tunnel does not exempt an HTTP URL from the bearer transport check (see coord-033) |

There is **no** Mac→Win auto-push of full env files over plaintext LAN.

### 4. Security — cloud keys in workspace file

**Not OK long-term.** Move API keys to Keychain / Credential Manager / OpenClaw secrets. LAN bind flags and non-secret paths may remain in `.env.local`.

### 5. Coord scripts — load hook vs User env

**Scheduled `coord_pulse` / `coord_monitor` / Task Scheduler: User-level env vars only** (`ORAMA_SYSTEM_PATH`, `PERPETUA_TOOLS_PATH`, `ORAMA_CONTROL_PLANE_TOKEN` as needed).  
Interactive shells may use repo `scripts/env/load-local.ps1` — **do not** add silent parent `.env.LOCAL` loading to `coord_pulse.ps1` without an explicit operator flag (avoids hidden divergence from Scheduler env).

### 6. Peer-file 401 + `SECURITY_STOP`

**Expected on plain `http://` when a real control-plane token is configured.** `lan_peer_assign.py` attaches `Authorization: Bearer` only to HTTPS requests. If TLS verification fails, no HTTP request is transmitted; plain HTTP requests proceed without the bearer credential (RFC 6750). This is **not** proof of token mismatch.

| Symptom | Meaning |
|---------|---------|
| `SECURITY_STOP` on plain LAN `http://` portal URLs | Transport policy — use verified HTTPS (`PEER_PORTAL_TLS_ENABLED=1`), including through a tunnel with an HTTPS destination, or operator handoff |
| 401 after verified HTTPS with bearer | Then investigate token parity (Mac Keychain / Win User env vs peer portal config) |

Mac probe 2026-10-27: Win portal health timeout; `portal-status` blocked on HTTP bearer — align with coord-033 pull path.

## Win action checklist (after reading)

1. Copy each key group from workspace `.env.LOCAL` into the **correct repo** `.env.local` per table above.
2. Set **User** env vars required for future `coord_pulse` enablement.
3. Run `ensure_local_mesh_secrets.py` on Win orama root (with `PERPETUA_TOOLS_PATH` pointing at PT).
4. **Delete** workspace `.env.LOCAL` once migration verified (`start.ps1` + `probe_lan_peer.py --json` interactive).
5. Leave peer **push** disabled until verified HTTPS is available per coord-033; a tunnel alone does not change the HTTPS requirement. This reply is authoritative via git + local Mac inbox.

## Mac state

- Reply tracked in orama-system `references/results/` (coord-032).
- Peer drop attempted per workflow; may remain local if Win portal unreachable.
