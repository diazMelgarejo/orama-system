---
name: shell-hygiene
description: >
  Safe shell command execution for agents in this environment. Covers two enforced
  gotchas: (1) sleep N && <command> chains are blocked — wait on background processes,
  file growth, or conditions with Monitor until-loops / run_in_background instead;
  (2) the shell is zsh, which does NOT word-split unquoted $vars or `for x in $var`,
  so iterate multiline output with `while IFS= read -r` and pass lists as arrays.
  Invoke when waiting on long-running work (background tasks, npm install, claude
  update, port/health, PID exit) or when looping over command output / file lists.
---

# Shell Hygiene — Safe Command Execution for Agents

> Renamed from `no-sleep-chains` (2026-06-13) — broadened to cover all agent shell
> execution gotchas in this environment, not just sleep chains.

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
