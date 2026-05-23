# First-Run Installation Reference

> **Owner:** orama-system (`bin/orama-system/`)
> **Script:** [`../scripts/first-run-install.sh`](../scripts/first-run-install.sh)
> **Sub-skill:** [`../skills/first-run-setup/SKILL.md`](../skills/first-run-setup/SKILL.md)
> **Navigator (outline only):** `OpenClaw/CLAUDE-instru.md` § 0
> **Last updated:** 2026-05-23

Run components **in order**. The installer is idempotent: satisfied components are skipped on re-run. `--force` re-validates and repairs configuration only — it never reinstalls components already marked satisfied.

## Path variables

| Variable | Detection |
|----------|-----------|
| `ORAMA_REPO_ROOT` | Git root of orama-system (parent of `bin/`; script auto-detects via `git rev-parse` fallback) |
| `OPENCLAW_ROOT` / `ORAMA_OPENCLAW_ROOT` | Explicit override, else parent of `ORAMA_REPO_ROOT` (package install: `…/OpenClaw/orama-system` → `…/OpenClaw`) |
| `ORAMA_INSTALL_DIR` | Same as `ORAMA_REPO_ROOT` when set — package install discovery |
| `NVM_NODE_BIN` | `$NVM_NODE_BIN` or `$HOME/.nvm/versions/node/v22.22.2/bin` |
| `MCP_JSON` | `$OPENCLAW_ROOT/.mcp.json` |

## State markers

| Path | Purpose |
|------|---------|
| `~/.orama-system/first-run.done` | Set when all mandatory components pass |
| `~/.orama-system/first-run.json` | Per-component status (`ok` / `warn` / `fail` / `skip` / `running`) and timestamps; `ollama.models` tracks per-model pull resume |

## Resume and progress (run only)

`status` is **fast** (&lt;5s): live probes only — no `ollama pull`, no `setup-embeddings`.

`run` performs heavy steps with **visible output**:

| Step | Progress | Resume |
|------|----------|--------|
| 0.3 Ollama models | `ollama pull` streams progress to the terminal | Per-model entries in `first-run.json` → `components.ollama.models.<name>` (`pulling` / `interrupted` / `ok` / `fail`). Re-run `run` after Ctrl+C resumes only missing models. |
| 0.5.1 Embeddings | `setup-embeddings` prints step banners to stdout | Skipped when `embeddings` status is `ok`. Set `embeddings` to `warn` or delete the key to retry. |

`--force` **re-validates** config-only checks (node, CRG, gbrain, etc.) but **does not** re-pull Ollama models or re-run `setup-embeddings` when those components are already `ok`.

## Idempotency matrix

| ID | Component | Satisfied when | `--force` behavior |
|----|-----------|----------------|---------------------|
| 0.1 | Node.js (NVM) | NVM node ≥ v20 active; `node --version` matches expected major | Re-check PATH hint in shell profile only |
| 0.2 | Python 3.13+ | `python3.13 --version` succeeds | Re-check only |
| 0.3 | Ollama + models | Ollama API up; `qwen3.5:9b-nvfp4` and `bge-m3` in `/api/tags` | Re-probe only; **does not** re-pull if component `ok` |
| 0.4 | code-review-graph | `uvx code-review-graph --version`; CRG entry in `.mcp.json` | Re-validate MCP env block only |
| 0.5 | gbrain | `gbrain` on PATH; `~/.gbrain/config.json` has `embedding_model` | Re-validate config keys only |
| 0.5.1 | Unified embeddings | `setup-embeddings` reports bge-m3 wired | Re-probe only if `ok`; re-run `setup-embeddings` manually to heal |
| 0.6 | Claude Code + profiles | `claude` on PATH; profiles dir exists under code-review skill | Re-check only |
| 0.7 | PreCompact hook | `PreCompact` present in `.claude/settings.local.json` | Re-check only |
| — | MCP orchestration stack | **Separate** — see [`install-mcp-stack.sh`](../scripts/install-mcp-stack.sh) | Not part of first-run.done |
| A.1 | OmniRoute (optional) | Probe only — never blocks first-run | Probe only |

