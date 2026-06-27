# Multi-Agent Collaboration Protocol

> Encode these rules in every agent's SOUL.md and session start. They prevent the most common
> conflicts when multiple AI agents work on the same codebase simultaneously.
>
> Offloaded from `bin/orama-system/SKILL.md` for progressive disclosure — load before any
> multi-agent session. Content is canonical here; SKILL.md carries only the navigational stub.
>
> **PR merge doctrine (user-facing):** [`skills/oramasys-method/references/integrative-merge.md`](../skills/oramasys-method/references/integrative-merge.md) —
> additive harmonization, six resolution modes, synthesize-never-amputate. Load via **oramasys-method** when modifying PRs.

## Pre-Session Sync Check

```bash
git fetch origin main
git log --oneline origin/main..HEAD   # your uncommitted commits
git log --oneline HEAD..origin/main   # other agents' recent pushes
```

## Scope Claim (first write of every session)

Append to `.claude/lessons/LESSONS.md` before touching any file:

```text
## [IN PROGRESS] YYYY-MM-DD — Claude — <topic>
Files: <list of files you plan to modify>
```

Replace with a proper dated header on completion. This is the coordination signal for other agents.

## IP and Endpoint Default Rule

- **Source code defaults**: always `127.0.0.1` — never a real LAN IP as a string literal
- **Real IPs**: live in `.env` (gitignored), injected via `os.getenv(KEY, "http://127.0.0.1:PORT")`
- **CI tests**: assert against the loopback default — they run on every machine, not just yours

## Version Bump Registry (UTS)

When bumping version, update ALL of these atomically:

| File                             | Field                               |
| -------------------------------- | ----------------------------------- |
| `pyproject.toml`                 | `version`                           |
| `bin/orama-system/SKILL.md`            | frontmatter `version:`              |
| `bin/config/agent_registry.json` | `"version"`                         |
| `portal_server.py`               | `VERSION`                           |
| `bin/agents/*/agent.md`          | `version:` frontmatter (each agent) |
| `CLAUDE.md`                      | mother skill version reference      |
| `docs/PERPLEXITY_BRIDGE.md`      | version header                      |

**Legacy markers** (do not auto-bump — they pin a stable API baseline):

- `api_server.py` / `bin/shared/*.py` / `bin/mcp_servers/*.py` → `1.1.0.0`
- `bin/orama-system/config/`, templates, `afrp/README.md` → `1.1.0.0`

**Current version: `1.1.0.0`** — do not bump until explicitly instructed.

## Embedded Git Repo: `.ecc/`

`.ecc/` is a gitlink (submodule stub), NOT a regular directory. Git warns about
"embedded git repository" — this is expected. Contents do not clone automatically.
To initialize: `git submodule update --init .ecc`. Do NOT delete or gitignore it.

## Commit Message Contract

Every commit body must state:

- Which **constants / env vars / function signatures** changed
- Which **files other agents must re-read** before making assumptions
- Whether any **test baselines changed**

This is the primary async channel between agents with no shared session memory.

## Nested-Branch Merge Protocol

When two or more agents produce branches concurrently against a moving `main`, follow
this sequence exactly. Guessing conflict resolution corrupts the codebase silently.

### Merge order

Always establish a topological ordering before starting:
- Identify the parent-child relationship between branches (which was created first / is based on which)
- Merge leaf → parent first, then parent → main
- Wait 10 minutes and confirm `mergeable_state: clean` via GitHub API before the next merge

### Step 1 — Simulate; touch nothing

```bash
# For EACH merge in the planned sequence:
git merge --no-commit --no-ff <branch>
git diff --name-only --diff-filter=U    # enumerate ALL real conflicts
git merge --abort

# Do this for ALL merges BEFORE resolving any conflict.
# Knowing the full conflict surface prevents mid-resolution surprises.
```

### Step 2 — Present every conflict to the human

For every conflicting file, show **both sides** explicitly:

```python
import re
text = Path(conflicted_file).read_text()
for m in re.finditer(r'<<<<<<< HEAD\n(.*?)=======\n(.*?)>>>>>>> [^\n]+\n', text, re.DOTALL):
    print("OURS:  ", m.group(1)[:400])
    print("THEIRS:", m.group(2)[:400])
```

One question per file. Never proceed without explicit human direction.

### Step 3 — Resolution strategies (human-directed)

| Strategy | When | Action |
|---|---|---|
| `additive` | One side empty, other has content | Take the content side |
| `union` | Both sides partial/complementary | Concatenate — ours first, theirs appended |
| `superset` | One side structurally contains all rows of the other | Verify inclusion, take the superset |
| `synthesize` | Both sides changed the same region for different valid reasons | Blend both intents (e.g. hardened API + incoming tests) |
| `architecturally-correct` | One side has a bug the other fixes | Take the correct side regardless of branch origin |
| `api-correct` | Casing/type mismatch | Take the API-correct form (lowercase IDs, typed values) |
| `archive` | Content must be removed | Move to `docs/archive/` or `bin/orama-system/skills/archive/`; never delete |

