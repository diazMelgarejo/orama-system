<!-- lint-ignore LINT-013 -->
# Shell Portability Invariants

> Four invariants every agent and script must honour on this stack: `codex review` needs
> `< /dev/null`, never bare `timeout` on macOS, the OpenClaw delegation key name, and zsh word
> splitting. The first three were moved verbatim out of `SKILL.md`; the heading stays there as a pointer.

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

**4. The Bash tool is zsh: it does not word-split, and a leading `=` is a command lookup.**
zsh leaves `SH_WORD_SPLIT` off, so an unquoted `$var` stays one word. `set -- $var`,
`for x in $var` and a command stored in a variable (`$GIT`) all misbehave **silently**: the
arguments are swallowed or the call fails with "command not found". Seen again on 2026-11-17:
`set -- $spec` left `$1` empty and a `gh api repos/$1/pulls/$2/comments` call returned 404.

```bash
# Wrong: one word in zsh, so $1 and $2 are empty
set -- $spec; gh api "repos/$1/pulls/$2/comments"

# Right: explicit arguments, a function, an array, or a line-by-line read
list() { gh api "repos/$1/pulls/$2/comments"; }; list owner/repo 519
args=(--paginate -q '.[].id'); gh api "repos/owner/repo/pulls/519/comments" "${args[@]}"
printf '%s\n' "$multiline" | while IFS= read -r line; do printf '%s\n' "$line"; done
```

- Never store a command in a variable; wrap it in a function or spell it out.
- A word that starts with `=` expands as `=cmd`: `echo ======` fails ("= not found"). Use
  `printf -- '======\n'`.
- An unmatched glob aborts the whole command in zsh; quote it or use `find -exec`.