Hardware policy (fail closed for orchestration startup) matches [`orama-system/CLAUDE.md`](../../../CLAUDE.md) and [`CLAUDE-instru.md`](../../../../CLAUDE-instru.md) § 5:

- **Mac hard:** Ollama `localhost:11434` with `qwen3.5:9b-nvfp4` + `bge-m3`
- **Windows hard:** LM Studio at `$LM_STUDIO_WIN_ENDPOINTS` (see `scripts/ensure_requirements.ps1`)

---

## 0.1 Node.js — Explicit Path Policy

> **HARD RULE:** System node at `/usr/bin/node` is often v14 (wrong). Prefer NVM node:

```bash
# Verify the correct node is active
"${NVM_NODE_BIN}/node" --version   # expect v22.x
"${NVM_NODE_BIN}/npm" --version

# Add to shell profile (~/.zshrc or ~/.zprofile) if missing:
export PATH="${NVM_NODE_BIN}:$PATH"
```

**Idempotent satisfied:** Active `node` resolves to NVM path and major version ≥ 20.

---

## 0.2 Python 3.13

`code-review-graph` requires Python 3.13+.

```bash
python3.13 --version          # must print 3.13.x
# If missing (macOS):
brew install python@3.13
```

**Idempotent satisfied:** `python3.13 --version` exits 0.

---

## 0.3 Ollama + Required Models (Hard Requirements)

> **Fail closed** for orama orchestration if absent — do not start without these on Mac.

```bash
brew install ollama    # if binary missing
# Prefer the installer (shows pull progress + resume):
bash "${ORAMA_REPO_ROOT}/bin/orama-system/scripts/first-run-install.sh" run
# Manual equivalent:
ollama pull qwen3.5:9b-nvfp4
ollama pull bge-m3

curl -s http://localhost:11434/api/tags | grep -q "qwen3.5:9b-nvfp4" || echo "MISSING: inference model"
curl -s http://localhost:11434/api/tags | grep -q "bge-m3"           || echo "MISSING: embedding model"
```

Deeper auto-install: [`../../../scripts/ensure_requirements.sh`](../../../scripts/ensure_requirements.sh).

**Idempotent satisfied:** Both models appear in Ollama tags API.

---

## 0.4 code-review-graph (MCP Knowledge Graph)

```bash
uvx code-review-graph --version
# Register MCP (from OPENCLAW_ROOT) — first-run-install.sh and setup-embeddings
# create $OPENCLAW_ROOT/.mcp.json when missing (template fallback if install fails):
code-review-graph install --platform claude-code --repo "$OPENCLAW_ROOT"

# Initial graph (once per machine / after large moves):
cd "$OPENCLAW_ROOT"
code-review-graph build-graph --repo .
```

PostToolUse hooks in `.claude/settings.json` keep the graph fresh during normal work.

**Idempotent satisfied:** `uvx code-review-graph --version` OK and `.mcp.json` contains `code-review-graph` server entry.

---

## 0.5 gbrain (Semantic Memory + Code Search)

```bash
pip3.13 install gbrain   # or uv tool install gbrain

mkdir -p ~/.gbrain
# embedding_model: ollama:bge-m3, embedding_dimensions: 1024
chmod 0600 ~/.gbrain/config.json

# Per-worktree pins (run /sync-gbrain in each repo):
#   AlphaClaw/.gbrain-source
#   orama-system/.gbrain-source
#   Perpetua-Tools/.gbrain-source

gbrain autopilot --install   # optional incremental refresh
```

**Idempotent satisfied:** `gbrain` on PATH and config file exists with embedding settings.

---

## 0.5.1 Unified Embeddings (gbrain + CRG, bge-m3)

Both gbrain and code-review-graph use **Ollama bge-m3** (1024-dim) in the same vector space.

**Idempotent setup:**

