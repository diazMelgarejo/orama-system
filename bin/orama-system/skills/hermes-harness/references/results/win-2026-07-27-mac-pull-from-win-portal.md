# Mac → Win portal PULL instructions (peer push blocked)

**Fan-out:** coord-033  
**Status:** OPERATOR RULE  
**From:** win-cursor (RTX5080)  
**Date:** 2026-07-27

## Why pull instead of push

Win→Mac `lan_peer_assign.py drop --peer` is **blocked**:

- `http://` + bearer token → `SECURITY_STOP` (RFC 6750 fail-closed in `lan_peer_assign.py`)
- `https://` → Mac portal has **no TLS** on :8002 (`SSL: WRONG_VERSION_NUMBER`)

**Workaround:** Mac **pulls** from Win portal (LAN HTTP). Win portal is bound `0.0.0.0:8002` after `start.ps1 --lan-peer`.

## Win portal endpoints (this host)

| Resource | URL |
|----------|-----|
| Health (no auth) | `http://192.168.9.18:8002/health` |
| Portal UI | `http://192.168.9.18:8002/peer-inbox` |
| List inbox JSON | `http://192.168.9.18:8002/api/peer-inbox` |
| Read one file | `http://192.168.9.18:8002/api/peer-inbox/<filename>` |
| HTML render | `http://192.168.9.18:8002/api/peer-inbox/<filename>/html` |

Replace IP if DHCP changed — check Win `ipconfig` / `last_discovery.json`.

## Auth

Use the **same** `ORAMA_CONTROL_PLANE_TOKEN` as Win `.env.LOCAL` (do not paste token into tracked files).

```bash
export ORAMA_CONTROL_PLANE_TOKEN='<match Win workspace .env.LOCAL>'
export WIN_PORTAL=http://192.168.9.18:8002
```

## Mac terminal — copy/paste block

```bash
# 0) Prerequisites
cd "$ORAMA_SYSTEM_PATH"
export WIN_PORTAL=http://192.168.9.18:8002
# export ORAMA_CONTROL_PLANE_TOKEN from Mac ~/.openclaw or Keychain — MUST match Win

# 1) Health (no token)
curl -sS "$WIN_PORTAL/health" | head

# 2) List Win inbox
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
