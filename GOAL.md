# GOAL.md — Complete the oramasys Rename & Methodology Consistency

> **Persistent goal for Claude Code.** Re-read this file at the start of every
> session. Do **not** stop iterating until every acceptance check in § 4 is
> green and verified programmatically. This is the P0 foundation of v1.1 —
> nothing else in v1.1 should land until this is done.

**Repo:** `orama-system` (lockstep partner: `Perpetua-Tools`)
**Branch:** `feat/v1.1/p0-rename` off `main`
**Commit identity:** `cyre <diazMelgarejo@gmail.com>`

---

## 1. The Goal in One Sentence

`orama-system` (and the parts of `Perpetua-Tools` that reference it) must be
**fully consistent on the oramasys naming and methodology** — zero stray
`ultrathink` identifiers except deliberate legacy aliases/shims — with **all
tests, hygiene, and the oramasys-method skill eval passing**.

"Right" = every checkbox in § 4 is checked, each backed by a command whose exit
code you have actually observed as 0 (or whose output you have actually read).
Not "should pass." **Verified passing.**

---

## 2. Why this is not done yet (known defects — verified 2026-06-10)

Re-scan (§ 4.0) before trusting this list; it may be partially fixed.

1. **`bin/shared/ultrathink_core.py`** — the canonical core module, must become
   `oramasys_core.py`. Imported by `bridge_contract.py`, `message_bus.py`,
   `orchestrator_logic.py` via both dotted (`bin.shared.ultrathink_core`) and
   bare (`ultrathink_core`) import paths.

2. **`.claude/skills/agent-methodology/SKILL.md`** — defines Crystallize →
   Architect → Execute → Refine → Verify. **Diverges** from the canonical
   `references/ultrathink-5-stages.md` and mother SKILL.md (Context Immersion →
   Visionary Architecture → Ruthless Refinement → Masterful Execution →
   Crystallize Vision). Fix the card; the canonical source is authoritative.

3. **Duplicated config JSONs** — `bin/config/` and `bin/orama-system/config/`
   both contain `agent_registry.json` + `routing_rules.json` still saying
   `"ultrathink-agent-network"`, `"ultrathink multi-agent"`, and
   `skill_path: "agents/orchestrator/ultrathink-orchestrator.md"`.

4. **`bin/orama-system/afrp/SKILL.md`** — line 3 has a UTF-8 mojibake artifact
   (`â€"` instead of `—`) and body still says "Full ultrathink 5-stage process"
   and "Applying ultrathink MODE 2".

5. **`references/ultrathink-5-stages.md`** — canonical target filename is
   `references/oramasys-5-stages.md`. Keep a stub/redirect at the old name if
   anything still imports it.

**Baseline count (2026-06-10):** 67 residual `ultrathink` refs in production
code/skills (excluding deliberate legacy/shim/alias lines).

> **Keep, do NOT "fix":** anything explicitly marked legacy / deprecated / shim /
> alias / historical (e.g. the `POST /ultrathink` compat route, the
> "treat legacy ultrathink prompts as oramasys" line, the legacy→oramasys map
> in the oramasys-method skill). These are intentional.

---

## 3. The Iteration Loop

Run this loop every session. It is the oramasys 5-stage method applied to itself.

```
1. CONTEXT ── Re-read GOAL.md. Run the § 4.0 baseline scan.
              Search local memory FIRST (frugality — zero cost):
                gbrain search "oramasys rename status"
                gbrain code-def ultrathink_core   (find all importers)
              Mark which § 4 checks already pass. Do NOT redo passing work.

2. ARCHITECT — Pick the SINGLE highest-leverage failing check. Plan the
               smallest change that makes it pass without breaking a green one.

3. EXECUTE ── Make the change. One acceptance criterion at a time.
              If renaming a symbol/module, update ALL importers in the same
              commit (use gbrain code-callers to find them all; do NOT
              rely on grep alone).

4. REFINE ─── Re-run the affected check. Did it go green? Did any previously
              green check go red? Fix regressions before moving on.

5. VERIFY ─── Run the FULL § 4 gate (all checks). Read actual output.
              If all green → § 5 Stop Condition. Else → loop back to 1.
```

**Never** advance on "this should work." Run the command, read the output.

---

## 4. Acceptance Criteria (all must be green)

### 4.0 — Baseline scan (run first, every session)

```bash
grep -rn "ultrathink" \
  --include="*.py" --include="*.json" --include="SKILL.md" \
  --include="*.sh" --include="*.toml" \
  bin/ .claude/ .agents/ api_server.py \
  | grep -vi "legacy\|deprecated\|historical\|shim\|alias\|compat\|successor"
# DONE when: no output (grep exit 1 = nothing found = good)
```

- [ ] **AC1 — agent-methodology matches canonical 5 stages**
  ```bash
  for s in "Context Immersion" "Visionary Architecture" "Ruthless Refinement" \
           "Masterful Execution" "Crystallize Vision"; do
    grep -q "$s" .claude/skills/agent-methodology/SKILL.md \
      || { echo "MISSING: $s"; exit 1; }
  done && echo "AC1 PASS"
  ```

