# /learn-eval + ECC Instinct Ritual — Reference Card

> Load after closing a review-remediation session or incident that produced durable lessons.
> Harmonize like periscope ECC — **supplement** bundles, never overwrite wholesale.

---

## When to run

- Post-review micro-remediation complete (Phase 4 verification passed)
- Incident produced 2–4 actionable instincts (not bulk auto-dump)
- Cross-repo stack (orama + PT) needs synchronized homunculus triggers

---

## Pipeline (6 steps)

| Step | Action | Artifact |
| --- | --- | --- |
| 1 | Close incident → append lesson | `.agent/memory/semantic/lessons.jsonl` + episodic row |
| 2 | Write working doc with PR refs + evidence | `.agent/memory/working/<TOPIC>.md` |
| 3 | Curate 2–4 instincts | `.claude/homunculus/instincts/inherited/<stack>-<date>.yaml` |
| 4 | Import locally | `/instinct-import <yaml> --dry-run` then `--force` |
| 5 | Verify | `/instinct-status` |
| 6 | Post-merge sync | `/ecc-sync` in each repo |

**Checklist script (orama canonical):**

```bash
bash scripts/derive-pr-stack-instincts.sh --check
bash scripts/derive-pr-stack-instincts.sh --list
```

---

## Harmonization rules (periscope pattern)

| Rule | Detail |
| --- | --- |
| **Supplement, don't replace** | Add session YAML under `instincts/inherited/`; append triggers to `*-instincts.yaml` bundle |
| **Exclude timestamp churn** | Do not commit `ecc-tools.json` / `identity.json` unless intentional |
| **Cross-repo parity** | orama canonical instincts first; PT mirrors downstream stack lessons |
| **Quality gate** | Prefer 2–4 high-confidence instincts over duplicated auto-dumps |

### Bundle files (do not overwrite)

- orama: `.claude/homunculus/instincts/inherited/orama-system-instincts.yaml`
- PT: `.claude/homunculus/instincts/inherited/Perpetua-Tools-instincts.yaml`
- periscope: `.claude/homunculus/instincts/inherited/periscope-instincts.yaml`

Session files (safe to add): `guard-sync-pr251-2026-08-01.yaml`,
`guard-sync-pr314-2026-08-01.yaml`, etc.

---

## /learn-eval integration

After `/learn-eval` verdict **Save** or **Absorb**:

1. If lesson is PR-stack scoped → also run instinct derivation (step 3 above).
2. Link `related_lessons` in instinct YAML to lesson IDs.
3. Wire mechanical hooks when instinct references a script (e.g. `remind-pr-body-append-only.sh`).
4. PR body follow-up: operator mints `operator-grant-v2`, then `append-pr-body.sh` — **never** delta `update_pr`.

---

## Post-merge /ecc-sync

```bash
git pull origin main
/instinct-import .claude/homunculus/instincts/inherited/<bundle-or-session>.yaml
/instinct-status
git add -A && git commit -m "chore(ecc): post-merge instinct import sync $(date +%Y-%m-%d)"
git push origin main
```

See `bin/orama-system/skills/ecc-sync/SKILL.md`.

---

## Related

- `bin/orama-system/references/post-review-micro-remediation.md` — 6-phase remediation
- `bin/orama-system/references/pr-body-anti-clobber-incident-ledger.md` — PR body enforcement
- `bin/orama-system/skills/periscope-ecc/SKILL.md` — periscope harmonization model
- `.cursor/commands/learn-eval.md` — quality gate before saving patterns
