> ✅ **RESOLVED 2026-06-14** — weaning goal met: 0 `Canonical:.*CLAUDE-instru` refs in skills, `docs/how-to/` present; regression guard `scripts/check_no_instru_canonical_in_skills.sh` shipped.

# CLAUDE-instru Progressive Weaning — Autoplan

> **Date:** 2026-05-23  
> **Status:** Draft (auto-reviewed)  
> **Scope:** orama-system + OpenClaw multi-repo navigation  
> **Backup:** `OpenClaw/CLAUDE-instru.md.20260523.BAK`

---

## Problem

`CLAUDE-instru.md` at the OpenClaw hub was acting as an accidental **content owner** for install checklists, hardware policy, and tool-chain rules. Skills and profiles duplicated that content via `Canonical: CLAUDE-instru.md` pointers, causing drift and token waste. Agents read the external hub when in-repo references already exist.

## Goal

**Progressive weaning:** `CLAUDE-instru.md` remains the **cross-repo navigator** (registry, doc index, “where to look”). All **executable** onboarding and agent behavior lives in orama-system canonicals:

| Topic | Canonical in-repo |
|-------|-------------------|
| First-run install | `bin/orama-system/references/first-run-install.md` + `scripts/first-run-install.sh` |
| Tool chain | `bin/orama-system/skills/code-review/references/tool-chain.md` |
| Profiles | `bin/orama-system/skills/code-review/profiles/` |
| Hardware (detail) | `docs/v2/17-hardware-policy-enforcement.md`, `CLAUDE.md` §0 summary |

## Phases

### Phase 1 — Inventory (this session)

- `rg CLAUDE-instru` across orama-system (7 md hits in repo root/docs/scripts; 0 in `bin/orama-system/skills`)
- Profiles under `skills/code-review/profiles/` already point at in-repo paths
- gbrain search blocked (DB unreachable in sandbox) — grep is source of truth for this pass

### Phase 2 — Skills (done)

- Remove `Canonical: CLAUDE-instru` from skill SKILL.md files
- Skills route to `references/` and `references/first-run-install.md`

### Phase 3 — Scripts + docs (in progress)

- `first-run-install.sh`: resume state v2, visible `ollama pull` + `setup-embeddings` on `run` only
- `ensure_requirements.sh`, wiki, UNIFIED plan: replace instru pointers with in-repo links where duplicated
- Keep **one** navigator link in `first-run-install.md` for cross-repo context

### Phase 4 — Profiles (done / maintain)

- `profiles/J-drona23-v5/`, `CLAUDE.coding.md`, `CLAUDE.agents.md` → `tool-chain.md`, `first-run-install.md`
- No `OpenClaw/profiles/` top-level dir; canonical tree is under code-review skill

### Phase 5 — Navigator-only external pointer

- `CLAUDE-instru.md` keeps §0 outline → `first-run-install.md`
- `orama-system/CLAUDE.md` keeps single link to `../CLAUDE-instru.md` for hub routing
- Deprecation banner in `CLAUDE-instru.md` (optional): “Install detail: orama-system/bin/orama-system/references/first-run-install.md”

---

## First-run resume design (shipped in script)

**File:** `~/.orama-system/first-run.json` (version 2)

```json
{
  "version": 2,
  "components": {
    "ollama": {
      "status": "ok",
      "models": {
        "qwen3.5:9b-nvfp4": { "status": "ok", "updated_at": "..." },
        "bge-m3": { "status": "pulling", "updated_at": "..." }
      }
    },
    "embeddings": { "status": "ok", "detail": "bge-m3 wired" }
  },
  "completed_at": "..."
}
```

| Command | Behavior |
|---------|----------|
| `status` | Fast probes; no pull; no setup-embeddings |
| `run` | Pulls missing models with `ollama pull` progress; runs setup-embeddings with stdout |
| `run --force` | Re-validates checks; **skips** heavy steps if component already `ok` |
| Re-run after interrupt | Resumes only models not `ok` in API tags |

---

## CEO Review (auto-decided)

**Mode:** HOLD SCOPE — weaning is hygiene, not product expansion.

| Finding | Decision | Principle |
|---------|----------|-----------|
| Expand CLAUDE-instru with more sections | **Reject** — opposite of goal | Scope discipline |
| Delete CLAUDE-instru entirely | **Reject** — breaks multi-repo hub | User trust / migration cost |
| Single canonical install doc | **Accept** | One source of truth |
| CI grep gate for skill Canonical lines | **Accept** (phase 3b) | Fail closed on regression |

**10-star check:** Developer opens one repo, runs one script, sees progress — **yes** after first-run resume work.

---

## Eng Review (auto-decided)

| Finding | Decision | Rationale |
|---------|----------|-----------|
| State file without jq | **Keep** python3 JSON helpers | Matches existing script style |
| Separate `probe_ollama` vs `run_ollama_models` | **Accept** | Guarantees status &lt;5s |
| Version bump state v1→v2 | **Accept** — additive `models` map | Backward compatible reads |
| Pre-commit grep | **Accept** as `scripts/check_no_instru_canonical_in_skills.sh` | Cheap guard |

