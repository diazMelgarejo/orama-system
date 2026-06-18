# Hermes/ECC Fork Migration Inventory

This inventory records Hermes-created Hermes/ECC fork surfaces that were found
during the PT-orama harness migration. It is intentionally an audit artifact,
not a verbatim import: durable behavior moves into canonical orama-system
skills, while Hermes-local files remain thin adapters or private operator state.

## Source Classes

| Source class | Example surface | Decision | Canonical target |
|---|---|---|---|
| Corrected local wrappers | `%LOCALAPPDATA%/hermes/skills/pt-orama/*/SKILL.md` | Keep local and thin; regenerate from repo | `../scripts/install_hermes_thin_skills.py` |
| Rich Hermes council fork | `%LOCALAPPDATA%/hermes/skills/autonomous-ai-agents/pt-orama-council/SKILL.md` | Distill only reusable workflow rules | `../commands/pt-orama-council/SKILL.md` and `../SKILL.md` |
| Hermes correction packet | `Hermes-input-02.md` operator handoff | Treat as local correction source, not tracked canonical content | `../commands/*/SKILL.md`, `../../../mcp-orchestration/SKILL.md` |
| Naive Hermes output | `Hermes-Output-01.md` operator transcript | Mine for useful ideas; do not trust claims without verification | This inventory plus follow-up skill edits |
| Hermes skill authoring fork | `%LOCALAPPDATA%/hermes/skills/software-development/hermes-agent-skill-authoring/SKILL.md` | Distill cross-harness authoring rules only | `../../skillify/SKILL.md` and `../../skillify/references/` |
| ECC cross-harness template | `%LOCALAPPDATA%/hermes/skills/software-development/hermes-agent-skill-authoring/references/ecc-cross-harness-skill-template.md` | Distill checklist if needed; do not copy template wholesale | `../../skillify/references/codex-thin-wrapper-installs.md` or a new skillify reference |
| Hermes Agent checkout | `%LOCALAPPDATA%/hermes/hermes-agent` | Treat as upstream runtime checkout, not canonical PT-orama source | `../SKILL.md` for onboarding and adapter boundaries |

## Distillation Decisions

### Already canonicalized

- Local `/pt-orama-council`, `/pt-orama-review`, and `/pt-orama-delegate`
  wrappers now point to canonical repo cards under
  `bin/orama-system/skills/hermes-harness/commands/`.
- Council safety rules are present in canonical command cards:
  verified branches only, no secrets, exact model IDs only, LM Studio chat
  canary, visible AGY readiness, and Codex/orama final judgment.
- Windows readiness is captured in `docs/wiki/15-hermes-windows-harness.md`.

### Useful follow-up distillation

- Move the rich council fork's review-gate language into the canonical
  council command only if it improves the current concise command card.
- Move Hermes/ECC authoring conventions into `skillify` only when they apply to
  all cross-harness skill authoring; keep Hermes-specific validator details out
  of orama unless they affect wrapper generation.
- If ECC-native skill packaging becomes a recurring PT-orama task, add a small
  `skillify` reference for ECC-style frontmatter and harness adapter checks.

### Do not import

- Do not import raw Hermes hub cache, bundled marketplace skills, local usage
  telemetry, lock files, or provider config.
- Do not import package-lock drift or local runtime checkout changes from the
  Hermes Agent repo.
- Do not trust claimed Hermes/ECC branch names or commit SHAs unless verified
  with git/GitHub.
- Do not preserve invented model names such as "Qwen 3.6 Coder"; use live model
  IDs returned by provider APIs.
- Do not paste mojibake from transcripts into canonical docs; describe the
  issue or repair the text first.

## Commit Strategy

1. Inventory forks and decisions in this file.
2. Distill council workflow improvements into `commands/pt-orama-council`.
3. Distill cross-harness skill-authoring improvements into `skillify` if needed.
4. Regenerate Hermes local wrappers and verify they remain thin.
5. Update lessons and PR body with validation evidence.

Each step should be a separate commit so reviewers can distinguish audit,
behavioral changes, adapter regeneration, and documentation updates.
