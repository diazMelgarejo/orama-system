---
name: shell-hygiene
description: >-
  Safe shell command execution for agents. Covers enforced no-sleep-chain rules and
  zsh word-splitting behavior. Agents must use Monitor until-loops and
  run_in_background instead of sleep chains, and iterate command output with
  `while IFS= read -r` rather than unquoted `for x in $var`. Also covers the silent
  zsh traps (a variable named `path`, a colon-modifier after a parameter), quoted
  here-docs for literal payloads, and absolute paths for hand-made worktrees.
  Activates when waiting on long-running work, looping over command output, naming
  shell variables, or building a ref:path or worktree path.
version: 1.0.0
compatibility: claude-code, cursor, codex, gemini, openclaw, hermes
allowed-tools: bash
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

## Purpose

Keep agent shell execution correct on the first attempt in an environment where the shell
is zsh, commands run under a harness that rejects leading `sleep`, and a wrong answer
often looks like a right one. Waiting, looping, quoting and naming each have one safe
form below; this skill is the single place they are recorded.

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

## Shell Portability — zsh names and modifiers that fail silently

Three more zsh-only traps. Each returns a wrong answer that looks like a right one, so the
error surfaces several steps later as a confusing failure somewhere else.

| Trap | What zsh does | Do this instead |
| --- | --- | --- |
| A variable named `path` | `path` is tied to `$PATH`; assigning it, even with `local path=...`, overwrites the command search path, so the next `head`, `git` or `cut` is "command not found" | Never name a variable `path`; use `file`, `target` or `fp`. Same for `status` (read-only) and `argv` |
| `"$ref:src/a.py"` | A `:` after a parameter starts a history-style modifier (`:s`, `:t`, `:h`), so `$sha:src/x` is silently substituted | Brace it: `"${ref}:src/a.py"` |
| `git -C <repo> worktree add <relative>` | The relative path resolves from `<repo>`, not the shell's cwd: `worktrees/x` lands inside the checkout and `../x` beside it, never where you are standing | Pass an absolute path, then `git -C <repo> status` to confirm the checkout stayed clean |

How to debug it: when a probe reports "absent" or "no such path" for something you read
moments ago, suspect the probe before the repository. Print the expanded value first
(`printf '%s\n' "$var"`) and re-run once with a literal. If the literal works and the
variable form does not, the variable is wrong: quoting or a modifier, but equally an
unset, stale or mistyped value, so inspect the value before naming the cause. State
that the first answer was a harness error before you give the corrected one.

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
- For a multi-line payload use a here-doc with a **quoted** delimiter (`<<'EOF'`). An
  unquoted delimiter (`<<EOF`) still performs command substitution on backticks and
  `$(...)`, so it is not a safe alternative (verified in bash 3.2 and zsh).
- If you need interpolation, escape the backticks or build the string with `printf`.
- Treat missing literal code spans in posted text as a sender-side quoting bug
  before suspecting the bus, storage, or receiver.

## Boundaries

### Always Do

- Wait with `run_in_background` or a Monitor until-loop, with a hard ceiling on every
  external dispatch.
- Iterate command output with `while IFS= read -r` and quote every expansion.
- Brace a parameter that is followed by a colon (`"${ref}:path"`) and use absolute paths
  for `git worktree add`.
- Write literal multi-line payloads through a here-doc with a quoted delimiter
  (`<<'EOF'`).

### Ask First

- Killing a backgrounded process you did not start, or removing any lock file another
  session may hold.
- Running a downloaded installer outside a private `mktemp -d` directory.

### Never Do

- Put `sleep` first in a command, or poll in a chain of short sleeps.
- Use `for x in $multiline_var` and expect word-splitting.
- Name a variable `path` (it is tied to `$PATH`), `status` or `argv`.
- Rely on an unquoted here-doc delimiter, or backticks inside a double-quoted payload,
  to carry literal text.

## Related skills

- [[fable5-git-rebase-safety]] — when a shell audit turns up branches/worktrees that look stale, divergent, or "N behind" — use its tree-twin doctrine and per-file triage (patch-id matching, structural-supersession checks) instead of trusting raw ahead/behind output.

## Enforced by hooks (provision and re-create)

The traps above, and the other zsh and macOS ones agents keep hitting, are stopped before the
command runs by `hooks/shell-gotchas.py`, a table-driven PreToolUse hook for the Bash tool. Each rule
carries bad and good fixtures that `shell-gotchas.py --self-test` executes, so the rules, this table
and the tests come from one registry. `hooks/no-workstation-paths.py` does the same for Write and
Edit (no `/Users/<name>/` paths in tracked files).

Provision or repair (idempotent; `--check` is read-only and is the default):

```bash
bash bin/orama-system/scripts/install-shell-hooks.sh --check
bash bin/orama-system/scripts/install-shell-hooks.sh --apply
```

`--apply` copies the canonical hooks into `~/.claude/hooks/`, merges their registrations into
`~/.claude/settings.json` (a timestamped backup first, no other key or hook touched), retires the
superseded `zsh-reserved-vars.py` registration, and runs the self-test.

