---
name: lan-peer-self-talk
description: >-
  Probe and coordinate with the parallel orama-system install on the LAN peer
  (Mac↔Win). Uses discovery JSON + HTTP — no SSH required.
version: 1.0.1
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

> **Canonical operator instructions (Mac + Win — identical):**
> [`../../references/lan-peer-self-talk.md` § Operator playbook](../../references/lan-peer-self-talk.md#operator-playbook)
>
> Both machines must `git pull --ff-only origin main` and follow that section verbatim.

## Procedure

1. Load the [Operator playbook](../../references/lan-peer-self-talk.md#operator-playbook).
2. Verify prerequisites (`.env.local`, discovery, thin wrapper installed).
3. Run `probe_lan_peer.py --json` or accept the slash command `/lan-peer-self-talk`.
4. Return core result with `checks[]` from probe output. On success, report
   `SUCCESS` and the local artifact path `~/.openclaw/state/last_lan_peer_probe.json`
   (`result_path` in JSON mode).

## Envelope

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

## References

- [`../../references/lan-peer-self-talk.md`](../../references/lan-peer-self-talk.md) — architecture + operator playbook
- [`../../references/lan-endpoint-contract.md`](../../references/lan-endpoint-contract.md) — localhost vs LAN IP
- [`../../references/win-localhost-runtime-checklist.md`](../../references/win-localhost-runtime-checklist.md)
- [`../../scripts/probe_lan_peer.py`](../../scripts/probe_lan_peer.py)
- Mac handoff: [`../../../../../../docs/plans/2026-06-28-mac-e2e-handoff.md`](../../../../../../docs/plans/2026-06-28-mac-e2e-handoff.md)
- Win checklist: [`../../../../../../docs/plans/2026-06-28-windows-powershell-todo.md`](../../../../../../docs/plans/2026-06-28-windows-powershell-todo.md)
