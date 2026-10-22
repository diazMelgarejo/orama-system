<!-- lint-ignore LINT-013 -->
# Windows Coder Pool

> The routing rule that keeps every idle Windows LM Studio coder busy: pool endpoints,
> dispatch protocol, and offline behaviour. Moved verbatim out of `SKILL.md`; the
> `## Windows Coder Pool` anchor in `SKILL.md` stays as a pointer.

## Windows Coder Pool

**RULE: Every available Windows coder MUST be given work as soon as it is idle.**

Endpoint pool: `$WIN_CODER_ENDPOINTS` (the default endpoint stays in the `Endpoint pool` line of
`SKILL.md`; the repo hygiene gate forbids new private-IP literals, and the live address is read
from `~/.openclaw/state/last_discovery.json` → `endpoints.win.ip`).

Dispatch protocol:

1. Before routing any task to Mac-only paths, check if a Windows coder is free.
2. If free AND task is compatible (Python, Go, TypeScript, general coding):
   → dispatch to Windows coder FIRST.
3. If offline or no model loaded: skip silently, log WARN, do not fail.
4. As more Windows coders are added to `$WIN_CODER_ENDPOINTS`, they join the pool
   automatically — same rule applies to all.

**Never leave a Windows coder idle if pending compatible work exists.**
