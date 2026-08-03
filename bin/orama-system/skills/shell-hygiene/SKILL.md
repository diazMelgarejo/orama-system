---
name: shell-hygiene
description: >-
  Safe shell command execution for agents. Covers enforced no-sleep-chain rules and
  zsh word-splitting behavior. Agents must use Monitor until-loops and
  run_in_background instead of sleep chains, and iterate command output with
  `while IFS= read -r` rather than unquoted `for x in $var`.
when_to_use: >-
  Activates when waiting on long-running work (background tasks, npm install,
  claude update, port/health checks, PID exit) or when looping over command output
  / file lists.
effort: low
paths:
  - "bin/orama-system/scripts/**"
  - "bin/orama-system/gstack/**"
---

# Shell Hygiene — Safe Command Execution for Agents

> Renamed from `no-sleep-chains` (2026-06-13) — broadened to cover all agent shell
> execution gotchas in this environment, not just sleep chains. The legacy slug
> `no-sleep-chains` is a directory symlink to this skill.

> **This rule is enforced at the shell level.** A leading `sleep` followed by
> any command is detected and rejected before execution. There is no workaround
> that involves `sleep` as the first token.
>
> Origin: 2026-05-16 session — `sleep 30 && cat <task-output-file>` to wait
> for npm install. Re-triggered: 2026-05-29 session — `sleep 15 && cat` and
> `sleep 20 && cat` on a `claude update` background task.

---

## The Rule

**Never** write:

```bash
sleep N && <command>
sleep N; <command>
```

**Never** split into shorter sleeps to work around the block:

```bash
sleep 5 && sleep 5 && cmd   # also blocked
```

---

## Correct Patterns

### 1. Waiting for a `run_in_background: true` task

Do nothing. You will receive an automatic notification when it completes.
Read the output file only **after** the notification fires.

```text
# Wrong
Bash(command: "sleep 30 && cat /tmp/.../task.output")

# Correct
Bash(command: "...", run_in_background: true)
# → wait for system notification → then:
Bash(command: "cat /tmp/.../task.output")
```

### 2. Waiting for a condition on a file (Monitor until-loop)

Use a `Bash` until-loop with short inner sleeps — the block only applies to
`sleep` as the **first token** of the command string:

```bash
# Wait for a keyword to appear in an output file
until grep -qE "done|error|added|Updated|failed" /path/to/output 2>/dev/null; do
  sleep 3
done
cat /path/to/output | tail -20
```

```bash
# Wait for a file to grow beyond N lines
until [ "$(wc -l < /path/to/output 2>/dev/null)" -gt 17 ]; do
  sleep 3
done
cat /path/to/output
```

### 3. Waiting for a process to exit

```bash
# If you have the PID
until ! kill -0 "$PID" 2>/dev/null; do sleep 2; done

# If you know a sentinel file it writes on completion
until [ -f /path/to/done.marker ]; do sleep 2; done
```

### 4. Waiting for a port / service to come up

```bash
until curl -s http://localhost:18789/health >/dev/null 2>&1; do sleep 2; done
echo "service ready"
```

### 5. Hard ceiling on backgrounded external CLI/agent dispatches (default: 15 minutes)

`run_in_background: true` gives you a completion notification, but that alone
is not a deadline — a hung `codex exec`, `kimi -p`, or subagent call (stuck on
a network stall, a dead MCP sidecar, or a wedged sandbox) runs forever with no
signal, because "still running" and "silently hung" look identical from the
outside. **Every background dispatch to an external CLI or model needs an
explicit hard ceiling**, not just the implicit one from waiting for its own
exit.

Default ceiling: **15 minutes** from the point you notice it's taking
unusually long (not necessarily from launch). This snippet is a simple
wall-clock guard for an external dispatch that should have a bounded runtime; it
is intentionally conservative and may stop a healthy-but-slow process. If the
task is expected to exceed 15 minutes, set an explicit longer deadline up front
and monitor progress/activity separately (`ps -o %cpu,stat -p <pid>`, output
file growth, or service logs) before killing it.

