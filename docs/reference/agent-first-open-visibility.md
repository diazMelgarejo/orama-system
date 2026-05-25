# Agent first-open visibility map

> **Quadrant:** Reference (information-oriented). **Last updated:** 2026-05-25  
> **Purpose:** What each coding-agent host typically loads on first open of the orama stack — paths and entry docs, not procedure (see how-to for steps).

Canonical install and review procedure: [`../how-to/first-run-and-code-review.md`](../how-to/first-run-and-code-review.md). Open gap checklists: [`../../bin/orama-system/skills/code-review/references/pressure-test-notes.md`](../../bin/orama-system/skills/code-review/references/pressure-test-notes.md) § Fortify pass.

---

## Surface comparison

| Surface | Cursor | Claude Code | OpenClaw |
|---------|--------|-------------|----------|
| **Root workspace (typical)** | `orama-system/` repo root, or nested path e.g. `bin/orama-system/skills/code-review/` when task-scoped | `orama-system/` git root (`git rev-parse --show-toplevel`) | `OpenClaw/` parent folder (multi-repo layout; **not** one git root) |
| **Navigator (`CLAUDE.md` / `AGENTS.md`)** | Repo [`orama-system/CLAUDE.md`](../../CLAUDE.md); parent [`OpenClaw/CLAUDE.md`](../../../CLAUDE.md) when workspace includes parent; Cursor may inject workspace rules from `.cursor/rules/` | [`orama-system/CLAUDE.md`](../../CLAUDE.md) at repo root; hub [`OpenClaw/CLAUDE-instru.md`](../../../CLAUDE-instru.md) for cross-repo registry | [`OpenClaw/CLAUDE.md`](../../../CLAUDE.md) (top-level navigator); [`CLAUDE-instru.md`](../../../CLAUDE-instru.md) for full doc index |
| **`.mcp.json` location** | Committed [`orama-system/.cursor/mcp.json`](../../.cursor/mcp.json) when workspace is the repo root; OpenClaw hub still uses [`OpenClaw/.mcp.json`](../../../.mcp.json). Sync CRG env with `crg-embed-mode` or `openclaw-env.sh` | `claude mcp` reads user/project config; CRG env block matches OpenClaw file when `OPENCLAW_ROOT` set | [`OpenClaw/.mcp.json`](../../../.mcp.json) — `code-review-graph` via `uvx code-review-graph serve` |
| **Mother skill** | Load `bin/orama-system/SKILL.md` via Cursor skills / rules | `/skill bin/orama-system/SKILL.md` | Same path under `orama-system/bin/orama-system/SKILL.md` |
| **code-review skill** | `bin/orama-system/skills/code-review/SKILL.md` | Same | Same |
| **First-run entry** | [`docs/how-to/first-run-and-code-review.md`](../how-to/first-run-and-code-review.md) | [`bin/orama-system/references/first-run-install.md`](../../bin/orama-system/references/first-run-install.md) + [`skills/first-run-setup/SKILL.md`](../../bin/orama-system/skills/first-run-setup/SKILL.md) | `CLAUDE-instru.md` §0 outline → in-repo [`first-run-install.md`](../../bin/orama-system/references/first-run-install.md) |
| **gbrain guidance injection** | `orama-system/CLAUDE.md` gstack block (after `/sync-gbrain`); OpenClaw block if parent in workspace | Same blocks in `orama-system/CLAUDE.md` | `OpenClaw/CLAUDE.md` gstack-gbrain-search-guidance block |
| **Rules / hooks / profiles** | [`orama-system/.cursor/rules/`](../../.cursor/rules/) (e.g. commit identity); no graph-before-Read hook yet | [`.claude/settings.json`](../../.claude/settings.json), [`.claude/skills/`](../../.claude/skills/), PreCompact hook via first-run | Profile bundle [`skills/code-review/profiles/J-drona23-v5/`](../../bin/orama-system/skills/code-review/profiles/J-drona23-v5/) (referenced from OpenClaw `CLAUDE.md`) |
| **MCP tool invoke names** | Host exposes `detect_changes_tool`, `get_review_context_tool`, etc. when CRG registered | Same `*_tool` suffix in Claude Code MCP | Documented in OpenClaw `CLAUDE.md` with `*_tool` note |
| **LESSONS / memory** | [`docs/LESSONS.md`](../LESSONS.md) | Same | Same path via orama-system sibling |

### Path variables (all hosts)

| Variable | Meaning |
|----------|---------|
| `ORAMA_REPO_ROOT` | `orama-system` git root |
| `OPENCLAW_ROOT` | Parent of `orama-system` (contains `.mcp.json`) |
| `MCP_JSON` | `$OPENCLAW_ROOT/.mcp.json` |

Detection: [`bin/orama-system/scripts/lib/openclaw-env.sh`](../../bin/orama-system/scripts/lib/openclaw-env.sh).

---

## Designed first-open flow (by host)

### Cursor

- Open **`orama-system`** (or skill subfolder with repo rules still applying from parent context).
- Read **workspace rules** + repo **`CLAUDE.md`** → graph-first chain (CRG → gbrain → Read).
- Confirm **MCP**: `code-review-graph` in project MCP — reload after pull if `.cursor/mcp.json` changed (`crg-embed-mode status`).
- For bootstrap: follow [`first-run-and-code-review.md`](../how-to/first-run-and-code-review.md); invoke **code-review** skill for reviews.

### Claude Code

- `cd` to **`orama-system`**; read **`docs/LESSONS.md`** and **`CLAUDE.md`**.
- Load mother skill: **`/skill bin/orama-system/SKILL.md`**.
- If `~/.orama-system/first-run.done` missing: `first-run-install.sh status` → `run`; then **`install-mcp-stack.sh`**; MCP build/embed graph per how-to.
- Reviews: **code-review** skill → `detect_changes_tool` → gbrain → `get_review_context_tool` → scoped Read.

### OpenClaw (multi-repo hub)

- Start at **`OpenClaw/CLAUDE.md`** (exploration order + skill routing).
- Cross-repo detail: **`CLAUDE-instru.md`** (navigator only — install body lives in orama-system).
- CRG and embeddings: **`OpenClaw/.mcp.json`** + [`setup-embeddings`](../../bin/orama-system/mcp-install/references/setup-embeddings.md).
- Implementation work lands in **`orama-system/`** skills and scripts; default coding profile **`J-drona23-v5`**.

---

## Related

| Doc | Role |
|-----|------|
| [`../how-to/first-run-and-code-review.md`](../how-to/first-run-and-code-review.md) | Task-oriented bootstrap |
| [`../../bin/orama-system/skills/code-review/references/agent-matrix.md`](../../bin/orama-system/skills/code-review/references/agent-matrix.md) | Per-agent tool invocation |
| [`../../bin/orama-system/skills/code-review/references/tool-chain.md`](../../bin/orama-system/skills/code-review/references/tool-chain.md) | CRG → gbrain → Read |
| [`../local-env-catch-up.md`](../local-env-catch-up.md) | Secrets and env after pull |
