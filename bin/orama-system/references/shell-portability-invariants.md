<!-- lint-ignore LINT-013 -->
# Shell Portability Invariants

> Three invariants every agent and script must honour on this stack: `codex review` needs
> `< /dev/null`, never bare `timeout` on macOS, and the OpenClaw delegation key name. Moved
> verbatim out of `SKILL.md`; the heading stays there as a pointer.

## Shell Portability Invariants (all agents / all scripts)

**1. `codex review` always needs `< /dev/null`.**
Without it the process blocks on stdin indefinitely — the hang is invisible.

```bash
codex review "<prompt>" -c 'model_reasoning_effort="high"' < /dev/null
```

**2. Never use bare `timeout N <cmd>` on macOS.** GNU `timeout` is absent on stock macOS. Use:

```bash
_TO=$(command -v gtimeout 2>/dev/null || command -v timeout 2>/dev/null || echo "")
if [ -n "$_TO" ]; then "$_TO" N <cmd>; else <cmd>; fi
```

`gtimeout` = Homebrew coreutils. `timeout` = Linux. Omit the wrapper only when hanging is safe to ignore.

**3. OpenClaw delegation key is `agents.defaults.subagents.allowAgents`** (or `agents.list[id].subagents.allowAgents`).
The key `agents.bindings.*.allowAgents` is rejected by the oramaclaw control plane.