```bash
PID=<pid-of-the-external-process>
OUTPUT_FILE=/path/to/its/output
DEADLINE=$(( $(date +%s) + 900 ))   # 15 min
while true; do
  if ! kill -0 "$PID" 2>/dev/null; then
    echo "process $PID exited on its own"
    [ -s "$OUTPUT_FILE" ] && echo "SUCCESS: output present" || echo "WARNING: exited but output is EMPTY — check stderr"
    exit 0
  fi
  if [ "$(date +%s)" -ge "$DEADLINE" ]; then
    echo "HARD CEILING HIT after 15 min — stopping $PID"
    kill "$PID" 2>/dev/null || true
    sleep 5
    kill -9 "$PID" 2>/dev/null || true
    exit 1
  fi
  sleep 15
done
```

Run this as a `Monitor` (not a foreground `Bash`, and never a `sleep N &&`
chain) so it reports back on its own — see the Monitor tool's `timeout_ms`
for the same ceiling at the tool level. Applies to every fan-out voice in a
multi-agent review (`codex exec`, `kimi -p`, an `Agent`/`SendMessage`
subagent) — see [`../kimi-agent/SKILL.md § Extended use`](../kimi-agent/SKILL.md)
and [`../../gstack/SKILL.md § Third Review Voice`](../../gstack/SKILL.md) for
the pattern this ceiling protects. Origin: a `codex exec` Eng-review dispatch
ran unbounded past 19 minutes with near-zero CPU before this ceiling was
added retroactively (2026-07-12) — the fix belongs in the pattern, not
re-derived per session. This is the same failure class the `max_steps`
guard in [`docs/v2/references/patterns/multi-agent-orchestration.md`](../../../../docs/v2/references/patterns/multi-agent-orchestration.md)
(AutoGen nested-chat recursion) exists to prevent — a runaway/hung dispatch
looks identical to a slow-but-fine one until you cap it.

### 6. Concurrent `git commit`/`git add` contention (multiple agents, same repo)

When 2+ agent sessions (this session + a parallel Codex/Claude/Kimi session,
a coordination-board dogfood, a CI job) commit to the **same checkout**
concurrently, two distinct failures show up — treat them differently:

**A) `fatal: Unable to create '.git/index.lock': File exists`** (or a
sandbox/hook reporting the same thing, e.g. `BLOCKED: Access to
'.git/index.lock' denied`) — a live git process holds the lock right now.
**Never delete `.git/index.lock` yourself** — if a real process holds it,
removing it corrupts that process's in-flight commit. Retry the commit
itself in a bounded loop instead; the lock clears on its own once the other
process finishes:

```bash
n=0
until git commit -m "..."; do
  n=$((n+1))
  [ "$n" -ge 15 ] && { echo "giving up after 15 attempts"; break; }
  sleep 2
done
```

**B) `git commit` succeeds with "nothing to commit" (or commits an empty
subset) right after a `git add`.** This is not a lock failure — the other
session's commit already landed between your `add` and your `commit`,
clearing the index of what you staged. In a shared checkout, do **not** blindly
re-stage after another agent commits; first verify the worktree/staged diff
still contains only files you own, or move the retry into an isolated worktree.
Then verify ownership once before the loop, and re-run `git add` immediately
before retrying `git commit` (don't just retry the bare commit — it will keep
reporting nothing staged):

```bash
git status --short -- <files>   # inspect before retrying; stop if files are not yours
n=0
until git add <files> && git commit -m "..."; do
  n=$((n+1))
  [ "$n" -ge 15 ] && { echo "giving up after 15 attempts"; break; }
  sleep 3
done
```

Both are serialization hazards at the git-porcelain layer, not true reducer
lost-update examples: Git's index lock prevents silent concurrent writes, while
application reducers prevent whole-state overwrite. A bounded retry loop is
sufficient only after ownership/diff checks confirm you are not committing
another agent's work. Origin: hit twice in one
session (2026-07-12) coordinating STM-gate doc commits with a concurrent
Codex session over the same GossipBus claim board.

### 7. Private temp directories and installer downloads

Never download installers to predictable shared paths (`/tmp/cursor-install.sh`).
Use a **private mode-700 directory**, download inside it, chain `curl` success
before `bash`, and **CLAYGO** the directory on exit unless the operator explicitly
keeps artifacts for review.

```bash
install_dir="$(mktemp -d -t pkg-install.XXXXXX)"
chmod 700 "$install_dir"
install_script="${install_dir}/install.sh"
trap 'rm -rf "$install_dir"' EXIT   # CLAYGO — remove unless maintainer keeps for audit
curl -fsS "https://example.com/install" -o "$install_script" && bash "$install_script"
```

