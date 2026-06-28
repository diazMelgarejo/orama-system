# LAN peer self-talk — Mac ↔ Win parallel orama-system installs

> **Goal:** Two orama-system clones (Mac + Win) on the same LAN can **see** and **probe**
> each other without new RPC infrastructure. Reuse discovery, HTTP probes, and the
> Hermes envelope — do not build a second control plane.
>
> **Canonical operator playbook (Mac + Win — identical text):** [§ Operator playbook](#operator-playbook)

---

## Operator playbook

> **SSOT:** Both machines sync `main` and follow **this section** verbatim.
> Clean tree: `git pull --ff-only origin main`.
> Dirty tree: [`../../git-history-surgery/references/safe-cross-host-sync-reference-card.md`](../../git-history-surgery/references/safe-cross-host-sync-reference-card.md).
> Do not maintain forked Mac-only or Win-only copies of these steps.

### A. One-time setup (run on **each** host)

1. **Sync orama-system on `main`:**
   ```bash
   export ORAMA_SYSTEM_PATH="$(git -C /path/to/orama-system rev-parse --show-toplevel)"
   cd "$ORAMA_SYSTEM_PATH"
   git fetch origin --prune && git checkout main && git pull --ff-only origin main
   ```

2. **`.env.local`** in the orama-system clone root (never commit; **same token on both hosts**):
   ```dotenv
   PORTAL_BIND_LAN=1
   ORAMA_BIND_LAN=1
   ORAMA_CONTROL_PLANE_TOKEN=<same-secret-on-Mac-and-Win>
   # Joint-account (optional): PT lane + orama lane — when both set, either unlocks both
   # PT_CONTROL_PLANE_TOKEN=<PT/.state or explicit PT key>
   # ORAMA_CONTROL_PLANE_TOKEN_LOCAL=<orama portal key this host accepts>
   # ORAMA_CONTROL_PLANE_TOKEN_PEER=<peer key to try first on outbound probe>
   ```

3. **Discovery fresh** — peer IP must come from `~/.openclaw/state/last_discovery.json`
   (never hardcode DHCP). Refresh via PT `discover-lm-studio.sh` or the LAN watcher.

4. **Inference running locally** — LM Studio on Win (`localhost:1234`); Ollama/LMS on Mac
   per hardware policy.

5. **Install Hermes thin wrapper** (once per host after pull):
   ```bash
   python3 bin/orama-system/skills/hermes-harness/scripts/install_hermes_thin_skills.py --install --verify
   ```
   Windows: use `python` instead of `python3`.

6. **Restart portal/stack** if already running so `PORTAL_BIND_LAN=1` takes effect.
   Shortcut on Mac: `./start.sh --stop && ./start.sh --lan-peer --no-open` (sets bind flags
   and runs `probe_lan_peer.py` after start). Windows: `.\platform\windows\start.ps1 --lan-peer`.

**Note:** Mac→Win **inference** (models over LAN) works without portal bind. Portal bind
is required only for peer `/health` and `/api/status` on port 8002.

### B. What to tell Hermes (copy-paste)

**Slash command (preferred):**
```
/lan-peer-self-talk
```

**Plain English:**
```
Probe the LAN peer orama install. Use last_discovery.json for the peer IP, run
probe_lan_peer.py --json from ORAMA_SYSTEM_PATH, and report every check in checks[].
```

**JSON envelope** (programmatic dispatch):
```json
{
  "skill_id": "lan-peer-self-talk",
  "args": { "probe": "full", "json": true },
  "agent_id": "hermes",
  "harness": "hermes",
  "orama_system_root": "$ORAMA_SYSTEM_PATH",
  "transport": { "partner": "hermes", "profile": "lan-peer-probe" }
}
```

Hermes must run (from `$ORAMA_SYSTEM_PATH`):

```bash
python3 bin/orama-system/skills/hermes-harness/scripts/probe_lan_peer.py --json
```

Windows equivalent:

```powershell
python bin\orama-system\skills\hermes-harness\scripts\probe_lan_peer.py --json
```

### C. Pass criteria (`checks[]`)

| Check | PASS means |
|-------|------------|
| `portal-health` | Peer portal `GET /health` on LAN `:8002` |
| `portal-status` | Peer `GET /api/status` with shared bearer token |
| `peer-lmstudio` | Peer `GET /v1/models` at discovery IP + port |

On **SUCCESS**, probe writes a local-only artifact (never commit):

`~/.openclaw/state/last_lan_peer_probe.json`

Hermes must print `SUCCESS` and the full path in the operator reply.

### D. If a check fails

| Failure | Fix |
|---------|-----|
| `portal-health` FAIL | Set `PORTAL_BIND_LAN=1`, restart portal on **peer** |
| `portal-status` FAIL | Align tokens: same `ORAMA_CONTROL_PLANE_TOKEN` on both hosts, or set `ORAMA_CONTROL_PLANE_TOKEN_PEER` to the peer's token (probe tries all candidates) |
| `peer-lmstudio` FAIL | Re-run discovery; ensure LM Studio listening on peer |
| No peer IP | Refresh `last_discovery.json`; do not hardcode LAN IP |

### F. File-based work assignments (autoresearch fan-out)

Use **markdown/plain-text drops** instead of streaming large payloads over WS.
Peer reads files from `~/.openclaw/state/lan_peer/inbox/` on the receiving host.

**Win → Mac assignment:**

```powershell
cd $env:ORAMA_SYSTEM_PATH
python bin\orama-system\skills\hermes-harness\scripts\lan_peer_assign.py drop --peer `
  --file .\tasks\mac-hypothesis.md `
  --assignee mac --topic autoresearch/hypothesis `
  --fanout-id 2026-06-28-001
```

**Mac reads peer inbox:**

```bash
python3 bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py list --peer
python3 bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py read --peer \
  --name 2026-06-28-mac-hypothesis.md
```

**Fan-out manifest (split topics per host):**

```json
{
  "fanout_id": "2026-06-28-autoresearch-001",
  "assignments": [
    {"assignee": "mac", "topic": "hypothesis", "filename": "mac-hypothesis.md", "path": "./tasks/mac.md"},
    {"assignee": "win", "topic": "gpu-run", "filename": "win-gpu.md", "path": "./tasks/win.md"}
  ]
}
```

```bash
python3 bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py fanout \
  --manifest bin/orama-system/skills/hermes-harness/references/autoresearch-fanout-example.json
```

HTTP API (Bearer token): `POST /api/peer-file`, `GET /api/peer-inbox`, `GET /api/peer-inbox/{filename}`.

WS/SSE remain for **heartbeat + probe** only; assignments travel as files.

### E. What Hermes cannot do (today)

| Not supported | Why |
|---------------|-----|
| Run Hermes/Codex **on** the peer host | Partners are local PATH per machine — probe only |
| SSH to Win for setup | Use HTTP only (`:22` not required) |
| Remote `api_server` dispatch | v2 increment — not shipped yet |

For cross-host **inference** (e.g. Mac using Win 27B), use `verify_partner_canaries.py`
and `start.sh --status` / `start.ps1 --status` — not a separate Hermes RPC layer.

---

## What already talks today (no code changes)

| Channel | Direction | Mechanism | Code |
|---------|-----------|-----------|------|
| Inference | Mac → Win | HTTP `LM Studio` / Ollama on LAN IP | `verify_partner_canaries.py`, `portal_server.py` probes |
| Inference | Win → Mac | Same (localhost on Mac; LAN IP from peer) | `lan-endpoint-contract.md` locality rule |
| Discovery | Both | `~/.openclaw/state/last_discovery.json` | PT `lan_discovery.py`, `discover-lm-studio.sh` |
| Affinity | Both | `start.sh` / `start.ps1 --hardware-policy` | Shared policy files |
| Tier-1 status | Mac UI | `start.sh --status` aggregates Mac + Win models | Reads discovery + probes |
| Work assignments | Both | HTTP file inbox (`/api/peer-file`) | `lan_peer_assign.py`, `~/.openclaw/state/lan_peer/inbox/` |

**Proof (2026-06-28):** Mac `verify_partner_canaries.py` against Win LAN URL returned
`LM_READY` on 27B; `start.sh --status` showed Tier 1 FULL for both nodes.

---

## What does *not* talk yet (gap)

| Gap | Why |
|-----|-----|
| Mac portal → Win portal `:8002` | Services default-bind `localhost` unless `*_BIND_LAN=1` |
| Win Hermes from Mac SSH | `GPU_BOX` SSH `:22` timed out — use HTTP, not SSH |
| orama API `:8001` peer dispatch | No routed envelope to remote `api_server` yet |
| Bidirectional agent dispatch | Partners (Hermes/Codex) are **local PATH** per host |

---

## Minimal changes to pipe Mac ↔ Win (reuse-first)

### 1. Enable LAN bind (both hosts, `.env.local`)

```dotenv
PORTAL_BIND_LAN=1
ORAMA_BIND_LAN=1
ORAMA_CONTROL_PLANE_TOKEN=<same-secret-on-both>
```

Implementation already exists: `src/utils/control_plane_auth.py::default_bind_host()`.

### 2. Run the peer probe (new thin script)

```bash
python3 bin/orama-system/skills/hermes-harness/scripts/probe_lan_peer.py --json
```

Checks:

- Peer IP from `last_discovery.json` (never hardcode DHCP IP)
- Peer portal `GET /health` (public)
- Peer portal `GET /api/status` (Bearer token when set)
- Peer LM Studio `GET /v1/models`

### 3. Optional next increment (no new services)

| Increment | Reuse | Effort |
|-----------|-------|--------|
| Mac dashboard shows Win portal tile | `portal_server.py` already probes Win LMS | Done |
| POST `/api/user-input` cross-peer | Existing portal proxy to PT `:8000` | Add peer URL + token in envelope |
| Codex fanout on peer tests | `dispatch_codex_partner.py` pattern | Point `--pytest` at peer clone via SSH or shared git — SSH optional |
| Hermes `/lan-peer-self-talk` slash | `install_hermes_thin_skills.py` wrapper | Done with command card |

**Do not** add a second discovery system. Extend `last_discovery.json` schema only if
portal reachability must be gossiped (v2).

---

## Repurpose map (existing assets)

| Asset | Repurpose for LAN self-talk |
|-------|----------------------------|
| `last_discovery.json` | Peer IP + model catalog |
| `verify_partner_canaries.py` | Inference readiness (LM/Hermes) per host |
| `probe_lan_peer.py` | Control-plane + inference peer probe |
| `portal_server.py` `/api/status` | Aggregated health JSON (redacted) |
| `hermes-universal-invocation-protocol.md` | Envelope for `skill_id: lan-peer-self-talk` |
| `lan-endpoint-contract.md` | Locality rule (localhost vs LAN IP) |
| `install_hermes_thin_skills.py` | Install `/lan-peer-self-talk` on Hermes |
| `pt-orama-harness-integration` | Absorbed → this harness |

---

## Skill: `/lan-peer-self-talk`

Command card: [`../commands/lan-peer-self-talk/SKILL.md`](../commands/lan-peer-self-talk/SKILL.md)

**Envelope example:**

```json
{
  "skill_id": "lan-peer-self-talk",
  "args": { "probe": "full", "json": true },
  "agent_id": "hermes",
  "harness": "hermes",
  "orama_system_root": "$ORAMA_SYSTEM_PATH",
  "transport": { "partner": "hermes", "profile": "lan-peer-probe" }
}
```

**Result shape:** core superset with `checks[]` mirroring `probe_lan_peer.py` output.

---

## Security

- `/health` is public; `/api/status` requires `ORAMA_CONTROL_PLANE_TOKEN`.
- Never commit tokens or LAN IPs in tracked files.
- Bind LAN only on trusted home subnets; firewall Win ports if exposed beyond LAN.

---

## Related

- [`win-localhost-runtime-checklist.md`](win-localhost-runtime-checklist.md)
- [`docs/guides/lan-peer-mac-win-operator.md`](../../../../docs/guides/lan-peer-mac-win-operator.md) — `docs/` navigation entry (links here)
- [`docs/guides/lan-peer-bidirectional-talk-2026-06-28.md`](../../../../docs/guides/lan-peer-bidirectional-talk-2026-06-28.md) — live attempts, probe matrix, future plan
- [`docs/plans/2026-06-28-windows-powershell-todo.md`](../../../../docs/plans/2026-06-28-windows-powershell-todo.md)
- [`ecc-hermes-cross-harness.md`](ecc-hermes-cross-harness.md)
