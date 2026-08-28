# Feature Extraction: LangGraph Checkpointers

> **Reconciliation status (2026-08-28):** thread/checkpoint identity -- **ADOPT**. Atomic
> successful-boundary checkpoints -- **ADOPT / ADAPT**. Durable resumability and durable
> deterministic resume -- **ADOPT R4 TARGET**. The historical "perfect resumption" phrase is
> **REJECT WORDING ONLY**, not a feature rejection: it means rigorously planned re-entry from an
> explicit saved boundary, not total reversibility, time travel, or universal exactly-once effects.
> See [`RECONCILIATION-2026-08-27.md`](RECONCILIATION-2026-08-27.md).
>
> **Goal:** Repurpose the "Compiled Graph" persistence model for our \`SqliteCheckpointer\`.

## 1. The Core Mechanic

LangGraph uses a **Thread ID + Checkpoint** key-value pair. This allows the same graph to handle
multiple concurrent sessions (threads) while maintaining a versioned history of state.

## 2. Best Practices to Mine

- **State Reducers**: LangGraph allows defining *how* new data merges with old data (e.g.,
  \`operator.add\` for message lists).
- **Atomic Writes**: Each node execution is wrapped in a transaction. If a node fails, the
  checkpoint remains at a known boundary, enabling planned resumability from saved state. The
  historical shorthand "perfect resumption" refers only to the precision of that boundary-defined
  resume contract; it does not imply reversing external reality or undoing effects that already
  occurred.
- **Async Efficiency**: Use \`aiosqlite\` to ensure the checkpointer never blocks the event loop
  (aligned with Gemini Hardening 7c).

## 3. oramasys v2 Adaptation

We will adopt the **Thread ID** concept as our \`session_id\`. Our \`SqliteCheckpointer\` (Tier 3
plugin) will store the full \`PerpetuaState\` blob after every successful node transition, indexed
by \`session_id\`.

R4 then promotes that persistence primitive into **durable deterministic resume** by adding
checkpoint lineage, graph/version identity, state-schema identity, an explicit replay boundary,
and effect identity/idempotency/deduplication policy.

The ambition is intentionally strong and realistic: save session and graph state precisely enough
to resume execution predictably from a declared point. This is resumability, not time travel.

**Reference Implementation Hint:**

```python
# Re-enter from the latest compatible declared checkpoint boundary.
def aresume(session_id: str, user_input: str):
    last_checkpoint = load_latest(session_id)
    # Validate compatibility and replay policy before resuming execution.
```
