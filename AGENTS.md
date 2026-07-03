# Agent instructions — orama-system

## Claude Code runtime — read before touching the binary

Two install paths exist on this machine (`~/.local/bin/claude` + npm global) — intentionally.
Before updating, relocating, or assuming only one exists, read:
→ [`../CLAUDE-CODE-RUNTIME.md`](../CLAUDE-CODE-RUNTIME.md)

## History-rewrite & branch re-anchor — MANDATORY before judging any branch

**Applies to every AI agent in this repo — Claude, Codex, Cursor, CodeRabbit, Greptile, and any future agent.** This repo's `main` has been **rewritten** (squash-rebundle / expunge / force-push). After a rewrite every pre-rewrite commit keeps its content but gets a **new SHA**.

- **NEVER** judge whether a branch is orphaned, behind, or divergent using `git rev-list --count`, ahead/behind, or `git merge-base`. Across a rewrite boundary these are SHA-graph proxies and are **provably meaningless** — a branch can read "N behind" while its tip is byte-identical to a commit already in `main`. If you ever see "N behind + identical content," **HALT** — that contradiction means a rewrite, not a healthy branch.
- **ALWAYS** use the **tree-twin** test (`%T` match) via the canonical tool:
  ```bash
  scripts/git/reanchor_scan.sh <repo_path> origin/main [remotes|heads|all]
  git cherry -v origin/main <branch_tip> <branch_base>   # + = missing from main, - = already in main
  ```
