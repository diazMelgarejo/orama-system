# Known Patterns

## Anti-patterns to avoid
- Reading files before running code-review-graph to scope the work
- Hardcoding absolute paths
- Not testing before declaring done
- Re-reading files unnecessarily
- Over-engineering simple solutions
- Summarizing architecture from memory instead of referencing canonical docs

## Good patterns
- code-review-graph → gbrain → Read (in that order)
- Test after every significant change
- Use relative paths
- Keep solutions minimal
- Handle edge cases in data (nulls, empty strings, type mismatches)
- For architecture: "As defined in `docs/2026-05-14--UNIFIED-ABSORPTION-PLAN.md` §X"
- For HITL gates: "See `HUMAN-IN-LOOP-ACCOUNTABILITY.md` Rule N"

## Multi-repo patterns
- Always check `.gbrain-source` to know which corpus is indexed
- Cross-repo: use `--source gstack-brain-lawrencecyremelgarejo` for LESSONS/decisions
- Hard requirements live in [`../../../references/first-run-install.md`](../../../references/first-run-install.md) § 0.3 and orama-system `CLAUDE.md`
