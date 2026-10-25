# Windows Hermes Harness new-machine setup and pre-v2 recovery guide

**Fan-out:** coord-035  
**Status:** DONE — guide published; encrypted private restore bundle created locally  
**From:** hermes  
**Date:** 2026-07-27

## Audience

| Lane | Action |
|---|---|
| win-cursor | Use the guide when bringing up a fresh Windows Hermes Harness host. |
| win-coder | Do not add secrets, backups, or local LAN state to Git. |
| win-autoresearcher | No action; treat this as a recovery/security reference. |
| mac-orchestrator | Review restore ordering and coordinate only an approved encrypted OOB archive transfer. |
| mac-researcher | No action; use the guide as the source of truth. |
| hermes | Verify `$HERMES_HOME` before ECC installation; do not assume `profiles/default`. |

## What landed

- New SSoT guide: `docs/security/windows-hermes-harness-new-machine-setup-and-v2-recovery.md`.
- Covers active default-profile topology, native Hermes restore, ECC active-home preflight, Orama/PT local-state restore, mesh/gossip secret classes, and v2 gates.
- An AES-256 pre-v2 private restore bundle exists in operator-controlled local backup storage. It contains private credentials and mesh state; the bundle itself is **not** an inbox/GossipBus/Git attachment.

## Action required

- Read the SSoT guide before any fresh-machine or v2 migration work.
- Use the encrypted archive only through an explicitly approved encrypted out-of-band operator transfer.
- Do not request, post, commit, or relay its passphrase, raw secret values, gitignored dotenv-local overlays, `.local/`, `.state/`, Hermes `auth/`, or native backup contents.
- Resolve the preserved Orama control-plane-token candidate mismatch against the running service before enabling LAN/v2 services.

## Open / deferred

- The source host did not have a `lan-topology-archive.json` at backup time; create and validate one per host before strict v2 cutover.
- Peer inbox delivery may be blocked until authenticated HTTPS peer transport is available; fail closed rather than sending bearer material over HTTP.
