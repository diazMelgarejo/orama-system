# Fable 5 Distillation To-Do List

## Phase 1: Distillation Workflow Automation

- [ ] Create `orama-system/docs/distill-fable-5/` directory structure to centralize Fable 5 learnings.
- [ ] Write Fable 5 chat export parser logic in python.
- [ ] Implement Stage 2 & 3 prompt interactive loops in script.
- [ ] Create artifact generation logic (SKILL.md snippets, YAML snippets).
- [ ] Connect `verify_before_done.py` and `capture_lesson.py` hooks.
- [ ] Finalize `orama-system/bin/orama-system/scripts/distill_session.py`.

## Phase 2: Configuration & Orchestration

- [ ] Update `Perpetua-Tools/config/models.yml` with Fable 5 definition.
- [ ] Update `Perpetua-Tools/config/routing.yml` with Oramasys -> LM Studio Win -> Ollama -> LM Studio Mac fallback chain.
- [ ] Update `Perpetua-Tools/config/devices.yml` with device threshold capabilities.
- [ ] Modify `Perpetua-Tools/orchestrator/model_registry.py` to support dynamic thresholding.
- [ ] Update `Perpetua-Tools/orchestrator/cost_guard.py` with budget and escalation rules.

## Phase 3: Testing and Verification

- [ ] Create Fable vs Local test suite under `tests/` directories.
- [ ] Implement evaluation logic using an open-source eval framework (e.g., DeepEval).
- [ ] Setup `pre-commit` hook for YAML config validation.
- [ ] Setup `Claude Pre-commit` hook for `SKILL.md` format checking in `.github/workflows/ci.yml`.

## Phase 4: Frugal Toolchain Emulation

- [ ] Adapt/copy/emulate/submodule/be inspired by (for v2) **Langfuse's** prompt versioning and full trace tree structure for `orama-system`'s `capture_lesson.py` and `LESSONS.md`.
- [ ] Adapt/copy/emulate/submodule/be inspired by (for v2) **ClawRouter's** 15-dimension weighted scoring for `Perpetua-Tools`'s `model_registry.py`.
- [ ] Adapt/copy/emulate/submodule/be inspired by (for v2) **Manifest's** cost-tiering and governance logs for `Perpetua-Tools`'s `cost_guard.py`.
- [ ] Adapt/copy/emulate/submodule/be inspired by (for v2) **Helicone's** proxy-caching mechanisms to natively cache/batch GPT-5.5, Claude Fable 5/Opus 4.8, and Grok within `Perpetua-Tools`'s `MultiLLMRouter`.