- Method + worked examples: [`bin/orama-system/skills/git-history-surgery/SKILL.md`](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/git-history-surgery/SKILL.md) § B5. Why this keeps recurring and how we make it stick: [`docs/LESSONS.md` § 2026-06-05](https://github.com/diazMelgarejo/orama-system/blob/main/docs/LESSONS.md#2026-06-05) · failure catalog [`bin/orama-system/afrp/failure-modes.md` § Failure Mode 7](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/afrp/failure-modes.md).
- **Rebasing/force-updating/reviving a remote branch requires explicit current-user authorization** (see § Security PR stacking). Always preserve old tips (vault `refs/pull/*/head` + `backup/*` tags) before any force-push.
- Companion repo with the same protocol: [Perpetua-Tools `AGENTS.md`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/AGENTS.md). **periscope is excluded** — its `main`/`agentsview` are pure upstream mirrors, never rewritten by us.

## Attribution guards: single source of truth — ZERO fragmentation

**Applies to every agent.** The attribution/identity guard scripts are **canonical in orama `scripts/git/`** and **byte-identical in every repo**: `audit_attribution.sh`, `banned_attribution_lib.sh`, `check_commit_message.sh`, `check_identity.sh`, `daily-attribution-guard.sh` (+ `neutralize-cursor-coauthor-hook.sh`, `expunge-all-workspace-repos.sh`, `verify-git-guards.sh`).

- **NEVER hand-edit a guard script in a downstream repo.** Forks drift silently — a stale copy once made PT's strict `pre-push` reject the mainstream-AI co-authors (`coderabbitai`, `dependabot`, `anthropic.com`) that orama's allowlist already permits, blocking valid pushes.
- To change policy: edit orama's canonical copy, then redistribute — `bash scripts/git/sync-attribution-guard-scripts.sh <target-repo>`. The sync copies all guards; `check_commit_message.sh` + `check_identity.sh` are now in that list (they were the silent gap).
- `daily-attribution-guard.sh` is **self-contained** (derives its own `REPO_ROOT`, scans the whole workspace) — never a thin wrapper to another repo (a wrapper hardcodes a path and execs itself ⇒ infinite recursion).
- **Mainstream AI models / autonomous agents are allowed** as author and `Co-authored-by` (Codex, Cursor, CodeRabbit, Claude, Mistral, DeepSeek, …). The only hard ban is the VERBOTEN pattern in the gitignored private lib.
- Org-wide governance so future `oramasys/*` repos inherit identical hooks with zero drift: [`docs/v2/`](https://github.com/diazMelgarejo/orama-system/tree/main/docs/v2).

## Cursor Cloud: git commits

Cloud agents set `CURSOR_AGENT=1` and redirect `core.hookspath` to `~/.cursor/agent-hooks/…`, which can append unwanted `Co-authored-by` trailers. **`CURSOR_AGENT=0` is not supported** and does not disable this.

### On every cloud session (all OpenClaw repos)

```bash
bash scripts/git/apply-attribution-guard-all-repos.sh
bash scripts/git/check_identity.sh
```

### When `git commit` still adds trailers

```bash
bash scripts/git/commit-clean.sh -m "type(scope): short summary"
```

### Repos covered

- `orama-system` (this repo)
- `Perpetua-Tools` (`$PERPETUA_TOOLS_PATH` or `$OPENCLAW_HOME/Perpetua-Tools`)
- `AlphaClaw` (`$ALPHACLAW_INSTALL_DIR` or `$OPENCLAW_HOME/AlphaClaw`)

**AlphaClaw fork:** `main` = upstream mirror. `pr-4-macos` = upstream [PR #63](https://github.com/chrysb/alphaclaw/pull/63) — cherry-pick down from `feature/MacOS-post-install`; **never** FF integration onto it. Integration: `feature/MacOS-post-install`. Contrib: `cursor/sync-attribution-guards-6421` → PR into integration. `alphaclaw-align-all.sh` does not touch `pr-4-macos`. See `docs/wiki/13-alphaclaw-fork-contrib-branches.md` and AlphaClaw `docs/wiki/01-branch-roles.md`.

See `docs/wiki/12-cursor-cloud-commit-attribution.md`.

## Endpoint transport policy — Perpetua peer contract

**Applies when touching OpenClaw-generated model endpoints, gateway/proxy endpoint wiring, active_tilting references, SSRF policy, LAN discovery guidance, or cross-repo routing docs.**

- **Canonical implementation:** Perpetua-Tools owns `src/utils/endpoint_policy_core.py` and `.agent/endpoint-policy-contract.yml` on `main`.
- **Peer contract:** orama-system owns `.agent/endpoint-policy-contract.yml`, `scripts/security/check_endpoint_policy_contract.py`, and `.github/workflows/endpoint-policy-contract.yml` on `main`.
- **Transport identity:** endpoint identity is `scheme + hostname + backend-specific port`; preserve discovered `http`/`https` scheme first, normalize host second, then route by backend-specific port.
- **Do not fork implementation:** if orama needs Python endpoint reconstruction logic, sync the contract with Perpetua first instead of inventing a second parser.
- **Existing skills to load:** use `bin/orama-system/skills/oramasys-method/SKILL.md` for architecture-heavy changes, `bin/orama-system/skills/oramasys-method/references/integrative-merge.md` for cross-branch/repo synthesis, and `bin/orama-system/skills/git-history-surgery/SKILL.md` before judging rewritten branch state.
- **Security policy:** read `docs/SECURITY-POLICY.md` (redirects to `SECURITY.md`) before endpoint-security remediation PRs.
- **Validation:** run `python scripts/security/check_endpoint_policy_contract.py` before merging endpoint-policy or routing-guidance changes.

## Prime directives for agent-maintained records

- Treat vulnerability memory, lessons, audits, and review ledgers as append-only
  historical records. Do not erase, delete, replace, truncate, or rewrite prior
  entries unless the user explicitly instructs that exact destructive action.
- When a record is stale, defunct, remediated, duplicated, or superseded, update
  it additively: add or change status/notes/feedback fields, append a follow-up
  entry, or link to the replacement. Preserve the original evidence and dates.
- For JSON records, load and write with structured parsers (`json.load` /
  `json.dump(..., indent=4)` in Python). Never hand-edit by string
  concatenation, ad hoc patches, or regex substitutions.
- Before any destructive or ambiguity-prone record operation, use
  AskUserQuestions: ask the user which record to change, what status to apply,
  and whether deletion/replacement is truly intended.
- Git attribution must stay policy-compliant: primary author may be one of the
  approved owner emails or an approved well-known AI author such as
  `Codex <codex@openai.com>`; `Co-authored-by` may include well-known public
  AI/helper domains and markers, but random/unattributable Gmail co-authors are
  blocked.

## PR merge & conflict resolution — oramasys-method (MANDATORY)

**Applies to every agent when modifying, merging, or resolving conflicts on a PR.**

Load the **oramasys-method** skill and follow
[`bin/orama-system/skills/oramasys-method/references/integrative-merge.md`](bin/orama-system/skills/oramasys-method/references/integrative-merge.md):

- **Synthesize, never amputate** — additive, blending, union, superset; archive instead of delete.
- **Six modes:** additive → union → superset → synthesize → architecturally-correct → api-correct.
- **Simulate merges first**; one harmonization pass; pytest before push.
- Wrappers: `.claude/skills/oramasys-method/SKILL.md`, `.agents/skills/oramasys-method/SKILL.md`.
- Full 7-step protocol: [`bin/orama-system/references/multi-agent-collaboration-protocol.md`](bin/orama-system/references/multi-agent-collaboration-protocol.md).

## Security PR stacking directive

- Before opening or preparing any security-remediation PR, read
  `docs/SECURITY-POLICY.md` and follow its "Security PR stacking and merge
  strategy" section.
- Merge or revive existing security-priority branches before creating duplicate
  replacement branches.
- Stack security PRs in policy-priority order: `PR1` starts from `main`; each
  `PR(N+1)` is rebased on the previous PR branch before opening.
- Rebasing or force-updating an existing remote branch requires explicit current
  user authorization.
