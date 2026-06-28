# LAN peer Mac ↔ Win — operator guide

> **Canonical SSOT (Mac + Win read the same file after `git pull`):**
> [`bin/orama-system/skills/hermes-harness/references/lan-peer-self-talk.md`](../../bin/orama-system/skills/hermes-harness/references/lan-peer-self-talk.md#operator-playbook)
>
> This `docs/guides/` page is a **navigation entry** only. Do not fork operator steps here.

## Quick start (both hosts)

```bash
cd "$ORAMA_SYSTEM_PATH"
git pull --ff-only origin main
```

1. Follow playbook **§A** — `.env.local` bind + shared token, fresh discovery, thin wrappers.
2. Start with LAN bind shortcut:
   - **Mac:** `./start.sh --stop && ./start.sh --lan-peer --no-open`
   - **Win:** `.\platform\windows\start.ps1 --lan-peer`
3. Tell Hermes: **`/lan-peer-self-talk`** (prompts in playbook **§B**).
4. On success, local artifact: `~/.openclaw/state/last_lan_peer_probe.json` (never commit).

## Related docs

| Doc | Purpose |
|-----|---------|
| [Operator playbook §A–§E](../../bin/orama-system/skills/hermes-harness/references/lan-peer-self-talk.md#operator-playbook) | Full setup, Hermes prompts, pass/fail |
| [Mac E2E handoff](../plans/2026-06-28-mac-e2e-handoff.md) | Mac operator checklist |
| [Windows PowerShell TODO](../plans/2026-06-28-windows-powershell-todo.md) §5 | Win operator checklist |
| [E2E evidence](../testing/2026-06-28-mac-win-e2e-evidence.md) | Live re-verify matrix |
| [Bidirectional talk log (2026-06-28)](lan-peer-bidirectional-talk-2026-06-28.md) | Attempts, probe results, stale-IP fixes, future plan |
| [Hermes command card](../../bin/orama-system/skills/hermes-harness/commands/lan-peer-self-talk/SKILL.md) | `/lan-peer-self-talk` slash |

## PT companion

[Perpetua-Tools `docs/LESSONS.md`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/LESSONS.md) — pointer only; orama reference is authoritative.
