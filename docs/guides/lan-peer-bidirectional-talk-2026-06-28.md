# LAN peer bidirectional talk — attempts, evidence, and plans (2026-06-28)

> **Operator SSOT:** [`lan-peer-self-talk.md` § Operator playbook](../../bin/orama-system/skills/hermes-harness/references/lan-peer-self-talk.md#operator-playbook)  
> **Navigation:** [`lan-peer-mac-win-operator.md`](lan-peer-mac-win-operator.md)  
> **E2E matrix:** [`../testing/2026-06-28-mac-win-e2e-evidence.md`](../testing/2026-06-28-mac-win-e2e-evidence.md)

This page records **live bidirectional-talk attempts** on the Mac Studio ↔ Win RTX LAN,
what worked, what failed, why, and the **reuse-first plan** for full portal round-trip.
Do not hardcode DHCP IPs in tracked files — read `last_discovery.json` or run `discover.py --force`.

---

## Network topology (confirmed live)

| Host | Role | LAN IP (2026-06-28) | LM Studio | PT / orama / Portal |
|------|------|---------------------|-----------|---------------------|
| **Win** | RTX 3080 GGUF box | `192.168.254.100` | `:1234` (localhost + LAN) | `:8000` / `:8001` / `:8002` |
| **Mac** | Apple Silicon MLX box | `192.168.254.102` | `:1234` | `:8000` / `:8001` / `:8002` |

**Stale IP warning:** `192.168.254.110` appeared in old defaults (`start.ps1` gateway heuristic,
`agent_launcher.py`, lessons). It is **not** the current Mac address. Always probe or use discovery.

---

## What “bidirectional talk” means (three layers)

| Layer | Mechanism | Bidirectional today? |
|-------|-----------|-------------------|
| **L1 — Inference** | HTTP `GET /v1/models`, `POST /v1/chat/completions` on peer LM Studio | ✅ Yes (Mac↔Win over LAN) |
| **L2 — Control plane** | Portal `GET /health`, `GET /api/status` (Bearer token) | ⚠️ Partial — needs `*_BIND_LAN=1` + shared token on **both** hosts |
| **L3 — Agent dispatch** | Hermes/Codex on peer host, `POST /api/user-input` cross-peer | ❌ Not shipped (v2 increment) |

Hermes `/lan-peer-self-talk` probes **L1 + L2** only. It does not run partners on the remote host.

---

## Attempt log (2026-06-28, Win operator session)

### Attempt 1 — Stale Mac IP `192.168.254.110`

**Action:** `Test-NetConnection` and HTTP probes to `192.168.254.110` (ports 8002, 1234).

| Target | Port | Result |
|--------|------|--------|
| `192.168.254.110` | 8002 | TCP fail |
| `192.168.254.110` | 1234 | TCP fail |

**Root cause:** `.110` came from `start.ps1` gateway-subnet heuristic and PT code defaults — not from live discovery.

---

### Attempt 2 — Correct Mac IP `192.168.254.102` (inference only)

**Action:** HTTP probes and chat completions from Win.

| Check | Result |
|-------|--------|
| `192.168.254.102:1234/v1/models` | ✅ 200 |
| `192.168.254.100:1234/v1/models` (Win LAN) | ✅ 200 |
| `qwen3.5-9b-mlx` chat completion Mac→Win | ✅ HTTP 200 |
| Mac portal `:8002/health` | ❌ timeout (Mac stack not LAN-bound or down) |
| Win portal on LAN `192.168.254.100:8002` | ❌ fail (Win bound `127.0.0.1` only) |

**Lesson:** Inference works before portal bind. Portal bidirectional requires `--lan-peer` on **both** hosts.

---

### Attempt 3 — `probe_lan_peer.py` (pre-discovery fix)

```powershell
python bin\orama-system\skills\hermes-harness\scripts\probe_lan_peer.py --peer-ip 192.168.254.102 --json
```

| Check | Result |
|-------|--------|
| `portal-health` | ❌ timeout |
| `portal-status` | ❌ 401 |
| `peer-lmstudio` | ✅ PASS |

---

### Attempt 4 — Fresh `discover.py --force` + subnet scan

**Action:** Run repo `scripts/discover.py --force` after adding Windows subnet scan for remote Mac LM Studio.

```
Mac LM Studio found at 192.168.254.102 (subnet scan)
Mac: 192.168.254.102 — 4 models
Win: localhost — 7 models
```

**Artifact:** `~/.openclaw/state/last_discovery.json` updated with `endpoints.mac.ip = 192.168.254.102`.

---

### Attempt 5 — `start.ps1 --lan-peer --no-open` (post IP + bind fixes)

**Action:** Load `.env.local`, fresh discover, LAN bind, auto token from `PT/.state/control_plane_token`, peer probe.

```json
{
  "status": "fail",
  "peer_ip": "192.168.254.102",
  "checks": [
    { "name": "portal-health", "status": "PASS" },
    { "name": "portal-status", "status": "FAIL", "detail": "http 401 — check ORAMA_CONTROL_PLANE_TOKEN" },
    { "name": "peer-lmstudio", "status": "PASS" }
  ]
}
```

**Interpretation:**

- Win → Mac **portal reachability** (L2 health) ✅ after Mac ran `--lan-peer`.
- **Authenticated status** ❌ — tokens differ between hosts until Mac copies Win’s `ORAMA_CONTROL_PLANE_TOKEN` into `.env.local` (or shares `PT/.state/control_plane_token`).
- **Inference** ✅ both directions.

**Success artifact (when all checks PASS):** `~/.openclaw/state/last_lan_peer_probe.json` (local only, never commit).

---

### Attempt 6 — “Roundtrip message” (user-input queue)

**Not attempted end-to-end.** Cross-peer `POST /api/user-input` → remote PT `/user-input` is listed as
**optional v2 increment** in the playbook — not wired yet.

**Local round-trip (single host) works today:**

```powershell
# Win localhost only
curl -sX POST http://127.0.0.1:8000/user-input -H "Content-Type: application/json" -d "{\"message\":\"ping\",\"source\":\"cli\"}"
curl -s http://127.0.0.1:8000/user-input/next
```

---

## Code fixes shipped (stale IP → fresh discovery)

| Change | File | Behavior |
|--------|------|----------|
| Windows subnet scan for Mac | `scripts/discover.py` | When `$MAC_IP` unset and cache is `localhost`, scan `/24` for LM Studio |
| Mac URL in `.env.lmstudio` on Win | `scripts/discover.py` | `LM_STUDIO_MAC_ENDPOINT=http://<discovered-mac-ip>:1234` |
| Always run repo discover | `platform/windows/start.ps1` | `$RepoRoot/scripts/discover.py --force` before IP resolution |
| Read `last_discovery.json` | `platform/windows/start.ps1` | No gateway `.110` heuristic or hardcoded fallback |
| Load `.env.local` | `scripts/env/load-local.ps1` | Mirrors `load-local.sh` for Win |
| Token bootstrap | `platform/windows/start.ps1` | Generate/load `PT/.state/control_plane_token` when LAN bind on |
| Remove `.110` defaults | PT `agent_launcher.py`, `alphaclaw_bootstrap.py` | Empty default — discovery / `MAC_IP` env only |

---

## Operator checklist — full bidirectional portal (L1 + L2)

### Both hosts (one-time)

`.env.local` in orama-system root (gitignored):

```dotenv
PORTAL_BIND_LAN=1
ORAMA_BIND_LAN=1
PT_BIND_LAN=1
ORAMA_CONTROL_PLANE_TOKEN=<same-secret-on-both>
```

Copy token from Win after first `--lan-peer` start (logged as generated in `PT/.state/control_plane_token`)
or set manually on both machines.

### Win (`192.168.254.100`)

```powershell
$env:PERPETUA_TOOLS_PATH = "<canonical Perpetua-Tools clone>"
cd $env:ORAMA_SYSTEM_PATH
git pull --ff-only origin main
.\platform\windows\start.ps1 --stop
.\platform\windows\start.ps1 --lan-peer --no-open
python bin\orama-system\skills\hermes-harness\scripts\probe_lan_peer.py --json
```

### Mac (`192.168.254.102`)

```bash
cd "$ORAMA_SYSTEM_PATH"
git pull --ff-only origin main
./start.sh --stop
./start.sh --lan-peer --no-open
python3 bin/orama-system/skills/hermes-harness/scripts/probe_lan_peer.py --json
```

### Pass criteria (`probe_lan_peer.py`)

| Check | Meaning |
|-------|---------|
| `portal-health` | Peer Portal `:8002` reachable on LAN |
| `portal-status` | Shared Bearer token accepted |
| `peer-lmstudio` | Peer LM Studio `:1234` lists models |

Hermes: `/lan-peer-self-talk`

---

## Future plans (reuse-first, no new RPC layer)

From [`lan-peer-self-talk.md`](../../bin/orama-system/skills/hermes-harness/references/lan-peer-self-talk.md):

| Increment | Reuse | Status |
|-----------|-------|--------|
| Mac dashboard Win portal tile | `portal_server.py` Win LMS probe | Done |
| `probe_lan_peer.py` + `--lan-peer` launcher | Hermes thin skill | Done |
| Fresh Mac IP on Win (`discover.py` subnet scan) | `last_discovery.json` | Done (2026-06-28) |
| `POST /api/user-input` cross-peer | Portal proxy → PT `:8000` | Planned — point peer URL + token in envelope |
| Remote `api_server` dispatch (`:8001`) | Routed envelope | v2 — not shipped |
| Bidirectional Hermes/Codex on peer | Local PATH per host | Out of scope v1 — probe only |
| Gossip portal reachability in discovery | Extend `last_discovery.json` schema | v2 optional |

**Do not** add SSH, a second discovery system, or hardcoded LAN IPs.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Probe uses wrong Mac IP (e.g. `.110`) | `git pull`; run `start.ps1` (runs discover); verify `last_discovery.json` |
| `portal-health` timeout on peer | Peer needs `./start.sh --lan-peer` or `start.ps1 --lan-peer` |
| `portal-status` 401 | Same `ORAMA_CONTROL_PLANE_TOKEN` in both `.env.local` files |
| Win LAN ports closed | Restart with `--lan-peer`; confirm `PORTAL_BIND_LAN=1` in `.env.local` |
| `last_discovery.json` shows `localhost` for both | Run `python scripts/discover.py --force` on Win; Mac must have LM Studio on LAN |
| PT health probes `.110` for Ollama | Set `$env:MAC_IP=192.168.254.102` or refresh discovery after PT pull |

---

## Related memory (Perpetua-Tools)

- `.agent/memory/working/START_PS1_LAN_PEER_2026-06-28.md`
- `lesson_12ddf8cf63b9` — LAN peer HTTP-only self-talk
- `lesson_0d5d6b4a25eb`, `lesson_52add7792e48`, `lesson_51f853af60eb`, `lesson_998b0a438dd4` — `start.ps1` rehab
