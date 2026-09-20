---
name: offline-sandbox-agent-report
description: >-
  Canonical close-out format for agents with no LAN / not on the operator
  machine. Read docs/v2/references/offline-sandbox-agent-report.md first.
  Triggers on: offline agent report, sandbox agent report, Cursor Cloud
  close-out, no GossipBus, isolated VM, tip SHA + diffstat, Contents 403.
---

# offline-sandbox-agent-report

**Read first:** [`docs/v2/references/offline-sandbox-agent-report.md`](../../../docs/v2/references/offline-sandbox-agent-report.md)

That file is the canonical format. This card only activates it.

Dual-authority sibling (same skill name): Perpetua-Tools
`docs/coordination/offline-sandbox-agent-report.md`.

## When to use

- No LAN, no GossipBus board, not on the operator machine
- Cursor Cloud / GitHub sandbox / isolated VM close-out
- Operator asked for tip SHA + diffstat on a named PR/branch

## Do

1. Load the reference doc above before writing any report.
2. Soft-push onto the directed branch only.
3. Fill every field of the required report block (SHA, diffstat, PR URL).
4. If GitHub Contents write returns 403, stop and paste the exact error.

## Do not

- Open a new PR when told to reuse an existing one
- Merge or force-push
- Rewrite PR bodies
- Call GossipBus / LAN peer inbox as if they existed
- Drop the Perpetua-Tools Placement row
