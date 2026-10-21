<!-- lint-ignore LINT-013 -->
# Quick Start Usage Guide

> Activation phrases, the mandatory six-directive workflow commands and the integrated
> framework summary for the orama-system mother skill. Moved verbatim out of `SKILL.md`,
> which keeps the `## Quick Start` heading, the activation phrases and the HTTP-path
> historical note. Link targets were rebased for this folder.

## Quick Start (Usage Guide)

### 1. Activation

Trigger the full 5-stage process with:

- `ultrathink this`
- `apply the system to: [your task]`
- `production-ready [task]`

### 2. Mandatory Workflow

Follow the 6 directives in every non-trivial task:

1. **Plan**: `./scripts/create_task_plan.sh "Build feature"`
2. **Execute**: Build stage-by-stage (Context -> Architect -> Refine -> Execute -> Crystallize)
3. **Verify**: `python scripts/verify_before_done.py` (Must PASS before done)
4. **Learn**: `PERPETUA_TOOLS_ROOT=/path/to/Perpetua-Tools python scripts/capture_lesson.py --quick` (Run after any correction)

### 3. Integrated Frameworks

- **AFRP**: Pre-router gate. Classifies and clarifies intent before architecture.
- **CIDF v1.2**: Content insertion governance. Start at rank 1 (direct_form_input) for every write.

> **Historical Note:** The canonical HTTP path is `/oramasys`; legacy `/ultrathink` is implemented via `api_server.py` as a deprecated v1.x compatibility shim.
