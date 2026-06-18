# Hermes Council Review Gates

Use this reference when `/pt-orama-council` needs a multi-agent review loop.
The command card stays concise; this card holds the reusable protocol.

## Roles

| Role | Default surface | Responsibility |
|---|---|---|
| Host/Executor | Codex or current main orama agent | Plan, edit, verify, commit, and make final decisions |
| Reviewer/Critic | AGY/Antigravity | Review plans and deliveries after visible-output readiness passes |
| Local Specialist | Hermes | Handle bounded subtasks after provider canary; private data requires a verified local endpoint |

The main orama agent always keeps judgment. Workers may critique, propose, or
specialize; they do not commit, delete, deploy, force-push, change accounts, or
handle secrets directly.

## Gate Loop

Use the council only for multi-step, high-risk, private, or cross-harness work:

```text
Plan -> Review -> Execute -> Review -> Finalize
```

Proceed past a review gate only when:

- reviewer output is usable,
- findings are clean or intentionally accepted by the main orama agent,
- the relevant readiness canary passed for that lane,
- verification evidence is attached to the handoff.

If AGY, Hermes, Gemini, or LM Studio is unavailable, record that lane as
unavailable and continue with the remaining verified lanes. Never fake a
council participant.

### Checkpoints

Use only the checkpoints justified by task risk:

| Checkpoint | Use when | Evidence expected |
|---|---|---|
| Initial plan | The task is multi-step or assumptions are costly | Scope, constraints, plan, and known risks |
| Architecture | Interfaces, security boundaries, or data flow change | Alternatives considered and affected surfaces |
| Implementation | A major delivery is ready for critique | Focused diff or artifact plus targeted tests |
| Verification | Correctness depends on runtime or integration behavior | Commands, outputs, and residual gaps |
| Final review | Before commit, PR update, or handoff | Findings disposition and final test evidence |

Do not turn every checkpoint into a mandatory external call. A lane can be:

- `READY`: canary passed and useful output is available.
- `UNAVAILABLE`: missing, unauthenticated, quota-limited, or timed out.
- `SKIPPED`: available but unnecessary for this task.

Only `READY` lanes participate. The host records why other lanes were skipped
or unavailable and continues when it can still verify the result locally.

## Review Package

When sending work to a reviewer, include:

```text
GOAL:
CONTEXT:
CHANGES OR PLAN:
VERIFICATION:
KNOWN RISKS:
REQUESTED OUTPUT: FINDINGS, MISSING COVERAGE, APPROVAL
```

Reviewer output should be findings-first. Approval words such as `CLEAN` are
advisory; the main orama agent decides whether to proceed.

## Reusable Prompts

### Reviewer/Critic

```text
ROLE: Reviewer/Critic. Do not edit files or run destructive commands.
GOAL: <goal>
PLAN OR DELIVERY: <focused content>
VERIFICATION: <commands and results>
KNOWN RISKS: <risks or unknowns>

Return:
1. Critical findings
2. Important findings
3. Missing verification
4. Advisory status: CLEAN or NEEDS_REVISION
```

### Local Specialist

```text
ROLE: Bounded local specialist. Review, critique, or propose only.
GOAL: <goal>
SUBTASK: <one narrow task>
CONTEXT: <minimum required context>
MODEL: <exact ID returned by the live provider, when applicable>

Return:
ASSUMPTIONS:
FINDINGS OR PROPOSAL:
VERIFICATION:
LIMITATIONS:
```

Never describe a model by a guessed marketing name. Discover the exact model
identifier from the live provider and include it in the handoff only after the
relevant completion canary succeeds.

Hermes alone does not make a task local. Before sending private data, verify
that the selected provider resolves to the intended loopback LM Studio endpoint;
a Nous Portal, OpenRouter, or other hosted route is cloud egress.

## Do Not Use Council For

- Simple one-shot tasks.
- Work where no partner lane has passed readiness.
- Work requiring a worker to commit, deploy, delete, force-push, change account
  settings, or process secrets directly.
- Tasks where the overhead of the gate loop is larger than the risk it reduces.
