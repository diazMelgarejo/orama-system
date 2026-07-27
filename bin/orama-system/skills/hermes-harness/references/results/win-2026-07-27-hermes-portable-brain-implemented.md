# Hermes portable brain export/restore implemented

**Fan-out:** coord-034  
**Status:** DONE  
**From:** hermes  
**Date:** 2026-07-27

## Audience

| Lane | Action |
|------|--------|
| win-cursor | Use the new Orama Harness portable-brain script/reference as the SSoT for restoring Hermes onto fresh installs. |
| win-coder | Review/extend `hermes_portable_brain.py` if future code hardening is needed. |
| win-autoresearcher | No GPU action; note restored Hermes state can include sessions only with explicit flag. |
| mac-orchestrator | Pull this card from Win portal if peer push remains 401; compare against Mac Hermes profile install flow. |
| mac-researcher | No action unless validating cross-platform restore semantics. |
| hermes | Use this recipe next time: dry-run export, inspect manifest, restore dry-run, then apply. |

## What landed

- Added `bin/orama-system/skills/hermes-harness/scripts/hermes_portable_brain.py`.
- Added `bin/orama-system/skills/hermes-harness/references/hermes-portable-brain-archive.md`.
- Rewrote `bin/orama-system/skills/hermes-harness/references/hermes-portable-brain-map.md` for accuracy.
- Updated `bin/orama-system/skills/hermes-harness/references/openclaw-to-hermes-migration.md` to include actual current-Hermes archive/restore flow.
- Updated `bin/orama-system/skills/hermes-harness/commands/windows-hermes-setup/SKILL.md` to link the new archive reference.
- Improved root plan: `../2026-07-26_111557-hermes-openclaw-migration-cross-repo-plan.md` with dry-run/accuracy findings and implementation notes.
- Recorded PT `.agent` lessons/self-reflection in `Perplexity-Tools/.agent/memory/`.

## Verification

```bash
python bin/orama-system/skills/hermes-harness/scripts/hermes_portable_brain.py export --output $HERMES_HOME/cache/hermes-brain-test.zip --dry-run
python bin/orama-system/skills/hermes-harness/scripts/hermes_portable_brain.py export --output $HERMES_HOME/cache/hermes-brain-test.zip --include-sessions
python bin/orama-system/skills/hermes-harness/scripts/hermes_portable_brain.py inspect $HERMES_HOME/cache/hermes-brain-test.zip --summary
python bin/orama-system/skills/hermes-harness/scripts/hermes_portable_brain.py --hermes-home $HERMES_HOME/cache/restore-dryrun-target/hermes restore $HERMES_HOME/cache/hermes-brain-test.zip --include-sessions --dry-run
python -m py_compile bin/orama-system/skills/hermes-harness/scripts/hermes_portable_brain.py
```

Observed: schema `hermes-portable-brain/v1`; non-secret dry-run had 676 entries; include-sessions archive had 698 entries; restore dry-run planned 698 files and skipped 0.

## Current comms / LAN notes

- Local GossipBus was empty before this fanout (`no agents registered`, no claims, no tracked heartbeats, queue empty).
- Local peer inbox listed 78 files.
- Bidirectional peer check: local Win inbox works; Mac peer inbox list/drop still returns HTTP 401 / `SECURITY_STOP` for bearer-over-HTTP push path. Mac should pull from Win portal using `win-2026-07-27-mac-pull-from-win-portal.md` until portal auth/TLS policy is reconciled.
- `probe_lan_peer.py --json`: portal-health PASS, portal-status PASS, peer-lmstudio PASS, ws-peer FAIL due SSL wrong-version.

## Open / deferred

- Decide whether portable brain archive should be operator-only, local scheduled harness, or Hermes cron.
- Decide whether sessions should be included by default in operator runbooks; script currently requires `--include-sessions` explicitly.
- Secrets remain opt-in only (`--include-secrets`) and private archives must stay outside git-tracked repos.
