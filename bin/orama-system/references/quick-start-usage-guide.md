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

Follow the [six operational directives](core-operational-directives.md) in every non-trivial task:

1. **Plan**: establish the outcome, constraints, and checks before work that has three or more dependent steps.
2. **Delegate**: split independent work into bounded, separately reviewable assignments.
3. **Learn**: capture corrections through the canonical PT memory workflow after material feedback or failure.
4. **Verify**: run the checks proportionate to the changed surface before declaring completion.
5. **Refine**: prefer the simplest coherent design; remove avoidable duplication and ambiguity.
6. **Fix**: diagnose actionable defects to their cause, implement the narrow repair, and verify it end-to-end.

### 3. Integrated Frameworks

- **AFRP**: Pre-router gate. Classifies and clarifies intent before architecture.
- **CIDF v1.2**: Content insertion governance. Start at rank 1 (direct_form_input) for every write.

> **Historical Note:** The canonical HTTP path is `/oramasys`; legacy `/ultrathink` is implemented via `api_server.py` as a deprecated v1.x compatibility shim.
