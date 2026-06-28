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

**Interpretation (post-fix, Win `start.ps1 --lan-peer`):**

- Banner shows **`192.168.254.102`** (source: `last_discovery.json`) — not stale `.110`
- Win → Mac **portal-health** ✅ · **peer-lmstudio** ✅
- **portal-status** ❌ `401` until Mac `.env.local` has the **same** token as `PT/.state/control_plane_token`
- Win Portal **LAN** `192.168.254.100:8002/health` ✅ (Mac can probe back after token sync)

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
| `scripts/env/print-lan-peer-token.ps1` | Win → Mac token handoff for `.env.local` |
| Token bootstrap | `platform/windows/start.ps1` | Generate/load `PT/.state/control_plane_token` when LAN bind on |
| Remove `.110` defaults | PT `agent_launcher.py`, `alphaclaw_bootstrap.py` | Empty default — discovery / `MAC_IP` env only |

---

## Operator checklist — full bidirectional portal (L1 + L2)

**Token handoff (Win → Mac):**

```powershell
.\scripts\env\print-lan-peer-token.ps1
```

Paste the printed line into Mac `orama-system/.env.local`, then `./start.sh --lan-peer --no-open` on Mac.

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

---

## Open-source options — simplest / most frugal full bidirectional LAN talk (2026-06-28)

> **Context:** orama-system runs Python FastAPI on both Mac and Win (ports 8000/8001/8002).
> The ruling constraint from the Future Plans table is **reuse-first, no new RPC layer.**
> Everything below is ranked by (deps added, code complexity, P2P purity).

---

### Candidate survey

#### 1. FastAPI WebSocket — zero new deps (recommended)

`fastapi[standard]` already bundles `websockets`. Zero new packages.

**Pattern — dual-socket:** each host exposes a WS server endpoint **and** connects as a WS
client to the peer's endpoint. After handshake, both sides have a full-duplex channel.

```python
# In portal_server.py — server side (each host)
@app.websocket("/ws/portal-peer")
async def portal_peer_ws(ws: WebSocket):
    await ws.accept()
    async for msg in ws.iter_json():
        await handle_peer_event(msg)

# Background task on startup — client side (connects to peer)
async def connect_to_peer(peer_ip: str):
    async with websockets.connect(f"ws://{peer_ip}:8002/ws/portal-peer") as ws:
        async for msg in ws:
            await handle_peer_event(json.loads(msg))
```

| Axis | Score |
|------|-------|
| New packages | 0 |
| Lines of code to wire | ~40 |
| P2P purity | Dual-socket (both sides server+client) |
| Latency | Sub-millisecond on LAN |
| Auto-reconnect | Must implement (trivial loop) |
| Cross-language | Yes (any WS client speaks it) |

**Verdict: fits the reuse-first rule perfectly.**

---

#### 2. `websockets` library — 1 dep, standalone peer daemon

