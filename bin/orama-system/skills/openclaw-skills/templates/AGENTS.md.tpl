# AGENTS

## Sub-agent wiring
- Current agent: `{{agent_id}}`
- Parent agent: `{{parent_agent}}`

Allowed child agents:
{{allow_agents_yaml}}

Wiring rules:
- Spawn child agents only for bounded, parallelizable subtasks.
- Keep ownership boundaries explicit per child.
- Avoid duplicate delegation of unresolved work.
- Require structured handoff before task closure.

## Session startup sequence
{{startup_sequence}}

Default startup policy:
1. Load identity and safety constraints.
2. Load user preferences and operating context.
3. Validate tool availability and permissions.
4. Resolve required files and working paths.
5. Execute the first minimal, reversible action.

Coordination policy:
- Parent agent remains accountable for final integration.
- Child agents must return evidence, changed files, and risks.
- If a child fails, retry once with narrower scope.
- Escalate to parent when confidence remains low.

Shutdown policy:
- Persist outcome summary.
- Persist structured output contract.
- Close transient sessions and release temporary resources.
