---
name: lan-peer-self-talk
description: >-
  Probe and coordinate with the parallel orama-system install on the LAN peer
  (Mac↔Win). Uses discovery JSON + HTTP — no SSH required.
version: 1.0.0
license: Apache 2.0
compatibility: hermes, macos, windows
parent_skill: hermes-harness
triggers:
  - lan-peer-self-talk
  - lan peer
  - peer orama
  - mac win self talk
allowed-tools: bash, file-operations
---

# LAN Peer Self-Talk

Use when both orama-system clones (Mac + Win) are on the same LAN and you need
to verify they can see each other — inference endpoints **and** optional portal
health — without inventing new RPC.

## Prerequisites

1. `last_discovery.json` fresh (`scripts/discover-lm-studio.sh` or PT watcher).
2. On **both** hosts when portal peer access is needed:

   ```dotenv
   PORTAL_BIND_LAN=1
   ORAMA_CONTROL_PLANE_TOKEN=<shared-secret>
   ```

3. Locality rule: probe peer inference via LAN IP; probe local via `localhost`.
   See [`../../references/lan-endpoint-contract.md`](../../references/lan-endpoint-contract.md).

## Run probe

```bash
python3 bin/orama-system/skills/hermes-harness/scripts/probe_lan_peer.py --json
```

Windows:

```powershell
python bin\orama-system\skills\hermes-harness\scripts\probe_lan_peer.py --json
```

## Envelope

```json
{
  "skill_id": "lan-peer-self-talk",
  "args": { "probe": "full" },
  "agent_id": "hermes",
  "harness": "hermes",
  "orama_system_root": "$ORAMA_SYSTEM_PATH"
}
```

Return core result with `checks` populated from probe output.

## Windows operator checklist

Full PowerShell TODO: [`../../../../../../docs/plans/2026-06-28-windows-powershell-todo.md`](../../../../../../docs/plans/2026-06-28-windows-powershell-todo.md)

## References

- [`../../references/lan-peer-self-talk.md`](../../references/lan-peer-self-talk.md) — architecture + minimal changes
- [`../../references/win-localhost-runtime-checklist.md`](../../references/win-localhost-runtime-checklist.md)
- [`../../scripts/probe_lan_peer.py`](../../scripts/probe_lan_peer.py)