[`websockets`](https://github.com/python-websockets/websockets) — pure Python, no C
extensions, ~150 KB installed. More ergonomic than embedding WS in FastAPI for a
**standalone peer-sync daemon** running beside the portal.

```bash
pip install websockets  # 150 KB, no binary deps
```

```python
import asyncio, websockets, json

async def peer_daemon(my_port: int, peer_ip: str, peer_port: int):
    async def handler(ws):
        async for msg in ws:
            await handle(json.loads(msg))
    server = await websockets.serve(handler, "0.0.0.0", my_port)
    async with websockets.connect(f"ws://{peer_ip}:{peer_port}") as peer:
        await asyncio.gather(server.wait_closed(), recv_loop(peer))
```

Useful if you want a **separated process** (not entangled with portal_server.py) that
owns the bidirectional LAN channel.

---

#### 3. ZeroMQ PAIR sockets — 1 dep, true P2P semantics

[`pyzmq`](https://github.com/zeromq/pyzmq) — thin Python binding to libzmq (~1 MB).
**PAIR** = exclusive bidirectional socket: one host binds, the other dials; after connect
both `send` / `recv` with no protocol framing overhead.

```bash
pip install pyzmq  # ~1 MB native, cross-platform
```

```python
import zmq.asyncio, asyncio

async def zmq_peer(bind: bool, peer_ip: str, port: int = 5556):
    ctx = zmq.asyncio.Context()
    sock = ctx.socket(zmq.PAIR)
    if bind:
        sock.bind(f"tcp://*:{port}")
    else:
        sock.connect(f"tcp://{peer_ip}:{port}")
    # Both sides: send / recv freely once connected
    while True:
        msg = await sock.recv_json()
        await handle(msg)
```

**Decision rule:** if you need sub-ms throughput or to fan out to more than 2 hosts
in the future, ZeroMQ is the pragmatic upgrade. PAIR is 1-to-1; swap to PUB/SUB or
ROUTER/DEALER for N-to-N later — same library.

---

#### 4. Server-Sent Events + HTTP POST — zero deps, HTTP-only hybrid

Not true full-duplex, but zero infra change:

- **Push (server → client):** SSE endpoint `GET /events` streams `text/event-stream`.
  FastAPI supports this natively with `EventSourceResponse` (or plain `StreamingResponse`).
- **Push (client → server):** existing `POST /api/user-input`.

Each machine is both an SSE server (for its peer to subscribe to) and an SSE client
(consuming its peer's event stream). No new packages.

**Limitation:** HTTP/1.1 SSE is half-duplex per connection. True simultaneous push in
both directions needs two connections (one in each direction). Workable but less elegant
than WS.

---

#### 5. Mosquitto MQTT — 1 dep + 1 lightweight broker process

[`paho-mqtt`](https://github.com/eclipse/paho.mqtt.python) + Mosquitto broker (~25 KB binary,
negligible RAM).

```bash
pip install paho-mqtt          # Python client
# Run broker on either machine (once, stays running):
# Windows: mosquitto -c mosquitto.conf
# Mac: brew services start mosquitto
```

Each host publishes to `orama/win/events` and subscribes to `orama/mac/events` (and vice
versa). Full pub/sub semantics, auto-reconnect, retained messages, QoS levels.

**When it shines:** more than 2 peers, or when you want durable message queues between
restarts. Adds a 3rd process to manage. For a 2-host setup it is feature-overkill.

---

#### 6. gRPC bidirectional streaming — structured cross-language, heavier

[`grpcio`](https://github.com/grpc/grpc) + `grpcio-tools`. HTTP/2 transport; define a
`.proto` with `stream` in both directions.

```protobuf
service PortalPeer {
  rpc Talk(stream PeerEvent) returns (stream PeerEvent);
}
```

**When it shines:** strong schema contract needed; TypeScript / Node.js on one side
(Bun/portal web), Python on the other. Adds proto compilation step + ~5 MB deps.

---

#### 7. mDNS / Zeroconf — for zero-config discovery (orthogonal to transport)

[`zeroconf`](https://github.com/python-zeroconf/python-zeroconf) — 1 pure-Python dep.
Announces `_orama._tcp.local.` on the LAN; the peer discovers the IP/port automatically.
Removes the need for `$MAC_IP` / `$WIN_IP` env vars entirely.

```bash
pip install zeroconf
```

```python
from zeroconf import ServiceInfo, Zeroconf

info = ServiceInfo("_orama._tcp.local.", "win._orama._tcp.local.",
                   addresses=[socket.inet_aton("0.0.0.0")], port=8002)
zc = Zeroconf()
zc.register_service(info)
# Peer:
browser = ServiceBrowser(zc, "_orama._tcp.local.", MyListener())
```

Pairs with any of the transports above. This is the zero-config upgrade to the existing
`discover.py` subnet scan.

---

### Comparison table

| Option | New pkgs | Code LoC | P2P purity | LAN latency | Reconnect | Notes |
|--------|----------|----------|------------|-------------|-----------|-------|
| **FastAPI WebSocket** | **0** | ~40 | Dual-socket | <1 ms | Manual loop | Best reuse-first fit |
| `websockets` daemon | 1 | ~60 | Dual-socket | <1 ms | Built-in backoff | Isolated process |
| ZeroMQ PAIR | 1 | ~30 | True PAIR | <0.1 ms | Auto-retry | Best if scaling to N peers |
| SSE + POST | 0 | ~50 | 2 connections | ~1 ms | Manual | HTTP-only, no upgrade |
| MQTT + Mosquitto | 1 + broker | ~30 | Pub/Sub | ~1 ms | Auto | Overkill for 2 hosts |
| gRPC bidirec. | 2+ | ~100+ | True stream | <1 ms | Auto | Best cross-language |
| mDNS (zeroconf) | 1 | ~20 | (discovery) | N/A | Auto-announce | Orthogonal; pairs with any |

---

### Recommendation for orama-system

**Immediate (zero deps):** add `GET /ws/portal-peer` to `portal_server.py` and a
`lifespan`-managed background coroutine that connects as a WS client to
`ws://{PEER_IP}:8002/ws/portal-peer`. This directly enables L3 agent dispatch
(`POST /api/user-input` cross-peer) without any new packages or processes.

**Optional upgrade — discovery:** `pip install zeroconf` and announce `_orama._tcp.local.`
from `start.py` / `start.ps1` at startup. Eliminates dependence on `$MAC_IP` / `$WIN_IP`
env vars and makes the LAN stack truly zero-config.

**Do not add:** SSH tunnels, a second discovery daemon, or hardcoded LAN IPs.
The `reuse-first` rule in the Future Plans table above governs.

```
FastAPI WebSocket  +  (optional) zeroconf mDNS
       ↑ L3 transport              ↑ L1 discovery
```

---

## Implementation plan — WS primary + SSE/POST fallback (2026-06-28)

> **Decision:** try WebSocket first; fall back to SSE + HTTP POST if WS is unavailable.
> Zero new dependencies for both paths. FastAPI supports both natively.

---

### Transport stack

```
Primary:   ws://{PEER_IP}:8002/ws/portal-peer   ← full-duplex, 1 connection
Fallback:  GET  http://{PEER_IP}:8002/events/peer-stream   ← peer → us (SSE)
           POST http://{PEER_IP}:8002/api/peer-event        ← us → peer (HTTP)
```

Each host is simultaneously a **server** (accepting WS connections and serving the SSE
stream) and a **client** (dialling the peer's WS and subscribing to the peer's SSE).

---

### Connection state machine

```
IDLE
 └─► WS_CONNECTING  (attempt ws://{peer}:8002/ws/portal-peer, 5 s timeout)
       ├─ success ─► WS_CONNECTED  ──► [heartbeat loop]
       │               └─ drop ─────────────────────────────────┐
       └─ fail    ─► SSE_CONNECTING (GET /events/peer-stream)   │
                      ├─ success ─► SSE_CONNECTED               │
                      │               └─ drop ──────────────────┘
                      └─ fail    ─► DISCONNECTED  (retry in 30 s)
                                     └─► WS_CONNECTING (loop)
```

Reconnect: WS drop → immediate retry → WS_CONNECTING; two consecutive WS failures →
demote to SSE_CONNECTING for one attempt before retrying WS.

---

### Shared event schema (both transports)

```json
{
  "type":   "heartbeat | status | user-input | peer-event | ...",
  "source": "win | mac",
  "ts":     1719561600,
  "data":   {}
}
```

Both transports use the same JSON envelope — the channel manager abstracts the wire.

---

### Files to create / modify

| File | Change |
|------|--------|
| `src/orama_system/portal_server.py` | Add WS endpoint, SSE endpoint, POST inbound endpoint, lifespan hook |
| `src/orama_system/lan_peer_channel.py` | **New** — ~120 lines — channel manager (state machine, send, subscribe) |
| `bin/orama-system/skills/hermes-harness/scripts/probe_lan_peer.py` | Add `ws-peer` check to existing probe |

No new entries in `requirements.txt`.

---

### Phase breakdown

#### Phase 1 — Server endpoints in `portal_server.py`

```python
# WS server — peer connects here
@app.websocket("/ws/portal-peer")
async def ws_portal_peer(ws: WebSocket):
    await ws.accept()
    _channel.register_ws_peer(ws)
    try:
        async for msg in ws.iter_json():
            await _channel.on_inbound(msg)
    finally:
        _channel.unregister_ws_peer(ws)

# SSE server — peer subscribes here (fallback downlink)
@app.get("/events/peer-stream")
async def sse_peer_stream(request: Request):
    async def generator():
        async for event in _channel.outbound_queue():
            yield f"data: {json.dumps(event)}\n\n"
    return StreamingResponse(generator(), media_type="text/event-stream")

# POST inbound — peer POSTs here when WS unavailable (fallback uplink)
@app.post("/api/peer-event")
async def post_peer_event(event: dict, request: Request):
    await _channel.on_inbound(event)
    return {"ok": True}
```

#### Phase 2 — `lan_peer_channel.py` (new file)

Core responsibilities:
- Hold `state: Literal["idle","ws_connecting","ws_connected","sse_connecting","sse_connected","disconnected"]`
- `connect(peer_ip, peer_port)` — entry point, runs the state machine
- `send(event: dict)` — routes to WS send or `POST /api/peer-event` depending on state
- `on_inbound(event: dict)` — dispatches to registered handlers
- `outbound_queue()` — async generator for the SSE server endpoint to drain
- `_ws_connect_loop()` — tries WS, sets state, starts heartbeat
- `_sse_connect_loop()` — subscribes to peer SSE stream via `httpx.AsyncClient`
- `_heartbeat()` — sends `{"type":"heartbeat"}` every 15 s; detects silent drops

```python
# Minimal shape — not final
class LanPeerChannel:
    state: str = "idle"
    _ws: WebSocket | None = None
    _out_queue: asyncio.Queue = asyncio.Queue()

    async def connect(self, peer_ip: str, port: int = 8002): ...
    async def send(self, event: dict): ...
    async def on_inbound(self, event: dict): ...
    async def outbound_queue(self) -> AsyncGenerator: ...
```

#### Phase 3 — Wire into `lifespan` in `portal_server.py`

```python
from contextlib import asynccontextmanager

_channel = LanPeerChannel()

@asynccontextmanager
async def lifespan(app: FastAPI):
    peer_ip = os.getenv("PEER_IP") or _read_last_discovery_peer_ip()
    if os.getenv("PORTAL_BIND_LAN") and peer_ip:
        asyncio.create_task(_channel.connect(peer_ip))
    yield
    await _channel.close()
```

`_read_last_discovery_peer_ip()` reads `~/.openclaw/state/last_discovery.json` — same
source `start.ps1` uses. No new env vars.

#### Phase 4 — Add `ws-peer` check to `probe_lan_peer.py`

```python
# New check alongside portal-health / portal-status / peer-lmstudio
async def check_ws_peer(peer_ip: str) -> CheckResult:
    try:
        async with websockets.connect(
            f"ws://{peer_ip}:8002/ws/portal-peer", open_timeout=5
        ) as ws:
            await ws.send(json.dumps({"type": "probe", "source": platform()}))
            pong = await asyncio.wait_for(ws.recv(), timeout=5)
            return CheckResult("ws-peer", "PASS", detail=pong)
    except Exception as e:
        return CheckResult("ws-peer", "FAIL", detail=str(e))
```

#### Phase 5 — L3 agent dispatch (deferred, after Phase 1–4 green)

When channel is `WS_CONNECTED` or `SSE_CONNECTED`, the portal can forward
`POST /api/user-input` payloads cross-peer:

```python
await _channel.send({"type": "user-input", "source": platform(), "data": payload})
```

Remote host receives via `on_inbound`, enqueues into its local PT `/user-input` queue.
This closes the L3 gap in the attempt log above.

---

### Pass criteria (per phase)

| Phase | Test |
|-------|------|
| 1 | `wscat -c ws://localhost:8002/ws/portal-peer` → accepted; SSE `curl -N .../events/peer-stream` → streams; POST `curl -X POST .../api/peer-event -d '{}'` → `{"ok":true}` |
| 2–3 | `probe_lan_peer.py --json` shows `ws-peer: PASS` from both sides |
| 4 | `probe_lan_peer.py --json` includes `ws-peer` check in output |
| 5 | Cross-peer `POST /api/user-input` → remote `GET /api/user-input/next` returns message |

---

## Related memory (Perpetua-Tools)

- `.agent/memory/working/START_PS1_LAN_PEER_2026-06-28.md`
- `lesson_12ddf8cf63b9` — LAN peer HTTP-only self-talk
- `lesson_0d5d6b4a25eb`, `lesson_52add7792e48`, `lesson_51f853af60eb`, `lesson_998b0a438dd4` — `start.ps1` rehab
