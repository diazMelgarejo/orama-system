# v2 Skills Implementation Plan

> **Repository standard:** everything executable lives under `/src`; no root-level `scripts`/`tests`/`tools`/`examples`; data output and produced binaries stay `.gitignore`d, never committed with secrets, personal paths, or SecOps material. Additive — see [`46-repository-standard.md`](46-repository-standard.md).
Status: planning baseline
Scope: perpetua-core + oramasys v2 skill architecture
Source input: attached `05-docs-v2-skills.md`, renumbered into the correct v2 slot after reading `docs/v2/README.md`

## Decision

v2 skills must use concise `SKILL.md` orchestrators plus modular one-level support files.

`SKILL.md` is not the encyclopedia. It is the activation, routing, and boundary card.

## Size Policy

- New generated `SKILL.md` files should be <= 200 lines. Shorter is better.
- Existing or exceptional `SKILL.md` files must remain <= 500 lines.
- If a skill wants to exceed 200 lines, move material into `instructions/`, `examples/`, `references/`, `templates/`, `scripts/`, or `eval/`.
- Full body templates and long examples belong in references, not in the always-loaded skill card.

## Standard Folder Shape

```text
skills/<skill-name>/
├── SKILL.md
├── instructions/
├── examples/good/
├── examples/bad/
├── references/
├── scripts/
├── templates/
└── eval/
```

Trim unused folders for tiny skills. Do not create empty decorative structure.

## v2 Skill Set

| Skill | Role | Required shape |
|---|---|---|
| hardware-router | Enforce hardware affinity and model routing | Short orchestrator + `instructions/affinity-rules.md` + `eval/checklist.md` |
| autoresearcher | Govern autonomous research loops | Short orchestrator + loop details in `instructions/core-loop.md` + dry-run checklist |
| orchestrator | Route high-level tasks across skills | Short orchestrator + references to sub-skill contracts |
| multi-llm-router | Choose model/provider path | Short orchestrator + routing matrix in `references/routing-matrix.md` |

## Hardware Router Baseline

`skills/hardware-router/SKILL.md` should contain only:

- frontmatter with strong hardware/model-routing triggers,
- purpose,
- activation conditions,
- load order,
- 5-8 step workflow,
- hard prohibitions,
- references to policy and eval files.

Move model lists and detailed affinity rules to `instructions/affinity-rules.md`.

## AutoResearcher Baseline

`skills/autoresearcher/SKILL.md` should contain only:

- frontmatter with research-loop triggers,
- purpose,
- activation conditions,
- dry-run rule,
- compact loop outline,
- stop conditions,
- references to loop details and eval.

Long descriptions of uditgoenka/karpathy patterns, experiment formats, and result logs belong in `references/` or `instructions/`, not in `SKILL.md`.

## Dry-Run Rule

Any long-running v2 skill must support dry-run first.

Dry-run must not:

- call paid or external LLMs,
- install plugins,
- touch GPUs,
- mutate repos beyond a plan/report file,
- run autonomous loops,
- edit AlphaClaw directly.

Dry-run should:

- list affected files,
- show intended commands,
- show expected outputs,
- classify risks,
- stop for review.

## Cross-Skill Dependencies

- `hardware-router` owns hardware affinity decisions.
- `multi-llm-router` consumes hardware decisions before model calls.
- `autoresearcher` consumes both routers and must honor dry-run.
- `orchestrator` coordinates skills but does not duplicate their rules.

## Implementation Steps

1. Update `skillify` to generate concise orchestrator skills by default.
2. Move full templates/examples into `skillify/references/`.
3. For each v2 skill, create `SKILL.md` first and keep it <= 200 lines.
4. Add only the modular files required by that skill's actual complexity.
5. Add `eval/checklist.md` with 6Cs and reviewer personas for each non-trivial skill.
6. Verify all markdown fences have language specifiers.
7. Verify no raw workstation paths, LAN IPs, secrets, or hidden side effects.

## Acceptance Criteria

- Every new v2 `SKILL.md` is concise and triggerable.
- Every long example/template lives outside `SKILL.md`.
- Every non-trivial skill has an eval checklist.
- Every cross-skill dependency is referenced, not copied.
- Dry-run exists for long-running or autonomous skills.
- AlphaClaw is controlled through Perpetua and is not edited directly from v2 skill planning.

## References

- `docs/v2/README.md`
- `bin/orama-system/references/skill-architecture-guide.md`
- `bin/orama-system/skills/skillify/SKILL.md`
- `bin/orama-system/skills/skillify/references/modular-skill-authoring.md`
- `bin/orama-system/skills/skillify/references/skill-folder-template.md`