**Risks:** `ollama pull` still requires user to start Ollama daemon — documented in reference §0.3.

---

## DX Review (auto-decided)

| Touchpoint | Score | What makes it a 10 |
|------------|-------|-------------------|
| `first-run-install.sh run` | 8/10 | Visible pull progress + resume (shipped) |
| `status` speed | 9/10 | No heavy work |
| Discoverability from OpenClaw | 7/10 | Add one line to OpenClaw `CLAUDE.md` → first-run reference |
| Error after Ctrl+C | 9/10 | Re-run resumes per model |
| Docs duplication | 6/10 | Still 2 navigator links to instru in reference — intentional |

**DX recommendation:** Document in `first-run-install.md` heal table (done). Optional: `first-run-install.sh run --only ollama` in v2.1 — **defer**.

---

## Decision Audit Trail

| ID | Decision | Alternatives | Why |
|----|----------|--------------|-----|
| D1 | Heavy steps only on `run` | Always pull on status | User requirement &lt;5s status |
| D2 | `--force` skips satisfied heavy steps | Force re-pulls everything | Prior spec + avoids multi-GB re-download |
| D3 | Per-model state under `ollama.models` | Monolithic ollama flag only | Resume after interrupt |
| D4 | Keep CLAUDE-instru as navigator | Full migration off hub | Multi-repo still needs registry |
| D5 | Grep gate on skills, not all md | Repo-wide ban | Navigators legitimately link outward |
| D6 | Profiles live in code-review skill | Top-level OpenClaw/profiles | Already canonical; no second tree |

---

## Slow-wean playbook (recommended sequence)

1. **Forever in CLAUDE-instru:** repo registry (§1), cross-repo doc index, “start here” for new machines (one paragraph + link).
2. **Migrate to in-repo:** install steps, hardware probe detail, tool-chain order, profile behavior.
3. **Order of file classes:** skills (done) → scripts (`ensure_requirements.sh`) → docs/wiki → `CLAUDE.md` navigators (keep link only) → optional instru deprecation banner.
4. **CI gate:** `rg 'Canonical:.*CLAUDE-instru' bin/orama-system/skills` → must be 0. *(Checklist item for future CI — run locally before merge until wired.)*
5. **Deprecation:** Comment in `orama-system/CLAUDE.md`: “Install: see `bin/orama-system/references/first-run-install.md` (not CLAUDE-instru §0 body).”

---

## Test plan

- [ ] `bash -n bin/orama-system/scripts/first-run-install.sh`
- [ ] `time bash bin/orama-system/scripts/first-run-install.sh status` &lt; 5s
- [ ] Interrupt `ollama pull`; re-run `run`; only incomplete model pulls
- [ ] `rg 'Canonical:.*CLAUDE-instru' bin/orama-system/skills` → 0 matches

---

## Final Approval Gate (for human)

| Item | Recommendation | Override? |
|------|----------------|-----------|
| Keep CLAUDE-instru hub file | Yes — navigator only | |
| CI grep gate | Yes — skills only | |
| Defer `run --only <component>` | Yes | |
| Trim duplicate hardware prose in instru §5 | Optional taste — do when touching instru next | **Challenge if you want zero duplication now** |
| gbrain re-index after doc moves | Run `/sync-gbrain` when DB up | |

---

## Open TODOs (session gaps — 2026-05-25)

> Fortify / pressure-test gaps live in [`pressure-test-notes.md`](../../bin/orama-system/skills/code-review/references/pressure-test-notes.md). Agent host map: [`docs/reference/agent-first-open-visibility.md`](../reference/agent-first-open-visibility.md).

### Phase 3 — scripts + docs (remaining)

- [ ] Replace duplicated install/hardware prose in **`scripts/ensure_requirements.sh`** (and callers) with links to [`first-run-install.md`](../../bin/orama-system/references/first-run-install.md) — remove embedded `CLAUDE-instru` body strings
- [ ] Add **`docs/how-to/README.md`** Diataxis index (one entry: [`first-run-and-code-review.md`](../how-to/first-run-and-code-review.md))
- [ ] One-line E2E link in [`orama-system/CLAUDE.md`](../../CLAUDE.md) §3 skills table → how-to (DX 7/10 in autoplan)

### Phase 3b — CI gate (accepted, not shipped)

- [ ] Ship `scripts/check_no_instru_canonical_in_skills.sh` (or equivalent): `rg 'Canonical:.*CLAUDE-instru' bin/orama-system/skills` → must be 0
- [ ] Wire gate into pre-commit or CI when touching skills tree

### Cross-repo (out of repo scope)

- [ ] OpenClaw `CLAUDE.md` discoverability line → [`first-run-install.md`](../../bin/orama-system/references/first-run-install.md) (DX autoplan item)