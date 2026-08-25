---
name: self-improve
version: 1.0.0
description: Crystallize session learnings through the PT Agentic-Stack frontend and instincts. V1 uses tracked PT `.agent`; v2 runtime persistence is deferred to Anamnesis.
user-invocable: true
trigger: session-end
---

# Self-Improve — v1.0.0

Idempotent session-end skill. In v1, development lessons are written through PT's
tracked `.agent` pipeline. It reads what happened, proposes minimal additive updates,
and waits for approval before committing anything. The deferred runtime-memory contract
is in `docs/v2/56-anamnesis-runtime-memory-migration.md`.

**Trigger modes (Option C):**

- **Auto**: Claude invokes this at session end without being asked
- **Manual**: User types `/self-improve` at any checkpoint
- **Gate**: Nothing is committed until user explicitly approves the diff

---

## Version Guard (run first)

```python
BUNDLED = '1.0.0'
# Skip write if installed version is already newer
def _ver(path):
    import pathlib
    for line in pathlib.Path(path).read_text().splitlines():
        if line.strip().startswith("version:"):
            return tuple(int(x) for x in line.split(":",1)[1].strip().strip('"\'').split("."))
    return (0, 0, 0)

skill_path = ".claude/skills/self-improve/SKILL.md"
if _ver(skill_path) >= tuple(int(x) for x in BUNDLED.split(".")):
    print(f"skip — already at {BUNDLED}")
    exit(0)
```

---

## Step 1 — Read Current Knowledge Base

```bash
# Read PT Agentic-Stack's rendered development lesson view
test -n "$PERPETUA_TOOLS_ROOT" && cat "$PERPETUA_TOOLS_ROOT/.agent/memory/semantic/LESSONS.md"

# Read instincts (behavioral patterns)
cat .claude/homunculus/instincts/inherited/orama-system-instincts.yaml 2>/dev/null

# Read this session's git log (what actually changed)
git log --oneline -10
```

---

## Step 2 — Extract Session Learnings

From the session just completed, identify:

1. **New facts** — IPs, endpoints, configs confirmed or changed
2. **Patterns discovered** — what worked, what didn't, why
3. **Decisions made** — architectural choices and their rationale
4. **Errors resolved** — root cause + fix pattern for reuse
5. **Skills updated** — which skills changed and why
6. **Install/validation lessons** — wrapper policy, origin-sync rules, Windows encoding fixes, local-model test limits

Format each learning as a dated, concise entry:

```markdown
## [YYYY-MM-DD] <Topic>

- **Fact**: <what is now confirmed true>
- **Pattern**: <reusable approach>
- **Rationale**: <why this was chosen over alternatives>
```

---

## Penultimate Lesson Capture Gate

Before claiming any multi-step goal is complete, run one final lesson-capture pass:

1. Identify reusable lessons from the just-finished work.
2. Capture durable lessons through `capture_lesson.py` with `PERPETUA_TOOLS_ROOT` or update the relevant skill reference.
3. Update the canonical in-repo skill first; local Codex installs must remain thin wrappers.
4. If the lesson affects local Codex skill installs, update `bin/orama-system/skills/skillify/references/codex-thin-wrapper-installs.md`.
5. Re-run the relevant validation gates before declaring completion.

For Codex skill installs, remember the current rule: local `~/.codex/skills/*` directories are wrappers only; they point to origin-synced canonical in-repo cards and do not cache upstream bodies.

---

## Step 3 — Generate Proposed Diff

Produce a concrete, minimal diff — **additive only, no deletions** from PT lesson memory unless correcting a factual error:

```bash
# Show current tail of PT's rendered lesson view
tail -30 "$PERPETUA_TOOLS_ROOT/.agent/memory/semantic/LESSONS.md"
```

Compose the proposed addition. Show it to the user clearly:

```text
=== PROPOSED ADDITION TO PT .agent MEMORY ===

## [YYYY-MM-DD] <Session Summary>

<entries>

=== END PROPOSAL ===
```

---

## Step 4 — User Approval Gate (HARD STOP)

**Do NOT commit or write anything until user explicitly approves.**

Present:

```text
Self-improve proposal ready.

Options:
  A) Approve and commit — capture through PT `.agent` + git commit
  B) Edit first — show me the text so I can revise
  C) Skip — don't save this session (discard)

Which? (A/B/C)
```

- If **A**: proceed to Step 5
- If **B**: show raw text, accept edits, re-present for approval
- If **C**: exit without writing anything

---

## Step 5 — Write and Commit (only after approval)

```bash
# Capture through the stable controller, which delegates to PT learn.py.
PERPETUA_TOOLS_ROOT=/path/to/Perpetua-Tools \
  python bin/orama-system/scripts/capture_lesson.py --quick --pattern "[Pattern]"

# Stage and commit
git add .agent/memory
git commit -m "docs(lessons): crystallize session learnings [self-improve]

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"

# Never push automatically. Re-run the portable-memory guard after approval;
# a human must approve any push unless an explicit policy override is configured.
echo "Session learnings committed; push remains human-gated."
```

---

## Step 6 — Instincts Update (optional)

If the session revealed a strong new behavioral pattern that belongs in the instincts file:

```bash
# Check current instincts
cat .claude/homunculus/instincts/inherited/orama-system-instincts.yaml 2>/dev/null | tail -20
```

Propose the addition. Present separately for approval (same A/B/C gate). Only update if:

- The pattern is reusable across many future sessions
- It's not already covered
- It's concrete and actionable (not vague)

---

## Idempotency Rules

- Never duplicate an entry already in PT `.agent` memory (check for duplicate topics first)
- Never overwrite existing entries — append only
- Never bump the skill version number from inside the skill itself
- If running multiple times in one session, only the last run's learnings are committed

---

## Session-End Auto-Trigger

Claude should invoke this skill proactively when:

- The user says "we're done", "wrap up", "that's it for today", "end session"
- The conversation is naturally concluding after a major task set
- The user asks to save progress

Claude should NOT invoke without asking if:

- The session was exploratory/experimental and produced no stable facts
- The user has already run `/self-improve` in this session