- [ ] **AC2 — core module renamed + all importers updated**
  ```bash
  test ! -f bin/shared/ultrathink_core.py \
    && test -f bin/shared/oramasys_core.py \
    && ! grep -rn "ultrathink_core" --include="*.py" bin/ \
    && echo "AC2 PASS"
  ```

- [ ] **AC3 — config JSONs use oramasys naming (both copies)**
  ```bash
  ! grep -rn "ultrathink-agent-network\|ultrathink multi-agent\|ultrathink-orchestrator" \
    bin/config/ bin/orama-system/config/ \
    && echo "AC3 PASS"
  ```

- [ ] **AC4 — afrp/SKILL.md encoding fixed + methodology refs updated**
  ```bash
  ! grep -nP '\xc3\xa2' bin/orama-system/afrp/SKILL.md \
    && ! grep -ni "ultrathink" bin/orama-system/afrp/SKILL.md \
    && echo "AC4 PASS"
  ```

- [ ] **AC5 — methodology reference file renamed (stub at old path if needed)**
  ```bash
  test -f bin/orama-system/references/oramasys-5-stages.md && echo "AC5 PASS"
  ```

- [ ] **AC6 — full test suite green**
  ```bash
  python -m pytest tests/ bin/orama-system/cidf/tests/ -q
  # Expect: "N passed" with 0 failed. Read the actual count.
  ```

- [ ] **AC7 — repo hygiene green**
  ```bash
  python scripts/review/repo_hygiene.py .
  # Expect exit 0.
  ```

- [ ] **AC8 — oramasys-method skill eval: precision 1.00, recall ≥ 0.90**
  ```bash
  python scripts/eval/oramasys_trigger_eval.py
  # Expect: Precision: 1.00  Recall: >= 0.90  AC8 PASS
  ```

- [ ] **AC9 — Perpetua-Tools lockstep**
  ```bash
  cd ../Perpetua-Tools
  ! grep -rn "ultrathink_core\|ultrathink-agent-network" \
    --include="*.py" --include="*.json" orchestrator/ \
    && echo "AC9 PASS"
  cd -
  ```

- [ ] **AC10 — lesson captured**
  ```bash
  grep -q "oramasys rename" .claude/lessons/LESSONS.md && echo "AC10 PASS"
  ```

---

## 5. Stop Condition

Stop **only** when:
1. § 4.0 baseline scan returns nothing (no output), AND
2. AC1–AC10 each printed their PASS line / 0 failures **in this session**, AND
3. Work is committed on `feat/v1.1/p0-rename` with a clear message, AND
4. LESSONS.md entry appended (AC10).

Print: `GOAL COMPLETE — oramasys rename consistent, all gates green.`
Then open the PR or print the exact `gh pr create` command.

---

## 6. Anti-Patterns

- ❌ Marking a checkbox without running its command and reading the output.
- ❌ "Tests should pass now" — run them. Every time. Read the count.
- ❌ Renaming a symbol without updating every importer in the same commit.
- ❌ Deleting the deliberate legacy `/ultrathink` shim or the alias lines — intentional.
- ❌ Editing `references/ultrathink-5-stages.md` content to match agent-methodology
     — it is the CANONICAL source; fix the card, not the source.
- ❌ Skipping gbrain search and defaulting to Grep for "where is X used".
- ❌ `git push --force` to a shared branch; use `--force-with-lease` on own branch only.
- ❌ Spinning on the same failing check >3 times with the same error. Instead:
     write the error to LESSONS.md and ask the human.

---

## 7. Operating Invariants

- **Search first:** `gbrain code-callers <symbol>` before any rename; Grep only
  for known exact strings.
- **Frugality chain:** gbrain → CRG → Grep → Brave → Perplexity. Never skip tiers.
- **Lockstep PT:** cross-repo renames land on the same branch name in both repos.
- **Pydantic V2** (`@field_validator`), snake_case files, conventional commits.
- **CHANGELOG** entry in both repos for any cross-repo change.
- **Verify programmatically.** Never visually.

---

## 8. Progress Log

<!-- Append newest session at top. Template:
## YYYY-MM-DD — <session note>
### Checks green this session: AC1 ✓, AC6 ✓ (142 passed) ...
### Changed: ...
### Still failing: ...
### Next action: ...
-->

## 2026-06-10 — Session 0 (goal authored)
### Checks green this session
- None yet (goal just written; 67 residual refs confirmed in baseline scan)
### Known failing
- AC1 (agent-methodology diverges), AC2 (ultrathink_core.py exists),
  AC3 (config JSONs), AC4 (afrp mojibake), AC5 (ref file not renamed)
### Next action
- Run § 4.0 scan, pick AC2 (core module rename) as highest-leverage first step
  (fixes the most importers in one commit)
