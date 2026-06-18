# Hermes Council Review Gates

Use this reference when `/pt-orama-council` needs a multi-agent review loop.
The command card stays concise; this card holds the reusable protocol.

## Roles

| Role | Default surface | Responsibility |
|---|---|---|
| Host/Executor | Codex or current main orama agent | Plan, edit, verify, commit, and make final decisions |
| Reviewer/Critic | AGY/Antigravity | Review plans and deliveries after visible-output readiness passes |
| Local Specialist | Hermes | Handle bounded private or local subtasks after provider canary passes |

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

## Do Not Use Council For

- Simple one-shot tasks.
- Work where no partner lane has passed readiness.
- Work requiring a worker to commit, deploy, delete, force-push, change account
  settings, or process secrets directly.
- Tasks where the overhead of the gate loop is larger than the risk it reduces.
