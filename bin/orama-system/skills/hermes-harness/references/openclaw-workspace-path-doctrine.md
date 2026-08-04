# OpenClaw workspace path doctrine (orama canonical)

> **Do not use `$OPENCLAW_ROOT` in committed docs or skill prose.** It is not a
> stable, machine-verifiable path on this fleet. Agents that resolve
> `$OPENCLAW_ROOT` to a single fixed tree break on Windows nodes, cloud VMs,
> worktrees, and nested checkouts.

## Allowed runtime anchors

| Anchor | When to use | Example |
| ------ | ----------- | ------- |
| `$HOME` / `~` | User-level runtime (partner CLI, Hermes home) | `$HERMES_HOME`, `~/.local/bin` |
| `$REPO_ROOT` / git toplevel | Inside a git checkout | `git rev-parse --show-toplevel` |
| **ORAMA mother** | Git-relative crawl from orama root | `$(dirname "$(git -C "$ORAMA_ROOT" rev-parse --show-toplevel)")` |
| Explicit env | Operator override (preferred) | `$PERPETUA_TOOLS_ROOT`, `$ORAMA_SYSTEM_PATH` |

**Workspace mother** (ORAMA mother) = parent of the orama-system **git root** (from
`git rev-parse`, not the script directory). orama and Perpetua-Tools do **not**
always share the same immediate parent; PT is discovered by **reverse git crawl**
under the mother (`.git` + `orchestrator/fastapi_app.py` marker), not by
hardcoding a layout path in repo prose.

## Discovery rule (both repos)

**Never hardcode private workstation paths in committed files.** Use the same
algorithm in orama and Perpetua-Tools harness docs:

1. Resolve local git root: `git rev-parse --show-toplevel`
2. Crawl upward one level (mother) and shallow subdirs for sibling git repos
3. Validate candidate: `.git` present + `orchestrator/fastapi_app.py` (PT) or
   `start.sh` / `platform/windows/start.ps1` (orama)
4. Fallback crawl from `$HOME` (shallow, git-marker only) — **not** `$OPENCLAW_HOME`

**Do not use `$OPENCLAW_HOME`** for cross-repo discovery in committed prose or
default resolvers. Operator may export it at runtime; docs and skills must not
assume it.

## Forbidden / deprecated

| Pattern | Why |
| ------- | --- |
| `$OPENCLAW_ROOT/...` in committed prose | Assumes one layout; fails CI path hygiene |
| `$OPENCLAW_HOME/...` as primary discovery | Not set on scheduled tasks / many nodes |
| Hardcoded `../Perpetua-Tools` or `perplexity-api/...` in skills | Layout-specific; use git crawl |
| Literal workstation paths (`/Users/...`, `code/OpenClaw/...`) | CI hygiene + portability |

## PT root resolution (canonical order)

See [`workspace-path-resolution.md`](workspace-path-resolution.md). Harness
scripts implement the same order in `resolve_perp_harness.sh`:

1. `$PERPETUA_TOOLS_ROOT` / `$PERPETUA_TOOLS_PATH` / `$PT_HOME`
2. orama `.paths` → `PT_DIR` (written by `start.sh` / `start.ps1 --discover`)
3. Git crawl from ORAMA mother (depth-limited, marker-validated)
4. Git crawl from `$HOME` (depth-limited, marker-validated)

Summary: **mother-of-orama + `$HOME`, not `$OPENCLAW_HOME`**.

## Cross-repo references

- **In-repo:** relative paths from the citing file
- **Cross-repo:** `https://github.com/diazMelgarejo/<repo>/blob/main/...`
- **Runtime:** env placeholders only — never workstation absolute paths

## Fleet notes (Windows)

- Scheduled tasks (`coord_pulse`) do **not** load `.env.local`
- Set `ORAMA_SYSTEM_PATH` and `PERPETUA_TOOLS_PATH` at **User** scope for Task Scheduler
