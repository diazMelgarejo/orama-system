# cursor-agent Steering / Handoff

> **Role:** Standard pattern for Hermes → cursor-agent work continuation on Windows.
> **Absorbed from:** Hermes self-improve `windows-hermes-setup` reference (2026-07-23).

---

## Procedure

1. Write `.cursor/state/<handoff-name>.md` containing:
   - Verified current state (branch, dirty files, service status)
   - Recent actions completed
   - Open gaps / blockers
   - Explicit asks from the user
   - Key paths (env-var form only)
   - Constraints to respect
   - Intended next actions
2. Immediately invoke cursor-agent with a concise prompt pointing at that file.
3. Ask cursor-agent to acknowledge receipt and reply with top priorities or blockers.

This keeps the repo-local steering artifact in sync with the live agent handoff.

---

## Smoke Probe Recipe

| Step | Command |
|------|---------|
| Existence | `cursor-agent --version` |
| PATH | `Get-Command cursor-agent -ErrorAction SilentlyContinue` |
| Absolute path | `& "$env:LOCALAPPDATA\cursor-agent\cursor-agent.cmd" --help` |
| Process state | `Get-Process -Name "cursor*" -ErrorAction SilentlyContinue` |
| Dispatch test | `cursor-agent --print --model <model> "Read <steering-file>. Acknowledge and list top gaps."` |

If on-path probe fails, retry via absolute path before assuming missing.

---

## Example Steering File Location

```
<orama-system-root>/.cursor/state/steering-handoff-YYYY-MM-DD.md
```

---

## Related

- [`windows-hermes-setup.md`](windows-hermes-setup.md) — full Windows setup playbook
- [`../SKILL.md`](../SKILL.md) § Update the Board — GossipBus + peer-inbox
