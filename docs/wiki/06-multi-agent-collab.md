# 06. Multi-Agent Collaboration — Version Registry, Scope Claims, Orphan Branches

**TL;DR:** Two agents working simultaneously on overlapping files will diverge. Use scope claims, additive-only changes, commit messages as communication, and the version registry to stay coordinated.

---

## What Broke (2026-04-12)

During a 48-hour window two agents worked simultaneously on overlapping files:

1. **Orphan branch / no common ancestor** — feature branch in UTS had no shared history with `origin/main`; `git rebase origin/main` produced add/add conflicts on every file
2. **Hardcoded LAN IP broke CI** — `/health` defaults changed to `192.168.254.103` (real LAN IP) in source code; broke `test_health_uses_plain_string_defaults` on all CI machines

---

## Version Registry

**Single source of truth: `src/orama_system/_version.py`.**
Import as `from orama_system._version import __version__`.

**To bump:** edit `__version__` in `_version.py` only, then run:
```bash
python3 scripts/sync_version.py              # propagates to all surfaces below
python3 -m pytest tests/test_version_docs.py # verify
git add -A && git commit -m "chore(version): bump to X.Y.Z.W"
```

Canonical surfaces managed by `scripts/sync_version.py` (never edit manually):

| File | Field | Status |
|------|-------|--------|
| `src/orama_system/_version.py` | `__version__` | **SOURCE — edit only here** |
| `pyproject.toml` | `dynamic = ["version"]` via hatch | auto |
| `bin/orama-system/SKILL.md` | `version:` frontmatter | auto |
| `CLAUDE.md` | package ref | auto |
| `README.md` | version badge | auto |
| `bin/config/agent_registry.json` | `"version"` | auto |
| `bin/orama-system/config/agent_registry.json` | `"version"` | auto |
| `bin/orama-system/config/routing_rules.json` | `"version"` | auto |
| `src/orama_system/portal_server.py` | `VERSION =` | auto |
| `bin/agents/*/agent.md` | `version:` frontmatter | auto |
| `bin/mcp_servers/*.py` | `Version: X` docstring header | auto |
| `bin/shared/*.py` | `Version: X` docstring header | auto |
| `platform/windows/install.ps1` | `version = 'X'` | auto |
| `docs/PERPLEXITY_BRIDGE.md` | `## Version X` | auto |
| `docs/SYNC_ANALYSIS.md` | version refs | auto |
| `bin/orama-system/afrp/README.md` | `**Version:**` | auto |
| `bin/orama-system/skills/self-discovery/SKILL.md` | `version:` | auto |

**Not managed — intentional:**
- `CHANGELOG.md`, `docs/LESSONS.md` — accurate historical records
- `docs/plans/`, `docs/superpowers/specs/` — historical planning docs
- `scripts/setup_macos.py` `KNOWN_ALPHACLAW_VERSION` — AlphaClaw runtime (separate version train)
- `openrouter-defaults.md` `Version:` — skill-doc revision, not package version

---

## Multi-Agent Synchronization Protocol

1. **Read `docs/LESSONS.md` first** — mandatory on every session start
2. **Scope claim** — append `[IN PROGRESS: agent-name — file.py]` comment to LESSONS.md before touching files; remove when done
3. **Additive changes** — prefer appending over rewriting; no conflict risk when changes don't overlap
4. **Commit message as communication** — state which constants/APIs changed; this is the only async channel between agents sharing no session context
5. **Never hardcode ephemeral runtime values** — `127.0.0.1` as default in source code, real IP in `.env` only
6. **One canonical source per constant** — if two files both define the same IP string, they will diverge

## Nested-Branch Merge Protocol

When agents produce concurrent branches, follow this sequence. Guessing = data loss.

### Merge order
- Establish topological order (leaf → parent → main)
- Merge leaf first; wait 10 min + `mergeable_state: clean` before next merge

### 7-step protocol

| Step | Action |
|------|--------|
| **1 Simulate** | `git merge --no-commit --no-ff <branch>` → enumerate `--diff-filter=U` → `git merge --abort`. Do for ALL merges before touching any file. |
| **2 Present** | Show both sides of every conflict. One question per file. Wait for explicit direction. |
| **3 Strategy** | `additive` (empty+content→take content) · `union` (both partial→concat) · `superset` (verify inclusion→take larger) · `architecturally-correct` (bug→take fix) · `api-correct` (casing→take lowercase) |
| **4 Resolve** | One pass, directed strategy. Never delete — archive if needed. |
| **5 Verify** | `pytest -q` + `repo_hygiene.py` + confirm no `<<<<<<` remain |
| **6 Merge** | Push → CI → GitHub API squash merge. Undraft via GraphQL if needed. |
| **7 Buffer** | 10 minutes. Poll `mergeable_state: clean` before next merge. |

### Key invariants

```
"merged: true" on GitHub ≠ content on branch
  → always: git diff origin/main...origin/<branch> after any merge

CodeRabbit re-scans on every push → run post-merge sweep after EVERY merge

Draft PR blocks API merge → markPullRequestReadyForReview mutation first
```

Full reference with code snippets: [`bin/orama-system/references/multi-agent-collaboration-protocol.md` § Nested-Branch Merge Protocol](../../bin/orama-system/references/multi-agent-collaboration-protocol.md)
PT portable brain: [`PT/.agent/AGENTS.md` § Multi-agent merge conflict protocol](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/.agent/AGENTS.md)

## Clean-Lineage Git Hygiene

For recovery branches and other high-risk Git work:

1. Use dated branch names: `yyyy-mm-dd-001-brief-summary`
2. Verify identity before commit: `bash scripts/git/check_identity.sh`
3. Stash untracked files before branch surgery: `git stash push --include-untracked`
4. Do not replay polluted commits directly; manual-port reviewed intent into clean commits
5. Keep `.env`, `.env.local`, and `.paths` untracked; update example files instead
6. Run `python scripts/review/repo_hygiene.py .` before opening a PR

---

## Orphan Branch Recovery

```bash
# Symptoms: git merge-base HEAD origin/main returns exit 1
# git rebase origin/main produces add/add conflicts on EVERY file

# Fix:
git fetch origin main
git reset --hard origin/main
# Then manually re-apply your 5-ish changed files from /tmp backup or git stash
```

**Prevention**: Always create feature branches from `origin/main`:
```bash
git checkout -b feature/xyz origin/main
```

---

## Rules

1. **Always branch from `origin/main`** — never from a detached HEAD or an agent-created branch
2. **Source code defaults must be loopback** — real IPs live in `.env` only
3. **One canonical source per constant** — if two files define the same value, they will diverge
4. **Test isolation requires `autouse` fixtures** that restore module-level state after `importlib.reload()`
5. **Commit body must name changed constants/APIs** — it's the only async communication channel between concurrent agents
6. **Detailed salvage commit bodies are mandatory** — include `Why`, `What changed`, `Risk`, and `Verification`

---

## Pre-Commit Checklist (multi-agent sessions)

```bash
git fetch origin main
git log --oneline HEAD..origin/main          # changes by other agents
grep -rn "192\.168\." --include="*.py" | grep -v "test_\|\.env\|LESSONS"
python -m pytest -q
```

---

## Related

- [Session log 2026-04-12](../LESSONS.md#2026-04-12--claude--48-hour-multi-agent-sprint-collaboration-patterns--version-registry)
- Commit: `71a15f7` (PT) — fix(health): restore 127.0.0.1 loopback defaults
