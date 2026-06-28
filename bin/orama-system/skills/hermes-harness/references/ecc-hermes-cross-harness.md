# ECC Hermes Cross-Harness Notes

This reference adapts public ECC Hermes/OpenClaw guidance for PT-orama. It is a
summary and operating map, not a vendored copy.

Sources:

- <https://github.com/affaan-m/ECC/blob/main/docs/HERMES-SETUP.md>
- <https://github.com/affaan-m/ECC/blob/main/docs/HERMES-OPENCLAW-MIGRATION.md>
- <https://github.com/affaan-m/ECC/blob/main/docs/architecture/cross-harness.md>

## Deduced Goals

1. Make Hermes a first-class PT-orama harness beside OpenClaw, not a replacement
   for OpenClaw.
2. Keep durable workflow knowledge in canonical skills and references; keep
   harness-specific loading thin.
3. Use ECC as the cross-harness vocabulary for skills, rules, hooks, MCP config,
   commands, sessions, and migration decisions.
4. Use Gemini, AGY, Hermes, and Codex CLI as bounded coding partners with clear
   prompts, no secret exposure, and no autonomous commits.
5. Make Windows onboarding reproducible with existing frugal tools: LM Studio
   Node/npm, GitHub Desktop/Git for Windows, Hermes-managed uv, and explicit
   `HERMES_GIT_BASH_PATH`.

## ECC Setup Lessons

The ECC setup guide frames Hermes as the operator shell and ECC as the reusable
workflow substrate. The useful public surface is not a raw local Hermes export;
it is a sanitized set of skills, hooks, MCP conventions, generated workflow
patterns, cron topology, and operator docs.

Recommended PT-orama adaptation:

| ECC idea | PT-orama adaptation |
|---|---|
| Hermes front door | Hermes operator shell for chat, CLI, cron, and workspace state |
| ECC reusable substrate | orama-system canonical skills plus PT middleware |
| `~/.hermes/skills/ecc-imports/` | sanitized Hermes imports from canonical orama/ECC skills |
| `~/.hermes/config.yaml` | local-only provider routing and MCP registration |
| `~/.hermes/cron/jobs.json` | local operator automation, never repo source of truth |
| `~/.hermes/workspace/` | private workspace memory, do not publish |

Bring-up order:

1. Inventory any legacy Hermes/OpenClaw workspace before importing.
2. Plan and scaffold reusable artifacts before copying content.
3. Verify the canonical skill/harness repo tests first.
4. Install Hermes and point it at imported skills.
5. Register only the MCP servers used daily.
6. Authenticate providers locally, starting with GitHub and document stores.
7. Start with small recurring jobs before heavier personal workflows.

## Migration Decision Map

Treat Hermes and OpenClaw as source systems. Distill behavior into the smallest
safe PT-orama/ECC surface:

| Source artifact | Durable target |
|---|---|
| Reusable workflow knowledge | Skill |
| Procedural action | Command or hook |
| Runtime/session routing | Adapter or control-plane issue |
| Generic setup instructions | Doc or example |
| Private memory, tokens, account state | Do not ship |

Questions before importing:

1. Is it reusable across operators or personal to one workspace?
2. Is the asset mainly knowledge, procedure, or runtime behavior?
3. Should it become a skill, command, hook, doc/example, or issue?
4. Does publishing it leak secrets, private datasets, local paths, or personal
   operating state?

## Cross-Harness Rule

Put durable behavior in the shared source first. Use harness-specific files only
for loading, command names, event shapes, and platform limits.

For PT-orama:

- Canonical skills live under `bin/orama-system/skills/`.
- Perpetua-Tools should dispatch normalized envelopes and mediate local tools.
- Hermes imports or points at reusable skills but keeps credentials local.
- OpenClaw uses `openclaw-skills` for configuration, channels, cron, secrets,
  stow, restart, and gateway operations.
- Codex, Gemini, AGY, and Hermes are coding partners only when bounded by an
  explicit prompt and reviewed before edits land.

### PT-orama Loading Map

The canonical behavior remains in orama-system. Each harness receives only the
smallest adapter needed to locate and invoke it:

| Harness | PT-orama loading surface | Boundary |
|---|---|---|
| Codex | Thin local wrappers generated from the canonical skill manifest | Do not copy references or scripts into the local skill directory |
| Hermes | `install_hermes_thin_skills.py` installs `/pt-orama-*` wrappers | Keep provider config, credentials, and workspace memory local |
| Antigravity | `ANTIGRAVITY.md` and `.agent/` point back to canonical cards | Treat AGY output as advisory and require a visible readiness canary |
| Claude Code | Thin `.claude/skills/` wrappers and project instructions | Canonical skill bodies stay under `bin/orama-system/skills/` |
| OpenClaw | `openclaw-skills` owns gateway, channel, cron, and secret operations | Hermes onboarding must not replace or guess OpenClaw procedures |

Do not create another council skill merely to represent a harness. Extend the
canonical Hermes command/reference cards, then update only the relevant thin
adapter when its trigger or path changes.

## Authority And Defaults

- The council is an optional risk-control pattern, not the default for every
  onboarding task or one-shot operation.
- The main orama agent owns decisions, edits, verification, and final synthesis.
- Reviewer labels and scores are advisory; no external lane has veto authority.
- A missing, quota-limited, unauthenticated, or timed-out lane is recorded as
  unavailable rather than simulated.
- Hermes is a harness, not proof of local execution. Treat a task as private
  only when the active provider is verified as the intended loopback endpoint
  and its completion canary succeeds.

## Partner Prompt Contract

Use this shape for Hermes, Gemini, AGY, or Codex CLI workers:

```text
ROLE: coding partner for PT-orama
GOAL: <specific outcome>
CONSTRAINTS:
- do not commit, deploy, delete, or change accounts
- do not reveal or request secrets
- do not import raw Hermes/OpenClaw local state
- cite files and tests used as evidence
OUTPUT:
- assumptions
- findings
- proposed_edits
- tests
- risks
```

The main orama agent owns final synthesis, CIDF write discipline, and merge
readiness.

## Mac ↔ Win LAN peer (Hermes)

Identical operator instructions on both hosts:

- [lan-peer-self-talk.md § Operator playbook](lan-peer-self-talk.md#operator-playbook)
- [docs/guides/lan-peer-mac-win-operator.md](../../../../docs/guides/lan-peer-mac-win-operator.md)

Hermes slash: `/lan-peer-self-talk`. Launcher: `./start.sh --lan-peer` / `start.ps1 --lan-peer`.
