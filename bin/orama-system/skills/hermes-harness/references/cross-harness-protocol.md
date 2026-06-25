# Cross-Harness Protocol

Distilled from [`ecc-hermes-cross-harness.md`](ecc-hermes-cross-harness.md)
§ "Cross-Harness Rule" and "PT-orama Loading Map."

## The Rule

Put durable behavior in the shared source (orama-system) first. Use
harness-specific files only for loading, command names, event shapes, and
platform limits.

## Three-Layer Architecture

| Layer | Repo | Role |
|---|---|---|
| L3 | orama-system (this repo) | Owns canonical skill definitions, routing policy, and stateless methodology |
| L2 | Perpetua-Tools | Middleware: receives agent-neutral skill envelopes, resolves `openclaw_home`, runs tools, returns normalized results |
| L1 | Hermes / OpenClaw / Codex / AGY | Operator shell / harness: applies config changes, invokes skills, may spawn partner agents |

Standard L3 → L1 dispatch path:

```text
orama-system
  → Perpetua-Tools skill dispatcher
  → orama-system/skills/{skill_id}/SKILL.md (canonical procedure)
  → target harness home (Hermes ~/.hermes, OpenClaw ~/.openclaw)
  → files changed / stowed / verified
```

## PT-Orama Loading Map

Each harness receives only the smallest adapter needed to locate and invoke
canonical skills. Canonical skill bodies always stay under
`bin/orama-system/skills/`.

| Harness | Loading surface | Boundary |
|---|---|---|
| **Hermes** | `install_hermes_thin_skills.py` installs `/pt-orama-*` wrappers | Keep provider config, credentials, and workspace memory local |
| **OpenClaw** | `openclaw-skills` master skill + Nine Skills overlays | Config and gateway operations only; no skill body duplication |
| **Codex** | Thin local wrappers generated from the canonical skill manifest | Do not copy references or scripts into the local skill directory |
| **AGY** | `ANTIGRAVITY.md` + `.agent/` point back to canonical cards | Treat AGY output as advisory; require a visible readiness canary before dispatch |
| **Claude Code** | Thin `.claude/skills/` wrappers + project instructions | Canonical skill bodies stay under `bin/orama-system/skills/` |

## Hermes Slash-Command Envelope

Hermes thin wrappers invoke canonical skills via slash commands:

```text
/pt-hardware-policy   → commands/pt-hardware-policy/SKILL.md
/pt-orama-council     → commands/pt-orama-council/SKILL.md
/pt-orama-delegate    → commands/pt-orama-delegate/SKILL.md
/pt-orama-review      → commands/pt-orama-review/SKILL.md
```

The thin wrapper must:
1. Point back to the canonical `SKILL.md` path in orama-system.
2. Carry no procedure body of its own.
3. Be regenerated from canonical on `install_hermes_thin_skills.py --install`.

## Invariants

1. Durable skills/rules live in orama-system — never in `~/.hermes` alone.
2. Hermes and OpenClaw are consumers of canonical skills, not owners.
3. No harness-specific file may re-declare a policy already in PT's YAML.
4. Every thin wrapper must be reproducible via the install script.
5. A redirect stub is sufficient for an absorbed entry point — no duplicate content.
