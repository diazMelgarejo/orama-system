# Hermes/ECC Fork Migration Inventory

This inventory records Hermes-created Hermes/ECC fork surfaces that were found
during the PT-orama harness migration. It is intentionally an audit artifact,
not a verbatim import: durable behavior moves into canonical orama-system
skills, while Hermes-local files remain thin adapters or private operator state.

## Source Classes

| Source class | Example surface | Decision | Canonical target |
|---|---|---|---|
| Corrected local wrappers | `~/.hermes/skills/pt-orama/*/SKILL.md` | Keep local and thin; regenerate from repo | `../scripts/install_hermes_thin_skills.py` |
| Rich Hermes council fork | `~/.hermes/skills/autonomous-ai-agents/pt-orama-council/SKILL.md` | Distill only reusable workflow rules | `../commands/pt-orama-council/SKILL.md` and `../SKILL.md` |
| Hermes correction packet | `Hermes-input-02.md` operator handoff | Treat as local correction source, not tracked canonical content | `../commands/*/SKILL.md`, `../../../mcp-orchestration/SKILL.md` |
| Naive Hermes output | `Hermes-Output-01.md` operator transcript | Mine for useful ideas; do not trust claims without verification | This inventory plus follow-up skill edits |
| Hermes skill authoring fork | `~/.hermes/skills/software-development/hermes-agent-skill-authoring/SKILL.md` | Distill cross-harness authoring rules only | `../../skillify/SKILL.md` and `../../skillify/references/` |
| ECC cross-harness template | `~/.hermes/skills/software-development/hermes-agent-skill-authoring/references/ecc-cross-harness-skill-template.md` | Distill checklist; do not copy template wholesale | `../../skillify/references/ecc-cross-harness-authoring.md` |
| Hermes Agent checkout | `~/.hermes/hermes-agent` | Treat as upstream runtime checkout, not canonical PT-orama source | `../SKILL.md` for onboarding and adapter boundaries |

## Distillation Decisions

### Already canonicalized

- Local `/pt-orama-council`, `/pt-orama-review`, and `/pt-orama-delegate`
  wrappers now point to canonical repo cards under
  `bin/orama-system/skills/hermes-harness/commands/`.
- Council safety rules are present in canonical command cards:
  verified branches only, no secrets, exact model IDs only, LM Studio chat
  canary, visible AGY readiness, and Codex/orama final judgment.
- The useful council fork workflow is distilled into
  `hermes-council-review-gates.md`; `../commands/pt-orama-council/SKILL.md`
  points to it without creating another subskill or activation surface.
- Hermes/ECC authoring conventions are distilled into
  `../../skillify/references/ecc-cross-harness-authoring.md`.
- Windows readiness is captured in `docs/wiki/15-hermes-windows-harness.md`.

### Remaining follow-up distillation

- ✅ **Complete (2026-06-28).** Validator constraints absorbed into `skillify/SKILL.md`;
  post-edit guards into `hardware-affinity-gate/SKILL.md`; full map in
  [`hermes-skill-absorption-map.md`](hermes-skill-absorption-map.md).
- Extend `skillify` references only if a **new** recurring packaging gap appears
  that cannot be handled by existing reference cards.

## Absorption status (2026-06-28)

| Hermes source | Target | Status |
|---------------|--------|--------|
| `hermes-agent` | `hermes-harness` | ✅ redirect + body absorbed |
| `pt-orama-harness-integration` | `hermes-harness` | ✅ redirect + references |
| `local-inference` | `hardware-affinity-gate` | ✅ redirect chain |
| `perpetua-hardware` (orama) | `hardware-affinity-gate` | ✅ redirect |
| `hermes-agent-skill-authoring` | `skillify` + references | ✅ distilled |
| `pt-orama-council` fork rules | `commands/` + gates ref | ✅ distilled |
| `llm-council-orchestration` (archive) | `pt-orama-council` + gates | ✅ superseded 2026-06-28 |

See [`hermes-skill-absorption-map.md`](hermes-skill-absorption-map.md) for the full table.

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