Rollout: a new install registers `shell-gotchas.py` in warn mode (`SHELL_GOTCHAS_MODE=warn`), so
findings reach the model and the log but nothing is blocked while the rules are tuned. Review what
fired with `python3 ~/.claude/hooks/shell-gotchas.py --report`, then promote with
`install-shell-hooks.sh --apply --mode enforce`. Re-applying keeps the current mode unless `--mode`
is given. Rules marked `warn` below are heuristics that guess at runtime state and never block.
`bin/orama-system/scripts/first-run-install.sh` runs the same check and apply as one of its steps.

Controls, for the rare command that is correct as written:

- `# gotcha-ok: <rule-id>` (comma-separated, or `all`) inside the command skips those rules for it.
- `SHELL_GOTCHAS_MODE=warn` turns every block into a warning (staged rollout); `off` disables the
  hook. The default is `enforce`.
- Blocks and warnings are logged to `$XDG_STATE_HOME/shell-gotchas/usage.log` (default
  `~/.local/state/shell-gotchas/usage.log`, outside the Claude configuration directory) as rule ids
  and a command hash, never the command text, so false positives can be counted and a rule tuned.

<!-- shell-gotchas:begin -->
| Rule | Level | What goes wrong | Fix |
| --- | --- | --- | --- |
| `zsh-set-unquoted` | deny | `set -- $var` does not word-split in zsh | use an array (`args=(a b); set -- "${args[@]}"`) or loop with `while IFS= read -r x` |
| `zsh-for-scalar` | warn | `for x in $var` iterates once over a scalar in zsh | iterate an array (`"${arr[@]}"`), a glob, or `while IFS= read -r x` over the lines |
| `zsh-unquoted-list-var` | warn | a multi-line `$(...)` result is passed unquoted, so zsh sends it as one word | build an array, pass globs, or use `xargs`/`while IFS= read -r`; never `cmd $LIST` |
| `zsh-command-in-variable` | deny | a command line stored in a string variable is not split into words by zsh | use a function or an array (`GIT=(git -C dir); "${GIT[@]}" status`) |
| `zsh-reserved-var` | deny | assigning `status`, `path`, `argv`... clobbers a zsh special parameter | rename it (`job_status`, `file_path`); `path` is tied to PATH and breaks every later command |
| `zsh-unmatched-glob` | warn | an unquoted glob with no match aborts the whole command in zsh (`no matches found`) | quote the pattern for the tool, use `find`, or add `(N)`; check the files exist first |
| `zsh-colon-modifier` | warn | `$var:x` starts a history-style modifier in zsh (`$sha:src/a.py` is rewritten) | brace the name: `"${sha}:src/a.py"` |
| `git-worktree-relative` | warn | `git -C <repo> worktree add <relative>` resolves the path from <repo>, not the shell | pass an absolute path, then `git -C <repo> status` to confirm the checkout stayed clean |
| `echo-backslash` | deny | zsh and BSD `echo` interpret backslash sequences (`\copy`, `\n`) inside quotes | use `printf '%s\n' 'text'` for literal text |
| `bsd-cat-A` | deny | macOS `cat` has no `-A` | use `cat -et file` or `od -c file \| head` |
| `bsd-grep-P` | deny | macOS `grep` has no `-P` (Perl regex) | use `grep -E`, `rg -P`, or `git grep -P` |
| `bsd-sed-inplace` | deny | BSD `sed -i` needs a suffix argument; `sed -i 's/a/b/' f` fails | use `sed -i '' 's/a/b/' f`, or write with python3 |
| `bsd-sed-word-boundary` | warn | BSD `sed` has no `\b` word boundary | use `[[:<:]]`/`[[:>:]]`, or python3 |
| `secret-env-dump` | deny | dumping the environment prints every secret in it | list names only (`env \| cut -d= -f1`) or test one value (`printenv NAME \| wc -c`) |
| `secret-file-read` | warn | reading a credentials or `.env` file prints its values | count or list keys (`grep -c`, `cut -d= -f1`) and never paste the values |
| `git-interactive` | deny | interactive git commands wait for a terminal that is not there | use non-interactive forms (`git add <paths>`, `git rebase <base>`, `git diff`) |
| `git-commit-no-message` | deny | `git commit` without a message opens an editor and hangs | pass `-m "msg"` or `-F -` with a heredoc, or `--no-edit` when amending |
| `codex-review-stdin` | deny | `codex review` blocks silently on stdin | end the command with `< /dev/null` |
| `kill-by-pattern` | warn | `pkill -f` and `kill $(pgrep -f ...)` match the wrapper shell and this command itself | match with a bracket (`pgrep -f '[s]erver'`), use a pid file, or kill a known pid |
| `bash4-in-zsh` | deny | `${var,,}`, `${var^^}`, `mapfile` and `readarray` are bash 4+; they fail in zsh and bash 3.2 | use `tr '[:upper:]' '[:lower:]'` and `while IFS= read -r line` |
| `gnu-only-flags` | deny | GNU-only flags that BSD tools on macOS reject (`date -d`, `stat -c`, `find -printf`, ...) | use `date -v`, `stat -f`, `python3`, `base64 \| tr -d '\n'`, `sed '$d'`, `xargs -0` |
| `bsd-date-nanoseconds` | warn | BSD `date` has no `%N`; it prints a literal `N` | use python3 `time.time_ns()` |
<!-- shell-gotchas:end -->
