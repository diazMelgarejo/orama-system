---
name: periscope-ecc
description: >
  Optional LAZY SIDECAR for periscope ECC artifacts (repo-local skills + instincts).
  Activates ONLY when a periscope clone with ECC bundle paths is present; skip entirely
  if absent. Neither required by nor a dependency of any other skill — pure sidecar in
  v1; v2 treats periscope as an orbiting satellite that owns its ECC bundle while orama
  only probes and verifies mirror integrity.
metadata:
  type: reference
  optional: true
  sidecar: true
  satellite_v2: true
  verified: 2026-07-28
---

# Periscope ECC — lazy sidecar (optional, repo-local)

## Activation guard — skip if periscope ECC is absent

Run first; if it prints `SKIP`, do nothing else:

```bash
bash scripts/periscope/verify-ecc-skill-mirror.sh
```

Expected when absent:

```text
periscope ECC: not present — SKIP sidecar
```

## What this sidecar covers

Periscope owns its ECC bundle under the periscope repo:

| Path | Role |
| --- | --- |
| `.agents/skills/periscope/SKILL.md` | Codex-facing repo skill |
| `.claude/skills/periscope/SKILL.md` | Claude Code repo skill (must mirror Agents copy) |
| `.claude/homunculus/instincts/inherited/periscope-instincts.yaml` | Continuous-learning instincts |

orama-system does **not** vendor or install these files. It only documents the
contract and provides an idempotent mirror verifier.

## v1 vs v2 placement

| Version | Model | orama role |
| --- | --- | --- |
| **v1** | True sidecar | Probe + verify; never install; never fail if absent |
| **v2** | Orbiting satellite | Periscope repo remains ECC SSoT; orama may add transport hooks but does not duplicate bundle content |

## Mirror invariant (Agents ↔ Claude skills)

The two skill files must remain **byte-identical**:

- `.agents/skills/periscope/SKILL.md`
- `.claude/skills/periscope/SKILL.md`

Verify after any ECC harmonization or integrative merge:

```bash
export PERISCOPE_REPO=/path/to/periscope
bash scripts/periscope/verify-ecc-skill-mirror.sh
```

Exit `0` = in sync or absent (SKIP). Exit `1` = drift detected.

## Dependency-update instinct pair (intentional coexistence)

Keep **both** instincts; they serve different trigger granularities:

| ID | Trigger | Shape |
| --- | --- | --- |
| `periscope-workflow-dependency-update` | `when doing dependency update` | Numbered workflow steps |
| `periscope-instinct-dependency-update` | `When updating dependencies for a package or language ecosystem` | Concise action summary |

Each block cross-references its companion in `## Related`. Do not dedupe into one
instinct during harmonization merges.

## PR branch replay (when base already has overlapping ECC)

When the integration base (`merged`) already contains PR #10's bundle and an open PR
still carries pre-merge commits, do **not** merge or rebase wholesale. Use path-scoped
replay:

```bash
git fetch origin merged
git worktree add /tmp/periscope-pr-replay origin/merged
# apply harmonized paths only; git add; commit-clean; force-with-lease
```

Canonical procedure:
[`git-history-surgery/references/path-scoped-pr-replay-reference-card.md`](../git-history-surgery/references/path-scoped-pr-replay-reference-card.md).

Unique path set for the 2026-07-28 ECC fusion:

```text
.agents/skills/periscope/SKILL.md
.claude/skills/periscope/SKILL.md
.claude/homunculus/instincts/inherited/periscope-instincts.yaml
```

## Post-merge ECC sync (periscope repo only)

After an ECC PR merges into periscope `merged`:

```bash
cd "$PERISCOPE_REPO"
bash scripts/periscope/verify-ecc-skill-mirror.sh
/instinct-import .claude/homunculus/instincts/inherited/periscope-instincts.yaml
/instinct-status
```

If `/instinct-import` is unavailable, import manually or skip — do not block the
merge on orama-side tooling.

## Related

- `docs/v2/21-periscope-l4-glass.md` — L4 sidecar architecture
- `docs/reference/periscope-cursor-repo-rules.md` — cursor rules install
- `scripts/periscope/install-cursor-rules.sh` — attribution guards + rules (separate from ECC)
- `skills/ecc-sync/SKILL.md` — orama-system's own ECC post-merge sync (this repo, not periscope)
