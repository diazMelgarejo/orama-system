# Author, Actor, Endorsement, and Takeover Policy

## Purpose

This policy applies to every agent-generated coordination record, handoff,
claim, status update, review result, or completion statement. It is the
canonical instruction-layer policy for GossipBus and all OpenClaw-compatible
agent runners.

## Terms

- **Author** is the originating agent or lane that produced the work,
  analysis, or decision being described. It does not change when another
  agent publishes, reviews, resumes, or transports that work.
- **Actor** is the concrete current agent instance performing the operation.
  An actor must identify its `agent_id`, a run/session/instance identifier
  when available, and whether its identity was independently verified.
- **Endorser** is an agent that independently reviewed evidence and explicitly
  supports a bounded claim. Endorsement is not authorship and is not approval
  to merge, deploy, or otherwise advance work.
- **Takeover** is a new actor resuming, publishing, changing, committing, or
  completing work started by a different author or prior actor.

## Required provenance envelope

Use a structured envelope when the receiving contract supports one (for
example `orchestrator.envelope_standard.AgentEnvelope`). Otherwise include the
same facts as explicit fields or clearly labelled text:

```json
{
  "author": {
    "agent_id": "originating-lane-or-agent",
    "work_ref": "immutable commit, PR, artifact, or board reference"
  },
  "actor": {
    "agent_id": "current-agent",
    "instance_id": "run-or-session-id-if-known",
    "identity_verified": false
  },
  "endorsement": {
    "status": "none|independent-review",
    "evidence_refs": []
  },
  "takeover": null
}
```

`identity_verified` may be `true` only when a trustworthy runtime, credential,
or independently checked registry proves the actor identity. Self-reporting an
agent name is not verification. Do not omit the distinction merely because the
author and actor happen to have the same `agent_id`.

## Endorsement and completion boundaries

- State the exact reviewed evidence and the bounded conclusion. A passing test,
  a review comment, or a board note is not a blanket endorsement.
- Never convert an implementation author's claim into reviewer approval,
  merge authorization, dispatch authorization, qualification, or completion.
- Preserve pending review, CI, human authorization, and known-risk status in
  every summary. Only the authorized decision-maker may change those states.
- Record authorization to merge, deploy, dispatch, or promote work as a
  separate decision by its authorized owner, never as an endorsement status.

## Takeovers

Before taking over, publish or include all of the following:

1. the previous author/actor and their known status;
2. an immutable work reference (commit SHA, PR head SHA, artifact digest, or
   immutable board record);
3. independently checked evidence and the scope of what was verified;
4. the takeover actor and the intended next operation; and
5. any required authorization for commit, push, completion, merge, dispatch,
   or deployment.

The takeover actor may report its own new work, but must not rewrite prior
authorship. If the prior state, evidence, or authority cannot be established,
report the work as unverified and stop before making a completion or promotion
claim.

## Prohibitions

- No silent authorship reassignment or authorship rewrite.
- No spoofed pulse, heartbeat, status, claim, or completion event for a
  stopped, absent, or unverified agent.
- No cross-branch or cross-worktree transplantation presented as the original
  author's current work without the author reference and takeover disclosure.
- No direct SQLite writes to coordination storage; use `GossipBus.emit` or the
  supported coordination API so classification, redaction, and indexing occur.

## GossipBus minimums

- For a substantive `agent_note`, pair the same actor with an `agent_pulse`.
- Put `author`, `actor`, `endorsement`, and `takeover` fields in the payload
  for every substantive work claim, including when author and actor are the
  same agent. Liveness-only events may remain minimal, but cannot be used as
  evidence of authorship, endorsement, or takeover.
- Read the current board state before claiming, resuming, or contradicting
  work; append corrections rather than mutating or deleting history.
