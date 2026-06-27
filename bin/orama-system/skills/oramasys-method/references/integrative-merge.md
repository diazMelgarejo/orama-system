# Integrative PR Merge — additive harmonization (orama-way)

> **When to load:** Any PR edit, merge-conflict resolution, nested-branch integration,
> CodeRabbit fix that touches shared files, or rebasing a feature branch onto a moving base.
> This is the canonical merge doctrine for the oramasys workspace.

## Core principle

**Synthesize; never amputate.**

When two branches disagree, the goal is a **third state** that preserves every
valid intent from both sides — blended, rearranged, and combined — not a winner
and a loser. Deletion is the last resort; archival is the substitute.

| Do | Don't |
| --- | --- |
| Add, append, graft, union, supersede with notes | Delete prior evidence, lessons, or working code |
| Take the superset after verifying inclusion | Pick one side because it is "newer" without reading both |
| Rename/replace only when the old symbol is **removed from code** and tests prove the new API | Silently drop tests, docs, or guards from the other branch |
| Archive to `docs/archive/` or quarantine stubs | `git checkout --ours` / `--theirs` on whole files without inspection |

This is **CIDF rank-1 behavior**: merge and harmonize; never wholesale-replace.

---

## The six resolution modes

Apply in this order of preference (first match wins):

| Mode | Pattern | Action |
| --- | --- | --- |
| **1 additive** | One side empty, other has content | Take the content side unchanged |
| **2 union** | Both sides partial and complementary | Concatenate — base first, incoming appended; dedup JSONL by `id` |
| **3 superset** | One side structurally contains the other | Verify every row/field from the smaller exists in the larger; take superset |
| **4 synthesize** | Both sides changed the same region for different valid reasons | **Blend:** keep both behaviors (e.g. security-hardening API + locality heal tests) |
| **5 architecturally-correct** | One side fixes a bug the other reintroduces | Take the correct behavior; document why in commit body |
| **6 api-correct** | Casing, types, or canonical module path mismatch | Take the API-correct form (`_validate_*` over deleted `_FOO_RE`, lowercase model IDs) |

**archive** (not a merge mode — an escape hatch): content must leave the active
path → move to `docs/archive/` or `bin/orama-system/skills/archive/` with a
redirect stub. Never hard-delete history.

### Worked example — PR #158 (Perpetua-Tools)

Conflict: `tests/test_alphaclaw_bootstrap.py` — security branch renamed
`_ALLOWED_ENDPOINT_HOST_RE` → `_validate_endpoint_host()`; locality branch kept
the old test name.

**Wrong:** take either side wholesale (loses validation API or loses RFC-1918 coverage).

**Right (synthesize):** keep `test_validate_endpoint_host_accepts_rfc1918` name and
`_validate_endpoint_host()` calls from security-hardening; retain all PR #157
locality/canonical-loopback tests from the incoming branch.

---

## PR modification workflow

Run this **before** editing conflicted files:

```text
1. Simulate   git merge --no-commit --no-ff <incoming>
              git diff --name-only --diff-filter=U
              git merge --abort

2. Classify   For each conflicted file, label the mode (additive/union/superset/synthesize/…)

3. Harmonize  One pass — no <<<<<< markers left; no silent deletions

4. Verify     pytest -q (targeted + affected suites)
              repo_hygiene / pre-commit on touched paths

5. Commit     Message states what was blended from each side

6. Push → CI → merge → resolve review threads
```

Nested PR stacks (e.g. `coderabbitai/*` → `cursor/security-*` → `main`):
merge **leaf → parent → main**; wait for `mergeable_state: clean` between merges.

---

## File-type special cases

| File kind | Rule |
| --- | --- |
| `lessons.jsonl` / `AGENT_LEARNINGS.jsonl` | Union, dedup by `id`/`run_id` (keep first) |
| `LESSONS.md` | Never hand-merge — render via `graduate.py` |
| `SKILL.md` / `AGENTS.md` | Additive sections + cross-links; wrappers point to canonical |
| Tests | Prefer **unified** test file exercising both behaviors |
| Version surfaces | Edit `_version.py` / SSOT only; run `sync_version.py` |

---

## AFRP gate for merge tasks

```text
AFRP: Type C | Level Practitioner | Mode 2
Scope: Integratively merge <branch> into <base> without losing either side's intent
```

---

## See also

- [`multi-agent-collaboration-protocol.md`](../../references/multi-agent-collaboration-protocol.md) — full 7-step nested-branch protocol
- [`docs/wiki/06-multi-agent-collab.md`](../../../../docs/wiki/06-multi-agent-collab.md) — version registry + coordination
- Perpetua-Tools [`.agent/AGENTS.md` § Multi-agent merge](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/.agent/AGENTS.md) — portable brain entry