### Step 4 — Resolve all conflicts in one pass

```python
import re
from pathlib import Path

def resolve_union(path):
    text = Path(path).read_text()
    resolved = re.sub(
        r'<<<<<<< HEAD\n(.*?)=======\n(.*?)>>>>>>> [^\n]+\n',
        lambda m: m.group(1) + m.group(2),   # union
        text, flags=re.DOTALL
    )
    assert '<<<<<<' not in resolved
    Path(path).write_text(resolved)
```

Special cases for memory files:
- `AGENT_LEARNINGS.jsonl` / `lessons.jsonl` → union then dedup by `run_id` / `id` (keep **first** occurrence per key)
- `LESSONS.md` → rendered from `lessons.jsonl`; never hand-merge — run `graduate.py`

### Step 5 — Verify before committing

```bash
python3 -m pytest -q
python3 scripts/review/repo_hygiene.py .
git diff --name-only --diff-filter=U    # must be empty
```

### Step 6 — Push, CI, merge, buffer

```bash
git push origin <experiment-branch>

# Poll CI until green:
curl -s -H "Authorization: Bearer $GH_TOKEN" \
  "https://api.github.com/repos/diazMelgarejo/orama-system/commits/<sha>/check-runs" \
  | python3 -c "import json,sys; d=json.loads(sys.stdin.read()); ..."

# GitHub API merge (squash preferred):
curl -X PUT \
  -H "Authorization: Bearer $GH_TOKEN" \
  "https://api.github.com/repos/diazMelgarejo/orama-system/pulls/<N>/merge" \
  -d '{"merge_method":"squash","commit_title":"..."}'

# Undraft if needed first:
curl -X POST .../graphql -d '{"query":"mutation{markPullRequestReadyForReview(...)}"}'
```

### Step 7 — Wait 10 minutes; repeat for next merge

After each GitHub merge, GitHub recomputes `mergeable_state`. Do not proceed to the
next merge until the API returns `mergeable_state: clean`.

```bash
sleep 600   # or poll every 60s
curl .../pulls/<N> | python3 -c "... print(p.get('mergeable_state'))"
```

### Key invariants

| Invariant | What to do |
|---|---|
| `"merged": true` on GitHub ≠ content on target branch | Always verify: `git diff origin/main...origin/<branch>` |
| CodeRabbit re-scans on every push | Run post-merge sweep after **every** merge, not once |
| PR branch base may be stale vs current main | Check `git merge-base` before simulating |
| Draft PRs cannot be merged via API | Run `markPullRequestReadyForReview` GraphQL mutation first |
| `scan_tracked_secrets` catches token in commit body | Never paste tokens in PR titles, commit messages, or docs |



| Symptom                                    | Cause                               | Fix                                                                   |
| ------------------------------------------ | ----------------------------------- | --------------------------------------------------------------------- |
| `stash pop` conflicts on your files        | Other agent pushed while you worked | `git checkout --theirs` or `--ours`; patch manually                   |
| `rebase` add/add on every file             | No common ancestor (orphan branch)  | `git reset --hard origin/main`; re-apply files manually               |
| File appears doubled/concatenated          | Both conflict sides appended        | Keep only `lines[N:]` (good half); strip duplicate header             |
| CI fails with real LAN IP assertion        | IP leaked into source default       | Change source to `127.0.0.1`; test validates the env-agnostic default |
| Module constant contaminated between tests | `importlib.reload()` side effect    | `autouse` fixture that reloads before AND after each test             |

---

## See also

- [`skills/oramasys-method/references/integrative-merge.md`](../skills/oramasys-method/references/integrative-merge.md) — **canonical PR merge / harmonization doctrine (orama-way)**
- [`skills/git-history-surgery/SKILL.md`](../skills/git-history-surgery/SKILL.md) — history rewrite, re-anchor after rewrite, version-bump commit discipline; contains the Multi-Agent Branch Merge quick reference
- [`skills/using-git-worktrees/SKILL.md`](../skills/using-git-worktrees/SKILL.md) — parallel agent worktree lifecycle; Step 3 embeds the merge-protocol trigger
- [`docs/wiki/06-multi-agent-collab.md`](../../../../docs/wiki/06-multi-agent-collab.md) — version registry, Nested-Branch Merge Protocol table, cross-links to PT AGENTS.md
- [`PT/.agent/AGENTS.md` § Multi-agent merge conflict protocol](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/.agent/AGENTS.md) — harness-agnostic portable brain entry point
