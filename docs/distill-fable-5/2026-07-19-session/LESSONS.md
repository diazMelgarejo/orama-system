# Lessons — 2026-07-19 session (Fable-5 distillation V1→V2 track)

STATUS: TEMPLATE — skeleton only, not yet filled. This is scaffolding for the
agent(s) actually running this session's live work to fill in as it happens,
mirroring the format of `../2026-07-02-pilot/LESSONS.md` and
`../2026-07-03-session/LESSONS.md`: numbered items, **bold one-line rule**
first, then 1-4 sentences of concrete evidence (what broke, what was
verified, what command/log proved it) — not a narrative recap. Delete this
STATUS line and each `[FILL:]` placeholder as it's replaced with a real
entry; delete any numbered slot that ends up with nothing to report rather
than leaving it as unfilled scaffolding in the final version.

Scope note: this session is the **distillation V1→V2 track** (Fable 5 sense
(a), the model tier) — a different track from Parts 1/2, which were the
**orchestrator-role** pilot (sense (b)). Don't force this session's real
findings to look like Parts 1/2's CI/MCP/subagent-availability lessons if
they don't apply; capture what actually happened here.

1. **[FILL: real-export schema verification result]** — Step 2 of
   `references/Fable-5-implementation-plan-revised-2026-07-19.md` was the
   actual month-long blocker: does the real Claude conversation export match
   the schema `FableExportParser-skeleton.py` was built against (top-level
   `model` field, `current_leaf_message_uuid`/`parent_message_uuid`
   branching, `content[]` text blocks)? State the verdict plainly — matched
   as documented / diverged (and how) — with the exact field names observed,
   not just "looked fine."

2. **[FILL: FableExportParser real-data result]** — Once wired into
   `distill_session.py`'s `_PARSERS` (before `GenericJsonTranscriptParser`),
   did it parse the real export correctly on the first try, or did
   `can_parse()`/`parse()` need changes? If changes were needed, name the
   specific field/assumption that was wrong and the actual fix — this is the
   one slot most likely to contain a genuine surprise, since everything
   before it was built against documentation, not data.

3. **[FILL: Codex-review findings' real-world bite, if any]** — The
   2026-07-19 Codex review (`references/Fable-5-plan-and-parser-review-to-Claude-2026-07-19.md`)
   flagged two fail-open gaps (unwalkable lineage reaching `parse()`,
   unrecognized senders) that were fixed and smoke-tested against synthetic
   data before the real export existed. Did either gap actually fire against
   real data, or did the synthetic tests fully anticipate the real shape?
   Either answer is useful evidence for whether synthetic smoke-testing is
   sufficient before real data exists, or whether it systematically misses
   something.

4. **[FILL: delegation ladder outcome, if the ladder was actually exercised]** —
   Per Parts 1/2's `DELEGATION_MAP.md` pattern and this session's standing
   constraint (Kimi/Codex/Haiku/Sonnet-5-Medium only, never Opus): which rung
   actually did the Step 3 TDD work (add failing tests, implement, make
   green)? Note any escalation (local model failed → subagent → inline) the
   way Parts 1/2 did, with real timing/iteration-count evidence if available
   — not just "used Sonnet."

5. **[FILL: anything that broke and how it was actually root-caused]** —
   Parts 1/2's strongest lessons were CI/config failures resolved by reading
   actual logs (`gh run view --log-failed`) rather than by hypothesizing.
   If `uv run pytest -q tests/test_distill_session.py` failed at any point,
   record the actual error and the actual fix, not the guessed cause that
   turned out wrong (if there was one — that's still worth recording, per
   this workspace's "log the self-correction, don't silently overwrite it"
   discipline already used once in this track, see
   `Fable-5-implementation-plan-revised-2026-07-19.md` §3's model-field
   self-correction).

6. **[FILL: ADR D17/D18-D21 decision gate outcome]** — Step 4 of the plan
   (approve or explicitly re-defer the v2 routing/caching ADRs) is a decision
   gate, not an agent task. Record what was actually decided and by whom,
   since this gates Steps 5-9 (`MultiLLMRouter`, cache correctness,
   `config/{models,routing,devices}.yml`, `cost_guard.py`, eval harness) —
   leaving this unfilled means the next session has to re-derive whether v2
   implementation work is authorized yet.

## Related artifacts from this session (fill in paths once they exist)

- `[FILL: link to the real export file's location or handling, if kept — mind
  credential/PII handling per SECURITY.md, do not commit raw export content]`
- `[FILL: link to the FableExportParser commit once it lands in
  distill_session.py]`
- `[FILL: link to the new regression tests in test_distill_session.py]`
