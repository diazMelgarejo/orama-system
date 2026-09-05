# 61 — PT Coordination Principal Identity — Design (Not Built)

> **Status:** design only, nothing implemented
> **Date:** 2026-09-05
> **Supersedes-in-scope:** the shipped `PT_AGENT_ID` environment-variable
> cross-check (Perpetua-Tools, commit `7b7d7dd9`), which remains the live
> mechanism until this design is prioritized and built

**Status: design only.** Nothing in this document is implemented. Per
direct decision, this doc exists so the design isn't lost or reinvented
from scratch, not as a build order.

## Current state, honestly

Perpetua-Tools' coordination CLI (`orchestrator/coordination/task_queue.py`,
`cli.py`) has **no authentication mechanism**, confirmed directly (a
repo-wide search for any principal/session/auth concept found zero matches)
before any of this work started. `queue_claim`'s reservation check
(`required_agent_id`) compared only against a caller-supplied CLI argument
with zero verification — any process on the machine could claim a task
reserved for a different agent simply by typing that agent's name.

The shipped fix (`orchestrator/coordination/task_queue.py`, commit
`7b7d7dd9`) adds a `PT_AGENT_ID` environment-variable cross-check: when set,
it must agree with the CLI-supplied `agent_id` or the claim is rejected.
This is explicitly **not authentication** — an environment variable is
self-declared, exactly like the CLI argument it's checked against, just
harder to change accidentally mid-session. It closes the *careless*
impersonation case (a wrong agent_id typo, a stale copy-pasted command) and
cannot stop a *deliberate* one. This document proposes what a real
mechanism would look like, for when that gap needs closing.

## Why this is a separate, deferred decision

Building real identity infrastructure is a materially larger project than
anything else in this remediation arc — it touches every coordination
call site, needs its own migration path for existing callers, and has
real operational cost (key/token provisioning, rotation, revocation).
Bundling it into a review-fix pass would have meant either rushing a
half-built mechanism or silently skipping the concern; neither is
acceptable. This doc exists so the real design is available the moment
it's prioritized, not rediscovered under time pressure.

## Threat model this actually needs to address

The coordination template's own framing already scopes this precisely:
Gossip/LAN transport is explicitly *not* meant to be "a distributed lock
or authorization system." This system runs on trusted-operator-controlled
machines (a developer's own LAN, or a single machine's local worktrees) —
it is not internet-facing and does not need to defend against an
unrelated network attacker. The realistic threat is a **misconfigured or
compromised local agent process** impersonating a different agent's
identity to claim work it shouldn't, or a bug in one agent's own code
accidentally reusing another agent's `agent_id`. This scopes the design
away from full PKI/mTLS (real, but disproportionate complexity for a
single-machine or single-LAN trust boundary) toward something lighter.

## Proposed design: per-agent registered bearer tokens

**Registration.** Each agent identity (e.g. `mac-orchestrator-1`,
`win-autoresearcher-2`) is provisioned once with a locally-generated,
random token (32+ bytes, base64-encoded), stored in a new
`.agent/coordination/principals.json` file:

```json
{
  "mac-orchestrator-1": {
    "token_hash": "sha256:...",
    "created_at": "2026-09-05T00:00:00Z",
    "revoked": false
  }
}
```

Only the hash is stored (matching how a password/API-key store should
work); the raw token is generated once, shown once, and the caller is
responsible for storing it in their own agent's local, untracked
environment (e.g. `PT_AGENT_TOKEN`, alongside the existing `PT_AGENT_ID`).

**Authoritative source across hosts.** The coordination template's own
existing pattern already designates the Mac orchestrator as the host that
"controls the coordination round" — this design reuses that same authority
split rather than inventing a new one: the Mac host owns the canonical
`principals.json`, and every registration/revocation is a write to that one
file on that one host. Windows co-orchestrator hosts hold a synced,
**read-only** copy, refreshed via the same LAN peer-file-inbox transport
already used for cross-host coordination assignments (`lan_peer_assign.py`)
— not a new sync mechanism. A Windows host with a stale copy fails closed:
an unrecognized or since-revoked token is rejected as invalid, never
silently accepted because the local cache hadn't caught up yet. Revocation
propagation delay is therefore bounded by the existing peer-sync cadence,
not instantaneous — acceptable for this threat model (misconfiguration/
local-bug protection, stated in the threat-model section above), since it
is not defending against a sophisticated attacker racing a revocation.

