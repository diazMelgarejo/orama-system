# orama-system Skill Upgrade Roadmap

Date: 2026-07-06
Status: PR 1 planning artifact
Scope: Existing registered orama-system skills
Source standards: Claude Code skill guidance (`https://code.claude.com/docs/en/skills`), orama skill architecture guide, Skillify retiring-fellow runbook

## Decision

Do PR 1 as standards, validator, tests, and roadmap only.

Do not rewrite leaf skill behavior in this PR. Later PRs should use the validator and roadmap here to upgrade skills safely, starting with low-risk skills and ending with high-risk execution skills.

## PR 1 Contents

This PR should contain:

- `scripts/review/check_orama_skills.py` — baseline/strict skill quality validator.
- `tests/test_check_orama_skills.py` — unit tests for parsing and heuristics.
- `bin/orama-system/skills/skillify/references/modular-skill-authoring.md` — validator and Claude Code metadata guidance.
- `bin/orama-system/skills/skillify/references/retiring-fellow-skill-library.md` — validator gate and upgrade runbook.
- This roadmap.

This PR should not contain:

- behavioral changes to `mcp-orchestration`, `hermes-harness`, or other leaf skills,
- new MCP dispatch behavior,
- new OpenClaw/Hermes execution paths,
- new `.claude/skills/` canonical files.

## Validator Strategy

Run baseline mode now:

```bash
python3 scripts/review/check_orama_skills.py --mode baseline
```

Baseline mode reports findings without blocking the current legacy corpus.

Use strict mode later, after leaf skills are upgraded or warnings are explicitly allowlisted:

```bash
python3 scripts/review/check_orama_skills.py --mode strict
```

Strict mode exits non-zero on:

- any error, or
- any warning not allowed by `--allow-warning` or `--warning-allowlist`.

This aligns the future CI gate with the roadmap requirement that high-risk warnings must be resolved or explicitly allowlisted.

## Claude Code Metadata Strategy

Adopt these fields through later PRs, following orama paths and ownership rules:

| Field | orama use |
|---|---|
| `description` | Short core capability and primary use case |
| `when_to_use` | Trigger phrases and examples; combined with description <= 1,536 chars |
| `disable-model-invocation: true` | Explicit-only side-effect workflows |
| `user-invocable: false` | Background doctrine skills |
| `context: fork` + `agent:` | Isolated review, QA, research, or harness execution |
| `paths:` | Monorepo-aware activation hints, not a security boundary |
| `argument-hint` / `arguments` | Reusable invocations and argument substitution |
| `${CLAUDE_SKILL_DIR}` | Bundled skill scripts/references |
| `${CLAUDE_PROJECT_DIR}` | Repo-local validators and scripts |
| `hooks:` | Deterministic audit/policy enforcement with session-linked records |
| dynamic context | Pre-execution shell context; use only with scoped permissions and clear safety rationale |

## Global Acceptance Criteria

Every upgraded skill should satisfy:

- `SKILL.md` is an orchestrator, not the encyclopedia.
- New `SKILL.md` files target <= 200 lines.
- Existing or exceptional `SKILL.md` files stay <= 500 lines after upgrade.
- Trigger-rich third-person `description` plus `when_to_use`, combined <= 1,536 chars.
- Invocation controls match risk: explicit-only for side effects, background-only for doctrine.
- Imperative runbook voice.
- Every jargon term defined once and reused consistently.
- When to use, when not to use, and sibling routing are explicit.
- Commands are verified before being documented as copy-pasteable.
- Unproven claims are labeled `open` or `candidate`.
- Each durable fact has one canonical home; other skills link to it.
- Security-relevant skills state writes, shell, network, secrets, and human-approval requirements.
- High-risk skills require HITL/audit/context-firewall checks before execution behavior changes.

## PR 2 - Low-Risk Skills

Target skills:

- `shell-hygiene`
- `first-run-setup`
- `gstack`

Planned metadata:

| Skill | Metadata moves |
|---|---|
| `shell-hygiene` | `when_to_use`, `effort: low`, `paths:` for shell files, portable script references |
| `first-run-setup` | explicit invocation, `argument-hint: [target-env]`, arguments, bounded system-state checks |
| `gstack` | `when_to_use`, `effort: medium`, `context: fork` for QA routes, no mid-review user questions for automated QA |

## PR 3 - Medium-Risk Doctrine And Review Skills

