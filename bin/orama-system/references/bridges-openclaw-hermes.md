<!-- lint-ignore LINT-013 -->
# OpenClaw and Hermes Bridges

> Tier 2 bridge details for the orama-system mother skill: how to offload heavy reasoning
> through the OpenClaw gateway (`mcp-oramasys`) and how the Hermes cross-harness bridge
> relates to it. Moved verbatim out of `SKILL.md` to keep the mother skill under the OSSF-1
> 500-line ceiling. Paths in code spans are relative to `bin/orama-system/`; link targets
> were rebased for this folder. The loopback gateway address is written `localhost:18789` here
> (same host; the repo hygiene gate forbids new loopback IP literals).

## OpenClaw Multi-Agent Bridge (Tier 2)

Use the `mcp-oramasys` tool to offload heavy reasoning through the
OpenClaw gateway at `localhost:18789`. Model selection is automatic — OpenClaw
reads `~/.openclaw/openclaw.json` and routes each `agent_id` to the correct
live provider (LM Studio / Ollama, Mac / Windows GPU).

### Capabilities

- `openclaw_chat`: Route by role (`coder`, `orchestrator`, `mac-researcher`, `win-researcher`)
- `openclaw_list_agents`: List agents registered in `~/.openclaw/openclaw.json`
- `openclaw_orchestrate`: Dispatch Stage 4 execution tasks via OpenClaw gateway
- `openclaw_health`: Verify gateway is running at `localhost:18789`

## Hermes Cross-Harness Bridge (Tier 2 sibling)

Use [`skills/hermes-harness/SKILL.md`](../skills/hermes-harness/SKILL.md) when
Hermes is the operator shell for PT-orama work. Hermes consumes canonical
skills, MCP conventions, and bounded partner prompts; OpenClaw remains the
runtime gateway/configuration fabric. Do not import raw `~/.hermes` state,
secrets, personal memory, or local business artifacts into the repo.

Hermes worker default: bounded coding partner. The main orama agent keeps
judgment, CIDF write discipline, and final synthesis.

Companion context:

- `skills/hermes-harness/references/ecc-hermes-cross-harness.md` for ECC import
  decisions and cross-harness boundaries.
- `../../ANTIGRAVITY.md` and `../../.agent/AGENTS.md` for Antigravity project
  wiring that points back to canonical orama skills instead of copying them.
- `../../docs/wiki/15-hermes-windows-harness.md` for the Windows PATH,
  `HERMES_GIT_BASH_PATH`, and explicit Hermes one-shot provider route.