**Verification.** `queue_claim` (and any future principal-checked call)
requires both `PT_AGENT_ID` and `PT_AGENT_TOKEN` to be set. The token is
hashed and compared against the registered hash for that `agent_id`; a
mismatch, a revoked token, or a missing token is rejected before the
reservation check runs — the same insertion point the current
`PT_AGENT_ID`-only check uses today.

**Why bearer tokens over the alternatives considered:**

| Option | Rejected because |
| --- | --- |
| Full mTLS between agent processes | Real security, but requires a local CA, per-agent cert provisioning/rotation, and TLS termination in a CLI tool that currently has none — disproportionate to a single-machine/LAN trust boundary |
| OS-level process identity (`SO_PEERCRED` on a Unix socket) | Only works for same-host callers over a Unix socket; this coordination layer is SQLite-file-based, not socket-based, and Windows co-orchestrator hosts (named explicitly in the coordination template) have no equivalent primitive |
| Signed claims (each agent holds a private key, signs every claim) | Genuinely stronger (non-repudiation), but needs key provisioning/rotation infrastructure equivalent to the token approach with added asymmetric-crypto complexity, for a threat model that doesn't yet require non-repudiation |
| Bearer token (this proposal) | Matches the actual threat model (misconfiguration/local-bug protection, not defense against a sophisticated remote attacker), reuses infrastructure this repo already has patterns for (hash-then-store, matching how the endpoint-policy security primitive elsewhere in this org already handles comparable secrets) |

**`PT_AGENT_TOKEN` outcome matrix:**

| State | M-id-1 / M-id-2 (fallback active) | M-id-3 (token required) |
| --- | --- | --- |
| Unset | Falls back to today's `PT_AGENT_ID`-only check | Rejected: token required |
| Set, but no matching entry in `principals.json` | Rejected: unregistered token | Rejected: unregistered token |
| Set, matches an entry marked `revoked: true` | Rejected: revoked token | Rejected: revoked token |
| Set, hash mismatch against the registered `agent_id`'s entry | Rejected: token/identity mismatch | Rejected: token/identity mismatch |
| Set, valid, matches a non-revoked entry for this `agent_id` | Accepted | Accepted |

## Migration path, if and when this is prioritized

1. **M-id-1:** Ship `principals.json` + token generation/verification as
   opt-in — `PT_AGENT_TOKEN` unset falls back to today's `PT_AGENT_ID`-only
   check, so no existing caller breaks.
2. **M-id-2:** A deprecation window where `PT_AGENT_ID`-only claims log a
   warning but still succeed, giving every real caller time to provision a
   token.
3. **M-id-3:** `PT_AGENT_ID`-only claims are rejected; a token is required
   for every principal-checked call. This is the point at which the
   mechanism can honestly be called authentication rather than a
   defense-in-depth signal.

No timeline is set for M-id-1 in this document — it starts only when
explicitly prioritized, not as a consequence of this doc existing.

## Explicit non-goals

- This does not attempt to authenticate the *human* operator behind an
  agent process — the coordination template's own authority-boundary
  table already scopes that as the human operator's own responsibility,
  separate from agent-to-agent identity.
- This does not propose network-level authentication for the LAN
  peer-file-inbox transport (`lan_peer_assign.py`) — that's a separate
  transport with its own existing design, out of scope here.
- This does not claim to defend against a fully compromised machine —
  if an attacker has local code execution as the same user running these
  agents, they can read `principals.json`'s token store directly. This
  design raises the bar against misconfiguration and cross-agent
  confusion, not against a fully compromised host.
