# Mac → Win portal PULL instructions (peer push blocked)

**Fan-out:** coord-033  
**Status:** OPERATOR RULE  
**From:** win-cursor (RTX5080)  
**Date:** 2026-07-27

## Why pull instead of push

Win→Mac `lan_peer_assign.py drop --peer` is **blocked**:

- `http://` + bearer token → `SECURITY_STOP` (RFC 6750 fail-closed in `lan_peer_assign.py`)
- `https://` → Mac portal has **no TLS** on :8002 (`SSL: WRONG_VERSION_NUMBER`)

**Do not send `Authorization: Bearer` over plaintext HTTP in either direction** — reversing
Mac→Win does not fix LAN interception or token reuse.

## Approved alternatives (pick one before inbox pull)

1. **SSH tunnel** — forward Win portal to `https://127.0.0.1:<local>` and use HTTPS locally.
2. **mTLS / TLS-terminated reverse proxy** — terminate TLS on Win portal before bearer auth.
3. **Scoped non-reusable pull token** — short-lived, single-file scope (not the long-lived control-plane token).
4. **Operator handoff** — copy inbox files out-of-band (USB, encrypted sync) when TLS is unavailable.

Until one of the above is in place, use **health checks only** over HTTP (no bearer).

## Win portal endpoints (this host)

| Resource | URL |
|----------|-----|
| Health (no auth) | `http://${WIN_PORTAL_LAN_HOST}:8002/health` |
| Portal UI | `http://${WIN_PORTAL_LAN_HOST}:8002/peer-inbox` |
| List inbox JSON | `https://<TLS_ENDPOINT>/api/peer-inbox` (after TLS/tunnel) |
| Read one file | `https://<TLS_ENDPOINT>/api/peer-inbox/<filename>` |

Replace host if DHCP changed — check Win `ipconfig` / `last_discovery.json`.

## Auth

Use the **same** `ORAMA_CONTROL_PLANE_TOKEN` as Win `.env.LOCAL` only over **TLS or tunneled HTTPS** — do not paste token into tracked files.

```bash
export ORAMA_CONTROL_PLANE_TOKEN='<match Win workspace .env.LOCAL>'
export WIN_PORTAL=https://127.0.0.1:<LOCAL_FORWARD>/   # after ssh -L tunnel
```

## Mac terminal — copy/paste block (TLS/tunnel required)

```bash
# 0) Prerequisites — establish TLS or SSH tunnel first; do NOT use bare http:// with bearer
cd "$ORAMA_SYSTEM_PATH"
export WIN_PORTAL=https://127.0.0.1:<LOCAL_FORWARD>/
# export ORAMA_CONTROL_PLANE_TOKEN from Mac ~/.openclaw or Keychain — MUST match Win

# 1) Health (no token) — HTTP ok for liveness only when portal is LAN-reachable
curl -sS "http://${WIN_PORTAL_LAN_HOST}:8002/health" | head

# 2) List Win inbox (TLS/tunnel only)
curl -sS -H "Authorization: Bearer $ORAMA_CONTROL_PLANE_TOKEN" \
  "$WIN_PORTAL/api/peer-inbox" | python3 -m json.tool | head -80

# 3) Pull priority cards (coord-032 env-local ask + coord-031 H6 bookkeeping)
for f in \
  win-2026-07-27-env-local-policy-ask.md \
  mac-2026-07-24-h6-dispatch-bookkeeping-landed.md \
  win-2026-07-23-monitors-paused.md; do
  echo "=== $f ==="
  curl -sS -H "Authorization: Bearer $ORAMA_CONTROL_PLANE_TOKEN" \
    "$WIN_PORTAL/api/peer-inbox/$f" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('content',d)[:2000] if isinstance(d,dict) else d)"
done

# 4) Reply drop back to Win (if Mac push works Mac→Win; else leave reply in Mac local inbox)
python3 bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py drop \
  --file bin/orama-system/skills/hermes-harness/references/results/mac-2026-07-27-env-local-policy-reply.md \
  --assignee win --topic operator/env-local-policy --fanout-id coord-032
```

## Priority reads for Mac orchestrator

| File | Topic |
|------|-------|
| `win-2026-07-27-env-local-policy-ask.md` | **Reply required** — SSoT for workspace `.env.LOCAL` |
| `mac-2026-07-24-h6-dispatch-bookkeeping-landed.md` | H6 bookkeeping landed (informational) |
| `win-2026-07-23-monitors-paused.md` | Monitors paused until manual resume |

## Expected Mac reply

Create `mac-2026-07-27-env-local-policy-reply.md` with keep/migrate/delete per key group, then drop to Win inbox (or push if Mac→Win peer-file works).

## Win state (2026-07-27 ~14:45)

- Stack restarted: PT :8000, orama :8001, Portal :8002 UP
- `ORAMA_CONTROL_PLANE_TOKEN` synced to Windows **User** env from workspace `.env.LOCAL`
- `OramaCoordPulse` still **Disabled** (monitors paused)
- Outbox pending: coord-031 + coord-032 (Mac push failed)
