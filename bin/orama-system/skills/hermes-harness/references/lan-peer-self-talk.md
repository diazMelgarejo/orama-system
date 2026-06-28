# LAN peer self-talk — Mac ↔ Win parallel orama-system installs

> **Goal:** Two orama-system clones (Mac + Win) on the same LAN can **see** and **probe**
> each other without new RPC infrastructure. Reuse discovery, HTTP probes, and the
> Hermes envelope — do not build a second control plane.

---

## What already talks today (no code changes)

| Channel | Direction | Mechanism | Code |
|---------|-----------|-----------|------|
| Inference | Mac → Win | HTTP `LM Studio` / Ollama on LAN IP | `verify_partner_canaries.py`, `portal_server.py` probes |
| Inference | Win → Mac | Same (localhost on Mac; LAN IP from peer) | `lan-endpoint-contract.md` locality rule |
| Discovery | Both | `~/.openclaw/state/last_discovery.json` | PT `lan_discovery.py`, `discover-lm-studio.sh` |
| Affinity | Both | `start.sh` / `start.ps1 --hardware-policy` | Shared policy files |
| Tier-1 status | Mac UI | `start.sh --status` aggregates Mac + Win models | Reads discovery + probes |

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
- [`docs/plans/2026-06-28-windows-powershell-todo.md`](../../../../docs/plans/2026-06-28-windows-powershell-todo.md)
- [`ecc-hermes-cross-harness.md`](ecc-hermes-cross-harness.md)
