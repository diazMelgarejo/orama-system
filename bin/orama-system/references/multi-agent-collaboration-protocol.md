# Multi-Agent Collaboration Protocol

> Encode these rules in every agent's SOUL.md and session start. They prevent the most common
> conflicts when multiple AI agents work on the same codebase simultaneously.
>
> Offloaded from `bin/orama-system/SKILL.md` for progressive disclosure — load before any
> multi-agent session. Content is canonical here; SKILL.md carries only the navigational stub.

## Pre-Session Sync Check

```bash
git fetch origin main
git log --oneline origin/main..HEAD   # your uncommitted commits
git log --oneline HEAD..origin/main   # other agents' recent pushes
```

## Scope Claim (first write of every session)

Append to `.claude/lessons/LESSONS.md` before touching any file:

```
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

- `api_server.py` / `bin/shared/*.py` / `bin/mcp_servers/*.py` → `0.9.9.2`
- `bin/orama-system/config/`, templates, `afrp/README.md` → `0.9.9.0`

**Current version: `0.9.9.7`** — do not bump until explicitly instructed.

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

## Conflict Recovery Playbook

| Symptom                                    | Cause                               | Fix                                                                   |
| ------------------------------------------ | ----------------------------------- | --------------------------------------------------------------------- |
| `stash pop` conflicts on your files        | Other agent pushed while you worked | `git checkout --theirs` or `--ours`; patch manually                   |
| `rebase` add/add on every file             | No common ancestor (orphan branch)  | `git reset --hard origin/main`; re-apply files manually               |
| File appears doubled/concatenated          | Both conflict sides appended        | Keep only `lines[N:]` (good half); strip duplicate header             |
| CI fails with real LAN IP assertion        | IP leaked into source default       | Change source to `127.0.0.1`; test validates the env-agnostic default |
| Module constant contaminated between tests | `importlib.reload()` side effect    | `autouse` fixture that reloads before AND after each test             |
