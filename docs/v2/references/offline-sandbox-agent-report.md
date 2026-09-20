# Offline / sandbox agent report — canonical format

**Status:** canonical operational format (not a numbered v2 landmark)
**Audience:** agents with **no LAN** and **not on the operator's machine**
(Cursor Cloud, GitHub-hosted sandboxes, remote VMs, isolated worktrees)
**Skill name (shared):** `offline-sandbox-agent-report`

This is the close-out format those agents use when GossipBus, sibling
checkouts, and LAN peer inboxes are unavailable. GitHub (the directed PR
and branch) is the coordination surface. Do not invent a parallel board.

Dual-authority sibling (same skill name, PT coordination tree):
[`docs/coordination/offline-sandbox-agent-report.md`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/coordination/offline-sandbox-agent-report.md)
in Perpetua-Tools.

---

## Placement

| Repo | Path | Role |
| --- | --- | --- |
| **orama-system** | `docs/v2/references/offline-sandbox-agent-report.md` | Canonical format in this tree (this file) |
| **Perpetua-Tools** | `docs/coordination/offline-sandbox-agent-report.md` | Sibling dual-authority pointer — keep this path; do not collapse it into orama-only |
| **both** | `.agents/skills/offline-sandbox-agent-report/SKILL.md` | Shared skill name `offline-sandbox-agent-report`; skill card points here first |

This document does **not** take a numbered `docs/v2/NN-` slot. Supporting
reference only — same class as
[`new-agent-onboarding-dispatch-and-gossipbus.md`](new-agent-onboarding-dispatch-and-gossipbus.md).

---

## When this format applies

Use this format when **any** of the following is true:

- No LAN peer mesh, GossipBus SQLite, or `scripts/agent_coordination.py` board
- Not the operator workstation (cloud agent, Actions runner, remote sandbox)
- Sibling `Perpetua-Tools` / `AlphaClaw` checkouts are missing or read-only
- The operator directed reuse of an existing PR/branch and GitHub is the
  only shared log

LAN-capable agents on the operator machine still follow GossipBus + the
handoff packet in Perpetua-Tools `docs/coordination/`. This format does not
replace that path.

---

## Hard constraints (isolated agents)

- Docs/skill landings stay docs/skill unless the operator named product code.
- Soft-push only (`git push` fast-forward). **Do not force-push. Do not merge.**
- Reuse the named PR/branch when directed. Do not open a substitute PR.
- If the platform already opened a second PR, leave it unmerged and still
  land the same commits on the directed branch.
- Do not rewrite PR bodies. Comments only unless an operator grant exists
  ([PR reporting rearchitecture](2026-09-13-pr-reporting-rearchitecture.md)).
- Never commit workstation paths, LAN IPs, secrets, or prompt/tool payloads.
- If a GitHub Contents write returns **403**, stop. Report the exact error
  body/status. Do not retry with a different write API, a new branch, or a
  new PR.

---

## Required report (copy this block)

Fill every field. Empty string is allowed only for `Second PR` when none
exists. Do not omit keys.

```text
## Offline/sandbox agent report

- Repo:
- Directed PR:
- Branch:
- Tip SHA:
- Diffstat:
- Files landed:
- Merge: no
- Force-push: no
- New PR opened by this session: no | yes (URL, left unmerged)
- Second PR (if platform opened one): none | URL (left unmerged)
- Contents API 403: none | exact error
- GossipBus/LAN used: no
- Follow-ups / blockers:
```

### Field rules

| Field | Proof |
| --- | --- |
| **Tip SHA** | `git rev-parse HEAD` on the directed branch after the soft-push |
| **Diffstat** | `git show --stat --oneline HEAD` (or the range actually pushed) |
| **Directed PR** | Full `https://github.com/<org>/<repo>/pull/<n>` URL |
| **Branch** | Exact branch the operator named |
| **Files landed** | Repo-relative paths only |
| **Contents API 403** | Paste status + message verbatim; then halt |
| **Follow-ups** | Missing sibling dual-authority file, CI red, unmounted uploads, etc. |

Worked close-out commands:

```bash
git rev-parse HEAD
git show --stat --oneline HEAD
git status -sb
```

---

## Load order

1. This file (`docs/v2/references/offline-sandbox-agent-report.md`)
2. `.agents/skills/offline-sandbox-agent-report/SKILL.md` (activation card)
3. Operator turn instructions (PR number, branch, merge/force-push bans)
4. [New-agent onboarding](new-agent-onboarding-dispatch-and-gossipbus.md)
   for regime boundary only — skip GossipBus steps that need the local board

---

## Dual-authority

orama-system owns the v2-references copy. Perpetua-Tools owns the
coordination-tree copy at `docs/coordination/offline-sandbox-agent-report.md`.
The skill name is shared: `offline-sandbox-agent-report`. Neither copy
supersedes the other; keep both pointers. Do not treat a missing PT file as
permission to drop the PT row from the Placement table.