Rules:

- `mktemp -d` (directory), not a bare file in shared `TMPDIR`.
- `chmod 700` on the directory before writing downloads.
- `curl … && bash` — do not run a partial download when `curl` fails.
- Reject symlinked runtime parents before `mkdir -p` (see `hermes-spawn` PID dir).
- Cross-ref: [`integrative-editing-examples.md` §3](../cidf/references/integrative-editing-examples.md), [`fresh-main-integrity-diff-claygo.md`](../using-git-worktrees/references/fresh-main-integrity-diff-claygo.md).

---

## Why This Rule Exists

Sleep chains are the idiomatic polling-loop pattern, and polling loops are the
most common way agents burn tool-call budget waiting for I/O they could have
monitored. The shell hook enforces the correct patterns at the boundary so the
lesson is learned on the first violation rather than after wasted budget.

The `run_in_background: true` + notification model is strictly better: zero
wasted turns, guaranteed delivery, no timeout tuning required.

---

## Quick Reference

| Situation | Correct tool |
| ----------- | ------------- |
| Started a task with `run_in_background: true` | Wait for system notification — do nothing |
| Need to poll a file for content | `until grep -q "..." file; do sleep 3; done` |
| Need to poll a file for size | `until [ "$(wc -l < file)" -gt N ]; do sleep 3; done` |
| Need a service to be up | `until curl -s http://host/health >/dev/null; do sleep 2; done` |
| Need a PID to exit | `until ! kill -0 $PID 2>/dev/null; do sleep 2; done` |
| Backgrounded external CLI/agent dispatch (`codex exec`, `kimi -p`, review subagent) | 15-min hard ceiling (§ 5 above) — force-kill on timeout, don't let it run unbounded |
| `git commit`/`add` racing a concurrent agent session | Retry loop, never delete `.git/index.lock` yourself (§ 6 above) |
| Download + execute installer script | Private `mktemp -d` + `chmod 700` + `curl … && bash` + CLAYGO `trap` (§ 7 above) |
| "I'll just use a shorter sleep" | **No. Use one of the above.** |

## Shell Portability — zsh Word-Splitting (get it right the first time)

The agent shell here is **zsh**, not bash. zsh does **not** word-split unquoted parameter
expansions by default (`SH_WORD_SPLIT` is off). Bash habits silently break:

```bash
# WRONG — zsh treats the whole multiline blob as ONE iteration / ONE argument
for id in $IDS; do resolve "$id"; done       # fires once with all IDs joined
perl -i -pe 's/x/y/' $FILES                   # "Can't open <all-files-as-one-name>"

# CORRECT — iterate line-by-line; pass lists as explicit args or a real array
printf '%s\n' "$IDS" | while IFS= read -r id; do [ -n "$id" ] && resolve "$id"; done
cmd | while IFS= read -r item; do :; done
files=(a.py b.py c.py); perl -i -pe 's/x/y/' "${files[@]}"
```

Rules:

- Never `for x in $multiline_var` or `cmd $list_var` and expect splitting.
- Iterate command output with `… | while IFS= read -r x`.
- Pass file/argument lists as explicit args or `"${array[@]}"`.
- Quote every expansion (`"$var"`). These forms work identically in bash and zsh.

## Shell Quoting - Backticks in Double Quotes

When you are emitting coordination-board posts or other literal shell payloads,
do **not** wrap backticked code spans inside a double-quoted shell string.
Backticks still trigger command substitution in zsh and bash, so the enclosed
text can disappear before the payload reaches the board.

```bash
# WRONG
python3 scripts/agent_coordination.py log codex-primary-orchestrator "Use `agent_coordination.py list` here"

# CORRECT
python3 scripts/agent_coordination.py log codex-primary-orchestrator 'Use `agent_coordination.py list` here'
```

Rules:

- Use single quotes for literal board text when possible.
- If you need interpolation, escape backticks or use a here-doc / printf.
- Treat missing literal code spans in posted text as a sender-side quoting bug
  before suspecting the bus, storage, or receiver.

## Related skills

- [[fable5-git-rebase-safety]] — when a shell audit turns up branches/worktrees that look stale, divergent, or "N behind" — use its tree-twin doctrine and per-file triage (patch-id matching, structural-supersession checks) instead of trusting raw ahead/behind output.
