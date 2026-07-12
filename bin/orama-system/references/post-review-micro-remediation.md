# Post-Review Micro-Remediation Pattern

> **Role:** single reusable pattern for addressing CodeRabbit / human review
> findings after a PR is opened, without accumulating history churn or
> losing mechanical attribution. Do not duplicate this logic into individual
> skills — link here.
> **Origin:** evolved through trial and error during PT PR #205/#206 —
> multiple review rounds, a rogue-commit incident on `main`, a branch reset,
> and a follow-up review — formalized 2026-07-13.
> **Underlying principle:** minimize history churn after review; make every
> remediation mechanically attributable to the finding that caused it.

---

## The 6 phases

### Phase 0 — Freeze

- Do not continue developing on `main`.
- Treat the reviewed PR branch as the only write target until review is complete.
- **Mechanically enforced (added 2026-07-13):** `.githooks/pre-push` blocks
  direct pushes to `refs/heads/main`/`master` by default (escape hatch:
  `ALLOW_MAIN_PUSH=1`), synchronized identically across `Perpetua-Tools` and
  `orama-system`. `.github/workflows/main-push-guard.yml` is the visibility
  backstop for pushes that bypass the local hook (`--no-verify`) — it flags,
  it cannot block after the fact. Neither substitutes for GitHub branch
  protection on `main`, which requires `administration` scope not available
  to this project's tokens; that must be configured manually in repo
  Settings for durable, unbypassable enforcement. This closes the loop from
  the incident that motivated the doctrine: the doctrine's own authoring
  commit was briefly pushed straight to `main` before this guard existed.

### Phase 1 — Root-cause clustering

- Group review comments by underlying invariant (encoding, persistence,
  concurrency, lifecycle, security, etc.) — not by file or by comment order.
- Fix the abstraction once instead of applying isolated per-comment patches.
- Example: 3 independent copies of an undefined-heartbeat-handler bug across
  `agent_coordination.py`, `agent_coordination_legacy.py`, and
  `agent_coordination_core.py` cluster under "duplicated dispatch logic" —
  the durable fix is a shared facade, not 3 separate patches.

### Phase 2 — Branch discipline

- Work only on the open PR branch.
- Keep commits cohesive by failure class (one commit per root-cause cluster
  from Phase 1, not one commit per file or per review comment).
- Preserve the original PR scope and description; append updates rather
  than replacing them.

### Phase 3 — Integration

- Merge the reviewed PR.
- If post-merge problems are discovered, move `main` back to the last
  common ancestor with the remediation branch (when project policy allows),
  rather than accumulating revert commits that complicate later
  reconciliation. Revert chains make history harder to reason about with
  every additional revert; a clean ancestry reset is a single, auditable
  operation.
- **Before any reset, create a safety ref** (tag or branch) pointing at the
  commit about to be discarded. Never discard unique work — verify the
  content is preserved elsewhere (another branch, a safety ref) before
  resetting.
- Re-evaluate whether the remediation branch actually requires a rebase.
  If it already descends cleanly from the restored base
  (`merge-base(main, branch) == restored_base`), do not rebase. Rebase is a
  means, not a cleanliness ritual — don't rewrite an already-reviewable
  branch merely to remove an old merge commit when there's no missing base
  work.

### Phase 4 — Verification

- Run the full regression suite.
- For every review finding, confirm it is either:
  - **fixed** — with a regression test proving the fix (and, where
    practical, proving the test fails on the pre-fix code),
  - **intentionally superseded** by a deeper abstraction fix (state which
    fix supersedes it and why the original finding no longer applies), or
  - **documented as not applicable** — with a one-line reason, not silence.

### Phase 5 — Closure

- Leave the branch open for human review if requested.
- Merge only after review approval.

---

## Enforcement — reference this doc, don't duplicate it

Each consuming skill imports only the phases it needs, per the modular
Skillify pattern:

| Skill | Phases it needs |
|---|---|
| [`agent-methodology`](../skills/agent-methodology/SKILL.md) | All 6 — this is the doctrine's home methodology |
| [`code-review`](../skills/code-review/SKILL.md) | Phase 1 (root-cause clustering), Phase 4 (verification gates) |
| [`git-history-surgery`](../skills/git-history-surgery/SKILL.md) | Phase 3 (integration — safety refs, reset-vs-rebase decision) |
| [`gstack`](../gstack/SKILL.md) | Phase 0 (freeze), Phase 5 (closure) — AutoPlan review gating |
| [`skillify`](../skills/skillify/SKILL.md) | Phase 2 (branch discipline) — matches the modular-skill-authoring pattern this doc itself follows |
| [`hermes-harness`](../skills/hermes-harness/SKILL.md) | Phase 0 (freeze), Phase 2 (branch discipline) — multi-agent dispatch must not write to `main` mid-review |
| [`mcp-orchestration`](../skills/mcp-orchestration/SKILL.md) | Phase 1 (root-cause clustering) — routing bugs across providers cluster the same way as coordination-dispatch bugs did |

---

## Related

- [`multi-agent-collaboration-protocol.md`](multi-agent-collaboration-protocol.md) — the nested-branch merge protocol this pattern complements (that doc covers merging concurrent branches; this one covers remediating a single branch after review)
- [`oramasys-method/references/integrative-merge.md`](../skills/oramasys-method/references/integrative-merge.md) — synthesize, never amputate; six resolution modes referenced by Phase 3's reset-vs-rebase decision
- PT `.agent/AGENTS.md` § Multi-agent merge conflict protocol — portable-brain summary of the sister pattern for concurrent branches
