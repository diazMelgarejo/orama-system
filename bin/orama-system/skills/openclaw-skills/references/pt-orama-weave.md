# PT + orama-system Weave for OpenClaw Skill Execution

This document defines how Perpetua-Tools (L2) and orama-system (L3) cooperate
to spawn and operate OpenClaw instances through the OpenClaw skill pack.

## Layer Model
- L3: `orama-system` orchestration and policy intent.
- L2: `Perpetua-Tools` execution substrate and envelope resolver.
- L1: OpenClaw runtime instances and local agent procedures.

## Primary Resolver Path
PT resolver entrypoint:
`orchestrator/openclaw_skill_resolver.py::resolve_skill(skill_id, args, agent_id, openclaw_home, parent_chain)`

`resolve_skill(...)` returns a `SkillEnvelope` containing at minimum:
- `skill_id`
- `args`
- `agent_id`
- `openclaw_home`
- `parent_chain`
- resolved skill path
- execution constraints and budgets

## Bootstrap Path
PT bootstrap entrypoint:
`orchestrator/alphaclaw_manager.py::bootstrap_alphaclaw(mac_ip, win_ip) -> AlphaClawState`

`bootstrap_alphaclaw(...)` initializes cross-host state and returns `AlphaClawState` with:
- endpoint coordinates
- process health metadata
- channel readiness
- resolver capability status

## Normal Call Pattern
Standard execution flow:
1. orama L3 receives task intent requiring a skill.
2. orama calls `PT.resolve_skill(...)` with skill id and args.
3. PT validates recursion, policy, and asset availability.
4. PT returns a `SkillEnvelope`.
5. Target agent reads relevant `SKILL.md` instructions.
6. Agent executes the procedure using local tools/scripts.
7. Agent emits Output Contract JSON.
8. orama records result and decides next transition.

## Output Contract Expectations
Output should be structured JSON with explicit status semantics:
- `status`: `ok` | `warn` | `error`
- `data`: operation payload on success
- `message`: human-readable diagnostics on non-ok states
- optional `meta`: timing, files touched, child invocations

## Recursive Spawning Path
A spawned OpenClaw instance may invoke additional skills through PT:
`PT.child_envelope(parent_envelope, skill_id, args)`

This creates a child envelope that:
- appends to `parent_chain`
- inherits bounded execution context
- applies depth and budget checks before dispatch

## Parent-Child Continuity
Child envelopes must preserve lineage for traceability.
Lineage fields should include:
- originating top-level request id
- direct parent envelope id
- current depth
- skill transition reason

## MCP-Based Discovery Loop
OpenClaw skill discovery can run through MCP metadata and local file checks.

ASCII loop diagram:

```text
+------------------+        request skill        +----------------------+
| orama-system L3  | --------------------------> | PT resolver L2       |
| intent + policy  |                             | resolve_skill(...)   |
+------------------+                             +----------+-----------+
                                                           |
                                                           | SkillEnvelope
                                                           v
                                                +----------+-----------+
                                                | OpenClaw agent L1    |
                                                | read SKILL.md        |
                                                +----------+-----------+
                                                           |
                                                           | execute procedure
                                                           v
                                                +----------+-----------+
                                                | Output Contract JSON |
                                                +----------+-----------+
                                                           |
                                                           | result + meta
                                                           v
+------------------+      update graph/state   +----------+-----------+
| orama-system L3  | <------------------------- | PT bookkeeping L2    |
+------------------+                            +----------------------+
```

## Failure Semantics
If resolver checks fail, PT should fail before execution begins.
Common hard failures:
- unknown skill id
- missing skill files
- recursion depth violation
- envelope budget exceeded
- parent lineage inconsistency

## Recovery Semantics
Recovery should be explicit and typed:
- Retry only transient infrastructure failures.
- Do not retry deterministic validation failures.
- Emit structured error contracts for upstream policy routing.

## Integration Invariants
- `SKILL.md` remains procedural source of truth at execution time.
- PT resolver is authoritative for envelope constraints.
- orama controls policy-level branching and escalation.
- Child instances cannot bypass resolver checks.

## Operational Guardrails
- Keep skill ids stable and versioned.
- Enforce JSON contract validation at boundaries.
- Capture per-envelope telemetry for auditability.
- Persist lineage for all recursive branches.

## Example Lifecycle
1. Parent agent invokes `openclaw-new-agent` via resolver.
2. Skill creates files and returns `status=ok` with file manifest.
3. Parent immediately invokes `openclaw-add-script` as child task.
4. PT emits child envelope with incremented depth.
5. Child returns `status=warn` for optional missing tool.
6. Parent aggregates outputs and returns final contract.

## Suggested Validation Checks
- Envelope schema validation before dispatch.
- `parent_chain` monotonic append-only checks.
- Depth and budget checks per dispatch.
- Output Contract schema validation on return.

## Observability Hooks
Capture at minimum:
- resolver latency
- execution latency
- status distribution
- recursion depth histogram
- top failing skills

## Security Considerations
- Treat envelope args as untrusted input.
- Validate paths against allowed roots.
- Redact secrets from logs and output payloads.
- Reject attempts to mutate protected policy files.

## Summary
The weave is: intent at L3, bounded resolution at L2, deterministic procedure at L1,
then structured return to L3 for next-state orchestration.
