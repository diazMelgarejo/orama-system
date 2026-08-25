# Scripts

Automation tools that implement ultrathink's operational directives.

---

## `verify_before_done.py` (Directive #4)

Runs a comprehensive verification suite before you mark any task complete.

```bash
# Full interactive verification
python verify_before_done.py --task "Build auth system"

# Non-interactive (CI mode)
python verify_before_done.py --task "Build auth system" --no-interact

# Verify specific directory
python verify_before_done.py --task "API update" --dir ../my-project
```

**What it checks:**

1. Test suite (pytest / npm test)
2. Code linting (flake8, pylint, ESLint)
3. Debug artifact scan (print statements, hardcoded secrets, HACK comments)
4. Task plan completion (tasks/todo.md progress)
5. Staff engineer self-review (interactive checklist)

**Output:** Saves `tasks/verification-report.json`. Exits 0 on PASS, 1 on FAIL.

---

## `capture_lesson.py` (Directive #3)

Stable lesson-capture frontend. In v1 it delegates development lessons to PT's
tracked Agentic-Stack; use `--backend legacy` only for an intentional standalone
compatibility installation. Runtime capture is reserved for provisioned v2 Anamnesis.

```bash
# Interactive (guided prompts)
PERPETUA_TOOLS_ROOT=/path/to/Perpetua-Tools python capture_lesson.py

# With known pattern
PERPETUA_TOOLS_ROOT=/path/to/Perpetua-Tools python capture_lesson.py --quick --pattern "Premature Optimization"

# Review all lessons
PERPETUA_TOOLS_ROOT=/path/to/Perpetua-Tools python capture_lesson.py --review

# Show stats
PERPETUA_TOOLS_ROOT=/path/to/Perpetua-Tools python capture_lesson.py --stats
```

**Lesson format captures:**

- What went wrong
- Root cause
- Prevention rule
- Verification trigger (question to ask yourself before repeating)
- Good/bad examples

---

## `create_task_plan.sh` (Directive #1)

Generates a `tasks/todo.md` template for a new task. Run before any non-trivial implementation.

```bash
# With task name
./create_task_plan.sh "Build financial validator"

# With optimization target
./create_task_plan.sh "Refactor auth" --optimize reliability

# Interactive mode (guided prompts)
./create_task_plan.sh --interactive
```

---

## Requirements

- Python 3.8+
- Optional: `pytest`, `flake8`, `pylint` (for test/lint checks)
- Bash 4+ (for shell script)
