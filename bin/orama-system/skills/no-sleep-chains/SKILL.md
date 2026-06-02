---
name: no-sleep-chains
description: >
  Enforced rule for all agents: sleep N && <command> chains are blocked by the
  shell hook. Invoke this skill whenever you need to wait for a background
  process, a file to grow, or a condition to become true. Covers: background
  task output polling, npm install completion, claude update, any long-running
  subprocess.
---

# No Sleep Chains — Waiting for Background Work

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

```
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
|-----------|-------------|
| Started a task with `run_in_background: true` | Wait for system notification — do nothing |
| Need to poll a file for content | `until grep -q "..." file; do sleep 3; done` |
| Need to poll a file for size | `until [ "$(wc -l < file)" -gt N ]; do sleep 3; done` |
| Need a service to be up | `until curl -s http://host/health >/dev/null; do sleep 2; done` |
| Need a PID to exit | `until ! kill -0 $PID 2>/dev/null; do sleep 2; done` |
| "I'll just use a shorter sleep" | **No. Use one of the above.** |
