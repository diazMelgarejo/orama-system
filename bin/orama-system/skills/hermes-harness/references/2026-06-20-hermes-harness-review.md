# Hermes-Harness Review — 2026-06-20

**Reviewed by:** Claude Sonnet 4.6 + CRG (`detect_changes_tool` / `semantic_search_nodes_tool`)
**Scope:** `bin/orama-system/skills/hermes-harness/` (canonical) + `.agents/skills/hermes-harness/SKILL.md` (PT thin wrapper)
**Branch at review:** `feat/openclaw-codex-app-server` (pushed `544dc93`)
**Tools:** CRG graph review + direct file read; `codex review --commit HEAD` stalled on `list_graph_stats_tool` MCP call and did not produce output.

---

## What It Is

Windows bring-up skill for Hermes Agent (NousResearch) as a coding partner shell alongside OpenClaw. Payload:

| File | Purpose |
| --- | --- |
| `SKILL.md` | Windows bring-up: Hermes clone/repair, provider config, Codex/Gemini/AGY CLI install, skill import, verification checklist |
| `scripts/install_hermes_thin_skills.py` | Idempotent installer — writes 3 thin command wrappers to `$HERMES_HOME/skills/pt-orama/` |
| `commands/pt-orama-council/SKILL.md` | Canonical command card — PT-orama council coordination |
| `commands/pt-orama-review/SKILL.md` | Canonical command card — findings-first review |
| `commands/pt-orama-delegate/SKILL.md` | Canonical command card — bounded specialist delegation |
| `references/` | Cross-harness docs, fork inventory, council review gates |

The PT commit (`8acec8c`) adds a matching thin wrapper at `.agents/skills/hermes-harness/SKILL.md` using the same delegate-to-canonical pattern as `Perpetua-Tools/`, `perpetua-config/`, etc.

---

## Strengths

- `is_managed_wrapper()` uses a YAML sentinel (`created_by: agent`) so it never silently overwrites user-created wrappers — correct idempotency model.
- `install()` validates all 3 canonical command cards exist before writing anything (`scripts/install_hermes_thin_skills.py:122–124`), so a partial clone fails loudly rather than writing broken wrappers.
- `--dry-run` supported throughout `install()` and `main()`.
- SKILL.md steps 1 and 3 both use the save-first pattern instead of `irm|iex`, and SKILL.md honestly acknowledges the residual trust gap (bootstrap script itself not independently signed) rather than leaving a placeholder comment.
- `--audit=moderate` on npm installs flags known-vulnerable transitive packages without pinning a version number that will go stale.

---

## Issues

### Important

**I-1 — `wrapper_text()` generates the unsafe AGY installer form**
`scripts/install_hermes_thin_skills.py:87`

SKILL.md step 3 correctly uses the save-first pattern for the AGY installer. `wrapper_text()` generates wrappers that contain the raw `irm ... | iex` line instead. Every Hermes command card written by `--install` teaches the unsafe pattern to Windows operators.

Fix: replace the `irm ... | iex` line in `wrapper_text()` with the save-first form used in SKILL.md step 3.

**I-2 — Stale branch/PR reference baked into every generated wrapper**
`scripts/install_hermes_thin_skills.py:68–70`

```python
- Branch/PR at install time: `codex/hermes-ecc-harness-skills` / PR #96
```

Already wrong at review time (code lives on `feat/openclaw-codex-app-server`, not that branch, and PR #96 is not the current PR). Every `--install` run stamps this into wrapper files permanently. Either drop the branch/PR line or derive it dynamically with `git rev-parse --abbrev-ref HEAD` at install time.

---

### Notable

**N-1 — `REPO_ROOT` resolved by hardcoded ancestor depth**
`scripts/install_hermes_thin_skills.py:10`

```python
REPO_ROOT = Path(__file__).resolve().parents[5]
```

The script is exactly 5 levels deep from the repo root today. If it is ever moved, the canonical-card existence check resolves the wrong path and throws a misleading `FileNotFoundError`. A `subprocess.check_output(["git", "rev-parse", "--show-toplevel"])` fallback with `parents[5]` as the non-git backup would be more resilient.

**N-2 — `verify()` and `is_managed_wrapper()` diverge on what "managed" means**
`scripts/install_hermes_thin_skills.py:149–163` vs `103–118`

`verify()` checks for 4 content strings but never checks for `MANAGED_MARKER`. A wrapper whose `created_by: agent` frontmatter line was manually removed would pass `verify()` but fail `is_managed_wrapper()`, so `--install` would then skip it as "unmanaged" while `--verify` reports it as passing. The two functions should agree on the managed definition.

**N-3 — Zero test coverage on all 5 functions**
CRG reported: `install`, `is_managed_wrapper`, `main`, `verify`, `wrapper_text` — all untested.

The idempotency logic in `is_managed_wrapper` (YAML frontmatter scanning, sentinel matching) is the kind of thing that silently breaks when frontmatter format drifts. A pytest fixture covering managed / unmanaged / missing wrapper states in a `tmp_path` would be low-effort and high-value.

---

## CRG Blast-Radius Note

CRG reported 500 impacted nodes across 92 files. This is graph overcounting from generic Python script ecosystem patterns — none of the listed files import or call the installer. `detect_changes_tool` on `SKILL.md` alone scored 0.00 risk. Real blast radius is zero outside `bin/orama-system/skills/hermes-harness/`.

---

## Verdict

Ship-ready as pushed. No correctness bugs, no security issues in the committed code. Items I-1 and I-2 are worth a follow-up commit before anyone runs `--install` on a Windows host — the `irm|iex` inconsistency in `wrapper_text()` is the only thing that could actively mislead a Windows operator. N-1 through N-3 are best-effort cleanup, not blockers.
