# Agent Execution Frugality — Reference Card

> Strategic execution guardrails derived from review-remediation sessions.
> Load at session start for multi-repo, multi-PR, or post-review work.

---

## Tool use

| Do | Don't |
| --- | --- |
| Batch parallel reads/searches for independent context | Serial tool calls when inputs don't depend on each other |
| Grep with `head_limit` + narrow `glob`/`path` | Full-repo scans without scope |
| Read file sections (`offset`/`limit`) for large files | Re-read entire files after small edits |
| One push per repo per remediation batch | Push after every micro-commit |
| `verify-guard-parity.sh` once after sync | Hand-diff every synced file |

---

## Git discipline

| Do | Don't |
| --- | --- |
| Edit orama `scripts/git/` canonical first | Hand-edit PT guard copies |
| Abort sync on dirty worktree (harmonize first) | Blind `sync-attribution-guard-scripts.sh` over local edits |
| `publish-clean-branch.sh` for audited publish | Raw `git push --force` |
| Tree-twin (`reanchor_scan.sh`) after rewrites | `merge-base` / ahead-behind across rewrite boundaries |
| Safety ref before reset | Discard unique work |

---

## PR & review workflow

| Do | Don't |
| --- | --- |
| Root-cause cluster (Phase 1) before patching | One commit per review comment |
| `append-pr-body.sh` for PR updates | Delta-only `ManagePullRequest update_pr` |
| Integrative merge (synthesize, never amputate) | Delete prior follow-ups or Summary |
| Run actual failing CI command locally | Assume CI failure ≠ review finding |
| Close remediation on verification evidence | Report done without regression proof |

---

## Memory & documentation

| Do | Don't |
| --- | --- |
| Append-only for lessons/audits/incident ledgers | Rewrite historical records in place |
| Link to canonical reference docs | Duplicate doctrine into every skill |
| 2–4 curated ECC instincts per stack | Bulk auto-generate instinct dumps |
| Working docs for active plans; references for stable doctrine | Mix transient session notes into skills |

---

## Elegance heuristics

1. **Smallest correct diff** — one abstraction fix beats N file patches.
2. **Mechanical > mnemonic** — hooks, CI, and scripts beat repeated lessons.
3. **Canonical once** — manifest lists, reference cards, single source of truth.
4. **Dogfood the formula** — merge enforcement, then test post-merge hooks on real PRs.
5. **Stop when green** — don't rebase an already-reviewable branch for ritual cleanliness.

---

## Related

- `post-review-micro-remediation.md` — 6-phase pattern
- `pr-body-anti-clobber-incident-ledger.md` — PR body enforcement
- `learn-eval-ecc-ritual-reference-card.md` — lesson → instinct pipeline
- `integrative-merge.md` — conflict resolution modes
