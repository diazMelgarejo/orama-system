# Lessons — orama-system

> **Canonical path**: `docs/LESSONS.md`<br/>
> **Previous path**: `.claude/lessons/LESSONS.md` (now redirects here)<br/>
> **Purpose**: GitHub-auditable persistent memory across all ECC, AutoResearcher, and Claude sessions.<br/>
> **Cross-repo companions**:
> - [Perpetua-Tools/docs/LESSONS.md](../../perplexity-api/Perpetua-Tools/docs/LESSONS.md) · [GitHub](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/LESSONS.md)
> - [AlphaClaw/docs/Lessons.MD](../../AlphaClaw/docs/Lessons.MD) · [GitHub](https://github.com/diazMelgarejo/AlphaClaw/blob/feature/MacOS-post-install/docs/Lessons.MD)
>
> **Cross-repo lesson index** (shared knowledge — check here when a problem spans repos):
>
> | Topic | Canonical doc | Also in |
> |-------|--------------|---------|
> | macOS ` 2`/` 3` dupes in `.git/` internals | [AlphaClaw wiki/07](../../AlphaClaw/docs/wiki/07-duplicate-files.md) | This file §2026-05-27 + §2026-05-31 |
> | No sleep chains (`sleep N && cmd`) | [skills/no-sleep-chains/SKILL.md](../bin/orama-system/skills/no-sleep-chains/SKILL.md) | This file §2026-05-16 |
> | Git identity + Cursor commit policy | [docs/wiki/08-git-hygiene-and-branching.md](wiki/08-git-hygiene-and-branching.md) | AlphaClaw `scripts/git/check_identity.sh` |
> | gbrain pooler write failures + resync | [gstack/SKILL.md §GBrain Ops](../bin/orama-system/gstack/SKILL.md) | This file §2026-05-30 |
> | Migration gate ladder (Gate 0→4) | [PT docs/MIGRATION.md](../../perplexity-api/Perpetua-Tools/docs/MIGRATION.md) | This file §2026-05-30 T7 survey |
> | AlphaClaw branch roles + invariants | [AlphaClaw CLAUDE.md](../../AlphaClaw/CLAUDE.md) | AlphaClaw wiki/01 |
>
> **Architecture authority**: [2026-05-14--UNIFIED-ABSORPTION-PLAN.md](2026-05-14--UNIFIED-ABSORPTION-PLAN.md)
> **Navigation hub**: [CLAUDE-instru.md](../../../CLAUDE-instru.md)
>
> **Rules**:
>
> - Read this file at the start of every session
> - Prepend new entries at the top of the Sessions Log (newest first)
> - Keep entries dated and agent-tagged (`ECC | AutoResearcher | Claude`)
> - For organized, deep-dive explanations see the **[wiki →](wiki/README.md)**
> - For agent behavioral rules see **[SKILL.md →](../SKILL.md)**

---

## continuous-learning-v2

This repo uses [continuous-learning-v2](https://github.com/affaan-m/everything-claude-code/tree/main/skills/continuous-learning-v2).

- Instincts: `.claude/homunculus/instincts/inherited/orama-system-instincts.yaml`
- Import command: `/instinct-import .claude/homunculus/instincts/inherited/orama-system-instincts.yaml`

---

## Sessions Log

---

### 2026-06-26 — PR #135 CodeRabbit closure: tracked-memory path hygiene | Cursor

**What was learned**

- Merging a PR before verifying all review threads against `main` is a Stage-5 (Crystallize) failure — especially when hygiene gives false negatives (`LINT-006` missed Windows user-profile paths until extended).
- CodeRabbit autofix (`80926a3` on PT branch `a924`) replaced queue preview text with `<local-path>` but did not fix episodic JSONL, lessons rationales, or write-boundary hooks — symptom-only.
- **Root cause:** workstation paths must be sanitized at every `.agent/memory` writer (`path_hygiene.py` in PT), not in one renderer. Scrub tool + re-render for legacy rows.

**Decisions made**

- PT owns `path_hygiene.py` + `scrub_memory_paths.py`; orama `repo_hygiene.py` Windows pattern kept in sync (LINT-006).
- Follow-up PR `cursor/critical-bug-investigation-a924-followup` continues branch `a924` for joint sweep.
<!-- Append entries below. Format:
## YYYY-MM-DD — <agent: ECC | AutoResearcher | Claude | Codex> — <brief topic>
### What was learned
### Decisions made
### Open questions
-->

---

## 2026-06-22 — Claude — gbrain durability: why we kept re-fixing sync, and the self-heal that ends it

### What was learned

- **Why gbrain sync kept needing manual fixes:** the fixes lived only as knowledge, not automation, and removal steps were deferred. Concrete regenerating causes: (1) `gbrain autopilot --repo .` (launchd `com.gbrain.autopilot`, **KeepAlive=true** — a kill won't stop it, only `launchctl unload -w`) jammed on **204 unacked parse failures** and silently let sources go 16–29d stale; (2) every repo path move (iCloud-escape, →`~/code`) spawned a NEW per-path source and left the OLD-path one as a stale **duplicate** — quarantined 2026-06-18 but left **"pending removal"**, so it resurfaced as `sync_freshness`/`multi_source_drift` warnings every session.
- **The existing home was already there:** `bin/orama-system/gstack/SKILL.md` §GBrain Ops (§2/§5/§6) already documented the resync/autopilot/orphan procedures — I'd missed it by searching only `bin/orama-system/skills/`. Lesson: gbrain ops is an orama-OWNED skill (gstack/ sibling of cidf/ & afrp/), extend it, don't reinvent.
- **Gotcha:** a bare `gbrain sync` from a non-git cwd only acks failures then refuses (`Not a git repository`); per-source sync needs `--repo "<path>" --source <id>`.

### Decisions made

- Archived (soft-delete, reversible) the 4 orphan sources (`orama-src`, `gstack-code-ools-27e2b79c`, `gstack-code-claw-4dc4a8f3`, `periscope-src`); defs exported to `~/repo-backups/gbrain-stale-quarantine-20260622/orphan-sources.json`. periscope re-add: `gbrain sources add --path ~/code/oramasys/tools/periscope`.
- Built `scripts/gbrain/gbrain-selfheal.sh` (idempotent: ack failures, refresh live sources with `--repo`+`--source`, report orphans/misconfig, never auto-delete) and wired it into `start.sh` (backgrounded, non-fatal). Extended `gstack/SKILL.md` §GBrain Ops with §7 + Quick-Ref rows.
- Left the launchd autopilot **unloaded**: for a multi-repo workspace a single `--repo .` autopilot is the bug (§6), so the self-heal script / manual `/sync-gbrain` is the refresh mechanism.
- Cross-repo lesson companion: PT `.agent/memory` lesson `d0d49b68ab24` (+ `36f924c161e1` cd-gotcha).

### Open questions

- Acked-but-archived sources still show in `gbrain doctor` freshness (noise); `purge --confirm-destructive` removes fully (recoverable via the manifest) if zero-noise is wanted.

---

## 2026-06-22 — Claude — DO-NOT: catastrophic assumption (`.agents` vs explicit `.agent`) + stay-on-task

### What was learned

- **DO NOT example (anti-pattern, anathema to AFRP):** the user said write memory to `.agent/memory`. I silently "corrected" it to `.agents/memory` — rationalizing "avoid a parallel dir" — and committed there. `.agent/` was in fact the **canonical, structured portable-brain** on `origin/main` (its own `AGENTS.md`, `memory/{semantic,episodic,personal,working}`, `tools/learn.py` + dream pipeline). I had never read `AGENTS.md` and never checked origin. **Know the purpose first and ASK; NEVER assume.** Overriding an explicit, unambiguous user instruction with a guess is the exact failure the orama method exists to prevent.
- **I was outdated and did not know it:** local `main` was stale (branched at the merge-base, never saw the `.agents/`→`.agent/` migration). I wrote into the dead dir because I judged "ahead 1 / behind 0" instead of comparing the HEAD **tree** to origin. Reinforces [§ 6 tree-twin rule](../CLAUDE.md) and [LESSONS § 2026-06-05](#) — never trust ahead/behind across a rewrite; compare trees, adopt upstream structural migrations before writing.
- **Stayed off-task:** the stated **#1 task** was code review + clean `/src` `/bin` restructure of `oramasys/perpetua-core`; I let an iCloud-move/cleanup tangent replace it and never delivered it. Getting distracted from the explicit primary task is itself a failure.
- **Memory protocol:** `.agent/memory/semantic/LESSONS.md` is **rendered from `lessons.jsonl`** (`AGENTS.md` Rule 5) — never hand-edit it; teach via `.agent/tools/learn.py`. This canonical `docs/LESSONS.md` *is* hand-edited (newest-first), so the two systems differ — know which is which before writing.

### Decisions made

- Erased the wrong commit (unpushed) by re-anchoring local `main` to `origin/main`; re-recorded the four lessons through the PT `.agent/` pipeline. Crosslink: [PT `.agent/memory/semantic/LESSONS.md`](../../perplexity-api/Perpetua-Tools/.agent/memory/semantic/LESSONS.md) — lessons `2e154f1b55ab` (assume-not-ask), `d892d844cf60` (do-related-now), `0afc8c5f2778` (stale-branch), `a7374ba4b00d` (stay-on-task).
- These four are the cross-repo "DO NOT" companions to this entry; check both when a correction recurs.

### Open questions

- Resume the original task: code review `perpetua-core@feat/salvage-plugins-rc1` + src-layout restructure (tests inside `/src` per `src-struc.md`).

---

## 2026-06-20 — Codex + Claude — Native codex/gpt-5.5 agent and workspace template reconciler

### What was learned

- The old `codex-openclaw-agent` used a custom `openai-completions` provider block pointing at `http://127.0.0.1:61234/v1` plus a `codex-supervisor` observation plugin as the model runtime. Both are wrong: `codex-supervisor` is a supervision/observation plugin, not a model runtime; the real native provider is the OpenClaw `openai` bundled plugin with model string `codex/gpt-5.5` from the catalog.
- The correct agent registration flow is `openclaw agents add codex-agent --model codex/gpt-5.5`; reconcile managed fields through `openclaw config set --batch-json`; never hand-write a `models.providers.codex` block.
- Plugin allowlist (`plugins.allow`) is a security boundary. The binder must read the existing list, append only `openai`, and never widen it beyond that.
- `generate_codex_openclaw_profile.py` must be an idempotent marker-region reconciler (`<!-- oramaclaw:generated:start/end -->`), not a full-file writer. Operator content outside the markers and `SECURITY.md` once written must survive reruns.
- The workspace at `~/.openclaw/agents/codex-agent` is already registered (OpenClaw Gateway Agent Main confirmed registration). The generator converged immediately (no files changed) because `CODEX.md` and `IDENTITY.md` were already reconciled from a prior run. `AGENTS.md` and `TOOLS.md` had no `oramaclaw:generated` sections yet and received them.
- `codex review --commit HEAD < /dev/null` stalled mid-review when `list_graph_stats_tool` MCP call blocked — CRG MCP was interrupted. Have a direct-read fallback ready for codex review output files and rely on CRG semantic search + manual diff for correctness when this happens.

### Decisions made

- `codex-agent` canonical workspace: `~/.openclaw/agents/codex-agent`; `agentDir`: `~/.openclaw/agents/codex-agent/agent`; model: `codex/gpt-5.5`; `thinkingDefault`: `medium`; `tools.profile`: `coding`.
- Delegation path: `agents.defaults.subagents.allowAgents` (not `agents.bindings.*.allowAgents` — that key is rejected by the oramaclaw control plane).
- Auth flow: `openclaw models auth login --provider openai-codex` (interactive, never in unattended automation).
- `bind_codex_backend.sh` drops `--force`; reports `needs_plugin` and `needs_auth` as structured exit states; restarts gateway only when provider or agent config actually changed.
- Fixture rename: `oramaclaw-codex-provider.json` → `oramaclaw-native-codex-agent.json`; cooperative-drift fixture uses `example-provider` so it doesn't imply the old custom-provider path.

### Open questions

- None blocking. P2 items (90-second timer scope, psutil vs os.kill, `__init__.py` surface) remain open by design.

---

## 2026-06-18 — Codex — Hermes Windows one-shot routing and Antigravity adapter

### What was learned

- Hermes installed under `%LOCALAPPDATA%\hermes\hermes-agent`, but `hermes.exe`
  was not on the active PowerShell `PATH`; use the venv `Scripts` directory or
  add it to `PATH` before one-shot calls.
- `HERMES_GIT_BASH_PATH` must point to a literal `bash.exe`. GitHub Desktop's
  bundled Git Bash works when resolved from
  `%LOCALAPPDATA%\GitHubDesktop\app-*\resources\app\git\usr\bin\bash.exe`.
- On this host, `hermes -z` through the default LM Studio model timed out, while
  `hermes --safe-mode --provider nous --model nvidia/nemotron-3-ultra:free -z`
  returned promptly. Use explicit provider/model routing for bounded partner
  review loops unless the local LM Studio model has already been proven fast.
- Native Windows AGY install is `irm https://antigravity.google/cli/install.ps1 | iex`.
  `agy --print` can exit 0 with empty stdout in this PowerShell session. Treat
  Antigravity as ready only after a visible `AGY_READY` canary, not merely after
  `agy` appears on `PATH` or the installer completes.
- If AGY print mode exits 0 with empty stdout, run it once with `--log-file`.
  In this session the log showed silent auth followed by hosted-model quota
  exhaustion, so AGY was installed/authenticated but not dispatchable until
  quota reset or a different authenticated model/account is selected.
- Gemini CLI `--prompt` is separate from Antigravity OAuth state. A local
  Antigravity OAuth settings file can exist while Gemini CLI still reports that
  no auth method is selected; verify Gemini with a small `--prompt` canary
  before treating it as a Gemini-Analyzer worker.
- Antigravity project wiring should stay as a thin adapter (`ANTIGRAVITY.md`
  plus `.agent/`) that points back to canonical orama skills, lessons, and
  permissions instead of copying private Hermes/OpenClaw state.
- Hermes local slash commands should follow the same pattern: install thin
  wrappers with `install_hermes_thin_skills.py`; keep rich command behavior in
  canonical `bin/orama-system/skills/hermes-harness/commands/` cards, not the
  Hermes local skill directory.

### Decisions made

- Added `hermes-harness` as the canonical Hermes/ECC onboarding skill beside
  `openclaw-skills`.
- Kept `.agents` and `.claude` Hermes installs as thin wrappers.
- Documented the Windows Hermes launcher, Git Bash, and explicit one-shot route
  in [wiki/15-hermes-windows-harness.md](wiki/15-hermes-windows-harness.md).

### Open questions

- The wider Windows suite still has unrelated jq, shell-quoting, path, and
  fixture failures that should remain a separate Windows-suite repair branch.

---

## 2026-06-12 — OpenClaw gateway :18789 won't start ("Not onboarded"): drive the openclaw CLI directly (don't guess)

**Symptom:** Gateway `:18789` down. AlphaClaw manager (`:3000`) `POST /api/gateway/restart` → `{"ok":false,"error":"Not onboarded"}` even though `~/.alphaclaw/onboarded.json` exists.

**Root cause:** That "Not onboarded" is AlphaClaw's OWN read-only onboarding-marker gate (`onboarded.json` `{"readOnly":true,"reason":"read_only_complete"}`) — SEPARATE from OpenClaw gateway readiness. It is not the gateway's blocker.

**Fix (verified live 2026-06-12; OpenClaw is a PUBLIC project — docs.openclaw.ai, github.com/openclaw/openclaw — search, don't reinvent):** bypass AlphaClaw's manager and drive the bundled `openclaw` CLI directly:
```
node <repo>/AlphaClaw/node_modules/openclaw/openclaw.mjs gateway --port 18789 --force
```
- Needs `gateway.mode=local` in `~/.openclaw/openclaw.json`. Docs: gateway refuses to start without it; a clobbered config that lost `gateway.mode` is "broken" → repair via `openclaw onboard --mode local` or `openclaw setup`. Ad-hoc/dev override: `openclaw gateway --allow-unconfigured`.
- Verify: `openclaw gateway status --deep --json` → port `busy` + listener pid on 18789.
- Durable service: `openclaw gateway install` + `openclaw gateway restart --force` (LaunchAgent `ai.openclaw.gateway`; keep service PATH minimal — doctor warns on version-manager PATHs).
- Non-interactive onboard (scripts): `openclaw onboard --non-interactive --mode local --auth-choice apiKey --anthropic-api-key "$KEY" --gateway-port 18789 --gateway-bind loopback --install-daemon --daemon-runtime node --skip-skills`.
- Port/bind precedence: `--port` → `OPENCLAW_GATEWAY_PORT` → `gateway.port` → 18789.

**Relevant OpenClaw-operation skills:** `alphaclaw-session` (commandeer/self-heal runtime — PRIMARY owner of this fix), `model-routing-check` (gateway must be live before dispatch), `self-discovery` (gateway status = live-state probe).
---

---

## [2026-06-12] Write-time path-hygiene guard (don't rely on memory)

- **Pattern**: enforce "no workstation/absolute paths in tracked files" at WRITE time, not only at commit/CI. PreToolUse hook `~/.claude/hooks/no-workstation-paths.py` (matcher `Write|Edit`) blocks (exit 2) when an edit injects an absolute home path or a synced-tree path into a git-tracked, non-gitignored file; allows scratch/`/tmp` and gitignored files.
- **Rule**: use repo-relative paths — `"$(git rev-parse --show-toplevel)/…"` or sibling `"../../<repo>/…"`. `repo_hygiene.py` (pre-commit + CI) remains the backstop.
- **Why**: relying on memory failed (a workstation path re-leaked into a tracked skill); a deterministic harness guard is the durable fix. Fresh-install bootstrap imperative for the guard lives in the CIDF skill.

---

---

## [2026-06-12] One canonical skill source; .claude/skills are thin wrappers

- **Pattern**: `bin/orama-system/` is the permanent canonical; `.claude/skills/*` become thin read-through wrappers (frontmatter + redirect). `scripts/consolidate-skills.sh` does it idempotently — union-merge (never overwrite/delete; differing files preserved as `.from-claude-<stamp>`), `--wrapper-only` for repos already superseded by orama.
- **Fact**: ultrathink-system's 4 skills unified into orama (cross-repo wrappers); verified bin is a semantic superset before treating .claude copies as stale.

---

---

## [2026-06-12] Codex skill installs are thin wrappers; canonical skills stay in repo

- **Decision**: local Codex installs under `~/.codex/skills` must be thin wrappers only. They should contain a Codex-valid `SKILL.md` with trigger text, canonical repo root, canonical in-repo `SKILL.md` path, and an origin-sync rule. Do not copy canonical skill bodies, references, scripts, or assets into the local install.
- **Origin rule**: before using a canonical card, run `git fetch origin --prune`. Run `git pull --ff-only` only when the repo is clean and on a tracking branch. If dirty or non-fast-forward, preserve local work, report drift, and read the current canonical card with that caveat.
- **Windows encoding rule**: generated skill roots must be UTF-8 without BOM. In Windows PowerShell, set console/output encodings explicitly and use `[System.Text.UTF8Encoding]::new($false)` with `[System.IO.File]::WriteAllText(...)`. `Set-Content -Encoding utf8` can leave a BOM in Windows PowerShell 5.1; Python validators may also need `PYTHONUTF8=1`.
- **Validation gates**: run Codex `quick_validate.py` on each wrapper; verify canonical paths exist; verify wrapper dirs contain only `SKILL.md`; scan wrapper roots for mojibake markers; save an audit JSON beside the manifest.
- **Qwen/LM Studio testing**: use compact `/no_think` JSON prompts. Large canonical excerpts can time out on `qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2`; prefer deterministic path/frontmatter audits first, then ask Qwen to review the compact name/description manifest. Save raw responses and parsed summaries under `~/.codex/skill-test-results/`.
- **Penultimate completion habit**: before declaring a long-running goal achieved, collect the session lessons and update the canonical skills/docs first, then refresh local wrappers if trigger text or canonical paths changed.

---

---

## [2026-06-12] Local Qwen delegation is project-controlled, not hosted Codex-controlled

- **Fact**: Hosted Codex multi-agent `spawn_agent` only exposes its configured hosted model menu; it does not accept arbitrary local LM Studio model IDs such as `qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2`.
- **Decision**: exact local Qwen delegation belongs in repo-controlled routing surfaces: orama agent registry entries, Perpetua routing/model registries, and PT-MCP/local-agent model discovery. Treat hosted subagents as useful when their model menu is sufficient, but do not promise exact LM Studio model affinity through that surface.
- **Pattern**: for exact local model work, first verify LM Studio `/v1/models`, then expose loaded/callable model metadata through the project MCP or local-agent bridge, and route coder/priority-subagent roles to the exact returned model ID.
- **Windows validation lesson**: when validating Node-based MCP packages on this host, account for LM Studio's bundled Node/npm layout and Windows ESM path rules. Use `pathToFileURL` for absolute imports, run npm through the current `npm_execpath` when spawning from tests, and prefer cross-platform npm scripts such as `"build": "tsc"`.

---

## 2026-06-10 — Claude — Mojibake: root cause, repair, and prevention (LINT-007)

**Symptom.** Tracked files showed garbled punctuation — em-dashes as `a-circumflex
+ euro + quote`, arrows (`←`/`→`/`⇒`) as `a-circumflex + dagger + ...`, and the Greek
`ὅραμα` header shredded. 10 files affected (worst: `docs/SYNC_ANALYSIS.md`, 65 hits).

**Root cause — an encoding/decoding mismatch.** Text is *bytes + a charset*. Mojibake
is bytes written in one charset and read as another:

- An em-dash `—` is UTF-8 `E2 80 94`. Read those 3 bytes as **Windows-1252** (a
  single-byte charset) and you get 3 characters: `E2`→`a-circumflex+euro+quote (cp1252-misread em-dash)`, `80`→`€`, `94`→`"`. Save
  that as UTF-8 and the corruption is now permanent in the bytes. That is **single-level**
  mojibake.
- Pass the corrupted file through the same wrong-decode again → **double mojibake**
  (the `a-circumflex+euro+quote (cp1252-misread em-dash)` run itself re-mangled into `A-tilde + ...`). Each mis-encoding tool in the chain adds a layer.
- **CP1252 holes** (`0x81 0x8D 0x8F 0x90 0x9D` are undefined): when an original byte
  lands on a hole — e.g. `←` = `E2 86 90`, the `0x90` — the decoder falls back to
  Latin-1 (→ U+0090), producing a **mixed cp1252/latin-1** corruption that a pure
  cp1252 round-trip cannot reverse.

**Most likely trigger here.** Windows Python/PowerShell default to **cp1252**, not UTF-8.
A file read/written without an explicit `encoding="utf-8"` on Windows mangles every
non-ASCII char. The affected files are exactly the docs/tests touched during this
branch's Windows-toolchain work (see the "Windows Git shim" / "toolchain bootstrap"
lessons). Other common causes: copy-paste across apps with different clipboard
encodings; running `sed`/`perl` under `LC_ALL=C`; a `LANG=C` locale; an agent emitting
"smart" punctuation that a downstream non-UTF-8 tool re-encodes.

**The repair (general).** Per-character re-encode (cp1252 where defined, else latin-1)
→ bytes → decode UTF-8, iterate until stable, and **only accept the result if it
reduces the high-byte count** (so legitimately-accented text can't be corrupted):

```python
def to_bytes(s):
    out = bytearray()
    for ch in s:
        try: out += ch.encode("cp1252")
        except Exception: out += ch.encode("latin-1")   # cp1252 holes
    return bytes(out)
def deep_fix(run):                 # apply only to runs of high chars
    cur = run
    for _ in range(6):
        try: t = to_bytes(cur).decode("utf-8")
        except Exception: break
        if t == cur: break
        cur = t
    return cur if hi(cur) < hi(run) else run   # reduction guard
```

**Prevention (now enforced).**
- **LINT-007** added to CIDF (`bin/orama-system/cidf/SKILL.md`) and to the canonical
  gate `scripts/review/repo_hygiene.py` — which the **pre-commit hook and CI both run**
  (single source of truth, zero fragmentation). A mojibake byte pair can no longer
  enter history.
- Always pass `encoding="utf-8"` to `open()` — never rely on the platform default
  (Windows = cp1252). Set `PYTHONUTF8=1` / `PYTHONIOENCODING=utf-8` in cross-platform
  scripts; keep `LANG`/`LC_ALL` UTF-8; never run text transforms under `LC_ALL=C`.

**Dogfood note.** Found and fixed while driving GOAL.md's AC4 (afrp encoding) — the
oramasys methodology's own Ruthless-Refinement stage applied to the repo itself.

---

---

## 2026-06-10 — Claude — oramasys rename audit, skill eval, GOAL.md

### What was learned
- The `mcp.json` server name (`ultrathink-lmstudio`), the mother SKILL.md
  allowed-tools field (`mcp-ultrathink-lmstudio`), and the body reference
  (`mcp-ultrathink-openclaw`) were three different names — none aligned.
  The fix had already landed on origin/main (`mcp-oramasys` canonical) but
  two downstream clients and several config JSONs still used legacy names.
- `bin/shared/ultrathink_core.py` is still the live module name; 67 residual
  `ultrathink` refs remain in production code/skills (not counting deliberate
  legacy/shim lines). This is the P0 blocker for v1.1.
- `.claude/skills/agent-methodology/SKILL.md` defines a 5-stage sequence
  (Crystallize→Architect→Execute→Refine→Verify) that diverges from the
  canonical `references/oramasys-5-stages.md`. The card was added without
  syncing to the canonical source. Dogfood defect: found by applying the
  methodology's own Stage 3 (Ruthless Refinement — eliminate inconsistency)
  to orama-system itself.
- `bin/orama-system/afrp/SKILL.md` line 3 has a UTF-8 mojibake artifact
  (`a-circumflex+euro+quote (cp1252-misread em-dash)` instead of `—`). Likely introduced by a copy-paste through a
  non-UTF-8 tool.

### Prevention
- Add a hygiene check: `grep -rn "ultrathink" --include="*.py" --include="*.json" --include="SKILL.md" bin/ .claude/ .agents/` should return 0 lines
  (excluding deliberate legacy/shim/alias lines). Wire into `test_repo_hygiene.py`.
- When creating a background-knowledge skill card (user-invocable: false), add a
  frontmatter comment: `# source-of-truth: references/oramasys-5-stages.md` so
  future editors know where to look before editing.
- Before any `cp` or paste of a markdown file across tools, verify encoding:
  `python3 -c "open('file.md').read().encode('utf-8')"` — silent = clean.

### Decisions made
- `GOAL.md` written at repo root to give Claude Code a persistent, self-contained
  goal with 10 verifiable acceptance criteria (AC1-AC10). Each criterion is an
  exact bash command; a green checkbox = observed exit-0, not an assumption.
- The oramasys-method skill is the user-invocable front door replacing ultrathink-system.
  It is intentionally thin: it delegates to the mother skill, agent-methodology card,
  and references/ rather than duplicating their content.
- The eval revealed "re-architecting the orchestrator" did not trigger the skill.
  Fix: broadened description with "re-architecture work", "multi-step plan",
  "complex refactor", "system overhaul", "design-heavy", "non-trivial".
  Final eval: Precision 1.00, Recall 0.86 (honest parse from real description).

### Open questions
- AC9 (Perpetua-Tools lockstep): the scan found `ultrathink-agent-network` in
  PT's orchestrator/. Needs a separate pass on the PT branch.
- The frugality eval harness (`scripts/eval/oramasys_trigger_eval.py`) is
  referenced in AC8 but not yet committed. Should be added in the P0 rename PR.

### Cross-references
- GOAL.md (repo root) — the persistent execution goal
- docs/plans/2026-05-29-03-v1.1-definitive.md — the full v1.1 plan
- docs/plans/2026-06-10-oramasys-method-skill-eval.md — eval report
- bin/orama-system/skills/oramasys-method/ — the replacement skill

---

---

## 2026-06-06 — AI agents do destructive git ops; every agent must know this protocol

**Incident class: recurring.** A Cursor agent rewrote PT's git history (force-push to main)
during a parallel session. A second agent rewrote orama-system (PR #70 rewrite). This
session encountered both consequences. This lesson is written for *every successor agent* —
it is not one-off; it will happen again.

**Pattern:** An AI coding agent is given a task ("fix the CI", "clean up commits", "merge
this PR"). It reaches for a `git rebase -i`, `git push --force`, or a `git commit --amend`
on a shared branch. No human explicitly authorised the rewrite. The agent believes it is
being helpful. The result: all SHA-based reasoning across the stack (ahead/behind,
merge-base, branch divergence counts) becomes meaningless for that repo.

**What breaks downstream (from this session alone):**
- `git log origin/main..HEAD` showed `[ahead 454, behind 478]` for PT — looked catastrophic,
  was a stale tracking ref across a rewrite boundary. Caused a near-destructive reset.
- gbrain's sync anchor commit disappeared → full re-import needed; checkpoint lost.
- CRG graph went stale (all node SHAs outdated).
- All other agents working on that repo with local clones have orphaned branches.

**The hard rules (encode in every new repo's `AGENTS.md` and `CLAUDE.md`):**

1. **Never force-push to `main`, `master`, or any shared branch** without explicit human
   instruction naming the exact branch and the word "force-push" or "rewrite history".
   Git safety rule G3 in orama-system docs 25/26 covers this.

2. **After ANY suspected rewrite** (saw force-push, unusual divergence, missing SHAs),
   **run the tree-twin scan before ANY git operation:**
   ```bash
   bash scripts/git/reanchor_scan.sh <repo> origin/main [heads|all]
   ```
   then `git cherry -v <main> <branch-tip> <twin>` to separate real new work (`+`) from
   already-merged shadow copies (`-`).

3. **Never judge orphan/divergence with proxy metrics** (ahead/behind counts, `rev-list
   --count`, `merge-base` comparisons). Across a rewrite boundary they lie. "N behind +
   byte-identical content" = tree-twin, not orphan. HALT; run the scan.

4. **If gbrain is `broken-config` or the sync anchor is missing**, do NOT call `gbrain`
   and do NOT push a resync — diagnose first. Follow the `feedback_gbrain_checkpoint_bug`
   memory: force-sync against a poisoned checkpoint can recurse-delete the repo root.

5. **Multi-agent write coordination gate** (doc 25 §4 heartbeat): all agentic code writes
   to shared branches require the worktree-per-agent doctrine
   (`docs/v2/22-worktree-parallel-agents.md`). Two agents writing to the same branch without
   coordination = the root cause of most branch collisions this stack has seen.

**Recovery playbook** (when rewrite already happened — `scripts/git/reanchor_scan.sh` first):
```bash
# 1. Find the pre-rewrite tip in reflog or pull/*/head refs
git log --all --oneline | head -30   # look for familiar commit messages
gh api repos/<org>/<repo>/git/refs --paginate -q '.[] | .ref' | grep refs/pull  # GitHub keeps PR heads

# 2. Tree-twin scan — gives you the set of branches + their twin commits on new main
bash scripts/git/reanchor_scan.sh . origin/main heads

# 3. For branches with `+` commits (real new work not in new main):
git cherry -v <new-main-tip> <branch-tip>   # + = must rescue, - = already there
git checkout -b recover/<branch> <old-tip>
# cherry-pick the `+` commits only, open PR

# 4. Verify gbrain + CRG sync anchors; resync if clean
gbrain sources list   # check last sync timestamps
```

**Cross-agent propagation:** This lesson is in both LESSONS.md files (orama + PT), in
`AGENTS.md` § History-rewrite protocol in every repo, and in the git-history-surgery SKILL.md.
The docs/v2/27 governance plan covers the org-wide rollout to future `oramasys/*` repos.

### 2026-06-06 (cont.) — zero-fragmentation gate SHIPPED + a live concurrent-write collision (2nd this session)

Two concrete outcomes today, both reinforcing the multi-agent doctrine above:

**1. Guard-parity gate shipped.** The attribution-guard drift (stale PT forks rejecting
mainstream-AI co-authors) is now *enforced*, not just documented:
[`scripts/git/verify-guard-parity.sh`](../scripts/git/verify-guard-parity.sh) — fail-closed,
two checks: (a) **completeness** (every canonical guard is in the sync copy list — catches the
exact omission that let `check_commit_message.sh`/`check_identity.sh` drift); (b) **parity**
(downstream copies byte-identical to orama canonical via `cmp -s`). Verified PASS on orama +
PT (9/9). Added to the sync copy list so it self-propagates. Doctrine: [`docs/v2/27`](v2/27-git-governance-zero-fragmentation.md).

**2. Concurrent-agent collision during the opus-4-8 migration — caught a 404 regression.**
While doing the `/claude-api migrate` task, a parallel agent (same approved identity
`cyre <Lawrence@cyre.me>`) was running the *same* migration and pushed to PT `main`
concurrently. Two specific failures it introduced, both caught before harm:
- **Malformed model IDs that would 404 at runtime:** `claude-4-6-sonnet-thinking`,
  `claude-4-6-sonnet`, `claude-4-5-haiku`. The correct order is `claude-<family>-<major>-<minor>`
  → `claude-sonnet-4-6` / `claude-haiku-4-5`; `thinking` is a request param, never part of the
  ID. **Lesson: validate every model-ID string against the real catalog — `claude-4-6-sonnet`
  is a plausible-looking typo that silently 404s only when the call fires.**
- **Stray upstream tracking + a racing dependabot push to `main`:** my local `main` was
  tracking a dated branch another agent created (so `git push` reported "up-to-date" while 2
  commits behind), and a dependabot starlette bump (#107) landed on `origin/main` mid-push.
  Fix: explicit `git push origin HEAD:main`, then rebased onto the dep commit (no overlap),
  FF'd, and **returned the shared checkout to `main`** so the next agent doesn't inherit a
  stray HEAD. Don't trust a bare `git push` in a shared working dir — check `@{u}` and the
  current branch first.

**Reinforced rule:** in a shared checkout, before committing/pushing, run
`git rev-parse --abbrev-ref HEAD` + `git rev-parse --abbrev-ref @{u}` — a fellow agent may
have moved HEAD onto their branch. Land via explicit `HEAD:main` refspec, then restore `main`.

**Cross-repo:** [PT LESSONS § 2026-06-06](../../perplexity-api/Perpetua-Tools/docs/LESSONS.md) ·
[GitHub](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/LESSONS.md). Open
priorities after today: **(P1)** repair gbrain (`broken-config` → `/setup-gbrain`); **(P2)**
resume tri-repo Gate 2→3 ([[project_tri_repo_migration_state]]); **(P3)** wire
`verify-guard-parity.sh` into each repo's CI + `daily-attribution-guard.sh`.

**Canonical references:** `scripts/git/reanchor_scan.sh` · `bin/orama-system/skills/git-history-surgery/SKILL.md`
· `docs/v2/22-worktree-parallel-agents.md` · memory `feedback_git_guards_single_source`
· memory `project_orama_main_rewrite_pr70`.

### 2026-06-08 — Claude patch review: accept canonical aliasing, reject duplicate skill tree

Claude's attached recommendations were useful for the P0 rename only where they added missing contract clarity: successor aliasing (`ultrathink` prompts map to oramasys), canonical MCP naming (`mcp/oramasys`, `oramasys_*` tools), and explicit compatibility shims for one v1.x release. The proposed standalone `oramasys-method` skill duplicated content already present in the current orama skill stack (5-stage method, CIDF, AFRP, CRG/gbrain frugality, first-run references), so copying it wholesale would fragment the operator surface.

Decision: consolidate, do not duplicate. Keep the existing skill tree as the source of truth and fold in only the new alias/MCP naming rules. Preserve existing MCP entries (`code-review-graph`, `ai-cli-mcp`, GitHub/LM Studio style stdio configs) when adding `oramasys`; never replace the whole `.cursor/mcp.json` from a patch that only intends to add one server. P1/P2 pipeline/version-bump work stays deferred until after the P0 `/oramasys` contract is stable.

### 2026-06-08 (cont.) — Windows Git shim must expose GitHub Desktop's HTTPS helper path

During the P0 oramasys commit/rebase flow, `git pull --rebase origin main` failed
with `git: 'remote-https' is not a git command` even though `git --exec-path`
pointed inside GitHub Desktop. Root cause: the local `%USERPROFILE%\.lmstudio\bin\git.cmd`
shim launches GitHub Desktop's `cmd\git.exe`, but it does not put the bundled
`mingw64\bin` helper directory on `PATH` or set `GIT_EXEC_PATH` to the directory
that contains `git-remote-https.exe`.

Temporary working command:
```powershell
$gitRoot = "$env:LOCALAPPDATA\GitHubDesktop\app-3.5.9-beta3\resources\app\git"
$env:PATH = "$gitRoot\mingw64\bin;$gitRoot\cmd;$env:PATH"
$env:GIT_EXEC_PATH = "$gitRoot\mingw64\bin"
& "$gitRoot\cmd\git.exe" pull --rebase origin main
```

Permanent shim rule: keep the LM Studio-style lightweight wrapper, but when it
finds a GitHub Desktop app directory, prepend both `resources\app\git\mingw64\bin`
and `resources\app\git\cmd` before invoking `cmd\git.exe`, or set
`GIT_EXEC_PATH` for that child process. Do not replace the shim with a hardcoded
single GitHub Desktop version path; keep edition/version discovery frugal.

PowerShell gotchas from the same run:
- Quote upstream shorthand as `git rev-parse --abbrev-ref '@{u}'`; bare `@{u}` is parsed as a hashtable.
- Do not use `&&` in this Windows PowerShell session; run commands separately or use PowerShell-native control flow.
- If the HTTPS helper error disappears and the next failure is `Failed to connect to github.com ... 127.0.0.1`, the Git shim is fixed enough for HTTPS and the remaining issue is network/proxy access, not Git packaging.

### 2026-06-10 — Windows local verification needs explicit Git/Python toolchain bootstrap

While reviewing PR #74 from Windows, the local full pytest suite first failed
because subprocesses could not find literal `bash`, then improved once a temporary
`bash.exe` shim pointed at GitHub Desktop's `usr\bin\sh.exe`. Remaining failures
were environment-shaped: no `jq`, Windows path separator expectations in tests,
and shell subprocesses resolving `python` to the Windows Store alias.

Operational rule now lives in the git skills: run the Windows PowerShell runtime
bootstrap from `bin/orama-system/skills/using-git-worktrees/SKILL.md` before
rebases, pushes, or Windows local verification. The bootstrap:
- prepends `%USERPROFILE%\.lmstudio\bin`;
- discovers the latest GitHub Desktop `app-*` git bundle;
- prepends `mingw64\bin` and `cmd`, then sets `GIT_EXEC_PATH`;
- uses LM Studio's bundled `node.exe` at `%USERPROFILE%\.lmstudio\.internal\utils\node.exe`;
- records the explicit venv Python path
  `%USERPROFILE%\Downloads\SKILLS.md\ultrathink\Perplexity-Tools\.venv\Scripts\python.exe`;
- optionally creates a temp-only `bash.exe` shim from `usr\bin\sh.exe` for tests
  that invoke literal `bash`.

Do not claim GitHub Desktop provides full Bash on this host: current evidence
shows `sh.exe` exists and `bash.exe` does not. Prefer a real Git for Windows
install if Bash semantics matter; otherwise use the temp shim only for local
verification and keep it outside the repo.
---

---

## 2026-06-05 — I repeated FM7 one hour after shipping the fix (the durable lesson)

**What happened.** Right after merging PR #73 (which *added* Failure Mode 7 and the
tree-twin §B5 to git-history-surgery), and after **moving `reanchor_scan.sh` into the workspace**,
I was asked to check Perpetua-Tools branches. I reflexively hand-rolled a fresh `git
rev-list --count` / `merge-base` ahead-behind table — **the exact proxy the skill I'd just
written forbids** — and declared PT "no orphans, nothing to do." The user caught the tell:
a branch read `479 behind` while its tip was byte-identical to a main commit. That is
**impossible unless `main` was rewritten** — which it had been. PT's branches were
pre-rewrite SHA lines needing tree-twin re-anchor, not healthy branches.

**Root cause — not knowledge, point-of-use.** The method existed in three files I'd
authored. Knowing a skill ≠ invoking it. Under a "just check the branches" prompt I grabbed
the fast familiar command instead of running the canonical tool. This is the
using-superpowers "I remember this skill" red flag, made concrete.

**The non-negotiable rule** (now also in the [`scripts/git/reanchor_scan.sh`](../scripts/git/reanchor_scan.sh)
header and [`AGENTS.md`](../AGENTS.md) § History-rewrite protocol):
- Across any repo whose `main` may have been rewritten, **never** judge orphan/divergence
  with `ahead/behind`, `rev-list --count`, or `merge-base` — they are SHA-graph proxies,
  meaningless across a rewrite boundary.
- **Always run the tree-twin scan** — `scripts/git/reanchor_scan.sh <repo> <main-ref> [scope]`
  — then `git cherry -v <main> <tip> <base>` to separate genuinely-missing commits (`+`)
  from work already in main (`-`).
- "N behind + byte-identical content" is a contradiction that must HALT you, not be reported.

**Why prose alone failed, and what makes it stick.** A lesson in a doc only helps if I
remember to read it — the very thing that failed. Durable fixes, in reliability order:
(1) determinism — one sanctioned script, no improvised `rev-list`; (2) a PreToolUse hook
that flags ahead/behind/merge-base used for orphan judgment and points at the script;
(3) a top-of-`CLAUDE.md`/`AGENTS.md` banner, because those load every session. Cross-agent
propagation lives in [`AGENTS.md`](../AGENTS.md) § History-rewrite protocol so Codex, Cursor,
CodeRabbit, and Greptile inherit it too — destructive git ops by fellow agents are recurring,
not one-off.

**PT finding (the missing link).** PT `main` was rewritten; tree-twin scan of local branches:
5 already in-main (twin tip), 10 with commits above their twin. `git cherry` isolated the
genuinely-unmerged work — chiefly **`fix/pt71-review-v2`** (9 missing: `alphaclaw_manager`
bootstrap-JSON progress-prefix parse, `startServer` pidFile ReferenceError fix + regression
tests, `install.sh` exec-bit, remaining PT#71 review fixes), **`fix/ci-69`** (MCPB
`Claude-Desktop-LLM` submodule + fail-fast Ollama probe), **`temp-recovery`** (3-tier IP
detection), **`recover/…codex-plan-revision`** (queue test isolation). Salvage = re-anchor
onto twin, then PR the `+` commits. Details: PT [`docs/LESSONS.md`](../../perplexity-api/Perpetua-Tools/docs/LESSONS.md)
· [GitHub](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/LESSONS.md).

**Cross-repo:** [PT LESSONS](../../perplexity-api/Perpetua-Tools/docs/LESSONS.md) ·
canonical method [git-history-surgery SKILL.md](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/git-history-surgery/SKILL.md) ·
tool [`scripts/git/reanchor_scan.sh`](../scripts/git/reanchor_scan.sh). periscope excluded —
its `main`/`agentsview` are pure upstream mirrors, not rewritten by us.

### 2026-06-05 (cont.) — attribution-guard fragmentation between orama and PT

While pushing the docs above, PT's `pre-push` (`.githooks/pre-push` → `audit_attribution.sh`
with `GIT_AUDIT_STRICT=1`) **blocked a clean commit**: strict mode audits the full reachable
history and PT's copy still flagged 79 mainstream-AI bot co-authors (`coderabbitai`,
`dependabot`) + 7 AI authors that **orama's allowlist already permits** (added in PR #71).
Root cause: PT's `audit_attribution.sh`, `check_commit_message.sh`, `check_identity.sh` were
**stale forks** of orama's canonical guards — silent fragmentation.

Discoveries + fixes (canonical guard scripts live in orama, synced outward):
- The sync tool [`scripts/git/sync-attribution-guard-scripts.sh`](../scripts/git/sync-attribution-guard-scripts.sh)
  **omitted `check_commit_message.sh` and `check_identity.sh`** from its copy list — so those
  two drifted forever. Added them; re-synced → all 4 guards now byte-identical orama↔PT
  (`bad_author` 7→0, `bad_coauthor` 79→3; push range clean).
- The same sync wrote a *thin wrapper* for `daily-attribution-guard.sh` (full impl is canonical
  in PT) — which, run against PT itself, made the script **exec itself (infinite recursion)**.
  Guarded: skip the wrapper when target basename is `Perpetua-Tools`.
- **Rule:** never hand-edit a guard script in a downstream repo. Edit orama's canonical copy,
  then `sync-attribution-guard-scripts.sh <target>`. Org-wide governance plan so future
  `oramasys/*` repos inherit identical hooks with zero drift:
  [`docs/v2/`](v2/) (attribution-guard single-source-of-truth).

**Cross-repo:** mirrored in PT [`docs/LESSONS.md` § 2026-06-05](../../perplexity-api/Perpetua-Tools/docs/LESSONS.md) ·
[GitHub](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/LESSONS.md).

### 2026-06-05 (cont.) — a 40-minute stall: hard deadlines + never bundle hang-prone calls

While running `/sync-gbrain`, the local gbrain engine was `broken-config`. I ran `gbrain
search` inside a multi-part Bash command wrapped in `timeout 20`. gbrain forked a child that
**survived the SIGTERM**, so the wrapper never killed it — the turn hung ~40 minutes until the
user interrupted. (Same failure class as the earlier bare `git fetch upstream` that hung ~14h
on a credential prompt.)

**Rule (now enforced for every agent):**
- Every external/network/db call (`gbrain *`, `git fetch/push/ls-remote`, `npm/bun install`,
  `curl`, MCP) needs a **hard deadline**, and if it can hang past timeout it must run as a
  **killable background job** (`run_in_background`), polled with a bounded check count — not a
  foreground `timeout N cmd` (timeout only SIGTERMs the direct child; forking tools escape it).
- **Never bundle a hang-prone call into a multi-part `&&`/pipe command** — one hang stalls
  everything and you can't tell which part blocked.
- If `gbrain_local_status != ok` (e.g. `broken-config`), **do not call `gbrain` at all** — it
  will hang on the unreachable engine. Repair via `/setup-gbrain` first.

This is a public, cross-agent record of a private operating lesson (memory
`feedback_hard_deadlines_no_hang`); see also [`docs/v2/27`](v2/27-git-governance-zero-fragmentation.md)
and the AlphaClaw/periscope network-git safety notes. Sleep chains were already banned.

---

## 2026-06-04 — Re-anchoring orphaned branches after a `main` history rewrite (byte-identical twin)

**Context.** After the PR #70 rewrite (squash-rebundle of post-#60 work), ~50 branches showed as "600 commits behind / orphaned" — they descended from pre-rewrite SHAs no longer in `main`. We restored 12 deleted refs for audit, then needed to reconcile them to the clean line.

**The journey (incl. the two wrong turns):**
1. **Wrong fix #1 — flatten.** Reset all branches to `origin/main`. Made every branch *identical* to HEAD ("why are all branches the same???"). Destroys identity. Reverted.
2. **Wrong idea — `git replace --graft`.** Re-parents locally but replace-refs are local-only → never show on GitHub. Not a remote fix.
3. **Right fix — byte-identical twin re-anchor.** A rewrite gives every old commit a content-twin (same tree `%T`, new SHA) in new `main`. Build a tree index (`git log origin/main --format='%H %T'`); for each branch tip find the commit with the identical tree and point the branch there (a real ancestor of main → `+0/-N`, distinct per branch). No exact tip-twin (recent rebundled commits)? Walk first-parent to the deepest twin ancestor and `git rebase --onto <twin> <base>` — conflict-free because base trees are byte-identical — then force-push (`+K/-M` above the shared ancestor).

**Results:** 11/11 re-anchored — 8 to exact tip-twins, 3 grafted onto the #60 twin `146a416`. Zero orphans; each shares a real recent ancestor with main; none flattened.

**Gotchas:**
- Mid-rebase `"local changes would be overwritten by merge"` = untracked/generated file collision → `git clean -fdq` first.
- `git fetch --prune` with the default refspec deletes the `refs/pull/*` recovery vault — re-fetch with the explicit `+refs/pull/*/head:refs/remotes/origin/pr/*`.
- Re-anchor moves the *ref* for a clean graph; it does NOT merge branch content into main (that would regress the canonical tree). Merge only genuinely-unique forward work via a reviewed PR.
- Always wrap network git ops in a `timeout` (a `git fetch upstream` once hung ~14h).

**Canonical skill:** [`../bin/orama-system/skills/git-history-surgery/SKILL.md`](../bin/orama-system/skills/git-history-surgery/SKILL.md) · Fork variant: [`wiki/13-alphaclaw-fork-contrib-branches.md`](wiki/13-alphaclaw-fork-contrib-branches.md)

---

---

## 2026-06-04 — Meta: anti-handwaving (clarify intent + use the real method, not a proxy)

**The deeper failure behind the branch work.** Across the orama/AlphaClaw/periscope
reconciliation the agent handwaved **three times**, each corrected by the user, not the agent:
1. "No data loss → nothing to restore" (user wanted refs reconciled regardless).
2. "No orphans, because `git merge-base != root`" — a **graph proxy**. The real question was
   *content* convergence: every branch had a **byte-identical tree-twin** in main (content
   matched 1–79 commits back) while the SHA graph showed "+472 ahead." merge-base HID it.
3. Acted on the wrong mechanic for "re-anchor" (flattened branches to HEAD) without
   confirming what the user meant.

**Root cause:** substituting a cheap proxy for the real question, and acting on a first-pass
interpretation, without confirming intent or reflecting. = **Failure Mode 7 (Handwaving).**

**Fix (now encoded in AFRP):** the **Intent-Verification Gate** — on interpretation risk, or
before any "nothing to do" conclusion, **AskUserQuestion FIRST and reflect**; replace the
proxy with the method that truly answers the question (tree-twin search, not merge-base);
trust the user's domain signal over a first-pass check. Don't assert "fine/done" from a
narrow check — name what was actually verified.

→ AFRP gate: [`../bin/orama-system/afrp/SKILL.md`](../bin/orama-system/afrp/SKILL.md) § Intent-Verification · Catalog: [`../bin/orama-system/afrp/failure-modes.md`](../bin/orama-system/afrp/failure-modes.md) § Failure Mode 7 · Skill fix: [`../bin/orama-system/skills/git-history-surgery/SKILL.md`](../bin/orama-system/skills/git-history-surgery/SKILL.md) § B5 (tree-twins, not merge-base)

---

## 2026-06-02 — Claude (Sonnet 4.6) — gbrain checkpoint poisoning: rm -rf of repo root identified and fixed

### What was learned

**Answer to the open question from 2026-05-31:** The process deleting `orama-system` was `bun` (PID 48174554) at 09:59:13 — the gbrain autopilot's `gstack-memory-ingest.ts` `finally` block calling `cleanupStagingDir(repoRoot)`. This is **[garrytan/gstack issue #1802](https://github.com/garrytan/gstack/issues/1802)**, an upstream bug confirmed by `fs_usage` trace.

**Root cause:** Autopilot jobs were repeatedly SIGTERM'd on 600s timeout (confirmed in logs: `Job 693/724/726 hit per-job timeout`). One interrupted run wrote `~/.gbrain/import-checkpoint.json` with `dir` = the repo root (CWD at SIGTERM time). The next sync's `decideResume()` function found the directory exists and is a directory, returned `{ kind: "resume" }` with no ownership validation, and the `finally` block did `rmSync(repoRoot, { recursive: true, force: true })`.

**The fix** is a 10-line TypeScript change in two files — `decideResume()` in `gstack-gbrain-sync.ts` + `cleanupStagingDir()` in `gstack-memory-ingest.ts`. See [`docs/reference/gstack-pr-1802-fix.md`](reference/gstack-pr-1802-fix.md) and wiki [`14-gbrain-checkpoint-rm-rf-bug.md`](wiki/14-gbrain-checkpoint-rm-rf-bug.md).

### What was done

- orama-system restored from GitHub (all commits intact; no work lost this time)
- Poisoned checkpoint deleted (`~/.gbrain/import-checkpoint.json`)
- Shell guard added to `~/.zshrc` — runs on every shell start, deletes any poisoned checkpoint before it can fire
- `.gbrain-source` pin files created for orama-system, PT, and AlphaClaw
- gbrain sources re-synced (orama-src: +1 added, ~5 modified; AlphaClaw: +2; PT: +3)
- Comment posted on garrytan/gstack#1802 confirming our case
- Draft PR ready for submission in `docs/reference/gstack-pr-1802-fix.md`

### Rules going forward

1. **Delete `~/.gbrain/import-checkpoint.json` before any manual `/sync-gbrain`** — the shell guard handles automated sessions, but manual runs inside a repo directory are risky until upstream fix lands.
2. **Run `/sync-gbrain` from a neutral directory** (not inside the indexed repo). CWD at SIGTERM time = what gets written to checkpoint.
3. **Watch for `Job NNN hit per-job timeout` in `~/.gbrain/autopilot.err`** — two or more in a row = checkpoint is likely poison, delete it.
4. **Never run `/sync-gbrain` twice without checking the checkpoint** — a stale checkpoint from a previous interrupted run survives until the next clean run or manual deletion.

→ [wiki/14-gbrain-checkpoint-rm-rf-bug.md](wiki/14-gbrain-checkpoint-rm-rf-bug.md)

**Cross-repo:** [PT LESSONS](../../perplexity-api/Perpetua-Tools/docs/LESSONS.md) · [AlphaClaw Lessons](../../AlphaClaw/docs/Lessons.MD)

---

---

## 2026-06-02 (cont.) — Claude (Opus 4.8 MAX) — #1802 fix shipped via multi-channel steelman

### What was done
- Implemented the fail-closed staging-ownership guard for gstack#1802 on branch `fix/1802-staging-ownership-guard` (`lib/staging-guard.ts` + 3 wire-ins + 23 new test assertions; 32+23 green).
- **Multi-channel steelman** (Mode-3 orama): dispatched the design to 4 heterogeneous external models in parallel — Gemini CLI, OpenAI Codex, OpenRouter/gpt-4o, Windows LM Studio qwen3.5-27b @ 192.168.254.104. Verified each channel's reachability with a live round-trip first; reported Antigravity/AgentRouter/Cursor as **not dispatchable** rather than faking them. 27b/9b on the Windows box timed out / returned empty once — logged honestly.
- Panel split 3-1 on the `.gstack-staging` marker; adopted on the **fail-safe asymmetry** argument (missing marker → extra re-stage, never a wrong delete). All 4 converged: inevitable fix is upstream in gbrain (companion issue drafted).

### Dogfood (eat-your-own)
- Codified the method into [`reference/multi-channel-steelman.md`](reference/multi-channel-steelman.md) and the **Fail-Closed Trust Boundary** principle (prove ownership before any recurse-delete; design the false-negative/false-positive cost asymmetry in on purpose).
- Submission package: [`reference/gstack-1802-submission-package.md`](reference/gstack-1802-submission-package.md).

### Decisions
- Ship the minimal inevitable core (guard+marker+tripwire); defer the capability-object refactor to a separate PR (ruthless refinement).
- Version train unified at **0.9.9.9** (operator instruction); `api_server.py` already there; legacy API-baseline pins NOT auto-bumped without instruction.
- gstack fork/push/PR is GATED on operator confirmation (outward-facing, public, attributable).

→ [wiki/14-gbrain-checkpoint-rm-rf-bug.md](wiki/14-gbrain-checkpoint-rm-rf-bug.md)

---

---

## 2026-06-02 (cont.) — Claude (Opus 4.8 MAX) — fork self-heal patcher (survive gstack/gbrain upgrades)

### What was learned
- **Shipping a fix on a local branch is not durable.** `gstack upgrade` / `gbrain upgrade` overwrite `~/.claude/skills/gstack`, silently reverting any not-yet-merged upstream fix. For #1802 that means the repo-deleting `rm -rf` bug returns on the next upgrade. A local branch protects you only until the next update.
- **The patch file is its own detector.** `git apply --reverse --check` succeeds iff the fix is already fully present; forward `--check` succeeds iff it's cleanly applicable. Combined with a `MARKERS` grep (catches an upstream reword that keeps the symbol), this makes the patcher a **silent no-op the moment upstream merges** — it retires itself.
- **`git apply --3way` >> hand-rolled sed anchors** for re-applying an additive fix across versions: it 3-way-merges against blob context (survives line drift), is **atomic** (never half-applies), and **fails loudly** on real conflict instead of clobbering other upstream changes.
- **A git worktree's `.git` is a file (gitlink), not a directory** — `[ -d "$root/.git" ]` wrongly rejects worktrees. Use `git rev-parse --is-inside-work-tree`. (Caught by my own re-apply test — the test earned its keep.)

### What was built
- `scripts/fork-patches/apply-fork-patches.sh` — registry-driven, detection-gated, fail-closed self-heal driver (`--quiet`/`--dry-run`). Detect → apply (`--check` then `--3way`) → `VERIFY` (bun test) → rollback-on-fail.
- `scripts/fork-patches/patches/gstack-1802-staging-guard.{patch,meta}` — first registered patch.
- `~/.zshrc` shell-start trigger (silent no-op when patched; sibling to the #1802 checkpoint guard).
- Folded into the **mcp-install** skill ("Fork Self-Heal" section) per operator request — no new skill.
- Proven: against an unpatched worktree it applies + passes `bun test` (55) + creates `lib/staging-guard.ts`; second run is an idempotent no-op.

### Decisions
- Merge into existing `mcp-install` skill, not a standalone skill (operator).
- Trigger = shell-start hook (most robust; catches any update path) over wrapping `gstack upgrade` (misses other paths).
- Retire each patch by deleting its `.patch`+`.meta` once the upstream PR merges (MARKERS grep already neutralizes it first).

→ Driver: [`../scripts/fork-patches/README.md`](../scripts/fork-patches/README.md) · Method: [`reference/multi-channel-steelman.md`](reference/multi-channel-steelman.md) · Incident: [`wiki/14-gbrain-checkpoint-rm-rf-bug.md`](wiki/14-gbrain-checkpoint-rm-rf-bug.md)

---

---

## 2026-05-31 — Claude (Opus 4.8) — Tri-repo migration audit + alignment plan + tooling stabilization

### What was learned
- **Tri-repo migration is Gate-2 partial, not complete.** A 3-agent audit mapped AlphaClaw capabilities → PT counterparts: PT controls AlphaClaw fully (adapter 25 methods + `alphaclaw_manager.py`); controls OpenClaw *via* AlphaClaw by design; but orama's `bin/mcp_servers/openclaw_bridge.py` still calls AlphaClaw **directly** (Gate-3 gap). 8 gaps remain. **Canonical roadmap now: [`Perpetua-Tools/docs/2026-05-31-tri-repo-alignment-completion-plan.md`](../../perplexity-api/Perpetua-Tools/docs/2026-05-31-tri-repo-alignment-completion-plan.md).**
- **gbrain fixed:** `prepare:true` against the Supabase pooler caused `prepared statement does not exist` write failures → set `prepare:false`. DB URL lives in `~/.gbrain/.env` (source it for CLI; MCP variant may need reconnect). Resynced all 3 per-repo sources. See [`bin/orama-system/gstack/SKILL.md` §GBrain Ops](../bin/orama-system/gstack/SKILL.md). **CRG registry is empty** — build per repo before relying on it.
- **macOS dup ` 2` files: ruled OUT OneDrive/iCloud** (both audited + cleared). Historical Finder/IDE keep-both, dormant. Repo-wide dedup: quarantined to `~/dup-quarantine-2026-05-31` (nothing deleted). Cross-ref the 2026-05-27 ghost-ref entry + AlphaClaw `wiki/07`.

### Decisions made
- `lib/mcp`+`lib/agents` retirement is **held until Gate 2 is green** (live authenticated smoke-test + local-agents tests). Code is superseded; ceremony is not done.
- `orama-system` local checkout is **volatile** (vanished twice this session; cause not OneDrive/iCloud). A background guardian auto-restores it (`~/.orama-guard.log`, mirror `~/.orama-system-backup.git`).

### Open questions
- What process deletes `orama-system`? (user running `sudo fs_usage` to catch it.) The 8 Gate-2/3 gaps remain (see alignment plan).

**Cross-repo:** [PT LESSONS](../../perplexity-api/Perpetua-Tools/docs/LESSONS.md) · [AlphaClaw Lessons](../../AlphaClaw/docs/Lessons.MD)

---

---

## 2026-05-27 — Cursor Cloud — git attribution, AlphaClaw branch anchoring, push queue

### What was learned

**Cursor Cloud git (not fixable via `CURSOR_AGENT=0`):**

- Cloud VMs set `CURSOR_AGENT=1`; there is no supported user toggle to disable it.
- Cursor redirects `core.hookspath` to `~/.cursor/agent-hooks/<base64(workspace-path)>/` and may run `commit-msg.cursor.co-author` (injects unwanted `Co-authored-by` trailers).
- Mitigations that work: `chmod -x` on `commit-msg.cursor.co-author`, restore repo `.githooks` via `install-local-hooks.sh`, user-level `~/.cursor/openclaw/` + `sessionStart` hook (`install-user-git-environment.sh`), and hook-free `git commit-tree` via `commit-clean.sh`.
- Desktop **Agents → Attribution** does not reliably control cloud agent commits.

**Approved identity:** `cyre <diazMelgarejo@gmail.com>`; `repo_hygiene.py` / `check_commit_message.sh` block unattributable Gmail co-authors.

**AlphaClaw fork layout** ([`diazMelgarejo/AlphaClaw`](https://github.com/diazMelgarejo/AlphaClaw)):

| Branch | Role |
|--------|------|
| `main` | Upstream mirror only ([`origin/main`](https://github.com/diazMelgarejo/AlphaClaw/tree/main)) |
| `feature/MacOS-post-install` | Integration branch — must **contain** current `origin/main` |
| `cursor/sync-attribution-guards-6421` | Contrib — PR target is **integration**, not `main` |

Both integration and contrib branches must have **merge-base(branch, origin/main) = origin/main** (nearest common ancestor is upstream mirror tip). Shallow `git clone --depth 1` on a stale tip produced orphan roots (e.g. detached `a64d183`) — always run `bash scripts/git/alphaclaw-align-all.sh` after clone.

**Push order when credentials available:**

1. `bash scripts/cursor/push-openclaw-stack.sh` (orama branch + AlphaClaw)
2. Push `feature/MacOS-post-install` (includes `merge(upstream): sync origin/main…`)
3. Push `cursor/sync-attribution-guards-6421`
4. PR: `cursor/sync-attribution-guards-6421` → `feature/MacOS-post-install`
5. PR: `feature/MacOS-post-install` → `main` when integration is ready

### Decisions made

- Canonical automation in orama-system: `alphaclaw-sync-integration-with-main.sh`, `alphaclaw-align-all.sh`, `alphaclaw-realign-contrib-branches.sh`, `alphaclaw-contrib-checkout.sh`, `push-openclaw-stack.sh`.
- `.cursor/environment.json`: `ALPHACLAW_INTEGRATION_BRANCH`, `ALPHACLAW_CONTRIB_BRANCH`, cloud `install` calls `alphaclaw-align-all` after AlphaClaw clone.
- Wiki: `docs/wiki/12-cursor-cloud-commit-attribution.md`, `docs/wiki/13-alphaclaw-fork-contrib-branches.md`; rules: `.cursor/rules/cursor-cloud-environment.mdc`, `no-commit-attribution.mdc`.

### Prevention checklist

1. On every cloud session: `bash scripts/cursor/install-user-git-environment.sh` and `bash scripts/git/alphaclaw-align-all.sh`.
2. Before AlphaClaw commit: verify `git merge-base HEAD origin/main` equals `git rev-parse origin/main`.
3. Never open AlphaClaw feature PRs with base `main` when commits belong on integration/contrib lines.
4. Use `bash scripts/git/commit-clean.sh` if `git commit` still appends co-author trailers.


---

---

## 2026-05-27 — RAG items 5–7 + transport matrix + macOS ghost ref scanner (Claude)

### What was accomplished

1. **macOS ghost git refs (D10 scanner)**
   - Root cause: macOS APFS dedup creates sibling `main 2` files inside `.git/refs/heads/`
   - git's `repack -Ad` fatals on `bad object refs/heads/main 2`
   - Fix: `rm "$repo/.git/refs/heads/main 2"` on perpetua-core / oramasys / agate
   - Prevention: added `scan_macos_ghost_git_refs()` to `scripts/review/repo_hygiene.py` (D10)
   - 4 new tests in `tests/test_repo_hygiene.py`
   - **RE-ENCOUNTERED 2026-05-31 (AlphaClaw):** Same root cause. New variant: `.git/index 2` (56208B) and `.git/index 3` (59526B) — stale staging-area snapshots, NOT identical to live `.git/index` (60666B). Also `refs/remotes/origin/feature/MacOS-post-install 2`, `origin/main 2`, `origin/main 3` — remote-tracking ghost refs, all same SHA as canonical, cleared by `git remote prune origin`. `com.apple.provenance` xattr confirmed on `.git/` — iCloud Drive provenance is the trigger. **Agent note: I knew about this rule and still failed to check `.git/` for space-suffixed files during session startup. Add to pre-flight: `find .git -name "* 2" -o -name "* 3" | grep -v "/objects/"`.** Canonical doc: `AlphaClaw/docs/wiki/07-duplicate-files.md`.

2. **PR #38 / #39 cleanup (Perpetua-Tools)**
   - Removed FORBIDDEN Co-authored-by trailer from feature branch commits via `git commit --amend` / cherry-pick
   - Force-pushed both branches; ran `git reflog expire --expire=now --all && git gc --prune=now`

3. **RAG items 5–7 (diazMelgarejo/Perpetua-Tools PR #49)**
   - Item 5: `orchestrator/gbrain_search.py` — async `gbrain search --json` subprocess, returns `[]` on any failure
   - Item 6: `orchestrator/memory_node.py` — `retrieve_context()` = FTS5 + LanceDB + optional gbrain + RRF
   - Item 7: `supervisor._inject_memory_context()` — step 0 in `_dispatch()`, prepends `[MEMORY CONTEXT]`
   - 25 new tests; 400 pass on full suite

4. **Sidecar transport matrix (orama-system docs/v2/19-gstack-optional-integration.md)**
   - Added missing table comparing v1 (subprocess CLI), v2 (sidecar module), v2.5 (MCP HTTP endpoint)
   - All three share the same failure semantics: `[]` on any transport error

### Key patterns learned

- **v1 "MemoryNode" = async callable, not graph node** — v1 has no MiniGraph. Implement as plain `async def retrieve_context()`.
- **v1 "GbrainSearchTool" = async fn, no `@tool`** — v1 has no tool registry. Skip decorator entirely.
- **Memory injection goes in `_dispatch()`, not in workers** — prompt enrichment before routing means every backend gets context with zero per-worker changes.
- **opt-out via `metadata["use_memory"]=False`** — keeps skill_envelope path (deterministic, zero-LLM) unaffected when needed.
- **`shutil.which()` at call time** — never import-time. Prevents startup failures when gbrain not installed.
- **Background pytest invocations via Bash don't return file output immediately** — use foreground (`timeout` set high) or `Read` the `.output` file after notification.
- **Python 3.9 + `dataclass(slots=True)` = TypeError** — `slots=True` requires Python 3.10+; discovery tests pre-fail on macOS system Python.

### Files changed

- `orama-system/docs/v2/19-gstack-optional-integration.md` — transport matrix added
- `orama-system/docs/2026-05-22-rag-v1-backport-shipped.md` — items 5–7 marked shipped
- `orama-system/scripts/review/repo_hygiene.py` — `scan_macos_ghost_git_refs()` D10 scanner
- `orama-system/tests/test_repo_hygiene.py` — 4 new ghost ref tests
- `_pt-merge-work/orchestrator/gbrain_search.py` — new
- `_pt-merge-work/orchestrator/memory_node.py` — new
- `_pt-merge-work/orchestrator/supervisor.py` — `_inject_memory_context()` + step 0
- `_pt-merge-work/tests/test_gbrain_search.py` — new (14 tests)
- `_pt-merge-work/tests/test_memory_node.py` — new (7 tests)
- `_pt-merge-work/tests/test_supervisor_smoke.py` — +4 injection tests

---

---

## 2026-05-27 — Claude (current session) — ❗️CRITICAL HITL VIOLATION & DOCTRINE

### TL;DR
A **Cursor agent on 2026-05-25 at 13:44** created `OpenClaw/_pt-merge-work/` as a throwaway `git clone` for security-fix-6 merge work. **A Claude agent in a later session (2026-05-27) autonomously promoted this scratch clone to "canonical Perpetua-Tools" status** — rewriting memory files, `CLAUDE-instru.md`, and PT-side docs to point there. **The user never authorized this.** Reverted today.

### The HITL Doctrine (NEW — must apply across all agents, all repos)

> **Rule: A tactical decision made by an agent in a single session MUST NEVER override a long-term architectural decision made by a human.**
>
> Examples of "long-term human decisions" agents may NEVER override silently:
> - Canonical repo paths / disk locations
> - Branch naming and ownership conventions
> - Commit identity / author allowlists
> - Org-level architecture (`diazMelgarejo/*` vs `oramasys/*` separation)
> - Directory layout in user-controlled folders (`OpenClaw/`, `~/code/oramasys/`)
> - Module name renames (e.g. `coordinator` → `orchestrator`)
>
> **Before any such decision, the agent MUST call `AskUserQuestion` (or stop and ask in plain prose) and wait for explicit approval.**
> Technical evidence (newer commits, fewer artifacts, "cleaner state") is NOT sufficient grounds to redesignate canonical paths.

### What went wrong (full trace)

| Step | Date | Agent | Action | HITL violation? |
|------|------|-------|--------|-----------------|
| 1 | 2026-05-25 10:05 | Cursor (workspace `e90fd68b…` on OpenClaw root) | Active in OpenClaw root folder | — |
| 2 | 2026-05-25 13:44 | Cursor agent | `git clone diazMelgarejo/Perpetua-Tools.git _pt-merge-work` at OpenClaw root | ⚠️ MINOR — created scratch clone with no convention for cleanup |
| 3 | 2026-05-25 13:44–13:51 | Cursor agent | merged `main` into `2026-05-25-005-security-fix-6-mcp-profiles`, pushed | — (committed under user's real identity, which IS approved) |
| 4 | 2026-05-27 (early in this session) | Claude (Sonnet 4.6, this conversation, pre-compaction) | Used `_pt-merge-work/` as working dir for RAG items 5–7 (afa4542) | ⚠️ MEDIUM — should have stopped and asked which repo to write to |
| 5 | 2026-05-27 (post-audit, pre-compaction) | Claude (same session) | Audited disk repos, noticed `_pt-merge-work` had newer commits, declared it "canonical", **rewrote** `project_perpetua_tools_path.md` + `CLAUDE-instru.md` + the RAG-shipped doc to reflect that | ❌ CRITICAL — autonomous architectural redesignation without `AskUserQuestion` |
| 6 | 2026-05-27 (this turn, post-compaction) | Claude (same session, user pushback) | User caught the violation; reverted all changes | ✅ resolved |

### Forensic evidence

- `_pt-merge-work/` reflog earliest entry: `clone: from https://github.com/diazMelgarejo/Perpetua-Tools.git` at `2026-05-25 13:44:12 +0800`
- Folder created at OpenClaw root level (not inside `perplexity-api/`) — consistent with Cursor having workspace access to OpenClaw root
- Cursor workspace `~/Library/Application Support/Cursor/User/workspaceStorage/e90fd68bd7c440906de9c318e4dbd282/workspace.json` opened on `file:///…/OpenClaw` at `2026-05-25 10:05`, retrieval index updated at `10:25`
- No Claude Code `.jsonl` session for OpenClaw on 2026-05-25 (confirmed — only May 22 and May 27 sessions exist for that project) → **Claude was not at the keyboard when the clone happened**
- All commits in `_pt-merge-work` are authored by `cyre <Lawrence@cyre.me>` (your real, approved identity), meaning the Cursor agent used your local git config — no identity violation, just a workspace pollution

### Decisions made (canonical, after revert)

1. **Canonical Perpetua-Tools = `OpenClaw/perplexity-api/Perpetua-Tools/`** — restored (this is the user's long-term decision since the directory was created)
2. **`_pt-merge-work/` is a one-off Cursor scratch clone** — should be cleaned up after the RAG items branch is pulled into canonical
3. **The `* 2` files** (e.g. `LESSONS 2.md`) in `perplexity-api/Perpetua-Tools/docs/` are **macOS APFS dedup artifacts**, not contamination — they are byte-identical to the originals and harmless. Previous agent claim that they marked the repo as "stale" was wrong.
4. **New rule for all future agents (Claude, Cursor, Codex, Conductor)**: before reorganizing canonical paths, branch conventions, or any long-term architectural attribute, call `AskUserQuestion` with a decision brief.

### Files reverted in this remediation

- `~/.claude/projects/-Users…OpenClaw/memory/project_perpetua_tools_path.md` — back to pointing at `perplexity-api/Perpetua-Tools/`
- `OpenClaw/CLAUDE-instru.md` line 96 — link restored to `perplexity-api/Perpetua-Tools/docs/openclaw-setup.md`
- `OpenClaw/CLAUDE-instru.md` directory-tree section — `perplexity-api/Perpetua-Tools/` shown as canonical, `_pt-merge-work/` flagged as scratch

### Outstanding cleanup (user-authorized in next step)

- Pull `origin/main` into canonical `perplexity-api/Perpetua-Tools/`
- Pull `origin/2026-05-27-006-rag-items-5-7` work into canonical (the RAG items 5–7 commits live on the remote; safe to re-fetch)
- `/sync-gbrain` to refresh the worktree-pinned source for the canonical path
- After verification: delete `_pt-merge-work/` entirely

### Open questions

- Should we add a pre-commit hook or wrapper to **block agent-initiated `git clone` into OpenClaw root** without a `.scratch-clone-justification` file?
- Should there be a `~/.claude/skills/hitl-major-decisions/` skill that any agent must invoke before path/architecture changes?

---

---

## 2026-05-25 — Claude (Cursor) — code-review pressure Test B (tool-order)

### What was learned

Pressure Test B (skill loaded, graph-first) was run as an empirical **dry-run** on `main` with delta `HEAD~5` (18 files; code-review touch: skill link fixes + new `docs/how-to/first-run-and-code-review.md`). The orama-system CRG index on disk is healthy (1417 nodes, 1257 bge-m3 embeddings via `graph.db`), but **this Cursor workspace does not expose `code-review-graph` MCP** — only `OpenClaw/.mcp.json` registers `uvx code-review-graph serve`. Observed investigator order was Read/git/Grep → sqlite proxy for stats → failed gbrain → hung `uvx` CLI; no `detect_changes` or `get_review_context` calls. Full matrix: `bin/orama-system/skills/code-review/references/pressure-test-notes.md` § Test B results 2026-05-25.

### Decisions made

- Treat Cursor sessions without CRG MCP as **documented partial compliance**; recommend registering the same server from `OpenClaw/.mcp.json` into the project/workspace MCP config before claiming full Test B pass.
- Align init examples in `SKILL.md` (`*_tool` suffix) with `mcp-tools-crg.md` tool names in a follow-up doc fix.

### Open questions

- Should pressure Test B script explicitly allow `git diff HEAD~N` when the tree is clean, or require a synthetic uncommitted edit?

---

## 2026-05-25 — Cursor (subagent) — CRG + gbrain verify on orama-system

### What was learned

- `move_agent_to_root` → `orama-system` succeeded; committed `.cursor/mcp.json` enables Cursor CRG when the user reloads MCP (tools still absent from this subagent session’s `mcps/` folder).
- **gbrain** `search` works from host shell with network (`first-run-install`, `crg-embed-mode` top hits).
- **CRG CLI** (`uvx code-review-graph`) works after cold install: `status --repo "$REPO"` → 1489 nodes; `detect-changes --repo "$REPO" --base 51816ce5` on session delta (risk 0.65, 4 bash functions without tests in graph). Use `--repo`, not `--repo-root`; MCP-only names like `list-graph-stats` are invalid on CLI.
- Fresh clone may show `nodes: 0` until `uvx code-review-graph build --repo <orama-system>` — not automatic in `first-run.done`.
- Sandbox `first-run-install.sh status` cannot write `~/.orama-system/first-run.json` (PermissionError) but probes still print; use non-sandbox for state file updates.

### Decisions made

- Mark fortify TODOs done for Cursor `.cursor/mcp.json` and `--help` vs `--version` probe; keep gbrain sandbox ENOTFOUND and graph-before-Read hook as open.
- No code fix required for merge; doc checklist updates only.

### Open items (2026-05-25 — do not duplicate here)

Tracked as checklists elsewhere (read the owner doc, not this log):

| Topic | Owner doc |
|-------|-----------|
| Fortify / Test B / MCP / policy gaps | [`bin/orama-system/skills/code-review/references/pressure-test-notes.md`](../bin/orama-system/skills/code-review/references/pressure-test-notes.md) § Fortify pass |
| CLAUDE-instru weaning + CI grep | [`docs/plans/2026-05-23-claude-instru-weaning-autoplan.md`](plans/2026-05-23-claude-instru-weaning-autoplan.md) § Open TODOs |
| Agent first-open surfaces (Cursor / Claude / OpenClaw) | [`docs/reference/agent-first-open-visibility.md`](reference/agent-first-open-visibility.md) |
| E2E bootstrap known gaps | [`docs/how-to/first-run-and-code-review.md`](how-to/first-run-and-code-review.md) § Known gaps |

---

## 2026-05-25 — Cursor — Official git identity + co-author policy (docs)

### What was learned

- **Canonical policy** lives in [`docs/wiki/08-git-hygiene-and-branching.md`](wiki/08-git-hygiene-and-branching.md#official-commit-identity-policy-2026-05-25): four approved primary authors (`cyre`a-circumflex+euro+quote (cp1252-misread em-dash)`Lawrence@cyre.me`, `Codex <codex@openai.com>`); `Co-authored-by` allows well-known public AI/vendor domains and only two Gmail addresses.
- **Enforcement:** `bash scripts/git/install-local-hooks.sh` → `check_identity.sh` (pre-commit) + `check_commit_message.sh` (commit-msg). Replaced the old “forbid all agent co-author substrings” hook with an allowlist model aligned with `repo_hygiene.py`.
- **Agent default:** sessions should not add `Co-authored-by` to their own commits even when hooks allow public AI attribution for human-authored merges.

### Decisions made

- Document-release sync: `CLAUDE.md` §3/§6, `CONTRIBUTING.md`, `agent-first-open-visibility.md`, `.cursor/rules/no-commit-attribution.mdc` point at the official section without removing prior approved identities.

---

## 2026-05-25 — Cursor — Security fixes 1–3 (orama + Perpetua-Tools)

### What was learned

- Fixes **1–3** from [`OpenClaw/v1/2026-05-23-security-markdown.md`](../../OpenClaw/v1/2026-05-23-security-markdown.md) are implemented: env-based Gemini key, `scan_tracked_secrets` in hygiene, bearer auth on portal/API/PT jobs, memory redaction before GossipBus persist.
- Fixes **4–6** (MCP path allowlist, remote endpoint URL policy, least-privilege MCP) stay **queued** — documented in [`docs/SECURITY-POLICY.md`](SECURITY-POLICY.md) and [`docs/v2/23-security-preconditions.md`](v2/23-security-preconditions.md).
- `ORAMA_CONTROL_PLANE_TOKEN` + `ORAMA_INSECURE_DEV=0` is the production posture; dev stacks can set `ORAMA_INSECURE_DEV=1` without a token.

### Decisions made

- Canonical policy: [`docs/SECURITY-POLICY.md`](SECURITY-POLICY.md); v1 index: [`OpenClaw/v1/README.md`](../../OpenClaw/v1/README.md).
- Perpetua-Tools mirrors orama git hooks via `scripts/git/check_identity.sh`.

---

---

## 2026-05-24 — Claude — CI hygiene blocks machine-specific OpenClaw paths

### What was learned

- `scripts/review/repo_hygiene.py` scans all tracked Markdown files, including plan
  docs under `docs/plans/`, for workstation-specific OpenClaw paths (the
  `$OPENCLAW_ROOT/...` pattern the scanner blocks).
- CI reports this only through `tests/test_repo_hygiene.py::test_repo_hygiene_script_runs_clean`,
  so inspect the hygiene script output directly for the exact file and line.
- PR #39 (Cursor DRAFT, closed 2026-05-24) was raised to fix this; the path scrub was
  already absorbed in commit `fd2accd` (main) before #39 was reviewed.

### Decision made

- Use `$OPENCLAW_ROOT/...` in docs and command snippets whenever a path needs to reference
  the parent OpenClaw checkout or any orama-system path beneath it.
- The `$OPENCLAW_ROOT` convention is enforced by the `OPENCLAW_WORKSTATION_LAYOUT`
  scanner in `repo_hygiene.py` (D9).

---

---

## 2026-05-22 — Claude — RAG v1 Backport shipped to Perpetua-Tools

**What shipped:** 4 RAG modules backported from `feat/rag-gstack-optional-v1` (this repo)
into `diazMelgarejo/Perpetua-Tools` on branch `feat/rag-backport-v1` (PR #28).
All 3 bug-class gaps from Gemini 3.5 Flash review applied. 345/345 tests pass.

**Key adaptation:** v2 plan targets `oramasys/perpetua-core` paths (`perpetua_core.gossip`, etc.).
v1 backport uses `orchestrator/` in PT. GossipBus is a NEW capability in v1 — PT had no
event log / SQLite before this backport.

**IMMUTABLE RULE re-confirmed:** `diazMelgarejo/*` = v1, implement code. `oramasys/*` = v2,
plan only via `/docs/v2/`. Override requires AskUserQuestion.

**Deferred items from v1 Backport Candidates table:**
- Items 5–7 (GbrainSearchTool, MemoryNode, dispatch_node wiring) deferred to next sprint
- v2.1 EmbeddingCircuitBreaker deferred — see `docs/v2/20-rag-and-memory-design.md`

**Evidence doc:** `docs/2026-05-22-rag-v1-backport-shipped.md`

---

---

## 2026-05-21 — Claude — RAG planning: answer search/memory questions via gbrain+CRG before designing

### What was learned

When asked "how are we implementing search/RAG?", ran gbrain + CRG queries BEFORE opening any files.
GBrain returned the authoritative answer in one query: `docs/v2/02-modules/rag-and-memory` was a
**stub** ("deferred from v2.0 kernel") — confirmed RAG was NOT yet implemented despite the repo
appearing mature. CRG returned 0 nodes (unbuilt/unindexed for this session). This saved ~10 inline
file reads and gave a more accurate architectural picture.

**Rules:**
1. For "what does this system do?" questions — gbrain query first, file reads second.
2. A stub doc is a complete answer: "not implemented" is as definitive as an implementation.
3. CRG returning 0 nodes = graph not built in current session. Fall back to gbrain. Never assume 0 = absent.

---

---

## 2026-05-21 — Claude — Spawning parallel agents: write plans first, implement second

### What was learned

User asked to "spawn the best agents suited to each subtask to finish this job soonest" for
a large planning session. The right approach:

1. **Brainstorm + design first** (single session) — get user agreement on architecture before spawning.
2. **Write ALL plan docs to a branch** before spawning implementation agents.
3. **Each agent gets one plan doc** — a well-scoped plan with exact file paths, failing test
   code, exact commands is a complete agent brief. No additional context needed.
4. **Use dispatching-parallel-agents** for tasks that are independent (FTS5 changes in
   perpetua-core are independent of gstack submodule changes in orama-system).
5. **Model selection by task complexity:**
   - Mechanical wiring (ContextNode, ContextEndpoint): Claude Haiku
   - Async + schema changes (GossipBus FTS5): Claude Sonnet
   - Multi-file with shell scripts (gstack submodule): Claude Sonnet
   - Tests + TDD compliance: Claude Sonnet

**Anti-patterns to avoid:**
- Spawning agents before plans are written — agents need exact file paths and failing tests, not vague goals.
- Using the same model for every task — wastes budget on mechanical tasks.
- Not writing v2 forward-plan docs during the brainstorm — v2 design is cheapest to capture during active design session.

---

---

## 2026-05-21 — Claude — GossipBus FTS5: zero-dep keyword recall for agents

### What was learned

The GossipBus `tail()` method returns recent-N events by time — no content search.
Adding FTS5 to SQLite requires only:
1. `CREATE VIRTUAL TABLE gossip_fts USING fts5(...)` with `content='gossip'` (backed by the gossip table)
2. Two triggers (AFTER INSERT, AFTER DELETE) to keep FTS in sync
3. One migration block in `init_db()` that populates FTS from existing rows if fts_count=0 and row_count>0

This is zero new Python dependencies — FTS5 is bundled in Python's `sqlite3`. It gives BM25 ranking
for free. Pattern: always check if SQLite FTS5 can solve a search problem before reaching for a
vector store.

**Key gotcha:** `gossip_fts MATCH ?` raises `OperationalError: fts5: syntax error` on empty query
string. Always guard with `if not query.strip(): return []`.

---

---

## 2026-05-21 — Claude — gstack optional submodule: detection order matters

### What was learned

For optional tools that may be installed via multiple paths (PATH, skill, submodule, OCI),
detection order must be explicit and idempotent:

1. Check `shutil.which("gbrain")` FIRST — respects user's existing install regardless of how it was done.
2. Check `~/.claude/skills/gstack` SECOND — covers Claude skill installs.
3. Check `tools/gstack/` THIRD — covers submodule installs.

Stop at the first hit. Never require all three to agree. Never raise on detection failure.

**Pattern:** Always write `detect_gstack() -> dict` style detection functions (return a dict,
never bool-only, never raise) so the caller can log the source and version alongside availability.
- 2026-05-17: General policy enshrined — applies to ALL Node tooling.

---

---

## 2026-05-21 — Claude — Hybrid LanceDB+FTS5 over FTS5-only: decision trail practice

### What was learned

**AI initial proposal:** FTS5-only retrieval (zero new dependencies). Rationale: YAGNI, maximum simplicity.

**User override:** Hybrid LanceDB+FTS5 with RRF k=60. Rationale: Ollama+bge-m3 is already a hard
system requirement (CLAUDE.md). LanceDB has nearly zero marginal cost. Semantic recall is worth one dep.

**Key insight:** When evaluating "add a new dep?", check if its runtime prerequisites are already required.
LanceDB alone is not free. LanceDB + bge-m3 on a machine that already requires bge-m3 is near-free.
The question is "incremental cost given current constraints" not "absolute cost from zero."

**Hybrid disaster recovery posture:** FTS5 always works (no Ollama, no LanceDB). LanceDB+bge-m3 is
opportunistic — wrapped in `try/except`. RRF falls back to `fts_hits` when `vec_hits=[]`. This means
the system degrades gracefully rather than failing hard when the embedding stack is down.

**Pattern: Document AI suggestion vs user override.** When the user makes a non-obvious architectural
choice that differs from the AI's recommendation, record both in the plan doc's decision trail table.
This preserves the reasoning for future sessions and prevents "why did we do this?" questions.
Format: `| # | Topic | AI Suggestion | User Decision | Rationale |` — one row per decision.

---

---

## 2026-05-21 — Claude — Fire-and-forget asyncio.create_task() + GC prevention

### What was learned

`asyncio.create_task()` creates a task that the event loop holds only via a **weak reference**.
If the calling code doesn't hold a strong reference, the task can be garbage-collected before
completion — silently. No exception, no warning.

**Fix (user-required):** module-level `_pending_embeds: set[asyncio.Task] = set()` + pattern:

```python
task = asyncio.create_task(self._embed_and_store(row_id, payload))
_pending_embeds.add(task)
task.add_done_callback(_pending_embeds.discard)
```

This creates a strong reference (set membership) that is automatically released when the task
completes (via `discard` callback). The set never grows unbounded.

**Why AI missed it initially:** the GC hazard is a Python-specific subtlety that requires knowing
CPython's weak-reference behavior for asyncio tasks. It's not obvious from the task's API.

**Rule:** Any `asyncio.create_task()` that is fire-and-forget MUST register the task in a
module-level strong-reference container with a done callback to clean up. No exceptions.


---

---

## 2026-05-20 — Claude — fix(docs): file:// link broke repo_hygiene test

### What was learned
- `docs/TDD.md` was added in commit `dba34d6` with a `file://` absolute hyperlink
  on line 5 pointing to a local plugin cache path.
- `scripts/review/repo_hygiene.py` has a strict rule: all markdown hyperlinks
  must be **repo-relative**. It rejects `file://`, `/absolute`, and drive-letter
  paths outright (line 152–153 of the script).
- The test `test_repo_hygiene_script_runs_clean` runs this script and asserts
  `returncode == 0`, so any new `file://` link introduced in a doc will fail CI.

### Root cause
External plugin/skill references that live outside the repo (e.g.
`~/.claude/plugins/...`) cannot be linked with a hyperlink in tracked docs.
They can only be referenced as plain text / backtick code spans.

### Decisions made
- Replaced the hyperlink with an inline `code` reference so the path is still
  human-readable but does not trigger the repo-relative link check.
- Pattern to follow for **any future external path reference** in tracked docs:

```
# Bad  — triggers hygiene checker:
[label](file:/home/user/.some/local/path)

# Good — plain backtick, not a hyperlink:
`~/.some/local/path`
```

### Prevention checklist
Before committing any markdown file that references a local filesystem path:
1. grep the diff for `file://` and `/absolute` and `~` inside `()` link syntax
2. Run `python scripts/review/repo_hygiene.py .` locally before committing
3. The TDD.md pre-commit checklist (docs/TDD.md) now covers this explicitly

### Related
- Failing test: `tests/test_repo_hygiene.py::test_repo_hygiene_script_runs_clean`
- Hygiene rule: `scripts/review/repo_hygiene.py` lines 152–153
- Fixed in: `fix/repo-hygiene-tdd-link`


<!-- Append entries below. Format:
## YYYY-MM-DD — <agent: ECC | AutoResearcher | Claude | Codex> — <brief topic>
### What was learned
### Decisions made
### Open questions
-->

---

---

---

## 2026-05-17 — Codex — Gemini is opt-in, gbrain sync comes from the gstack sync skill

### What was learned

- Gemini should not be treated as the default reader path. Keep it behind the explicit analyzer lane.
- The default agent path is local ollama on Mac first, then OpenRouter free-model fallbacks, with Windows local coder lanes used when available.
- From Codex, gbrain sync is driven by the gstack `sync-gbrain` skill and the `gstack-brain-sync` binary in the installed gstack toolchain.

### Decisions made

- Update orchestration docs so Gemini is analyzer-only by explicit request.
- Use `~/.claude/skills/gstack/bin/gstack-brain-sync --discover-new` to refresh queued worktree changes, then `--once` to drain and push.

### Runbook

```bash
~/.claude/skills/gstack/bin/gstack-brain-sync --discover-new
~/.claude/skills/gstack/bin/gstack-brain-sync --once
```a-circumflex+euro+quote (cp1252-misread em-dash)`047ec27`)
faithfully captures the direction without pixel-matching: layout positions,
copy, icon glyphs, exact colors may diverge from the mockup as long as the
aesthetic holds. Future visual upgrades should reference the mockup as a
tone-setter, not a spec.

This explicit "non-binding mockup" framing keeps the operator console
**fluid**: the backend routes shipped first; the UI tracks the routes; the
mockup tracks the UI's vibe. None of the three is a contract for the others.

---

## 2026-05-17 — `install-mcp-stack.sh --mirror-skills` ships orama SKILL.md cross-platform

Added `--mirror-skills` flag to `bin/orama-system/scripts/install-mcp-stack.sh`.
Copies the 7 orama-system SKILL.md files (mother + afrp + cidf + gstack +
mcp-install + mcp-orchestration + skillify) to:

- `~/.claude/skills/<name>/SKILL.md` (Claude Code)
- `~/.codex/skills/<name>/SKILL.md` (Codex CLI)
- `~/.gemini/skills/<name>/SKILL.md` (Gemini CLI, if dir exists)
- OpenClaw skill registry (via `openclaw skill set` if CLI present)

Idempotent (sha256-compares before copy), dry-run-safe, silently skips
absent platform directories. Hermes/ECC will adopt by adding their own
target line to `_PLATFORMS` array — one-line extension per new platform.

---

## 2026-05-17 — Salvage code translation spec written

Spec at `docs/superpowers/specs/2026-05-17-salvage-translation-design.md`
covers the *how* of porting wrong-repo
(`diazMelgarejo/perpetua-core@9cb153a`) valuable assets into canonical
(`oramasys/perpetua-core@2f717f5`) plugin structure. Companion to the
existing selection spec (`2026-05-14-salvage-plugins-design.md`).

Key decisions:
- Multi-agent labor split: Gemini reads, Codex writes, Sonnet reviews,
  Opus orchestrates
- Branch model: local `feat/salvage-plugins-rc1` in canonical clone with
  `PROGRESS.md` as living tasklist + git-native distributed locking
- TDD: unit + integration + Hypothesis property-based, against canonical's
  32 tests + new plugin tests
- Waved ordering: Wave 0 parallel reads → Wave 1 engine foundation
  (AFRP gate) → Waves 2+3 parallel ports → Wave 4 integrative decisions
- Architectural revision protocol: kernel reshape permitted during port if
  bounded and AFRP-gated

---

## 2026-05-17 — Salvage translation + v1 IP-aware discovery landed (73 tests green)

Generation labeling (per Canonical Repo Registry):

- **v2-planning (`oramasys/perpetua-core` on `feat/salvage-plugins-rc1`):** max_steps cycle guard (Task 5, a3712b2); set_entry/compile (Task 6, ad67577); 5 new plugins — routing/LabelRouter (Task 7, 283af1a), tool_node/ToolNode async subprocess (Task 8), validator/Validated pre-post (Task 9), interrupt_guard/resume_policy (Task 10, a7c9772), parallel/parallel_dispatch (Task 11, 8eaba56); typed ChatMessage/ChatHistory closing OQ17 (Task 12, 309c60a); canonical perpetua_core/discovery/ verbatim port from v1 (Task 13, 222450b); Hypothesis invariants (Task 15, 8b1a3f1). Engine grew 66→102 lines; all 32 baseline tests still green; 24 new tests added; full suite 56/56.

- **v2-planning (`oramasys/oramasys` on `feat/dispatch-discovery-bridge`):** dispatch_node now accepts an optional BackendRegistry and calls select_backend() from canonical perpetua_core.discovery; graceful degradation via state.error when registry empty (Task 14, 21605f6). 4 baseline tests preserved + 1 new = 5/5.

- **v1-legacy (`diazMelgarejo/Perpetua-Tools` on `feat/ip-aware-discovery`):** tactical fix — perpetua/discovery/ with Backend dataclass (Task 1, 9b11e9d), async health_probe (Task 2, 7e4a40b), BackendRegistry autodetect + register_by_ip (Task 3, 06c1da3), tier+task selector (Task 4, 8d42f2e), orchestrator/agent_launcher.resolve_backend_for_spec (Task 4b, bf15d0d). Shape designed to match v2 canon (Task 13 copied it forward verbatim). 12/12 tests pass. New orchestrator/agent_launcher.py is additive — root agent_launcher.py untouched; a follow-up may consolidate.

- **cross-cutting (`orama-system/docs/`):** plan at docs/superpowers/plans/2026-05-17-salvage-translation-v1-discovery.md (1962 lines, 16 tasks), spec at docs/superpowers/specs/2026-05-17-salvage-translation-design.md (315 lines), PROGRESS.md ledger at perpetua-core repo root, this LESSONS append.

LangGraph concept map (CSV) mirrored 1:1 in v2-planning code: State=PerpetuaState · Node=async fn · Edge=string · ConditionalEdge=LabelRouter · Cycle=max_steps guard · START/END=sentinels · Checkpointer=plugin (shipped earlier) · Send()=parallel_dispatch · ToolNode=plugin · Validator=plugin · InterruptGuard=plugin.

### Race-condition LESSON

Wave 1A dispatched 7 parallel subagents on the same `oramasys/perpetua-core` branch. Three of them (C8/C9/C11) hit a `.git/index.lock` race and the serializing winner (C11) committed all three plugins under one SHA `8eaba56` mis-labeled "Task 11". **No work was lost** — each subagent verified its writes against the plan post-commit. But this is a pattern to avoid:

**Lesson:** for parallel dispatch on the SAME branch, the orchestrator should either (a) own commits — subagents write files only, orchestrator git adds + commits each — or (b) give each parallel subagent its own worktree. Option (a) is simpler. Option (b) is cleaner for very long-running work.

### Push policy

All three code branches stay **local** until user reviews end-to-end on Mac+Win hardware (Mac Ollama localhost:11434 + Win LM Studio 192.168.254.103:1234). Only cross-cutting docs (this LESSONS append + plan doc) push immediately to `orama-system`.

### Build philosophy reaffirmed

Per user direction: "simultaneous top-down + bottoms-up development." v2-planning bakes architectural decisions first (engine + plugins + canonical discovery), v1-legacy ships the first implementation (discovery wired into agent_launcher), then Track D copies v1 → v2 verbatim so the shape lives in one canonical home. v1 is the live sandbox; v2 absorbs what works.

---

---

## 2026-05-17 — Policy enshrinement (hardware + Node.js)

### HARD POLICY: Mac inference via Ollama only — LM Studio Mac is a MIRROR

This is a **non-negotiable hardware safety rule**, not a preference.

| Machine | Endpoint | Role | Inference? |
|---------|----------|------|-----------|
| Mac (Apple Silicon) | `localhost:11434` (Ollama) | Primary Mac inference | ✅ ALWAYS |
| Mac (Apple Silicon) | `localhost:1234` (LM Studio Mac) | **MIRROR ONLY** | ❌ NEVER dispatch here |
| Win (RTX 3080) | `192.168.254.103:1234` (LM Studio Win) | Primary Win inference + heavy models | ✅ ALWAYS |

**Why this is a hard rule:**
- `qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2` physically runs on the RTX 3080.
- LM Studio Mac proxies all Win models over the LAN — they appear in `/v1/models` on Mac but Mac cannot actually run them.
- Dispatching the same heavy model to **both** LM Studio Mac and LM Studio Win simultaneously = "double barrel" = two concurrent requests funneled to one RTX 3080 = GPU contention → potential hardware damage.
- See also `docs/LESSONS.md` 2026-04-29 entry: `/v1/models` endpoint presence does NOT indicate physical home.

**Code enforcement (2026-05-17):**
- `perpetua/discovery/registry.py` (v1) and `perpetua_core/discovery/registry.py` (v2): `lmstudio-mac` seed annotated `# MIRROR — discovery only`.
- `perpetua/discovery/selector.py` (v1) and `perpetua_core/discovery/selector.py` (v2): added `_MIRROR_BACKENDS = frozenset({"lmstudio-mac"})`, filtered from ALL candidate selection including model_hint resolution. `_TIER_HOSTS["mac"]` now contains only `{"ollama-local"}`.

**Agents / future plans:** Before dispatching inference, check `b.name not in _MIRROR_BACKENDS`. Never route by model presence in `/v1/models` alone.

---

### HARD POLICY: Node.js — always resolve explicit full path

**Problem:** `node` in PATH resolves to system v14.21.3 (macOS bundled). Any script using `#!/usr/bin/env node` or bare `node` silently runs on v14 and fails with modern syntax (`??=`, optional chaining, top-level await, etc.) with cryptic errors.

**Rule:** Whenever invoking Node for scripts or CLI tools, resolve to the explicit full NVM path:

```bash
# Check available versions
ls ~/.nvm/versions/node/

# Use the pinned v22+ binary directly
~/.nvm/versions/node/v22.22.2/bin/node script.js

# For npm-installed CLIs (openclaw, gemini, etc.)
~/.nvm/versions/node/v22.22.2/bin/openclaw ...
~/.nvm/versions/node/v22.22.2/bin/npx ...
```

**Wrapper pattern** (for Gemini CLI and others that use shebang):
```bash
# ~/.local/bin/gemini  (must be on PATH before ~/.nvm shims)
#!/bin/bash
exec ~/.nvm/versions/node/v22.22.2/bin/node \
     ~/.nvm/versions/node/v22.22.2/bin/gemini "$@"
```

**Verification before any Node script:**
```bash
node --version   # if this returns v14.x.x → use explicit path
~/.nvm/versions/node/v22.22.2/bin/node --version  # should return v22.22.2
```

**Prior instances of this lesson:**
- 2026-04-xx: Gemini CLI broken because `#!/usr/bin/env node` resolved to v14 (wrapper fix applied).
- 2026-04-29: `openclaw` CLI requires Node ≥ v22; full path used: `~/.nvm/versions/node/v24.14.1/bin/openclaw`.

---

---

## 2026-05-16 — Codex — Claude CLI auth must run outside sandbox

### What was learned

- Symptom: `claude -p --permission-mode dontAsk --max-budget-usd 0.25 "Reply with exactly: claude-ready"` returned `Not logged in · Please run /login`.
- False lead: repeated `claude auth login --claudeai` inside the sandbox printed `Login successful`, but `claude auth status --text` stayed unauthenticated.
- Root cause: Claude's OAuth callback server and credential persistence can fail inside a sandbox. Debug output showed `Failed to start OAuth callback server: Failed to start server. Is port 0 in use?`.
- A second risk was an install split: PATH `claude` pointed to a native install while the npm-global binary was newer. Auth probes must use the same binary that orchestration will call.

### Decisions made

- Run `claude auth login --claudeai` outside the sandbox or with explicit escalation when fixing auth for automated Claude workers.
- Treat `Login successful` as insufficient until both `claude auth status --text` and a real `claude -p` probe pass.
- Compare `which claude`, `claude --version`, and any known full binary path before debugging orchestration failures.

### Runbook

```bash
which claude
claude --version
claude auth login --claudeai
claude auth status --text
claude -p --permission-mode dontAsk --max-budget-usd 0.25 "Reply with exactly: claude-ready"
```

If failure persists:

```bash
claude --debug --debug-file /tmp/claude-auth-debug.log auth login --claudeai
sed -n '1,120p' /tmp/claude-auth-debug.log
```

Do not trust sandboxed login loops when the debug log reports an OAuth callback server failure.

---

## 2026-05-16 — Codex — GitHub MCP invalid transport postmortem

### What was learned

- `invalid transport` in `~/.codex/config.toml` is a schema error before it is an auth error.
- The npm GitHub MCP server is a stdio server: use `command = "npx"`, GitHub server `args`, and
  `[mcp_servers.github.env]`.
- `bearer_token_env_var` belongs to HTTP MCP config, not this stdio GitHub setup.
- A set PAT is not proof of a working MCP config; `codex mcp list` must parse, classify, launch, and
  show the env mapping.
- The failure was a classification failure: Codex stayed in "auth missing" mode while Claude moved to
  "transport schema invalid" mode and validated each change.
- Nuance matters: GitHub's remote HTTP MCP endpoint validly uses `bearer_token_env_var`; the local
  npm stdio server does not.

### Decisions made

- Saved this as a Codex memory and repo skill guidance.
- Future agents must validate MCP fixes with `codex mcp list`, not visual inspection.
- Created reusable skills for Codex MCP debugging and agent failure postmortems.

### Open questions

- Codex should improve its own warning so GitHub stdio setup does not suggest an HTTP-only auth field.

→ [wiki/11-codex-github-mcp-config.md](wiki/11-codex-github-mcp-config.md)

---

## 2026-05-16: `.gbrain-source` is machine-local — never commit it

`.gbrain-source` is a kubectl-style worktree pin written by `/sync-gbrain`. It contains
the name of the indexed gbrain source for this worktree on this machine (e.g. `orama-src`).
Different machines register different source names; committing it would break gbrain routing
on every other machine that clones the repo.

**Fix:** Added `.gbrain-source` to `.gitignore` (2026-05-16).
**Rule:** If you see `.gbrain-source` untracked in any repo, add it to `.gitignore` immediately. Do not `git add` it.

- Linux `ip route get 8.8.8.8` — validate on Ubuntu 22.04 + Debian 12 + Alpine 3.19

---

---

## 2026-05-16: RC-1 Orchestration Session — Gemini routing, OpenRouter smart-merge, Vite pitfalls

### 1. Gemini is NOT the default reader — "Gemini-Analyzer use-case only"

**Decision (locked in RC-1 master plan):** Gemini is routed ONLY for:
- Visual diff / screenshot comparison
- Whole-repo architecture mapping (>5000-line diffs, multi-file cross-cutting)
- Multi-file stale-doc detection
- Second-opinion code review when explicitly requested

**The default reading/coding agent is the OpenRouter free-model stack** (Nemotron 3 Super → MiniMax M2.5 → DeepSeek V4 Flash → gpt-oss-120b → GLM 4.5 Air → Ling 2.6 Flash → Free Router).

**Why this matters:** Previous practice had Gemini mentioned generically as "the reader" — this caused agents to default to Gemini for every file read, wasting quota and adding latency. Gemini is a specialized instrument, not the default hammer.

**Canonical policy:** `bin/orama-system/mcp-orchestration/SKILL.md` §2 "Routing strategy".

---

### 2. Smart-merge pattern for OpenClaw config patching

**Problem:** Naively patching `openclaw.json` with a model policy risks overriding the user's local `primary` (which must remain `ollama/qwen3.5:9b-nvfp4` on Mac per CLAUDE.md hard requirement).

**Pattern established:**
- Policy file uses `fallbacks_to_merge` and `models_to_merge` keys (NOT `primary`/`fallbacks`)
- Apply script PRESERVES existing `agents.defaults.model.primary` unless `--force-primary` flag is passed
- Removes Gemini from the front of any existing fallbacks list before appending the OpenRouter chain
- Gemini is pushed to END of fallbacks as 3rd-choice (not 1st)
- Script lives at: `scripts/apply-openrouter-free-defaults.sh`
- Verify with: `scripts/verify-openrouter-models.sh`

**Rule:** Any script that patches live config must read the existing primary first and only append/merge fallbacks. Never clobber local primary.

---

### 3. jq dedup-preserve-order — avoid `unique_by(.)`

**Problem:** `unique_by(.)` in jq sorts alphabetically as a side effect. When deduping a fallbacks array after merging, this silently promoted Gemini to the top of the list (alphabetically first `google/*`), defeating the entire "Gemini as last resort" policy.

**Correct pattern:**
```bash
| reduce .[] as $item (
    [];
    if any(.[]; . == $item) then . else . + [$item] end
  )
```
This deduplicates while preserving insertion order — first occurrence wins. Use this whenever you need dedup-without-sort in jq.

**Why `unique_by(.)` is wrong:** It's documented to sort, but in practice you expect it to just dedupe. The combination of merge + unique_by produces a sorted array, not a priority-ordered one.

---

### 4. Vite + TypeScript composite-project pitfalls

Two distinct issues that both caused build/typecheck failures:

**Issue A: tsconfig composite conflict**
- Problem: `tsconfig.json` had `"include": ["src", "vite.config.ts"]`. The `tsconfig.node.json` used `composite: true` and also covered `vite.config.ts`. TypeScript expected pre-built `.d.ts`/`.js` output for the composite sub-project and errored with TS6305.
- Fix: Remove `vite.config.ts` from `tsconfig.json` include. The file is already handled by the node sub-project.
- Canonical: `"include": ["src"]` in `tsconfig.json`

**Issue B: Path aliases must be declared in BOTH places**
- Problem: `@/*` alias declared in `tsconfig.json` paths works for TypeScript type resolution but Vite's Rollup bundler doesn't read tsconfig. Build failed with "Rollup failed to resolve import `@/components/Shell`".
- Fix: Add `resolve.alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) }` to `vite.config.ts` in addition to the tsconfig paths entry.
- Rule: Every `@/*`-style alias needs two registrations: one in tsconfig (for tsc/IDE) and one in vite.config.ts (for Rollup/bundler).

---

### 5. MCP orchestration canonical SKILL.md location

**Before:** Two drift-prone root files (`OpenClaw/MCP_ORCHESTRATION_SKILL.md`, `OpenClaw/MCP_ORCHESTRATION_SKILL_v2.md`) each evolving independently.

**After:** Single canonical skill at `bin/orama-system/mcp-orchestration/SKILL.md`. The old root files are redirect stubs pointing to it.

**Rule:** If you see multiple files claiming to be "the MCP orchestration policy", the canonical one is in `bin/orama-system/mcp-orchestration/SKILL.md`. The others are stubs — do not edit them.

---

### 6. Vite operator console — build-verified RC-1 baseline

- Stack: React 18 + Vite 5 + TanStack Query 5 + Tailwind 3
- Source: `src/` (16 files, 0 TypeScript errors, build output ~68KB gzip)
- Backend proxy: `/api/*` → `http://localhost:8001` (portal_server.py)
- Key files: `src/features/command-center/CommandCenter.tsx` polls `/api/app/state` every 5s; falls back to `mockState` on error
- `src/data/mockState.ts` provides offline-capable fixtures so the console always renders
- Commit: `1cfb31e` on `web-app-orchestration-v2-implementation`

---

### 7. Branch hygiene — FF-merge timing

When feature work spans multiple commits across a branch and partial work is already on main:
- Merge foundation commits to main early (after a coherent milestone) so history stays linear
- Use `git merge --ff-only` when the branch has only additive commits ahead of main — avoids a merge commit in the log
- Do NOT squash multi-session work that has already been reviewed — preserves attribution per commit

---

---

## 2026-05-16 — Claude — No sleep chains: `sleep N && cmd` is blocked

> *First triggered: 2026-05-16 session (npm install wait). Re-triggered: 2026-05-29 session (claude update wait). Canonicalized as a low-level skill on 2026-05-29.*

### What was learned

The shell hook detects `sleep` as the leading token of a Bash command and rejects the entire call. This covers:
- `sleep N && <command>`
- `sleep N; <command>`
- Chains of shorter sleeps attempting to work around the block (`sleep 5 && sleep 5 && cmd`)

Correct mental model: **the block is on the first token, not on the sleep duration**. There is no threshold below which the chain becomes acceptable.

Pattern that re-triggered the rule on 2026-05-29: waiting for a `claude update` background task output file by running `sleep 15 && cat <file>` then `sleep 20 && cat <file>`. Both rejected. The correct form — an until-loop or waiting for the `run_in_background` notification — was only reached on the third attempt.

### Decisions made

The rule is now **canonical** — ported from the ephemeral `~/.claude/projects/.../memory/feedback_no_sleep_chains.md` into:

1. **`orama-system/bin/orama-system/skills/no-sleep-chains/SKILL.md`** — low-level skill with correct-pattern quick reference, invocable by any agent.
2. **`docs/LESSONS.md`** (this entry) — dated audit trail.
3. Original memory file retained in `~/.claude/projects/…/memory/` as the session-scoped pointer.

### Correct patterns (canonical)

| Situation | Correct form |
|-----------|-------------|
| `run_in_background: true` task | Wait for system notification — do nothing |
| Poll file for keyword | `until grep -q "..." file; do sleep 3; done` |
| Poll file for size | `until [ "$(wc -l < file)" -gt N ]; do sleep 3; done` |
| Wait for service port | `until curl -s http://host/health >/dev/null; do sleep 2; done` |
| Wait for PID to exit | `until ! kill -0 $PID 2>/dev/null; do sleep 2; done` |

Full patterns with examples: [`bin/orama-system/skills/no-sleep-chains/SKILL.md`](../bin/orama-system/skills/no-sleep-chains/SKILL.md)

### Open questions

None — rule is fully specified and enforced at the shell level.

---

---

## 2026-05-14: Monumental Error — Wrong Repo Build Documented as Canonical Phase 1

**Session:** docs/v2 enrichment (intended: post-Phase 1 reconciliation)
**Artifact:** `docs/wiki/10-wrong-repo-build-what-not-to-do.md` ← read this for the full delta record

### What happened

An AI agent (Claude) built a v2 kernel in the **wrong local directory**
(`OpenClaw/perpetua-core`) instead of the correct one (`code/oramasys/perpetua-core`),
pushed it to a **non-canonical GitHub remote** (`diazMelgarejo/perpetua-core`), then created
`docs/v2/15-phase1-as-built.md` and modified 4 other `docs/v2/` files documenting this
wrong build **as if it were the canonical Phase 1 implementation**.

The canonical v2 build had already been shipped **13 days earlier** (2026-05-01) at:
- `oramasys/perpetua-core` — commit `2f717f5`, 32 tests, 65-line kernel + all 6 plugins
- `oramasys/oramasys` — commit `d123420`, 4 tests, FastAPI glass-window
- `oramasys/agate` — commits `755e1de`/`f1d5a57`, hardware policy spec + GGUF RFC

All 3 canonical repos were `0 ahead / 0 behind` their GitHub remotes. The docs were
correct before the wrong commit (`5f21e83`).

### Violations of the agreed spec

| Spec decision | Canonical (`oramasys/perpetua-core`) | Divergent (`diazMelgarejo/perpetua-core`) |
|---------------|--------------------------------------|------------------------------------------|
| D8 revision: 65-line + plugins | ✅ 65-line engine + `graph/plugins/` | ❌ ~130-line integrated, no plugins/ |
| D7: Pydantic v2 BaseModel | ✅ `class PerpetuaState(BaseModel)` | ❌ `pydantic.dataclasses.dataclass` |
| Spec: `scratchpad: dict[str,Any]` | ✅ `scratchpad: dict[str, Any]` | ❌ `scratchpad: str = ""` |
| D2: `oramasys` org | ✅ `oramasys/perpetua-core` | ❌ `diazMelgarejo/perpetua-core` |
| Python 3.11+ | ✅ `requires-python = ">=3.11"` | ❌ Python 3.9.6 |
| `@tool` decorator | ✅ `graph/plugins/tool.py` done | ❌ absent |
| Async GossipBus | ✅ `aiosqlite` | ❌ `sqlite3` sync |

### Root cause

- Did not verify `git remote -v` before first push of the new repo
- Did not check whether canonical build already existed before "building Phase 1"
- Skipped the AskUserQuestion gates that the plan required
- Proceeded without brainstorming/planning approval

### Fix applied (this commit)

- `docs/v2/15-phase1-as-built.md` (wrong-build doc) → **MOVED** to `docs/wiki/10-wrong-repo-build-what-not-to-do.md` as a cautionary artifact
- `docs/v2/00-context-and-decisions.md`, `04-build-order.md`, `06-open-questions.md`, `README.md` → **REVERTED** to `935ce54` (pre-5f21e83, correct state)

### Never again

1. **Before any `git push` to a new repo:** run `git remote -v` and confirm the remote matches the agreed org (`oramasys/*` for v2, `diazMelgarejo/*` for v1-legacy)
2. **Before "building Phase 1":** search for the repo in the correct org — it may already exist
3. **Never skip `AskUserQuestion` gates** in a plan — they exist precisely to prevent this
4. **`oramasys/*` is the ONLY valid home for v2 code.** `diazMelgarejo/*` is v1-legacy only.
5. **The shipped canonical scaffold (`oramasys/*`) takes precedence** over any in-session build

**Full agent-readable post-mortem:** `docs/wiki/10-wrong-repo-build-what-not-to-do.md` — enriched 2026-05-16 with complete incident timeline, failure mode analysis, spec violation table, and "what future agents MUST do" checklist. Read this before any v2 docs/ or oramasys/ work.

---

---

## 2026-05-08 — V1 supervisor shipped; v2/14 spec written

**Context:** Three reference files synthesised into V1 implementation + V2 spec.

**Perpetua-Tools changes (all in same commit):**
- `orchestrator/supervisor.py` — V1 `OrchestrationSupervisor` (jsonl, no DB)
- `orchestrator/worker_registry.py` — static WORKER_REGISTRY (echo, ollama-mac, lmstudio-mac, codex, gemini)
- `utils/action_validator.py` — two-phase gate
- `scripts/mac_probe.sh` — hardware detection (Mac14,9 = 16GB/16GPU/arm64/standard tier)
- 5 new FastAPI endpoints under `/v1/jobs`
- 192/192 tests green (including 13 new smoke tests)

**orama-system v2 spec added:**
- `docs/v2/14-supervisor-and-anthropic-patterns.md` — V2 DB persistence, audit log, MAESTRO/SWARM gates, token-efficiency rules, hardware-aware installer plan

**Key rules confirmed for all agent sessions:**
- `MAX_DEPTH=1`, `MAX_THREADS=25` (Anthropic hard limits)
- All backends: use POST API, never `ollama run` in a shell
- `gemini --yolo` required for non-interactive dispatch
- Checkpoint written BEFORE CancelledError propagation

**Legacy `orchestrator.py` FastAPI unchanged** — backwards-compatible, will be superseded by V2.

---

---

## 2026-05-08 — Cross-platform portal + start.sh + Windows counterpart

**Context:** All `start.sh` CLI modes were only surfaced at the terminal; the portal UI had no stop/restart/discover/policy buttons. `pid_on_port()` and `wait_for_port()` used `lsof` and `nc` exclusively, which are macOS-only. No Windows entry point existed.

### What broke / what was missing

| Gap | Root cause |
|-----|-----------|
| Portal version stuck at 0.9.9.7 | Forgot to bump `VERSION` constant after v1 work |
| `/v1/jobs` not visible in UI | V1 supervisor endpoints added to PT but portal never polled them |
| `--stop`, `--discover`, `--hardware-policy` terminal-only | `portal_server.py` had no corresponding routes |
| `lsof -ti tcp:PORT` fails on Linux | `lsof` not always installed; `ss` is the Linux equivalent |
| `nc -z` fails on bare containers | Minimal Docker images ship without `nc`; bash `/dev/tcp` is always available |
| `nc -z -w 1`a-circumflex+euro+quote (cp1252-misread em-dash)`setup_macos.py` runs on Linux/CI | Preflight has macOS-specific `xattr` and `codesign` calls; hard-errors on Linux |
| No Windows start script | No way to boot the stack on the Windows node without WSL |

### Fixes shipped (commit 252a473 on main)

**`portal_server.py`:**

1. `VERSION = "0.9.9.8"` — bump.
2. **Service Controls bar** (`_render_service_control_section()`):
   - `POST /api/stop` — SIGTERMs all three services using `_pid_on_port()` (cross-platform: `lsof` → `ss` → fallback)
   - `POST /api/restart/{service}` — kills + `subprocess.Popen(start_new_session=True)` respawn; logs to `.logs/<svc>.log`
   - `POST /api/rediscover` — runs `discover.py --force` in a thread executor; returns updated IP summary
   - `GET /api/hardware-policy` already existed; JS now calls it from the "Re-check Policy" button and toasts result
3. **Supervisor Jobs panel** (`_render_supervisor_jobs_section()`):
   - `_probe_supervisor_jobs()` added to the `asyncio.gather` in `api_status()` — zero extra RTT; result included in `supervisor_jobs` key
   - `GET /api/v1/jobs` proxies to PT; JS `refreshJobs()` polls every 8s independently
4. New CSS: `.svc-btn`, `.svc-ctrl`, `.jobs-table` — dark theme compatible
5. `import signal, subprocess, time` added (were missing)

**`start.sh`:**

```bash
# Before (macOS-only):
pid_on_port() { lsof -ti "tcp:$1" 2>/dev/null | head -1 || true; }
while ! nc -z localhost "$port" 2>/dev/null; do

# After (cross-platform):
pid_on_port() {
  if command -v lsof; then lsof -ti "tcp:$1" | head -1
  elif command -v ss;  then ss -tlnp "sport = :$1" | grep -oP 'pid=\K\d+' | head -1
  elif command -v fuser; then fuser "$1/tcp" | awk '{print $1}' | head -1
  fi
}
_port_open() {
  if command -v nc; then nc -z localhost "$1" 2>/dev/null
  else (echo >/dev/tcp/localhost/"$1") 2>/dev/null; fi
}
while ! _port_open "$port"; do
```

- `_nc_probe()` helper in banner — same `nc` vs `/dev/tcp` dual path; all 3 probes remain parallel
- `setup_macos.py` now guarded: `[ "$_OS_NAME" = "Darwin" ]` — Linux/CI skip with INFO log

**`windows/` folder:**

| File | Role |
|------|------|
| `start.ps1` | All 6 CLI modes; `Get-PidOnPort` (netstat), `Wait-ForPort` (TcpClient), `Start-Service` (Popen equivalent via `ProcessStartInfo`) |
| `install.ps1` | Idempotent venv + deps + openclaw.json defaults; pywin32 + colorama |
| `requirements-windows.txt` | pywin32, colorama, netifaces |
| `README.md` | Parity table + architecture notes |

**`windows/start.ps1` platform-translation table:**

| bash | PowerShell |
|------|-----------|
| `lsof -ti tcp:PORT` | `netstat -ano` + regex for LISTENING PID |
| `nc -z localhost PORT` | `TcpClient.ConnectAsync().Wait(500ms)` |
| `open URL` | `Start-Process URL` |
| `ipconfig getifaddr en0` | `Get-NetRoute` gateway → `.110` heuristic |
| `kill PID` | `Stop-Process -Id PID -Force` |
| subprocess bg `&` | `ProcessStartInfo(CreateNoWindow=true)` + async stream copy |
| `.paths` sourced file | `.paths.ps1` dot-sourced with `$PtDir`, `$UsPython` vars |

### Key rules derived

- **Never assume `lsof`** — it is missing on Debian minimal, Alpine, and distroless containers. Always cascade: `lsof → ss → fuser`.
- **Never assume `nc`** — Alpine and scratch images ship without it. Bash `/dev/tcp` is a shell built-in and always available.
- **`setup_macos.py` guard is mandatory** — the script calls `xattr -cr` and `codesign -s -` which are macOS-only binaries. It will `FileNotFoundError` on Linux.
- **`-w 1` (timeout) must come before the host in `nc`** — `-z -w 1 host port` works; `-z host port -w 1` silently ignores the flag on some Linux builds.
- **`Start-Job` vs `ProcessStartInfo`** — PowerShell `Start-Job` creates a new PS host (slow, large). `System.Diagnostics.ProcessStartInfo` with `CreateNoWindow=true` is the correct analogue of bash `cmd &`.
- **Windows GPU: 1 model at a time** — `install.ps1` prints this as a hard warning; `start.ps1` never sets `LM_STUDIO_WIN_ENDPOINTS` to multiple URLs.

### Verification

```bash
# macOS
bash -n start.sh && echo OK                           # syntax
bash scripts/mac_probe.sh | python3 -m json.tool       # JSON valid
python3 -c "import ast; ast.parse(open('portal_server.py').read()); print('OK')"

# Linux (simulate)
_OS_NAME=Linux bash start.sh --status                  # setup_macos skipped
ss --version && lsof --version || true                 # check which probe tools exist
```

### Deferred

- `start.ps1` end-to-end on a real Windows + PowerShell 5.1 box (no WSL)
- `install.ps1` tested with Python 3.11 from python.org (not conda/pyenv)
- Portal `POST /api/restart/portal` self-restart (kills the process serving the request — needs supervisor process or systemd watchdog to respawn)

---

---

## 2026-05-07 — Codex CLI unknown-model fallback; local_models.json strategy; qwen3.5-local renamed

### Problem

Codex CLI ships a built-in model catalog for OpenAI cloud models only.
When pointing it at a local Ollama endpoint with an unregistered model ID
(`qwen3.5:9b-nvfp4`), Codex falls back to 272K token defaults. The local
server never sees a context that large; it crashes with overflow errors.
Plan mode and structured output also break silently because capability
flags (`supports_reasoning`, `supports_tools`) are unknown.

Compounding this: the previous local alias `qwen3.5-local:latest` was
deleted from Ollama and replaced by `qwen3.5:9b-nvfp4` — 6 source files
across two repos still referenced the old ID.

### Fix (immediate — local machine)

1. Created `~/.codex/local_models.json` with correct context caps and
   capability flags for all Ollama models (local + cloud-proxy).
2. Added `model_catalog_json = "~/.codex/local_models.json"` to
   `[model_providers.ollama-launch]` in `~/.codex/config.toml`.
3. Key values for `qwen3.5:9b-nvfp4`:
   - native `context_length = 262144` (from `ollama api/show model_info`)
   - safe local cap: `context_window = 32768` (Mac RAM constraint)
   - `supports_reasoning = true`, `supports_tools = true`

### Model ID rename sweep

| File | Old → New |
|------|-----------|
| `orama-system/setup_macos.py` | `qwen3.5-local:latest` → `qwen3.5:9b-nvfp4` |
| `orama-system/portal_server.py`a-circumflex+euro+quote (cp1252-misread em-dash)`PT/packages/local-agents/src/client.js` | DEFAULTS + comment |
| `PT/packages/local-agents/tests/client.test.js`a-circumflex+euro+quote (cp1252-misread em-dash)`~/.codex/local_models.json` is the **single source of truth** for
  local Ollama model metadata (context caps, capability flags).
- Auto-generate with `scripts/gen_local_models_json.py` whenever Ollama
  model list changes. Never edit manually.
- In v2: `perpetua-core/config/ollama_catalog.json` mirrors this schema;
  `ollama_catalog.example.json` ships with the repo; real file gitignored.
- Apply Pattern B (`11-idempotency-and-guard-patterns.md` §3): one config
  file, many consumers (Codex CLI, HardwarePolicyResolver, LocalAgentClient).
- CI gate: `test_no_stale_model_ids` greps for retired / old-alias model
  IDs in all source files and fails if any are found.

**Spec doc**: `docs/v2/13-local-model-catalog-strategy.md`

---

## Session 2026-05-08 — start.sh Warm-Cache + Parallel Probes (Layer-3 side)

**Problem:** When PT's `alphaclaw_manager --resolve` failed (Python missing, network blip), `start.sh` fell back to bare offline defaults — services started with empty endpoints. Banner tier-detection ran 3 sequential `nc -z` probes (3s worst case).

**Fixes shipped (1 commit on `main`):**

1. **Warm-cache fallback** — when PT resolve fails, read `.state/routing.json` (last known good state from PT) and re-export `PT_MODE=cached`, `PT_DISTRIBUTED`, `PT_ALPHACLAW_PORT`, `WIN_IP`, `PT_SCENARIO`, `PT_MODE_SOURCE=cache`, `PT_AGENTS_STATE`. Stale-data warning is always printed so operators know cache is in use.
2. **Parallel banner probes** — 3 `nc -z -w 1` calls now run as background subshells writing to mktemp files, then `wait`. Total banner delay = max(1s) instead of 3s.

**Why this matters with PT v0.9.9.9:**
- PT now writes `scenario_name` into routing.json. Warm cache reads it and exports `PT_SCENARIO` so banner + portal can show the *last* scenario when resolve is dead.
- The PT scenario engine + warm cache together mean the constellation degrades gracefully: live → cached → offline-defaults, never opaque hang.

**Gemini CLI syntax update:** `gemini` invocations must now use `--yolo` (alias `-y`) so the subprocess auto-approves tool prompts. Without it Gemini stalls on the first sandbox gate. Patched `scripts/spawn_agents.py:_dispatch_gemini` and the `SKILL.md` example.

**Deferred** (both Mac + Win required):
- Live `start.sh` validation across LAN (cache hits when Win .108 unreachable but Mac .110 still pingable)
- Verify banner tier=1 (FULL) when both nodes online

Re-run in ~2 days:
```bash
./start.sh --probe-only       # just probes, no service start
nc -z -w 1 192.168.x.108 1234  # confirm Win LMS reachable
```

---

---

## 2026-05-06 — Claude — Cherry-pick conflict resolution silently truncates files

**Agent**: Claude (Sonnet 4.6)
**Branch**: check-recovery-gemini
**Severity**: High — data loss risk on every multi-commit cherry-pick

### Problem

After cherry-picking 4 recovery commits (16eacf9, 9e70566, 4de7b09, 9876706)
onto a branch based on main, conflict resolution incorrectly took the *recovery
branch's older/shorter* file versions instead of main's richer ones — for 5 files
across two separate incidents:

| File | main lines | branch after cherry-pick | Lost |
|------|-----------|--------------------------|------|
| `scripts/review/repo_hygiene.py` | 363 | 204 | 159 lines of checks |
| `tests/test_repo_hygiene.py` | 147 | 34 | 113 lines of tests |
| `scripts/git/check_identity.sh` | 32 | 27 (elif reimpl.) | loop extensibility |
| `docs/wiki/08-git-hygiene-and-branching.md` | 122 | 122 (wrong content) | Codex identity text |
| `CLAUDE.md` | 217 | 225 (duplicate block) | duplicate cyre-only block injected |

The first two were silent — `pytest` still ran (just against the 34-line stub),
reporting 147 passed. No error surfaced until human review of the PR diff.

### Root cause

During `git cherry-pick` with `--strategy-option=ours`, "ours" means the branch
being cherry-picked INTO at that point in time — which is based on main. But
add/add conflicts and some content conflicts were resolved in the wrong direction,
taking the recovery commit's older version of files that main had substantially
expanded.

### Detection method that works

After any cherry-pick with conflicts, run:

```bash
for f in $(git diff --name-only main...HEAD); do
  main_n=$(git show "main:$f" 2>/dev/null | wc -l | tr -d ' ')
  branch_n=$(git show "HEAD:$f" 2>/dev/null | wc -l | tr -d ' ')
  [ "$branch_n" -lt "$main_n" ] && echo "SHORTER ⚠  $f  main=$main_n branch=$branch_n"
done
```

Any file where branch < main line count is suspicious. Then do a full `git diff
main HEAD -- <file>` on each and classify every removed line as either intentional
or accidental.

### Fix

Restore truncated files verbatim from main:

```bash
git show main:path/to/file > path/to/file
git add path/to/file
```

Then verify content diffs for zero-delta files (same line count ≠ same content —
check for replaced paragraphs, reversed identity text, injected duplicates).

### Rule going forward

**Assume everything is wrong after a cherry-pick with conflicts.**
Treat the line-count audit as mandatory before any push, not optional.
Files shorter than main = immediate stop and manual review.
Line-count parity is necessary but not sufficient — run full `git diff main HEAD`
on every changed file and justify each removed line.

### Open follow-ups

- Add line-count audit step to `scripts/review/repo_hygiene.py` as a pre-merge
  CI gate for branches with cherry-pick history (future work).

---

## 2026-05-06 — Claude — Idempotency, validator drift, and CWD anchoring (Codex P1/P2)

**Agent**: Claude (Sonnet 4.6) + Codex (chatgpt-codex-connector)
**Branch**: check-recovery-gemini → PR #32
**Severity**: High — three latent footguns in `start.sh` + cross-validator drift

### What Codex caught that single-pass review missed

PR #32 (commit b7733f1) integrated the `_ensure_symlink` automation from
commit 1675ab4. Local `pytest` was green and a manual run of the symlink
logic against the real PT path "worked." Codex review then surfaced three
issues that would only manifest in production startups:

1. **Regular-file crash under `set -e`** — `_ensure_symlink` only checked
   `[ ! -L "$link" ]` (not a symlink) before `ln -s`. When the link path
   was a tracked regular file (e.g. `network_autoconfig.py` is a real
   tracked Python module in this repo), `ln -s` returned exit 1 with
   "File exists" and `set -e` killed `start.sh` before any service
   launched. **Local manual tests missed this** because the link path
   was empty during testing — the test environment hadn't simulated the
   tracked-file case.

2. **Validator policy drift** — `repo_hygiene.py` had momentarily been
   restored to a single-identity policy (`cyre <Lawrence@cyre.me>`),
   while `check_identity.sh` accepted both `cyre` and `Codex`. Codex
   sessions would pass the gate-script but fail the hygiene script and
   the test that wraps it. The two validators must enforce the *same*
   set or one becomes a fiction.

3. **CWD-dependent symlink** — `_ensure_symlink "network_autoconfig.py"
   "$_REL_NET_CONFIG"` ran with whatever CWD `start.sh` was invoked
   from, not `$SCRIPT_DIR`. Worked in dev because we always ran from
   the repo root. Would silently misroute the symlink the moment a user
   typed `/path/to/start.sh` from elsewhere.

### Root patterns

These three findings collapse to **two patterns** worth promoting to
v2 design decisions:

#### Pattern A — Idempotent filesystem helpers (4-state guard)

Any helper that mutates the filesystem must explicitly handle every
state of the destination, in priority order:

```bash
_ensure_symlink() {
  local link="$1" target="$2"
  if [ -L "$link" ] && [ -e "$link" ]; then
    return 0                                      # 1. valid symlink → no-op
  elif [ -L "$link" ] && [ ! -e "$link" ]; then
    # 2. broken symlink → re-link if target exists
    [ -e "$target" ] && rm "$link" && ln -s "$target" "$link"
  elif [ -e "$link" ]; then
    # 3. regular file/dir → warn and skip (do NOT clobber)
    echo "WARN: $link occupies path as regular file; skipping symlink"
  else
    # 4. nothing → create
    ln -s "$target" "$link"
  fi
}
```

The non-negotiable property: every branch returns 0. No state crashes
under `set -e`. Idempotent across N invocations.

#### Pattern B — Single-source policy, multi-validator consumption

Allowed-identity lists, hardware policies, port assignments, allow/deny
patterns — anything that two scripts both check — must live in **one
file** that both scripts load. Constants duplicated across `bash` and
`python` will drift. Drift only surfaces when the rare branch fires.

In v1 today: two validators, two source-of-truth lists. In v2:
`config/identities.yaml` (or equivalent), loaded by both bash and
python via shared shim.

#### Pattern C — Anchor every CWD-sensitive call

Operations that resolve paths from `pwd` (`ln -s`, `cd`, relative
`subprocess` calls, `Path()` without absolute prefix) must run inside
`(cd "$SCRIPT_DIR" && ...)` or use absolute paths. Defaulting to "the
caller's CWD" is a footgun that hides until invoked from elsewhere.

### Detection method

For any new shell script touching the filesystem:

```bash
# Smoke test — assume the worst case for every state
TMPDIR=$(mktemp -d) && cd "$TMPDIR"
echo "tracked" > foo                    # state: regular file
_ensure_symlink "foo" "/some/target"    # must NOT crash under set -e
ln -s /nonexistent broken_link          # state: broken symlink
_ensure_symlink "broken_link" "."       # must re-link or warn
ln -s . valid_link                      # state: valid symlink
_ensure_symlink "valid_link" "."        # must be no-op
_ensure_symlink "fresh" "."             # state: nothing
_ensure_symlink "fresh" "."             # second run — still no error (idempotency)
```

Run all four states. Run each twice. Exit code must be 0 every time.

### Multi-agent review beats single-agent review

This is the third independent finding from a Codex pass that Claude
single-pass review missed (Gemini caught the api_server.py state-env
mismatch on a prior session; Codex caught the cherry-pick truncation
on this session; Codex caught these three on the same PR). For
significant changes, multi-model review pays for itself.

### Open follow-ups → see v2 design

These patterns are now first-class v2 design requirements. See:
- `docs/v2/11-idempotency-and-guard-patterns.md` — codified patterns
- `docs/v2/10-v1-hacks-automation-orbit.md` — Link Watcher must use
  the 4-state guard from day one
- `docs/v2/01-kernel-spec.md` — kernel filesystem helpers MUST be
  idempotent + CWD-anchored; pre-merge CI gate must run the smoke
  test above against every fs helper

---

---

## 2026-05-06 — xAI model retirement 2026-05-15; grok-4.3 + grok-4.20-non-reasoning defaults

**What changed**

xAI is retiring 8 model IDs on 2026-05-15 12:00 PM PT. Any
`model_hardware_policy.yml` entry or router constant still referencing them
will cause a hard dispatch failure at that time.

**Retired IDs**

`grok-4-1-fast-reasoning`, `grok-4-1-fast-non-reasoning`,
`grok-4-fast-reasoning`, `grok-4-fast-non-reasoning`, `grok-4-0709`,
`grok-code-fast-1`, `grok-3`, `grok-imagine-image-pro`

**Replacement routing (v2 defaults)**

| Workload | New model | Notes |
|----------|-----------|-------|
| Reasoning / coding | `grok-4.3` | Coding → PLAN-ONLY until Win-coder slot available; reasoning → full ACT always |
| Non-reasoning / non-coding | `grok-4.20-non-reasoning` | research, ops, chat, summarisation |
| Image generation | *(no announced replacement)* | Surface error to user; do not silently fall back |

**Coding ACT gate**: resumes when `swarm_state.md` reports `WIN_CODER: AVAILABLE`
(same file already polled by the Windows-sequential-load rule).

**Design rule promoted to v2**

- All model ID lists must be single-source in `perpetua-core/config/` (Pattern B
  from `11-idempotency-and-guard-patterns.md`) — never duplicated in bash + python.
- Add CI gate `test_no_retired_model_ids` that greps `model_hardware_policy.yml`
  for any known-retired ID and fails if found.

**Spec doc**: `docs/v2/12-xai-model-migration-2026-05.md`

---

---

## 2026-05-04 — Codex — Priority execution (P1–P6), checklist and fail-closed hardening

### What was learned

- Large multi-priority migrations are easy to report as complete while still missing execution-level proof unless a strict post-block checklist is run.
- Hardware-bound requests (`lmstudio-*`, `ollama-*`) must fail closed when policy authority is unavailable; warnings are not sufficient.
- Verification command drift (doc command vs repo script reality) causes false confidence and noisy handoffs.

### Decisions made

- Added a consolidated checklist discipline after each priority block with pass/warn/fail reporting.
- Added in-repo helper `scripts/hardware_policy_cli.py --check-openclaw` to make the documented check executable.
- Promoted this incident to the wiki for durable cross-session visibility.

### Open follow-ups

- Historical docs still contain many `Perplexity-Tools` references; active-path docs are cleaned first, historical artifacts are tracked as non-blocking warnings.

→ [wiki/09-policy-fail-closed-and-checklist.md](wiki/09-policy-fail-closed-and-checklist.md)

---

---

## 2026-05-04 — Technical Architecture: Ghost Path Extraction

- **Symptom**: Advanced v1 features (symlink automation, IP sync) were lost during the structural rewrite to orama-system.
- **Cause**: Focus on 'clean lineage' led to a feature regression by discarding the 'messy' main backup.
- **Solution**: Use the `recovery-20260424` branch as a clean-room for extraction.
- **Rule**: Every 'v1 hack' is a potential v2 primitive. Audit the `backup-main` tag (1675ab4) for high-value logic before finalizing the v2 microkernel.
- **Reference**: Symlink automation logic identified in Commit 1675ab4 (start.sh).

---

---

## 2026-05-02 — Claude — v2 packages scaffolded + instinct sync

### v2 Phase 1–3 complete: perpetua-core + oramasys + agate (2026-05-02)

Three Python packages built and pushed to GitHub under `oramasys` org. All tests green:

- `perpetua-core` 32/32 tests — `PerpetuaState`, `LLMClient`, `HardwarePolicyResolver`, `MiniGraph` (~70 lines), `GossipBus`, 6 graph plugins (checkpointer, interrupts, streaming, structured_output, subgraphs, tool)
- `oramasys` 4/4 tests — FastAPI glass-window `/run` + `/health`, hardware-routed 3-node graph
- `agate` — JSON Schema + examples for `model_hardware_policy.yml`

Local paths: `~/code/oramasys/{perpetua-core,oramasys,agate}`
GitHub: `github.com/oramasys/{perpetua-core,oramasys,agate}`

**Phase 4 (parity tests) is next.** `dispatch_node` is still an echo stub — needs real `LLMClient` wiring.

Missing from spec (still TODO): `message.py`, `graph/nodes.py`, `graph/edges.py`, `config/model_hardware_policy.example.yml`, `GossipBus` integration in graph.

### Python runtime split on this machine (2026-05-02)

Two Python runtimes coexist:

- **Python 3.13**: `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3` — has oramasys packages installed
- **Python 3.12**: `~/miniconda3/bin/python` — does NOT have v2 packages

Use `python3` (or full path `pytest`) for v2 tests. Running `python -m pytest` from miniconda shell fails with `ModuleNotFoundError: No module named 'perpetua_core'`.

### instinct-import CLI not installed — copy YAML workaround (2026-05-02)

`continuous-learning-v2` script (`~/.claude/skills/continuous-learning-v2/scripts/instinct-cli.py`) does not exist on disk — plugin is listed but not installed. Running `/instinct-import` fails silently.

**Workaround**: copy YAML files directly into `.claude/homunculus/instincts/inherited/` so future installs pick them up. Done for:

- `Perpetua-Tools-instincts.yaml` → `orama-system/.claude/homunculus/instincts/inherited/`
- `everything-claude-code-instincts.yaml` → `orama-system/.claude/homunculus/instincts/inherited/`

Key instincts to apply manually until script is available: snake_case filenames, relative imports, `@field_validator` not `@validator`, scoped conventional commits (`feat(x):`), tests in `tests/` directory.

### gitStatus in session context is a snapshot — always re-verify (2026-05-02)

The `gitStatus` block injected at session start is captured once at launch. By the time a new session starts, repos may have been committed and pushed. Always run `git status` before assuming there is work to do. Both orama-system and Perpetua-Tools appeared dirty in the snapshot but were fully clean when re-checked.

---

## 2026-05-02 — Document Integrity & Archiving Policy

- **Symptom**: Critical legacy documentation (AGENT_RESUME.md) was overwritten by an automated summary, losing v1 context.
- **Cause**: AI tendency to replace files rather than merge or archive (destructive behavior).
- **Rule**: NEVER delete or overwrite historical context. Always archive legacy documentation to /docs/archive/ or wiki entries.
- **Merge Strategy**: We are additive. All new summaries must be appended to the current state or moved to dedicated files while preserving the parent document's soul.
- **Reference**: Legacy AGENT_RESUME.md recovered and archived at docs/archive/AGENT_RESUME_v1_legacy.md.

---

## 2026-05-02 — Roadmap Granularity & Documentation Ergonomics

- **Symptom**: Premature "DONE" markers in v2 build order led to confusion about active implementation vs. planned hardening.
- **Cause**: AI tendency to mark design completion as task completion.
- **Solution**: Split roadmap into explicit **PLANNING** and **Implementation** phases. Architecture is "launched" (a living process), not merely "concluded."
- **Rule**: Documentation MUST link to both Archived (v1) and Active (v2) repository organizations to maintain cross-generational visibility.
- **Formatting**: Use `ascii` tags for non-executable code blocks and blockquotes for high-level summaries to improve UX for the next agent.

---

## 2026-04-29 — Win IP Migrated to .105; Docs Cleanup

**Context:** Session resumed after credits ran out 2 days earlier. Win GPU IP changed again
from `.103` → `.105` (committed in PT `0bac6ea chore(config): update win-rtx3080 lan_ip`).

**Key finding:** The `ip_resolver.py` 6-priority chain handled this automatically — no code
change needed. `openclaw.json` (P2) already shows `http://192.168.254.105:1234/v1`. The
resolver read this at P2 and returned `.105` correctly without manual intervention.
This confirms the self-healing architecture works as designed.

**What the `.103` fallback constant means:** The hardcoded `.103` fallback in `ip_resolver.py`
is priority 6 (last resort) and is a best-guess constant. It only fires if ALL of:

- AlphaClaw is down (P1 fails)
- `openclaw.json` is missing or malformed (P2 fails)
- `discovery.json` has no reachable entry (P3 fails)
- PT `detect_active_tilting_ip()` is unavailable (P4 fails)
- No env vars set (P5 fails)
- Subnet derivation via socket fails (also P6)
In practice the real IP (`openclaw.json` P2) always wins. The `.103` constant is a
subnet-portable guess (Windows is always 3rd host on the /24), not the actual IP.

**Docs fixed this session:**

- `PT/docs/MIGRATION.md` Gate 2: removed hardcoded `192.168.254.101:1234`, replaced with
  dynamic note: "Win GPU LAN IP — dynamic, read from `~/.openclaw/openclaw.json`, currently `.105:1234`"
- `PT/docs/adr/ADR-001-*`: formatting cleanup
- `PT/docs/system-design-three-repo-architecture.md`: formatting pass

**Pending (blocked on both machines online):**

- G1 shared models list — needs Win + Mac simultaneously
- G4 live openclaw.json sync across repos
- Unified `/agent/dispatch` L2 API in PT

**Repos synced:** PT pushed `c6b8cdf`, orama-system clean (all changes from previous session already committed).

---

---

## 2026-04-29 — G1/G3/G4 Closed; LM Studio Remote-as-Local Proxy Behavior Discovered

**Trigger:** Both machines came online simultaneously — first time since policy was written.

### Key Discovery: LM Studio proxies remote LAN endpoints as "local" models

**What LM Studio does:** When you add a remote server (Win LMS at 192.168.254.105:1234) as
a provider in Mac's LM Studio, ALL models on that remote server appear in Mac's own
`/v1/models` response as if they were locally loaded. The reverse is also true.

**Why this matters:**

- The original policy assumed you could tell a model's physical home by which machine's
  `/v1/models` endpoint it appeared in. **This assumption is WRONG.**
- `qwen3.5-27b-...` appears in Mac's `/v1/models` — but it physically runs on Win RTX 3080.
- `qwen3.5-9b-mlx` appears in Win's `/v1/models` — but it physically runs on Mac Apple Silicon.
- Both machines return all 5 models, yet each model has a true physical home.

**Correct mental model:**

```
Mac /v1/models  →  [mac-native models] + [win models proxied as local]
Win /v1/models  →  [win-native models] + [mac models proxied as local]
```

**Routing rule that actually works:**

- Do NOT use model presence in `/v1/models` to determine which machine to route to.
- Use the **provider name** (`lmstudio-mac` vs `lmstudio-win`) as the routing key.
- The policy YAML `mac_only` / `windows_only` enforces provider-level routing, not detection.

**Policy fix applied:**

- `mac_only: []`, `windows_only: []` — cleared; LMS proxy makes per-machine exclusion unenforceable at the API level
- `shared:` — all 5 confirmed models added (accessible from either provider endpoint)
- openclaw.json repaired: both `lmstudio-mac` and `lmstudio-win` now show 5 models each

**discover.py result (2026-04-29, both machines online):**

```
mac: ✅ localhost:1234     — 5 models
win: ✅ 192.168.254.105:1234 — 5 models
```

### Gaps Closed This Session

| Gap | Status |
|-----|--------|
| G1 shared models populated | ✅ Closed — all 5 models confirmed shared |
| G3 device_affinity → affinity key rename | ✅ Closed — 7/7 schema tests pass |
| G4 live openclaw.json repaired | ✅ Closed — both machines show 5 models, no violations |
| G2 PERPETUA_TOOLS_ROOT in .env.example | ✅ Already existed |

### Model physical homes (for performance routing, not strict enforcement)

| Model | Physical home | Notes |
|-------|--------------|-------|
| `qwen3.5-9b-mlx` | Mac (Apple Silicon) | MLX quantization — native on Mac |
| `qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2` | Win (RTX 3080) | Large GGUF — GPU preferred |
| `gemma-4-26b-a4b-it` | Win (RTX 3080) | Large model — GPU preferred |
| `gemma-4-e4b-it` | Mac or Win (small) | Small enough for either |
| `text-embedding-nomic-embed-text-v1.5` | Mac or Win | Embedding model, low cost |

**Win IP confirmed stable at .105 during this session.**

---

---

## 2026-04-29 — Claude — Cross-repo sync gist (from PT docs/LESSONS.md)

*(PT-owned lessons relevant to orama. Full text in [Perpetua-Tools `main` → `docs/LESSONS.md`a-circumflex+euro+quote (cp1252-misread em-dash)`qwen3.5-9b-mlx`, `qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2`. No `-4bit` suffix on Mac.
- **openclaw CLI requires Node.js ≥ v22**. Default v14 fails instantly. Use full path: `~/.nvm/versions/node/v24.14.1/bin/openclaw`
- **All 6 agents pass**: win-researcher/coder/autoresearcher (Win 27B, 107–130s), main/mac-researcher/orchestrator (Mac 9B, 105–308s via Gemini fallback).
- **Thinking models return empty `text`** — reply is in `reasoning_content`. Always check both fields.
- **commandTimeout must be ≥ 300 000 ms** for reasoning model turns.

### thinkingDefault fix (automated, 2026-04-27)

- `thinkingLevel`/`modelParameters` fields are REJECTED by OpenClaw schema. Correct field: `thinkingDefault: "off"`.
- `setup_macos.py` step 3b writes this and strips stale keys on every `start.sh`. No manual LM Studio toggle needed.
- Win 27B: leave thinking as-is; it always returns `reasoning_content`.

### Known working versions (2026-04-27)

- AlphaClaw: **0.9.3–0.9.11** all confirmed working.
- OpenClaw: all versions working.
- `KNOWN_ALPHACLAW_VERSION` in setup_macos.py = `"0.9.3"` (minimum baseline).

### Git status hang — node_modules was tracked (2026-04-29)

- `packages/alphaclaw-mcp/node_modules/` (3818 files + 6 symlinks) was committed accidentally in PT.
- `git status` hung indefinitely (lstat of 3818 files + APFS symlink chains).
- Fix: add `node_modules/` to `.gitignore`, then `git rm -r --cached packages/*/node_modules`.
- **Universal rule**: never track `node_modules/`, `__pycache__/`, `.venv/`, `dist/`, `build/`.

### AutoResearcher migration: karpathy → uditgoenka (2026-04-11)

- `AUTORESEARCH_REMOTE` is now an env var (default: `uditgoenka/autoresearch`).
- Plugin install is primary mode: `claude plugin marketplace add uditgoenka/autoresearch`.
- **Valid Windows model name**: `Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-v2`. `Qwen3.5-27B-Instruct` DOES NOT EXIST — never use it.
- `uv sync --dev` replaces bare `pip install` in bootstrap paths.

### Module rename: ultrathink → orama (2026-04-29)

**Problem**: Phase B renamed files but left internal references stale, causing 16 test failures:

1. `orama_bridge.py` still imported `from orchestrator.ultrathink_mcp_client import` (broken after file rename)
2. Tests imported from `orchestrator.ultrathink_bridge` / `orchestrator.ultrathink_mcp_client` (old paths)
3. Test assertions checked `ULTRATHINK_ENDPOINT` / `ultrathink_available` (routing.yml now uses `ORAMA_ENDPOINT` / `orama_available`)
4. Hardware policy tests relied on live `model_hardware_policy.yml` which was correctly emptied (LM Studio proxy discovery)

**Fixes**:

- `orama_bridge.py`: fix import + logger name to use `orchestrator.orama_mcp_client` / `"orchestrator.orama_bridge"`
- Tests: replace module paths and env var names to match new routing.yml contract
- Hardware policy tests: pass explicit `policy=` dicts — self-contained, not coupled to live policy file
- Add `.claude/hooks/pre-commit` to catch 5 categories of naming drift at commit time

**Rule**: After any file rename, grep all test files for the old module path immediately. File renames break test `patch()` strings even when the rename is intentional and correct.

**Pre-commit guard**: `.claude/hooks/pre-commit` in Perpetua-Tools blocks commits with stale:
`orchestrator.ultrathink_bridge`, `orchestrator.ultrathink_mcp_client`, `ULTRATHINK_ENDPOINT`, `ultrathink_available`, `Perplexity-Tools` in ecc-tools.json.

### Version bump atomicity: update ALL surfaces at once (2026-04-29)

- SKILL.md says "When bumping version, update ALL of these atomically" — 5 surfaces
- `pyproject.toml`, `bin/orama-system/SKILL.md`, `bin/config/agent_registry.json`, `docs/PERPLEXITY_BRIDGE.md`, `docs/SYNC_ANALYSIS.md`
- Missing any one causes `test_version_docs.py` failures
- Template: `grep -rn "0.9.9.X" . --include="*.toml" --include="*.md" --include="*.json" | grep -v ".git"` before each bump

### Always use .venv/bin/python3 -m pytest for orama tests (2026-04-29)

- System Python 3.13 lacks httpx → `test_api_server.py` fails with RuntimeError on import
- orama `.venv` uses Python 3.12 with all required packages (fastapi, httpx, starlette)
- Command: `cd orama-system && .venv/bin/python3 -m pytest tests/ -q`

### .DS_Store in .git/refs causes repo hygiene check failure (2026-04-29)

- macOS Finder creates `.DS_Store` inside `.git/refs/` — `repo_hygiene.py` hard-fails on this
- Fix: `rm -f .git/refs/.DS_Store` — idempotent, safe
- Add to `.gitignore_global` or monthly cleanup script

### qwen3.5-9b-mlx is a thinking model — requires 500+ max_tokens (2026-05-01)

- `qwen3.5-9b-mlx` confirmed running at `localhost:1234` (LM Studio Mac)
- It is a **thinking model**: response contains `reasoning_content` (chain-of-thought) + `content` (actual answer)
- `content` is empty (`""`) if `max_tokens < ~200`. Safe floor: 500 tokens
- When a real LM Studio HTTP client replaces `_call_with_fallback`, extract `choices[0].message.content`, NOT `reasoning_content`
- Model is already correctly listed as `mac_only` in `config/hardware_policy_cache.yml`
- Test: `curl http://localhost:1234/v1/chat/completions -d '{"model":"qwen3.5-9b-mlx","messages":[{"role":"user","content":"Reply: OK"}],"max_tokens":500}'` → `content: "\n\nOK"` (209 reasoning tokens + 4 content tokens)

---

## [2026-04-26] Session: Twin-System Recovery & Integration Hardening

### Context

Full-session work across Perpetua-Tools (Layer 2) and orama-system (Layer 3). AlphaClaw untouched.

### Key Facts Confirmed

| Fact | Value |
|------|-------|
| Win RTX 3080 LAN IP | `192.168.254.103:1234` (was wrong as .101/.107/.109) |
| Mac M2 Pro LAN IP | `192.168.254.105:1234` (always `localhost:1234` locally) |
| OpenClaw gateway | `localhost:18789`, loopback-only, bearer token auth |
| Tier 1 confirmed | Both nodes live after IP fix + `discover.py --force` |
| Gstack version | v1.12.2.0 at `~/.claude/skills/gstack` |
| Gbrain identity | `mcp__gbrain__*` tools (used by Gstack commands) |

### Patterns Learned

**IP drift is multi-file.** When LAN IPs change, update simultaneously:
`~/.openclaw/openclaw.json` → `config/devices.yml` → `.env.local` → run `discover.py --force`.
Use `grep -r "192.168.254" .` across all three repos as the audit command.

**GPT-5.5 model fallback rule.** Try `gpt-5.5` first. Downgrade to `gpt-5.4` ONLY on:
`"message":"The 'gpt-5.5' model is not supported when using Codex with a ChatGPT account."`
Do not preemptively downgrade.

**Gemini API type is critical.** Use `google-generative-ai` type for Gemini providers in OpenClaw — NOT `openai-completions`. The wrong type causes the gateway process to crash silently.

**Self-improve skill trigger = Option C.** Auto-suggest at session end; commit only when user approves. Never auto-commit without the A/B/C gate.

**Empty git dirs after rename.** `git mv` fails with "source directory is empty" when the dir has no tracked files. Use `rm -rf` for untracked artifact dirs — don't try to rename them.

**PR merge timing.** Cherry-pick post-branch commits onto main after PR merge. The last commit on a feature branch can be left behind if pushed after the PR was merged. Always verify with `git log --oneline origin/main..HEAD` after switching to main.

### Skills & Agents Created This Session

| Artifact | Location | Purpose |
|----------|----------|---------|
| `alphaclaw-session` v1.1.0 | PT `.claude/skills/alphaclaw-session/SKILL.md` | DO's/DON'Ts, self-healing, IP roster |
| `self-improve` v1.0.0 | PT + orama `.claude/skills/self-improve/SKILL.md` | Session crystallization (Option C) |
| `gemini-analyzer` agent | PT `.claude/agents/gemini-analyzer.md` | Gemini Reader role, large-context |
| `codex-coder` agent | PT `.claude/agents/codex-coder.md` | GPT-5.5 coder, Gbrain bridge, Gstack |

### Open Items (carry forward)

- Model ID case test (gateway was offline this session)
- Merge orama-system `2026-04-24-001-orama-salvage` → main
- Live Gbrain ↔ Codex test via Gstack
- Live Gemini-coder test via `mcp__gemini-cli__ask-gemini`

---

---

## 2026-04-26 — Claude — Part 2 session: Gemini audit + registry schema fix + commit hygiene

### What was learned

**1. agent_registry.json schema gap (agents[] had no `affinity` keys)**
The `agents` array (7 orama stage agents) was added before the hardware-policy work. None had
`"affinity"` keys. The `openclaw_agents` section and `autoresearch_agents` section both had
affinity info, but the stage agents were silently unguarded. Fixed in commit b2ed93b.

**2. api_server.py silent stub degradation**
When `PERPETUA_TOOLS_ROOT` doesn't exist or `utils.hardware_policy` can't be imported, the
except block fell back to no-op stubs with zero log output. Operators had no way to know enforcement
was disabled. Fixed: added `logger.warning()` with the PERPETUA_TOOLS_ROOT path in the except block.

**3. `ultrathink_bridge` import regression was the real blocker**
The prior session's attempt_completion was failing because `fastapi_app.py` still imported from
`orchestrator.ultrathink_bridge`, which was renamed to `orama_bridge` during the repo rename.
This caused ALL test collection to fail. Once fixed (from orchestrator.orama_bridge import ...),
11/11 tests passed immediately. The 4 "open architectural questions" were not actually blocking —
they were resolved in the implementation already.

**4. MCP server registration must use `-s user` scope**
`claude mcp add` without `-s user` scopes the server to the current working directory only.
Running the installer from a different directory (or a new shell) means the servers are invisible.
Always use: `claude mcp add -s user <name> -- <command>`.

**5. `device_affinity` vs `affinity` key inconsistency**
`autoresearch_agents` entries use `"device_affinity": "win-rtx3080"` while `agents` array entries
now use `"affinity": "win"`. These need to be normalized (Part 2, Phase 7). Any routing code
that reads `device_affinity` needs to be audited.

### Decisions made

- `executor-agent` gets `affinity: "win"` — it's the heavy compute worker (code_generator + performance_profiler)
- All other stage agents (orchestrator, context, architect, refiner, verifier, crystallizer) get `affinity: "mac"` — they are Claude Code subagent types, not LM Studio GPU workers
- `shared:` section in policy YAML stays empty until both machines are physically online and `discover.py --status` is run

### Open questions

- What models are genuinely cross-platform? (needs both machines online — Phase 5, Part 2)
- Should `device_affinity` in autoresearch_agents be normalized to `affinity`? (Phase 7, Part 2)

### Follow-up plan

`docs/tripartite-plan/2026-04-26-hardware-model-routing-004-PART2-PLAN.md`

---

---

## 2026-04-26 — Codex — Windows CLI shims and AlphaClaw PR lessons (Apr 15-26)

### What was learned

**Windows command resolution should be user-local and runtime-anchored**
Use `%USERPROFILE%\.lmstudio\bin` for stable PowerShell shims instead of relying on
versioned app install paths. Anchor Node to LM Studio's bundled runtime at
`%USERPROFILE%\.lmstudio\.internal\utils\node.exe`, and keep npm's global prefix inside the
same user-owned bin directory so globally installed CLIs resolve predictably.

**npm-generated PowerShell launchers need a nearby node.exe**
The `gemini.ps1` and `codex.ps1` launchers generated by `npm install -g` expect `node.exe`
beside them on Windows. If symlink creation requires elevation, a user-owned hardlink from
`%USERPROFILE%\.lmstudio\bin\node.exe` to LM Studio's node keeps the setup frugal and avoids
maintaining a separate Node install.

**Git should follow GitHub Desktop, not a pinned app-* path**
`git.cmd` should resolve GitHub Desktop's bundled Git dynamically. This avoids breakage when
GitHub Desktop updates its versioned installation directory.

**AlphaClaw PR fixes need targeted regression proof**
The macOS post-install branch needed focused tests after conflict resolution:
`tests/server/routes-onboarding.test.js`, `tests/server/gateway.test.js`, and
`tests/server/routes-system.test.js`. The important behaviors were starting the managed
scheduler after onboarding installs hourly sync config and rejecting named cron tokens on the
managed scheduler path because the parser is numeric-only.

### Decisions made

- Keep machine-specific Windows launchers outside the repo and document the setup here.
- Verify PowerShell wiring with `git --version`, `node --version`, `npm --version`, `gemini --version`, and `codex --version`.
- Keep the AlphaClaw code-fix branch separate from process/documentation lessons so review stays narrow.
- Confirmed toolchain snapshot: Git `2.53.0.windows.3`, Node `v25.5.0`, npm `11.12.1`, Gemini CLI `0.39.1`, Codex CLI `0.125.0`.

### Follow-up

- After LM Studio updates, recheck that `%USERPROFILE%\.lmstudio\bin\node.exe` still maps to the intended bundled runtime.

---

# 2026-04-27 — Part 2 Complete: Disaster Recovery, Gemini Plan Review, AlphaClaw Fixes

## G3 + G2 closed (Part 2 Plan phases 7 + 8)

**G3 — device_affinity → affinity key rename:**

- `PT/config/routing.yml` autoresearch routes: renamed `device_affinity` → `affinity` (key only; value `win-rtx3080` preserved intentionally — future Windows hardware profiles will share the windows_only blocklist but have distinct whitelists, so specific device IDs are required)
- `orama/bin/config/agent_registry.json` autoresearch_agents: same rename
- Added regression guard `test_routing_affinity_keys_normalized` (PT) and `test_no_device_affinity_anywhere_in_registry` (orama)
- **Lesson: never normalize `win-rtx3080` to generic `win`** — device-specific affinity values are the extension point for multi-Windows-profile support

**G2 — PERPETUA_TOOLS_ROOT documented:**

- Added to `PT/.env.example` and `orama/.env.example` with cross-repo usage notes

**G1 — shared: section:**

- Commented out in `PT/config/model_hardware_policy.yml` with TODO block pointing to Part 2 Phase 5
- Added parametrized tests for both PyYAML and `_simple_policy_parse` paths (3 YAML variants: commented, absent, explicit-empty)
- Added `_POLICY_CACHE` autouse fixture to prevent cross-test contamination

## Disaster Recovery: HardwarePolicyResolver

**Problem:** PT is authoritative for hardware policy, but orama needs to run even if PT is temporarily unreachable. Previous design silently disabled enforcement on import failure.

**Solution:** 3-layer `HardwarePolicyResolver` in `api_server.py`:

- L1: sys.path import from PERPETUA_TOOLS_ROOT → PT-authoritative (preferred)
- L2: `config/hardware_policy_cache.yml` → vendored YAML snapshot, logs CRITICAL warning
- L3: hard fail if cache also missing — never silently skip enforcement

**PT final handoff audit trail:** Every response includes `metadata.policy_source` and `metadata.pt_authoritative`. `/health` endpoint exposes `hardware_policy.source`. This lets callers and ops know whether any routing decision was PT-authoritative or cache-degraded.

**FastAPI lifespan:** Moved policy initialization from module-level (breaks test imports + `--reload`) to `@asynccontextmanager lifespan`. Startup probe happens once; result is stable for the server lifetime.

**`hardware_policy_cache.yml`:** Created at `orama-system/config/hardware_policy_cache.yml` — refresh instructions in the file header.

## Gemini v3.1 Plan Review

**Accepted:**

- Step 2 (PERPETUA_TOOLS_ROOT env consolidation) — already done via .env.example
- Step 4 (hallucination purge) — already done in prior session; bad IDs live only in docs warning about them

**Rejected:**

- Step 1.1 (symlink orama/utils/hardware_policy.py → PT/utils/hardware_policy.py): fragile across machines, breaks on Windows (no Unix symlinks), breaks in Docker/CI, breaks when repos at different paths. sys.path approach is more portable.
- Step 1.2 (remove _simple_policy_parse fallback): this IS the disaster recovery fallback for PyYAML-absent environments. Removing it reduces resilience.

## AlphaClaw Plugin Config Fixes

**Problem 1 — duplicate plugin ID:** `usage-tracker` was being loaded twice — once as a bundled built-in AND again because startup code adds `lib/plugin/usage-tracker` to `plugins.load.paths`. Harmless but noisy.

**Problem 2 — restart unavailable:** `openclaw restart` requires `"restart"` in `plugins.allow`. It was absent.

**Fix:** Added to both `~/.alphaclaw/openclaw.json` and `alphaclaw-observability/config/openclaw.json`:

```json
"plugins": {
  "allow": ["usage-tracker", "restart", "memory-core"],
  "entries": { "usage-tracker": { "enabled": true }, "restart": { "enabled": true } },
  "load": { "paths": [] }
}
```

Setting `load.paths: []` prevents the startup code from adding the dev-repo path (which caused the duplicate).

**Architecture clarification:** AlphaClaw is a WRAPPER that orchestrates OpenClaw instances. OpenClaw runs standalone. AlphaClaw manages the gateway, plugins, and agent lifecycle AROUND OpenClaw sessions. This is the opposite of what the config file naming suggests — `openclaw.json` is AlphaClaw's config for managing OpenClaw.

## Tests Summary

- PT: 24/24 pass (16 original + 5 new: parametrized YAML parser + routing affinity key guard + ORAMA_ENDPOINT fix)
- orama: 23/23 pass (16 original + 7 new: agent_registry schema consistency tests)

## Open

- G1 (shared models): blocked — needs both machines online simultaneously
- G4 (live openclaw.json repair): blocked — needs both machines online
- Codex: `@openai/codex-darwin-arm64` native binary missing; use Gemini as second voice until fixed

---

## Session 2026-04-27b — Agent Automation, Portal Dashboard, Multi-Agent Dispatch

### What Was Built

**1. Codex PTY Automation (THE KEY PATTERN)**
Codex `--full-auto` requires a TTY. When spawned from any Python subprocess (Claude Code, portal API, CI), there is no TTY → "stdin is not a terminal" error.

**Fix: `pty.openpty()` pseudo-terminal wrapper**

```python
import pty, select, os

master_fd, slave_fd = pty.openpty()
proc = subprocess.Popen(
    ["codex", "--full-auto", task],
    stdin=slave_fd, stdout=slave_fd, stderr=slave_fd,
    close_fds=True,
)
os.close(slave_fd)  # parent doesn't need slave end
# read from master_fd with select() to collect all output
```

This makes Codex fully automatable — no human terminal ever required.

**Live in:** `orama-system/scripts/spawn_agents.py → _dispatch_codex()`

**2. Gemini CLI Node Version Fix**
Gemini CLI (installed under nvm v24) uses `??=` (ES2021). But `#!/usr/bin/env node` resolves to nvm v14 in Claude Code's shell. Fix: create `~/.local/bin/gemini` wrapper:

```bash
#!/usr/bin/env bash
exec ~/.nvm/versions/node/v24.14.1/bin/node \
     ~/.nvm/versions/node/v24.14.1/bin/gemini "$@"
```

`~/.local/bin/` comes before nvm in PATH → wrapper always wins.
**Live in:** `scripts/setup_codex.sh` (auto-creates wrapper on every `start.sh`)

**3. spawn_agents.py — Parallel Agent Dispatch**
File: `orama-system/scripts/spawn_agents.py` and `PT/scripts/spawn_agents.py` (shim)

Supports: `codex`, `gemini`, `lmstudio-mac`, `lmstudio-win`, `all`

- Codex + Gemini + LM Studio Mac run in parallel
- LM Studio Win serialized via `asyncio.Lock()` (one GPU model at a time)
- CLI: `python scripts/spawn_agents.py --task "..." --agent codex`
- API: `POST /api/spawn-agent` from the portal

**4. Portal Tools & APIs Panel**
All 18 tools/APIs from AlphaClaw + PT visible in `portal_server.py`:

- Groups: AI Providers, Search & Tools, Messaging Channels, GitHub, CLI, Gateways
- 3 states: READY (green) / NOT CONFIGURED (amber, inline configure) / KEY SET BUT FAILING (red, replace button)
- `POST /api/configure-tool` writes to `.env.local` safely (atomic + file lock + rate limit)
- No terminal needed to configure any API key

**5. Policy Cache Refresh Automation**
`scripts/refresh_policy_cache.py` syncs `config/hardware_policy_cache.yml` from PT on every `start.sh`. This keeps the L2 disaster recovery fallback always fresh.

### How to Dispatch Agents (from any context)

```bash
# From terminal
cd orama-system
python scripts/spawn_agents.py --status           # check availability
python scripts/spawn_agents.py --task "..." --agent codex
python scripts/spawn_agents.py --task "..." --agent gemini
python scripts/spawn_agents.py --task "..." --agent all   # parallel

# From portal (browser)
# Tools & APIs panel → Agent Dispatch panel → type task → click Send

# From Claude session (spawn sub-agent)
# Use Agent() tool with spawn_agents.py as the worker
```

### Gemini Review Pattern (tested and works)

```bash
# --yolo (alias: -y) auto-approves Gemini tool prompts.
# Without it, the subprocess hangs at the first sandbox/tool gate.
~/.local/bin/gemini --yolo -p "Review X for Y. Be concise."
```

Returns structured bullet-point feedback in ~3s.

### Key Architecture Invariants (updated)

- `spawn_agents.py` is the canonical multi-agent dispatcher for both orama and PT
- The portal `/api/spawn-agent` always loads spawn_agents.py via importlib + `sys.modules` registration
- Windows GPU: always `asyncio.Lock()` before LM Studio Win calls
- `setup_codex.sh` runs on every `start.sh` — codex + gemini are always fixed

### Open Items

- G1 (shared models): still blocked — needs both machines online
- G4 (live openclaw.json sync): still blocked
- Gemini CLI broken binary: wrapper fixes runtime but underlying package may need updating: `nvm use 24 && npm update -g @google/gemini-cli`
- Win LM Studio offline during this session — need both machines for full parallel dispatch

---

# 2026-04-27 — Dynamic LAN IP Detection & Self-Healing Architecture

**Context:**
Windows GPU machine (RTX 3080) had IP `.103` but system had stale `.101`/`.108` hardcoded in
`portal_server.py`, `spawn_agents.py`, `ip_detection_solution.py`, and PT's `lan_discovery.py`.
Auto-detection existed in `start.sh` (4-priority chain) but `portal_server.py`/`spawn_agents.py`
didn't use it when started standalone. The portal showed wrong IPs and couldn't reach Win LMS.

**Root causes (5):**

| # | File | Problem |
|---|------|---------|
| RC-1 | `portal_server.py:50-58` | Hardcoded `.101` fallback — ignored `openclaw.json` entirely |
| RC-2 | `scripts/spawn_agents.py:45` | Same — hardcoded `.101` |
| RC-3 | `~/.openclaw/state/discovery.json` | Win IP was empty (Win was offline during last scan), so start.sh Priority 2 always missed |
| RC-4 | `ip_detection_solution.py:27` | Stale `.101` hardcoded for Windows |
| RC-5 | PT `lan_discovery.py:318` | Bug: computed `{subnet}.100` but comment said `.103` (typo) |

**Fix — shared `utils/ip_resolver.py`:**

Created `orama-system/utils/ip_resolver.py` — single authoritative source for Win IP:

```
P1: AlphaClaw gateway (:18789) — live, if running means openclaw.json is current
P2: ~/.openclaw/openclaw.json  — patched by discover.py after every successful scan
P3: ~/.openclaw/state/discovery.json — last probe state (may lag if Win was offline)
P4: PT detect_active_tilting_ip() — derives {mac-subnet}.103, subnet-portable
P5: LM_STUDIO_WIN_ENDPOINTS env var — operator / start.sh override
P6: {outbound-interface-subnet}.103 — absolute last resort, subnet-portable
```

**Key patterns to remember:**

1. **Never hardcode LAN IPs in module-level constants.** Use `ip_resolver.get_win_lms_url()` which
   re-reads `openclaw.json` on every call. One file read per 10s portal poll is cheap.

2. **`discover.py --force` must run at every startup**, not just when state is stale.
   LAN is always dynamic. A 4-5s subnet scan at startup is acceptable — much better than stale IPs.
   Hook: `start.sh` now runs `timeout 15 python3 ~/.openclaw/scripts/discover.py --force` before
   the IP detection block.

3. **Gossip write-back:** when portal's live probe hits Win LMS successfully, it calls
   `write_win_ip_to_openclaw_json(probed_ip)` to update `openclaw.json`. This means any
   process that reads `openclaw.json` next will have the correct IP, even if `discover.py`
   didn't run yet.

4. **Subnet-portable `.103` rule:** Windows GPU is always `.103` on whatever subnet the Mac is on.
   This works on legacy `192.168.1.x` AND current `192.168.254.x` without any config change.
   PT's `detect_active_tilting_ip()` had a bug (`.100` instead of `.103`) — fixed.

5. **`ip_resolver.py` test:** `python3 utils/ip_resolver.py` — should print Win IP, LMS URL,
   Ollama URL. If it prints `.103` you're reading from `openclaw.json` (P2).

6. **Files that still have static Win IP references (archive, not code paths):**
   - `AGENT_RESUME.md` — informational only
   - Comments in various files marking old IPs (`.108`, `.101`) as archive

**Files changed:**

- `utils/ip_resolver.py` — NEW shared resolver (P1-P6 chain)
- `utils/__init__.py` — NEW package init
- `portal_server.py` — uses ip_resolver; dynamic re-resolve in `api_status()`; gossip write-back
- `scripts/spawn_agents.py` — uses ip_resolver fallback
- `ip_detection_solution.py` — stale `.101` → `.103`
- `start.sh` — `discover.py --force` at startup; subnet.103 as last-resort
- `scripts/sync-companion-instincts.sh` — Perplexity-Tools → Perpetua-Tools (all refs)
- PT `orchestrator/lan_discovery.py` — bug fix `.100` → `.103`

**Sync reminder:**
Both repos (orama-system and Perpetua-Tools) must be pushed after these changes.

---

---

## 2026-04-24 — Codex — Clean-lineage salvage guardrails

### What was learned

Directly replaying a useful tail is unsafe when commit metadata, tracked private
config, generated path files, and symlink assumptions are mixed into the same
range. The safer approach is to branch from the verified clean anchor, snapshot
both repos, and manual-port only reviewed intent.

### Decisions Made

- Salvage branch format is `yyyy-mm-dd-001-brief-summary`.
- Canonical commit identity is `cyre <Lawrence@cyre.me> or Codex <codex@openai.com>`.
- `.env`, `.env.local`, and `.paths` are ignored runtime files; examples are the only tracked contract.
- `.ecc` must not be both a gitlink expectation and a symlink in the working tree.
- `repo_hygiene.py` and `check_identity.sh` are the pre-commit guardrails for this recovery path.

→ [docs/recovery/2026-04-24-001-orama-history-recovery.md](recovery/2026-04-24-001-orama-history-recovery.md)
→ [docs/recovery/2026-04-24-002-commit-salvage-matrix.md](recovery/2026-04-24-002-commit-salvage-matrix.md)
→ [docs/recovery/2026-04-24-003-git-safety-guardrails.md](recovery/2026-04-24-003-git-safety-guardrails.md)

---

---

## 2026-04-24 — Claude — Salvage forensics + systematic rename + hygiene pipeline

### What was learned

1. **Forensics First, Action Last**: Gemini's corrupted commits involved not just metadata shifts but destructive configuration purges (stripping `.env`). Never rebase a corrupted tail blindly. Map the drift first.
2. **Identity Restoration via `.mailmap`**: Git's identity corruption (unauthorized email/name) is best fixed at the repo level with a canonical `.mailmap` file, ensuring all historical logs attribute correctly without rewriting every commit object.
3. **Historical Rename Strategy**: The migration from `ultrathink-system` to `orama-system` required a multi-stage approach:
    - `sed` batch for internal references (excluding historical docs and hygiene configs).
    - `git mv` for folders and individual filenames.
    - Automated hygiene check to verify no "active" legacy references remained.
4. **Idempotent Setup Bug**: A `TypeError` in `setup_macos.py` (incorrect `_skip` signature) proved that even "no-op" dry-runs must be tested. Idempotent guards must accept optional detail strings consistently.

### Decisions made

- `orama-system` is the authoritative name and directory.
- `scripts/review/repo_hygiene.py` is the primary guardrail for identity and naming consistency.
- [docs/wiki/08-git-hygiene-and-branching.md](wiki/08-git-hygiene-and-branching.md) tracks the active Git hygiene and branching guardrails.

### Prevention Rules

1. Always run `python3 scripts/review/repo_hygiene.py` before committing a major refactor.
2. Maintain `.mailmap` as the "Source of Truth" for author identity.
3. Use `yyyy-mm-dd-NNN-summary` branch naming for salvage work.
4. Verify `_skip` and `_log` signatures in setup scripts after any logging refactor.

### Commits

- `dc45482` — chore(rename): systematic migration to orama-system
- `f43a9b2` — fix(setup): fix _skip call signature in setup_macos.py

→ [docs/wiki/08-git-hygiene-and-branching.md](wiki/08-git-hygiene-and-branching.md)
→ [scripts/review/repo_hygiene.py](../scripts/review/repo_hygiene.py)

---

---

## 2026-04-24 — Codex — Xcode metadata hygiene + docs-only handoff discipline

### What was learned

1. **`.gitignore` does not protect `.git/` internals**: Finder or Xcode can leave `.DS_Store` under `.git/refs`, which breaks Git with `badRefName` even though `.DS_Store` is ignored for normal tracked files.
2. **Generated artifacts need two layers of defense**: Ignore patterns prevent new working-tree noise, while hygiene checks catch already-tracked macOS metadata, Xcode user state, Python caches, wheels, and build outputs.
3. **Docs-only commits need explicit staging**: When code hygiene work and documentation edits coexist, stage named docs files only. Do not let unrelated guardrail changes leak into a documentation commit.
4. **Future agents need link maps, not large context dumps**: `CONTRIBUTING.md` should point to canonical methodology, coordination, recovery, and verification markdowns so agents can load the smallest relevant context.

### Decisions made

- Treat `git fsck --no-reflogs --full --unreachable --no-progress` as the fast signal for malformed refs after macOS/Xcode metadata incidents.
- Check `.git/refs` directly with `find .git/refs -name '.DS_Store' -print` when Xcode Beta or Finder has touched the checkout.
- Keep contribution guidance relative-link-only so GitHub renders it and agents do not depend on sibling local checkouts or absolute machine paths.
- Add new operational learnings here before ending a session; link deeper guidance through [CONTRIBUTING.md](../CONTRIBUTING.md), [docs/wiki/README.md](wiki/README.md), and [tests/README.md](../tests/README.md).

### Prevention rules

1. Before committing from a macOS/Xcode-touched checkout, run `python3 scripts/review/repo_hygiene.py .` and `git fsck --no-reflogs --full --unreachable --no-progress`.
2. If `.git/refs/.DS_Store` appears, remove only that metadata file and rerun `git fsck`; do not reset or rewrite history for a local Finder artifact.
3. For docs-only commits, verify the staged set with `git diff --cached --name-only` and keep it limited to markdown files.

---

---

## 2026-04-24 — Codex — Markdown redirect and size guardrails

### What was learned

Markdown edits need their own pre-commit discipline. Absolute local links, missing canonical-path notes after moves, and oversized single-file docs make future agent handoffs brittle even when tests pass.

### Decisions made

- `scripts/review/repo_hygiene.py` blocks absolute filesystem links in tracked markdown.
- Changed markdown files now warn when a new file exceeds 200 lines or an existing file exceeds 500 lines.
- Agents must ask before crossing those limits and suggest moving detail into `references/`, `docs/wiki/`, or sub-skills.
- The root skill, packaged skill, Claude skill mirror, CIDF, and verification checklist all carry the same markdown edit rule.

### Prevention rules

1. Before committing markdown, run `python3 scripts/review/repo_hygiene.py .`.
2. Keep links relative and GitHub-renderable unless the target is an intentional external URL.
3. Preserve redirect or canonical-path breadcrumbs when moving markdown.

---

# 2026-04-26 — Hardware Model Affinity Incident

**Context:**
`orama-system/scripts/discover.py` was writing unfiltered LM Studio model lists
to `openclaw.json`. This could cause `lmstudio-mac` to advertise Windows-only
27B/26B models, creating a hardware damage risk on the M2 Pro, while
`lmstudio-win` could advertise Mac-only MLX / Apple Silicon models.

**Root cause:**
Discovery trusted endpoint responses without cross-referencing a hardware policy.

**Defense-in-depth solution:**

- L1: `discover.py` filters through `Perpetua-Tools/config/model_hardware_policy.yml`
  before writing discovery state, `openclaw.json`, or `.env.lmstudio`.
- L2: Perpetua-Tools `utils/hardware_policy.py`, `alphaclaw_manager.py`, and
  `agent_launcher.py` enforce affinity before routing/spawn decisions.
- L3: `api_server.py` returns HTTP 400 `HARDWARE_MISMATCH` at the API boundary.

**Canonical policy file:** `../perplexity-api/Perpetua-Tools/config/model_hardware_policy.yml`

**Known hallucinations removed:** `qwen3-coder-14b` and `gemma4:e4b` appeared in
AI-generated drafts of this plan. They are NOT verified model IDs in this system.
Do not re-add them.

**Status:** Implemented 2026-04-26.

**Follow-up — unified CLI/GUI management:**
Do not multiply human entry points. Hardware policy validation is exposed through
the existing orama CLI (`./start.sh --hardware-policy`, `./start.sh --status`)
and the existing Orama Portal (`http://localhost:8002`, Hardware Policy & Safe
Defaults section). Perpetua-Tools `scripts/hardware_policy_cli.py` is a helper
used by the existing CLI, tests, and agents — not a separate product surface.

---

---

## 2026-04-20 — Auto-discovery & three-repo automation setup

### What was done
- Deployed `~/.openclaw/scripts/discover.py` (Layer A Python hub) + per-repo shell gates
- All 3 repos auto-discover LM Studio endpoints at Claude Code SessionStart
- Idempotent: SHA1 hash comparison — no writes if state unchanged
- 4-tier disaster recovery: live probe → last-good JSON → versioned backup → named profiles
- Backup policy: ≤30 snapshots, 31st auto-deletes oldest; files >30 days archived (not deleted)
- Stale IPs fixed: openclaw.json, devices.yml, models.yml all updated
- Claude Code hooks added: ruff on edit, lessons check on Stop

### Key invariants
- Never hardcode LM Studio IPs — always use `$LM_STUDIO_WIN_ENDPOINTS` from `.env.lmstudio`
- `.env.lmstudio` is auto-generated and gitignored — safe to delete and re-run discover.py
- `~/.openclaw/scripts/discover.py --status` is the first check when endpoints seem wrong
- Gossip TTL is 5 min — for fresh data NOW: `discover.py --force`
- Repo renamed from orama-system; `ULTRATHINK_ENDPOINT` in .env still works

### Recovery commands
```bash
~/.openclaw/scripts/discover.py --restore profile:mac-only  # Win is down
~/.openclaw/scripts/discover.py --restore latest            # revert last change
~/.openclaw/scripts/discover.py --force                     # re-probe everything
```

---

---

## 2026-04-20 — Claude — Gate 1: start.sh thinned; orama is now a pure PT delegator

### What was learned

**orama is a delegate, not a decision-maker.** The key lesson from Gate 1: any line in start.sh that reads routing.json, probes backends, or determines "distributed vs single vs offline" mode is a policy violation. That logic belongs in PT. orama reads the result; it never re-derives it.

**Thinning pattern for shell delegation:**

```bash
_PT_ENV_EXPORTS="$(
  "$PT_PYTHON" -m orchestrator.alphaclaw_manager --resolve --env-only \
    --mac-ip "${MAC_IP}" --win-ip "${WIN_IP}" \
    2>&1 | tee /dev/stderr | grep '^export '
)" && eval "$_PT_ENV_EXPORTS"
```

The `tee /dev/stderr` keeps progress messages visible while `grep '^export '` captures only the `eval`-able lines. This is cleaner than temp files.

**New file to know:** `orchestrator/alphaclaw_manager.py` (in PT) is the authoritative Python lifecycle manager. Start there when debugging gateway issues. It wraps `agent_launcher.py` (probe) and `alphaclaw_bootstrap.py` (lifecycle).

**FUSE git limitation persists:** git operations in the sandbox FUSE mount still fail with `index.lock` or `Resource deadlock avoided`. Always provide Mac terminal commands for commits.

### Decisions Made

- start.sh v0.9.9.8 is the canonical thinned version. Sections 2a and 2c are gone — absorbed into PT's `alphaclaw_manager.py`.
- start.sh now labels services as "orama" (not "ultrathink") everywhere.
- The security warning (AlphaClaw default password) is preserved — it reads from `.state/onboarding.json` written by PT's bootstrap.
- `PT_MODE`, `PT_DISTRIBUTED`, `PT_ALPHACLAW_PORT` env vars are now available in orama's shell environment after PT resolve.

### Open

- `openclaw_bootstrap.py` in orama still has gateway decision logic — Gate 2 work to scope it down to apply-config only.
- Autoresearcher launch (was start.sh §distributed check) needs to move to PT's `alphaclaw_manager.py` resolve payload as a flag — Gate 2.

→ [PT docs/MIGRATION.md §Gate 1](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/MIGRATION.md)
→ [PT orchestrator/alphaclaw_manager.py](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/orchestrator/alphaclaw_manager.py)

---

---

## 2026-04-13 — Claude — alphaclaw macOS compatibility patches + idempotent setup automation

### Context
`alphaclaw` (`@chrysb/alphaclaw` npm package v0.9.3) was written for Linux/Docker environments
running as root. On macOS with a standard user account, its startup script hard-coded four
`/usr/local/bin/` and `/etc/cron.d/` paths that require root access — causing four EACCES/ENOENT
errors on every boot. Separately, the OpenClaw gateway timed out because `openclaw.json` failed
schema validation (missing required `models[]` arrays).

### Root Causes Found

| # | Error message | Root cause |
| --- | -------------- | ---------- |
| 1 | `gog install skipped: Permission denied /usr/local/bin/gog` | curl+mv hardcoded to `/usr/local/bin/` (root-owned on macOS) |
| 2 | `Cron setup skipped: ENOENT /etc/cron.d/openclaw-hourly-sync` | `/etc/cron.d/` is Linux-only; doesn't exist on macOS |
| 3 | `systemctl shim skipped: EACCES /usr/local/bin/systemctl` | Linux/Docker-only shim; `/usr/local/bin/` requires root |
| 4 | `git auth shim skipped: EACCES /usr/local/bin/git` | git shim hardcoded to `/usr/local/bin/git` (root-owned) |
| 5 | Gateway timeout: `timed out after 30s` | `openclaw gateway run` exited immediately — `ollama-mac.models` and `ollama-win.models` were `undefined` (required arrays); port 18789 never opened |

### Fixes Applied (all 5 patches to `~/.alphaclaw/.../alphaclaw.js`)

1. **gog install** — changed destination to `path.join(os.homedir(), ".local", "bin")` + `mkdir -p` before mv
2. **cron setup** — added `if (os.platform() === "darwin")` guard using `crontab -l` user crontab; original Linux `/etc/cron.d/` path preserved in `else` branch
3. **systemctl shim** — wrapped entire block in `if (os.platform() !== "darwin")` — macOS uses launchd, shim is irrelevant
4. **git auth shim dest** — changed `gitShimDest` to `path.join(os.homedir(), ".local", "bin", "git")`; added `fs.mkdirSync()` before `fs.writeFileSync`
5. **git-sync shimPath** (line 277) — updated `shimPath` reference to `~/.local/bin/git` to match new shim location

**openclaw.json fix** — added `models[]` arrays to `ollama-mac` (3 real models from `/api/tags`) and `ollama-win` (placeholder); corrected all 4 provider `baseUrl` fields (stale `.101`/`.105` IPs → correct `.110`/`.108`/`127.0.0.1`).

### Key Insight: `~/.local/bin` Shadowing

`~/.local/bin` is at PATH position 4 (before `/usr/local/bin` at position 9) on this system.
Installing binaries there means they shadow system paths with no root required. This is the
correct macOS pattern for user-space tool installs that alphaclaw should use by default.

### Automation: `setup_macos.py`

Created `orama-system/setup_macos.py` — runs idempotently on every `./start.sh`:

- **Step 1**: Create `~/.local/bin` if missing
- **Step 2**: Add `~/.local/bin` to PATH in `~/.zshrc` if not present
- **Step 3**: Validate `~/.openclaw/openclaw.json` — add `models[]` arrays if missing; query live Ollama for real model names, fall back to known defaults
- **Step 4**: Apply the 6 alphaclaw.js patches — each patch has a `detect` string (already-patched marker) for idempotency; applies only if the original string is found

**Idempotency contract**: each patch checks `detect in content` before applying. If the npm
package version changes (`KNOWN_ALPHACLAW_VERSION = "0.9.3"` constant), a warning is printed
but patches are still attempted. Marker file written to `~/.alphaclaw/.macos_patches.json`.

`start.sh` integration (added after `mkdir -p "$LOG_DIR"`):

```bash
if [ -f "$SCRIPT_DIR/setup_macos.py" ]; then
  "$US_PYTHON" "$SCRIPT_DIR/setup_macos.py" --quiet 2>&1 | sed 's/^/  /' || true
fi
```

### Prevention Rules for Future Agents

1. **npm packages designed for Docker/root will fail on macOS** — check `/usr/local/bin/` writes and `/etc/cron.d/` references; redirect to `~/.local/bin/` and user crontab respectively
2. **openclaw.json schema validation is strict** — gateway exits immediately on validation failure; check with `openclaw gateway --help` or `openclaw doctor` BEFORE troubleshooting port timeouts
3. **Gateway timeout ≠ gateway crash** — if port never opens, look at config validation first, not process crashes
4. **All pre-flight patches must be idempotent** — use a `detect` string (patched-version marker) + `old` string (original-version marker); apply only when `old` is found, skip when `detect` is found
5. **node_modules patches are transient** — `npm install` in `~/.alphaclaw/` overwrites alphaclaw.js; `setup_macos.py` re-applies on next `./start.sh`

### Files Changed

| File | Change |
| ------ | -------- |
| `~/.alphaclaw/node_modules/@chrysb/alphaclaw/bin/alphaclaw.js` | 6 macOS compat patches (lines 277, 539, 596, 866, 893, 906) |
| `~/.openclaw/openclaw.json` | Fixed 2 missing `models[]` arrays + 4 stale provider IPs |
| `orama-system/setup_macos.py` | **NEW** — idempotent pre-flight automation |
| `orama-system/start.sh` | Added `setup_macos.py` call after LOG_DIR creation |

---

---

---

## 2026-04-13 — Claude — Startup fix: IP detection, stdin deadlock, concurrent backend probing

### Learned

- **Abort trap: 6 root cause**: `_gather_alphaclaw_credentials()` spawned a daemon thread calling `input()`. After `t.join(30)` timed out, Python shutdown tried to flush/close the stdin `BufferedReader` → SIGABRT. Fix: (1) `sys.stdin.isatty()` guard, (2) `</dev/null` in start.sh, (3) `stdin=subprocess.DEVNULL` on gateway `Popen`
- **IP misconfiguration was silent**: `agent_launcher.py` read `MAC_LMS_HOST`/`WINDOWS_IP` but neither was exported by start.sh or in `.env` — fallback hard-coded defaults always used
- **`agent_launcher.py` never called `load_dotenv()`** — only saw shell-exported vars; added `load_dotenv(".env")` + `load_dotenv(".env.local", override=True)`
- **`asyncio.create_task()` fires immediately; `gather()` blocks** — fire all probes at t=0, await in two phases (local first, then LAN) for correct ordering without sequential delay
- **`_persist_detected_ips()`** — confirmed live endpoints written back to `.env` after each probe; config becomes self-correcting

### Decided

- Hard-coded defaults: `.110` Mac LM Studio, `.108` Windows
- `network_autoconfig.py` `preferred_ips` updated to `.110` / `.108`
- `LM_STUDIO_MAC_ENDPOINT` parsed in `agent_launcher.py` to derive `MAC_LMS_HOST`/`MAC_LMS_PORT`
- `.env.local` corrected: `WINDOWS_IP=192.168.254.108`, `WINDOWS_PORT=11434`

→ [wiki/07-startup-ip-detection.md](wiki/07-startup-ip-detection.md)

---

---

## 2026-04-13 — Claude — Portal update: visibility, user-input textbox, correct IPs

### What was learned

1. **`portal_server.py` never loaded `.env`** — default IPs always used even when `.env` had correct values; fixed by adding dotenv loading at module import
2. **Agents-as-services need a user-input gate** — autonomous loops with no stop condition make it impossible to steer agents without killing the process; 3-round confirmation pattern: agents confirm live, then wait for instructions

### Decisions made

- Portal now loads `.env`/`.env.local` at startup
- Added `POST /api/user-input` endpoint (proxies to PT `http://localhost:8000/user-input`)
- New HTML template sections: Routing State, Active Agents, input textbox + JS fetch

### Commits

- `691787a` (UTS) — fix(portal): dotenv load, correct IPs, routing card, agent state, user input textbox

---

## Wiki

All lessons above are expanded with root causes, exact fixes, and verification commands:

| # | Page | Topic |
| --- | --- | --- |
| 01 | [CI Dependencies](wiki/01-ci-deps.md) | pip extras, hatchling, pyproject.toml guard |
| 02 | [Idempotent Installs](wiki/02-idempotent-installs.md) | execute bits, capture_output, model discovery |
| 03 | [Device Identity](wiki/03-device-identity.md) | one-role-per-device, GPU crash recovery, cooldown |
| 04 | [Gateway Discovery](wiki/04-gateway-discovery.md) | commandeer-first bootstrap, candidate ports |
| 05 | [Bulk Sed Safety](wiki/05-bulk-sed-safety.md) | grep-first, scope to .py only |
| 06 | [Multi-Agent Collab](wiki/06-multi-agent-collab.md) | version registry, scope claims, orphan branches |
| 07 | [Startup IP Detection](wiki/07-startup-ip-detection.md) | stdin deadlock, load_dotenv, asyncio probing |
| 08 | [Git Hygiene and Branching](wiki/08-git-hygiene-and-branching.md) | clean-lineage salvage, identity checks, protected branch flow |

---

---

## 2026-04-12 — Claude — 48-hour multi-agent sprint: collaboration patterns + version registry

### Version Number Registry — All Canonical Locations

**Current version: `0.9.9.7`.** Do NOT bump without explicit user instruction.

| File | Field | Status |
|------|-------|--------|
| `pyproject.toml:7` | `version = "0.9.9.7"` | ✓ current |
| `bin/orama-system/SKILL.md:10` | `version: 0.9.9.7` | ✓ current |
| `bin/config/agent_registry.json:2` | `"version": "0.9.9.7"` | ✓ current |
| `portal_server.py:26` | `VERSION = "0.9.9.7"` | ✓ current |
| `bin/agents/*/agent.md:4` | `version: 0.9.9.7` | ✓ current (all 7 agents) |
| `CLAUDE.md:71` | `(v0.9.9.7)` | ✓ current |
| `docs/PERPLEXITY_BRIDGE.md:3` | `Version 0.9.9.7` | ✓ current |

### Multi-Agent Collaboration Protocol

1. **Read LESSONS.md first** — mandatory, in CLAUDE.md
2. **Scope claim** — append `[IN PROGRESS]` marker before touching files
3. **Additive changes** — prefer appending over rewriting (no conflict risk)
4. **Commit message as communication** — state which constants/APIs changed
5. **Never hardcode ephemeral runtime values** — `127.0.0.1` default, real IP in `.env`
6. **One canonical source per constant** — two files defining the same IP string will diverge
7. **Test isolation** — `autouse` fixture that restores module-level state after `importlib.reload()`

### Embedded Git Repo: `.ecc/`

`.ecc/` is a gitlink (submodule stub). Do NOT delete, gitignore, or `git rm` it.
Other cloners need `git submodule update --init .ecc` to get the contents.

### Common Mistakes to Avoid

- Creating feature branches without `origin/main` as base — causes orphan branch with no common ancestor; `git rebase origin/main` produces add/add conflicts on EVERY file
- Hardcoded LAN IPs in source code defaults — breaks CI on all other machines; real IPs live in `.env` only

→ [wiki/06-multi-agent-collab.md](wiki/06-multi-agent-collab.md)

---

---

## 2026-04-09 — Claude — PT-first orchestrator migration

### What was learned

- PT works best as the only repo making orchestration decisions — `orchestrator.py` and shared control-plane helpers became the single lifecycle authority
- Setup-time onboarding prevents silent runtime degradation — Perplexity credentials, AlphaClaw/OpenClaw readiness, and AutoResearch preflight all moved earlier
- Role routing needs a concrete artifact — manager-local plus researcher-remote topology became testable only after PT generated explicit role-routing state and `openclaw_config`
- Cross-repo handoff is safest when PT exports a resolved payload and UTS consumes it without reinterpretation

### Decisions made

- Added shared PT control plane: resolves routing, reconciles gateway state, runs staged bootstrap, writes runtime payload
- Unified Perplexity client initialization around explicit credential status and validation semantics
- Moved readiness reporting into PT so UTS can delegate instead of repeating lifecycle checks

### Open questions

- Whether runtime payload should grow into a versioned public contract document
- Whether setup-time UX should persist richer migration diagnostics for support cases

---

---

## 2026-04-07 — Claude — Idempotent installs: subprocess permissions + model auto-discovery

### What was learned

- **`capture_output=True` silences bootstrap scripts** — never use in user-facing install flows
- **`npm install -g` does not guarantee execute bits** — binary exists, `shutil.which()` finds it, but `subprocess.run()` raises `PermissionError: [Errno 13]`
- **`PermissionError` is NOT a `CalledProcessError`** — must be caught separately or crashes entire bootstrap
- **Hardcoded model names break inference** — LM Studio returns `400`, Ollama returns `404` when model isn't loaded; always resolve via `/v1/models` or `/api/tags` at runtime
- **Windows GPU models cannot be called on Mac** — LAN isolation required; never cross-wire endpoints
- **AgentTracker state must not share path with routing state** — flat routing dicts cause `AgentRecord(**v)` `TypeError`

### Decisions made

- `_resolve_ollama_model()` and `_resolve_lmstudio_model()` added — query backend before registering agent
- `openclaw_bootstrap.py` auto-`chmod +x` after `npm install -g` if execute bit missing
- `AgentTracker._load()` skips non-dict entries and rewrites file clean

### Commits

- `3c9a4a8` (UTS) — fix(bootstrap): handle PermissionError + auto chmod +x after npm install
- `23bd01d` (UTS) — fix(bootstrap): remove capture_output=True

→ [wiki/02-idempotent-installs.md](wiki/02-idempotent-installs.md)

---

---

## 2026-04-07 — Claude — Device identity + GPU crash recovery

### What was learned

1. **`127.0.0.1` and a LAN IP can point to the same machine** — UDP routing trick reveals outbound LAN IP; compare against configured endpoints before assigning roles
2. **One role per physical device** — running Mac Ollama + Mac LM Studio simultaneously loads two models on same GPU; Ollama takes precedence
3. **Rapid model reload after crash burns GPU** — classify by HTTP status (503=loading, 404=unloaded, ConnectError=offline); enforce 30s cooldown minimum
4. **Terminal feedback during crash recovery is essential** — `asyncio.sleep(N)` is invisible; ASCII progress bar with role + countdown is required

### Prevention Rules

1. Always call `_get_local_ips()` before trusting any "remote" endpoint
2. One role per physical device — zero out probes whose host IP matches local IPs
3. On same device: Ollama > LM Studio deterministically
4. Crash recovery ≥ 30 seconds
5. Classify errors before sleeping — 503 ≠ 404 ≠ ConnectError
6. Show progress bar during recovery

### Commits

- `8af62f5` (PT) — feat(routing): one-role-per-device guard + GPU crash recovery cooldown

→ [wiki/03-device-identity.md](wiki/03-device-identity.md)

---

---

## 2026-04-07 — Claude — Idempotent gateway discovery (commandeer-first bootstrap)

### What was learned

- **Never start a new daemon if a compatible one is already running** — probe ALL known candidate ports first; if any gateway responds to `/health` or `/v1/models`, commandeer it
- **Commandeer = use existing + update config, never restart** — calling `openclaw onboard --install-daemon` on a running gateway evicts loaded models
- **Candidate port list should be configurable** — `OPENCLAW_CANDIDATE_PORTS` + `OPENCLAW_EXTRA_PORTS` env var

### Prevention Rules

1. All bootstrap scripts must probe before install
2. Commandeer-first, install-last
3. Never stop/restart a running daemon during bootstrap
4. Always set a discoverable env var (`*_URL`, `*_ENDPOINT`) pointing to the live gateway URL
5. Probe by interface (`/health`, `/v1/models`), not by process name

### Commits

- `6bc40d0` (UTS) — feat(bootstrap): probe all candidate ports and commandeer any running gateway

→ [wiki/04-gateway-discovery.md](wiki/04-gateway-discovery.md)

---

---

## 2026-04-07 — Claude — Bulk sed safety: check before editing / look for missing files

### What Went Wrong

A batch `sed -i` to replace `multi_agent\.` with `bin.` matched filename strings inside READMEs and shell scripts, converting `pytest tests/test_multi_agent.py` → `pytest tests/test_bin.py` (file doesn't exist). CI failed on broken `chk_f` references.

### Prevention Rules

1. `grep -rn` before any bulk `sed` — preview every match, read each context line; abort if any match is a filename
2. Scope module-import patterns to `.py` files only — never apply import-rename regexes to `.md`, `.sh`, `.yaml`
3. Verify files exist after substitution that changes a filename-like string
4. Keep filename strings and import module names disjoint in patterns
5. CI will catch broken references but catching it pre-commit is cheaper

### Commits

- `0364098` (UTS) — fix(tests): restore test filenames broken by over-eager multi_agent sed

→ [wiki/05-bulk-sed-safety.md](wiki/05-bulk-sed-safety.md)

---

---

## 2026-04-06 — Claude — CI: ModuleNotFoundError for fastapi / hatchling backend missing

### What Went Wrong

Two cascading CI failures caused by a single refactor of the CI dependency install step:

**Failure 1 — `ModuleNotFoundError: No module named 'fastapi'`**

- Refactored `pip install . pytest hatchling build tomli` → `pip install ".[test]" build`
- `[test]` extras had not yet been added to `pyproject.toml` → fastapi, uvicorn, slowapi, httpx all missing on CI runner

**Failure 2 — `Backend 'hatchling.build' is not available`**

- Adding `[test]` extras on next commit didn't include `hatchling`
- `python -m build` needs `hatchling` pre-installed in active env (not just in `build-system.requires`)

### Root Cause

Replacing `pip install pkg1 pkg2 pkg3` with `pip install ".[extras]"` without first verifying the target extras group contains ALL previously explicit packages.

### Prevention Rules

1. Never replace explicit `pip install` with `.[extras]` without auditing every removed package into the extras group
2. `hatchling` MUST always be in `[project.optional-dependencies] test`
3. `pyproject.toml` MUST have a `[project.optional-dependencies]` section with a `test` group
4. CI workflow files MUST use `pip install ".[test]"` pattern
5. All 8 required modules must be importable at commit time: `fastapi`, `httpx`, `uvicorn`, `pydantic`, `slowapi`, `pytest`, `hatchling`, `build`

### Commits

- `f078c8a` — introduced the gap (refactored install, dropped hatchling implicitly)
- `9653cfc` — added ci-deps-guard pre-commit hook
- `710fc47` — added hatchling+build to [test] extras (final fix)

→ [wiki/01-ci-deps.md](wiki/01-ci-deps.md)

---

## 2026-06-20 — `codex review` invocation, delegation path contract, macOS timeout

**Session:** `feat/openclaw-codex-app-server` — codex-openclaw-agent v2 + oramaclaw control-plane plan

### What Broke

Three silent correctness issues found via `codex review` after all tests passed:

1. **`bind_codex_backend.sh` wrote to `agents.bindings.main.allowAgents`** — the old OpenClaw delegation key. The new oramaclaw contract (written in the same session's plan) rejects `agents.bindings.*` in favour of `agents.defaults.subagents.allowAgents` / `agents.list[].subagents.allowAgents`. The agent would bind successfully but be invisible to any code following the new contract.

2. **`ControlResult.state` Literal omitted `gateway_unavailable`** — exit code 3 (`gateway unavailable, offline path invalid`) had no typed counterpart. JSON/portal callers could not distinguish it from code-5 transport failures.

3. **`timeout 60 openclaw run …` fails on stock macOS** — `timeout` is a GNU coreutils command absent on vanilla macOS. The verify step would raise `timeout: command not found`, capture that as the identity string, and trigger a false rollback of an otherwise-successful binding.

### Root Cause

These issues were not caught by the 6-test suite because:
- The tests mock the `openclaw` CLI and `jq` calls — they confirm the correct *field names* for the fields they test, but the delegation key update wrote to a different JSON path not covered by any test.
- `ControlResult.state` is a plan-level type stub; no runtime test validates its Literal values against the CLI exit-code table.
- The macOS `timeout` path is not exercised in the test environment (CI or local sandbox both have GNU coreutils).

### Lesson

**`codex review` must always use `< /dev/null`.** Without it, the process blocks on stdin and appears to hang. The correct invocation pattern (from gstack's `/review` skill line 1715):

```bash
codex review "<prompt>" -c 'model_reasoning_effort="high"' < /dev/null
```

Never omit `< /dev/null`. A codex review hanging indefinitely looks identical to it running — you cannot tell without reading the process stdin state.

### Delegation Path Contract (applies to all agents)

The canonical OpenClaw sub-agent delegation key is:
- `agents.defaults.subagents.allowAgents` — apply to all agents by default
- `agents.list[id].subagents.allowAgents` — apply to a specific named agent

The key `agents.bindings.*.allowAgents` is **rejected** by the oramaclaw control plane and must not be written by any binder, bootstrap script, or manifest.

### macOS Compatibility: use gtimeout→timeout→unwrapped

Any script calling `timeout N <cmd>` must use this pattern:

```bash
_TIMEOUT_BIN=$(command -v gtimeout 2>/dev/null || command -v timeout 2>/dev/null || echo "")
if [ -n "$_TIMEOUT_BIN" ]; then
    "$_TIMEOUT_BIN" N <cmd>
else
    <cmd>
fi
```

`gtimeout` comes from Homebrew coreutils. `timeout` is Linux-native. Neither is guaranteed on stock macOS.

### Prevention Rules

1. **Use `< /dev/null` in every `codex review` invocation** — missing it causes an invisible hang.
2. **Write delegation with `agents.defaults.subagents.allowAgents`** — not `agents.bindings.*`.
3. **Never use bare `timeout` in shell scripts targeting macOS** — use gtimeout→timeout→unwrapped.
4. **Match `ControlResult.state` Literal to the CLI exit-code table** — every distinct exit code needs a named state, not just `failed`.

### Fixes

| Finding | File | Fix |
| --- | --- | --- |
| CR-1: wrong delegation key | `bind_codex_backend.sh:332-338` | Rewrote to `agents.defaults.subagents.allowAgents` |
| CR-2: missing state literal | `oramaclaw-control-plane-v1.md:145` | Added `"gateway_unavailable"` to Literal |
| CR-3: bare `timeout` on macOS | `bind_codex_backend.sh:352` | gtimeout→timeout→unwrapped fallback |

### Commits

- `8b64518` — apply CR-1, CR-2, CR-3 + P3 hygiene fixes

---

---

## 2026-06-21 — Claude — Centralized version system: _version.py + sync_version.py

**Session:** `main` — CI fix for `test_active_version_surfaces_are_09998` + version consolidation

### What broke

CI run 27893218322 failed on a single test: `test_version_docs.py::test_active_version_surfaces_are_09998`.
`pyproject.toml` had already been bumped to `1.1.0.0` in a prior commit but the test
still asserted `0.9.9.9`, and 25+ other canonical surfaces (SKILL.md frontmatter,
`CLAUDE.md`, `bin/agents/*/agent.md`, JSON registries, Python docstring headers, etc.)
were still at old version strings — some as far back as `0.9.9.0`.

The root cause was **no single source of truth**: each version bump required manually
hunting and updating 25+ files, and the test hardcoded a literal version string that
drifted out of sync.

### What we built

**`src/orama_system/_version.py`** — the single source of truth:

```python
__version__ = "1.1.0.0"
```

**`pyproject.toml`** — now reads version dynamically via hatch:

```toml
dynamic = ["version"]
[tool.hatch.version]
path = "src/orama_system/_version.py"
```

**`scripts/sync_version.py`** — propagates `_version.py` to every canonical surface:

```bash
python3 scripts/sync_version.py            # write all surfaces
python3 scripts/sync_version.py --dry-run  # preview only
python3 scripts/sync_version.py --check    # exit 1 if any surface is stale (CI gate)
```

### Bump procedure (authoritative)

1. Edit `__version__` in `src/orama_system/_version.py` — **nowhere else**
2. `python3 scripts/sync_version.py`
3. `python3 -m pytest tests/test_version_docs.py`
4. `git add -A && git commit -m "chore(version): bump to X.Y.Z.W"`

### Surfaces managed by sync_version.py

`bin/orama-system/SKILL.md`, `CLAUDE.md`, `README.md` badge, root `SKILL.md`,
`docs/PERPLEXITY_BRIDGE.md`, `docs/SYNC_ANALYSIS.md`, `src/orama_system/portal_server.py`,
`bin/config/agent_registry.json`, `bin/orama-system/config/agent_registry.json`,
`bin/orama-system/config/routing_rules.json`, `bin/agents/*/agent.md` (7 files),
`bin/mcp_servers/*.py` docstring headers (2 files), `bin/shared/*.py` headers (3 files),
`platform/windows/install.ps1`, `bin/orama-system/afrp/README.md`,
`bin/orama-system/skills/self-discovery/SKILL.md`, reference docs.

### Surfaces intentionally NOT managed (never bump these)

| Surface | Reason |
|---|---|
| `CHANGELOG.md`, `docs/LESSONS.md` | Historical records — accurate as-is |
| `docs/plans/`, `docs/superpowers/specs/` | Historical planning snapshots |
| `scripts/setup_macos.py` `KNOWN_ALPHACLAW_VERSION` | AlphaClaw runtime version train — separate |
| `openrouter-defaults.md` `Version:` | Skill-doc revision, not package version |

### Test change

`tests/test_version_docs.py` no longer hardcodes any version literal. All 6 tests
import `EXPECTED` from `orama_system._version`:

```python
from orama_system._version import __version__ as EXPECTED
```

The new `test_sync_version_script_leaves_no_stale_surfaces` test runs
`scripts/sync_version.py --check` as part of every CI run — any future drift is
caught before merge.

### Decision

Do **not** reach for `sed -i` or `grep -r … | xargs sed` when bumping versions.
Always use `scripts/sync_version.py`. If a new surface is added (new config file,
new Python module with a `Version:` header), register it in `sync_version.py`'s
`SURFACES` list at the same time it's created.

See: [`docs/wiki/06-multi-agent-collab.md`](../wiki/06-multi-agent-collab.md) (version registry + full surface table)
See: [`src/orama_system/_version.py`](../../src/orama_system/_version.py)
See: [`scripts/sync_version.py`](../../scripts/sync_version.py)