```bash
bash "${ORAMA_REPO_ROOT}/bin/orama-system/mcp-install/scripts/setup-embeddings"
bash "${ORAMA_REPO_ROOT}/bin/orama-system/skills/code-review/scripts/crg-embed-mode" status
```

After `.mcp.json` changes: restart the IDE, then re-embed via MCP `embed_graph_tool`.

**Full plan:** [`../../../docs/plans/2026-05-19-gbrain-crg-embedding-integration.md`](../../../docs/plans/2026-05-19-gbrain-crg-embedding-integration.md)

---

## 0.6 Claude Code + Profiles

```bash
npm install -g @anthropic-ai/claude-code    # uses NVM node
claude doctor
```

Default agentic profiles (canonical in repo):

- `bin/orama-system/skills/code-review/profiles/J-drona23-v5/`
- `bin/orama-system/skills/code-review/profiles/CLAUDE.coding.md`
- `bin/orama-system/skills/code-review/profiles/CLAUDE.agents.md`

**Idempotent satisfied:** `claude` on PATH; profiles directory present.

---

## 0.7 PreCompact Hook (Auto-Save Before Context Compaction)

Configured in `$OPENCLAW_ROOT/.claude/settings.local.json` (local-only, not committed).

```bash
grep -A5 '"PreCompact"' "$OPENCLAW_ROOT/.claude/settings.local.json"
```

**Idempotent satisfied:** `PreCompact` hook block found in settings.local.json.

---

## MCP orchestration stack (separate installer)

First-run does **not** install ai-cli-mcp or Gemini. After first-run completes:

```bash
bash "${ORAMA_REPO_ROOT}/bin/orama-system/scripts/install-mcp-stack.sh"
# Optional analyzer lane:
bash "${ORAMA_REPO_ROOT}/bin/orama-system/scripts/install-mcp-stack.sh" --include-gemini
```

See [`../mcp-install/SKILL.md`](../mcp-install/SKILL.md).

---

## Appendix A — OmniRoute (Optional, Never Required)

> **NEVER install in first-run. NEVER fail closed. NEVER add to mandatory checklist.**

OmniRoute is a user-managed HTTP MCP sidecar (ports 20128 MCP, 20129 UI). Skills probe at session start; workflow continues unchanged when absent.

```bash
# Probe only (first-run-install.sh does this automatically):
curl -sf --max-time 2 "http://127.0.0.1:20128/api/mcp/stream" \
  -H "Authorization: Bearer ${OMNIROUTE_TOKEN:-}" >/dev/null && echo "omniroute: up" || echo "omniroute: unavailable"
```

Full install and daisy-chain documentation: user-managed; defer to operator docs and [`../mcp-install/SKILL.md`](../mcp-install/SKILL.md) — not duplicated here to avoid drift.

---

## Heal / resume

| Situation | Action |
|-----------|--------|
| Fresh machine | `bash bin/orama-system/scripts/first-run-install.sh run` |
| Check only | `bash bin/orama-system/scripts/first-run-install.sh status` |
| After partial failure / interrupted pull | Re-run `run` — resumes per-model pulls from `first-run.json` |
| Re-validate configs (no re-pull) | `bash bin/orama-system/scripts/first-run-install.sh run --force` |
| Check only (no heavy work) | `bash bin/orama-system/scripts/first-run-install.sh status` |
| Embeddings drift | `bash bin/orama-system/mcp-install/scripts/setup-embeddings` |
| MCP workers missing | `bash bin/orama-system/scripts/install-mcp-stack.sh` |

---

## See also

- [`../../../docs/local-env-catch-up.md`](../../../docs/local-env-catch-up.md) — `.env.local`, OpenClaw secrets after redaction, `check-local-env.sh`
- [`../skills/code-review/references/tool-chain.md`](../skills/code-review/references/tool-chain.md) — code exploration order
- [`../../../CLAUDE.md`](../../../CLAUDE.md) — repo navigator + hardware summary
- [`../../../docs/v2/17-hardware-policy-enforcement.md`](../../../docs/v2/17-hardware-policy-enforcement.md) — D14 mirror policy