Target skills:

- `code-review`
- `git-history-surgery`
- `cidf`
- `afrp`

Planned metadata:

| Skill | Metadata moves |
|---|---|
| `code-review` | explicit invocation, `context: fork`, `argument-hint: [file-or-PR]`, `effort: high`, audit hook plan |
| `git-history-surgery` | explicit invocation, disallowed force-push patterns, `argument-hint: [commit-range]`, `effort: high`, Gate/HITL hook plan |
| `cidf` | `user-invocable: false`, `when_to_use`, low or medium effort depending on reasoning load |
| `afrp` | `user-invocable: false`, `when_to_use`, `effort: low` |

## PR 4 - Elevated-Risk Operational Skills

Target skills:

- `mcp-install`
- `openclaw-skills`

Planned metadata:

| Skill | Metadata moves |
|---|---|
| `mcp-install` | explicit invocation, scoped install tools, publish-oriented disallowed tools, `argument-hint: [mcp-server-name]` |
| `openclaw-skills` | explicit invocation, `effort: medium`, `paths:` for canonical skill/config surfaces, `argument-hint: [skill-name]` |

## PR 5 - High-Risk Planning-Only Refactor

Target skills:

- `hermes-harness`
- `mcp-orchestration`

Allowed:

- Split long `SKILL.md` bodies into references.
- Add security-surface sections.
- Add dry-run planner sections.
- Add HITL, audit-log, and context-firewall references.
- Improve metadata and trigger descriptions.
- Draft, but do not activate, hooks that write session-linked audit records.

Blocked until verified:

- new execution paths,
- new MCP dispatch behavior,
- connector expansion,
- autonomous partner routing,
- changes that bypass human approval or audit trails.

High-risk precondition:

```text
STATUS: BLOCKED until verified
- Gate 3 / HITL human-approval node is present and non-bypassable.
- Audit append target is configured.
- MCP context-firewall / mediator rules are incorporated.
- Operator acknowledges the risk class.
```

## Candidate New Skills

Create these only if reuse-before-create fails:

| Candidate | Create only if |
|---|---|
| `human-gate-verifier` | HITL/accountability docs cannot be routed through existing skills |
| `workflow-qualifier` | Existing review skills cannot own green/red workflow gating |
| `compliance-checker` | Compliance gates cannot fit into security/review skills |
| `hallucination-guard` | Grounding checks cannot be added cleanly to `code-review` or `cidf` |
| `prompt-engineer` | Existing skillify/docs-writing routes cannot own prompt design |

## Review Comments Root-Cause Plan

First-principles problem statement: the validator and reference snippet tried to enforce skill quality before their own parser semantics were proven.

Root causes:

1. Markdown fences are paired delimiters, not independent lines; validating every fence line treats closers as malformed openers.
2. Relative path depth is a count of leading parent segments, not a string contains check.
3. `root` meant two different things in the CLI, obscuring repo root vs. scan roots.
4. Strict-mode roadmap language exceeded the initial implementation because warnings had no allowlist mechanism.
5. The validator shipped without tests for parser and heuristic boundaries.

Countermeasures in this PR:

- Paired fence parser in the validator and Skillify snippet.
- Leading-parent segment counter for reference-depth warnings.
- `--scan-root` replaces the confusing repeatable `--root` option.
- Strict mode fails on errors and unallowlisted warnings.
- Unit tests cover frontmatter, fences, link depth, personal paths, and strict warning allowlisting.

## Review Checklist For Each Later PR

- Run `python3 scripts/review/check_orama_skills.py --mode baseline`.
- Compare warning deltas for touched skills.
- Confirm no skill moved canonical source into `.claude/skills/`.
- Confirm line-count movement trends downward or is justified.
- Confirm `description` + `when_to_use` stays <= 1,536 chars.
- Confirm invocation controls match side-effect/background/forked-skill risk.
- Confirm one-home-per-fact ownership.
- Confirm high-risk skills stayed planning-only unless preconditions were satisfied.

## Final Promotion Gate

After PRs 2-5, consider turning validator strict mode into CI.

Do not enable strict mode until:

- oversized legacy skills are split,
- high-risk skill warnings are resolved or explicitly allowlisted,
- all registered skills have compliant descriptions and `when_to_use` metadata,
- all code fences in skill markdown have language specifiers,
- side-effect/background skill invocation controls are in place.
