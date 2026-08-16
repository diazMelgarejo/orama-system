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
> | macOS ` 2`/` 3` dupes in `.git/` internals | [AlphaClaw wiki/07](https://github.com/diazMelgarejo/AlphaClaw/blob/main/docs/wiki/07-duplicate-files.md) | [May 2026 archive](archive/2026-05--May-Archived-LESSONS.md) §2026-05-27 + §2026-05-31 |
> | No sleep chains (`sleep N && cmd`) | [skills/no-sleep-chains/SKILL.md](../bin/orama-system/skills/no-sleep-chains/SKILL.md) | [May 2026 archive](archive/2026-05--May-Archived-LESSONS.md) §2026-05-16 |
> | Git identity + Cursor commit policy | [docs/wiki/08-git-hygiene-and-branching.md](wiki/08-git-hygiene-and-branching.md) | AlphaClaw `scripts/git/check_identity.sh` |
> | gbrain pooler write failures + resync | [gstack/SKILL.md §GBrain Ops](../bin/orama-system/gstack/SKILL.md) | This file §2026-05-30 (note: no §2026-05-30 entry exists in the log, before or after this archival — pre-existing stale reference, not touched) |
> | Migration gate ladder (Gate 0→4) | [PT docs/MIGRATION.md](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/MIGRATION.md) | This file §2026-05-30 T7 survey (same pre-existing stale reference as above) |
> | Hermes integration authority (envelope + thin wrappers) | [hermes-universal-invocation-protocol.md](../bin/orama-system/skills/hermes-harness/references/hermes-universal-invocation-protocol.md) | PT [LESSONS.md §2026-06-28](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/LESSONS.md) |
> | LAN peer Mac↔Win (Hermes operator playbook) | [lan-peer-self-talk.md § Operator playbook](../bin/orama-system/skills/hermes-harness/references/lan-peer-self-talk.md#operator-playbook) | [docs/guides/lan-peer-mac-win-operator.md](guides/lan-peer-mac-win-operator.md) |
> | Mac↔Win co-orchestrator (file inbox + ws-peer GO) | [mac-co-orchestrator-playbook.md](../bin/orama-system/skills/hermes-harness/references/mac-co-orchestrator-playbook.md) | PT [LESSONS.md §2026-06-28](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/LESSONS.md) |
> | AlphaClaw branch roles + invariants | [AlphaClaw CLAUDE.md](../../AlphaClaw/CLAUDE.md) | AlphaClaw wiki/01 |
> | skillify/gstack permanent thin-wrapper exemption | [scripts/consolidate-skills.sh](../scripts/consolidate-skills.sh) | This file §2026-07-24 (note: no §2026-07-24 entry exists in the log, before or after this archival — pre-existing stale reference, not touched) + [skillify SKILL.md](../bin/orama-system/skills/skillify/SKILL.md) § Non-Negotiables |
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

### 2026-08-08 — ALWAYS verify, NEVER trust: PR #283's merged tree silently dropped OSSF-1 content | Claude

**Scope:** orama-system git-history-surgery doctrine + PR #283 (`2026-08-07-001-harden-skills-vendor-blend-lessons`)

**What happened:** Asked to add "always check whether local `main`'s content
exists in origin's rewritten history" to the git-history-surgery skill, this
session's own local branch for that PR was checked against `origin/main` as a
live test case. `git cherry -v origin/main <branch>` reported 17 `+`
candidates out of 1293 commits; message cross-check resolved all but 2 as
SAFE-BEHIND (already upstream under different SHAs). The remaining 2 were the
branch's own OSSF-1 pilot work. Fetching the PR's *source* head via
`gh pr view 283 --json headRefOid` returned `73ba185c...` — **not** the local
branch tip (`e5e2cc51...`) — because an earlier "cherry-reanchor conflict
resolution" pass in this same session had produced a different final commit.
(`headRefOid` / `head.sha` is the PR source-branch tip; treat it as a source
SHA unless separately verified as the landed tree — for merge-commit merges
it often matches, but squash/rebase can diverge.) A direct tree diff between
the local tip and that source head showed the merge had dropped, relative to
the branch's real work: the OSSF-1 pre-commit
gate script (`scripts/hooks/check_ossf1_skill_md.py`, 143 lines), its
`.githooks/pre-commit` wiring (9 lines), the progressive-disclosure reference
card `bin/orama-system/skills/hermes-harness/references/ossf-operating-procedures.md`
(439 lines), and three other skills' OSSF-1-pilot SKILL.md content
(`pt-orama-security-planner`, `hardware-affinity-gate`, `openclaw-skills`) —
while `hermes-harness/SKILL.md` reverted from its intended thin-pointer form
back to the pre-split 439-line monolith. None of this had been noticed until
this explicit re-verification.

**Operational lesson:** a conflict-resolution/reanchor pass that reports
"CONFIRMED-SAFE" or "aligned" is a claim, not a fact — the only proof is a
direct tree/content diff between what was *intended* (the branch's real tip)
and what actually *landed* (the merge commit on `origin/main`), never the
agent's own summary of its own resolution. This is the same failure shape as
[[feedback_verify_before_replaying_past_agent_work]] one layer up: it applies
even to your own prior-session git-surgery output, not just a different
agent's. Ahead/behind counts and even `git cherry -v`'s `+`/`-` split are
necessary but not sufficient — a `-` (patch-ID match) can still hide a
partial merge that dropped some hunks while keeping others, so the real gate
is a full tree/stat diff against the landed merge commit
(`mergeCommit.oid` / `merge_commit_sha`), not an assumed local tip and not
`headRefOid` alone (use the source head only when the merge strategy is a
plain merge commit and you have confirmed the trees match).

**Cross-references:**

- Doctrine added this session: [`git-history-surgery/references/reanchor-after-rewrite.md`](../bin/orama-system/skills/git-history-surgery/references/reanchor-after-rewrite.md)
  § "ALWAYS check your own main before syncing it — safe-behind vs needs-reanchor"
- Decision Flow pointer: [`git-history-surgery/SKILL.md`](../bin/orama-system/skills/git-history-surgery/SKILL.md) item 2
- Content believed lost: `scripts/hooks/check_ossf1_skill_md.py`,
  `.githooks/pre-commit` (its wiring),
  `bin/orama-system/skills/hermes-harness/references/ossf-operating-procedures.md`,
  `.agents/skills/pt-orama-security-planner/SKILL.md`,
  `bin/orama-system/skills/hardware-affinity-gate/SKILL.md`,
  `bin/orama-system/skills/openclaw-skills/SKILL.md` — **not yet restored;
  flagged for follow-up, no fix applied in this entry.**
- PR: [#283](https://github.com/diazMelgarejo/orama-system/pull/283), merged
  `2026-08-08T02:52:18Z`, source head (`headRefOid`) `73ba185c`, landed
  merge commit (`merge_commit_sha`) `b0e09b10` (same tree as the source head
  for this merge-commit merge; record both so squash/rebase cases stay
  unambiguous).
- **Update — 2026-08-08:** all six paths above restored by
  [PR #291](https://github.com/diazMelgarejo/orama-system/pull/291). The
  "not yet restored" note above is the original incident-time record and is
  preserved as-is for history; this line records current status only.

---

### 2026-07-24 — Formalized skillify/gstack permanent thin-wrapper exemption | Claude

**Scope:** orama-system `.claude/skills/*` -> `bin/orama-system/skills/*` consolidation

**What changed:** `scripts/consolidate-skills.sh` now hardcodes a permanent
`EXEMPT_SKILLS=("skillify" "gstack")` skip list, checked before any merge or
wrapper conversion — not a CLI flag, so it cannot be silently overridden by an
invocation. Both `skillify` copies (`.claude/skills/skillify/SKILL.md` and the
canonical `bin/orama-system/skills/skillify/SKILL.md`) got a matching
Non-Negotiables bullet stating the exemption explicitly.

**Operational lesson:** this rule already existed as tribal knowledge scattered
across two places — the `73f100c5` doctrine-wiring commit's message ("gstack
has no wrapper mirror") and the 2026-07-22 incident log in
`skillify/references/dogfood-upgrade-log.md` (gstack's own bundled `skillify`
skill, an unrelated tool sharing the same name, was silently clobbered when a
wrapper-generator script's `TARGET_ROOTS` briefly included `~/.claude/skills`)
— but was never codified as an enforced rule in the consolidation tool itself.
A user request to "codify and formalize" it surfaced that gap: knowing a rule
happened once is not the same as the tool refusing to repeat it. The exemption
is scoped precisely: `skillify` (name collision, proven incident) and the bare
`gstack` slug (same class of risk, pre-empted after this repo's own
gstack-integration sub-skill was renamed to the disambiguated `gstack-gbrain`
on 2026-07-22) — `gstack-gbrain` itself is NOT exempt, since it has no
collision risk and was already safely wrapped before this session.

**Cross-references:**

- Enforcement: `scripts/consolidate-skills.sh` (header comment + `EXEMPT_SKILLS`)
- Policy statement: `bin/orama-system/skills/skillify/SKILL.md` and
  `.claude/skills/skillify/SKILL.md` § Non-Negotiables
- Incident log: `bin/orama-system/skills/skillify/references/dogfood-upgrade-log.md`
- Doctrine origin: commit `73f100c5` ("Post-Review Micro-Remediation Pattern")

---

### 2026-07-18 — Clean replacement PR after scrub/reanchor churn | Codex + Claude

**Scope:** orama-system + Perpetua-Tools git-history-surgery doctrine

**What changed:** The git-history-surgery skill now treats metadata scrub,
current-tree hygiene, PR-unique blob hygiene, and repository-wide all-ref blob
hygiene as separate proof gates. It also documents the clean replacement PR
option: when the final PR tree is correct but intervening branch history is
contaminated or too noisy to review safely, preserve the old ref, replay the
final tree onto current `origin/main`, prove the saved diff matches, then open a
replacement PR.

**Operational lesson:** Tree-twin reanchor is the right first diagnostic after a
rewrite, but blob changes can make an exact twin impossible. In that Case C,
switch from "preserve this branch ancestry" to "preserve this reviewed content"
and keep scope language precise. A clean PR-unique scan does not prove inherited
main history is clean.

**Cross-references:**

- Skill entrypoint: `bin/orama-system/skills/git-history-surgery/SKILL.md`
- Reanchor doctrine: `bin/orama-system/skills/git-history-surgery/references/reanchor-after-rewrite.md`
- Expunge + clean replacement checklist: `bin/orama-system/skills/git-history-surgery/references/expunge-contaminated-history.md`
- PT companion memory: `../../perplexity-api/Perpetua-Tools/.agent/memory/working/PR258_CODE_REVIEW_COORDINATION_SYNTHESIS_2026-07-18.md`

**Validation rule:** Before declaring scrub/surgery complete, name the exact
scope that passed and cite the evidence for that scope. If repository-wide
all-ref scanning is deferred or still has inherited hits, say so.

---

### 2026-07-18 — ClinePass route auth must be verified before fan-out | Codex

**Scope:** orama-system + Perpetua-Tools cross-repo agent dispatch

**What changed:** Added a parallel `clinepass-deepseek-flash` skill for
non-interactive Cline fan-out using the ClinePass DeepSeek V4 Flash route at
high reasoning. The existing GLM ClinePass route remains valid; this is an
additional low-cost/free-route profile, not a replacement.

**Operational lesson:** Do not treat a ClinePass model slug as sufficient proof
that Cline is authenticated/configured to ClinePass. A headless smoke run can
accept the CLI flag shape while still routing through another provider, where
the ClinePass model slug is invalid. Run a harmless provider-auth smoke test
before dispatch, and repair Cline auth/config rather than silently switching
models.

**Cross-references:**

- New skill: `bin/orama-system/skills/clinepass-deepseek-flash/SKILL.md`
- PT companion lesson: `../../perplexity-api/Perpetua-Tools/.agent/memory/semantic/LESSONS.md`
- Existing Cline route: `bin/orama-system/skills/cline-openclaw-agent/SKILL.md`
- Kimi fan-out parallel: `bin/orama-system/skills/kimi-agent/SKILL.md`

**Validation:** EXA found the official Cline CLI/ClinePass docs; Firecrawl
scraped the Cline CLI overview; local `cline task --help` verified the installed
CLI flag shape; the new skill validated with `quick_validate.py`.

---

### 2026-07-18 — Private literals and local topology stay local | Codex

**Scope:** orama-system + Perpetua-Tools cross-repo guard parity

**What changed:** The repositories now treat private owner identity literals,
forbidden attribution literals, live device topology, and workstation-specific
paths as local-only inputs. Tracked code may define policy, runtime loaders,
synthetic fixtures, and hygiene checks, but it must not contain the actual
values or encoded forms.

**Operational lesson:** Do not stop using `.agent/memory/**`; sanitize and
commit it when it carries durable knowledge. The durable rule is that memory,
docs, templates, tests, hooks, commit messages, and PR text must describe the
category without quoting private literals.

**Cross-references:**

- Orama memory note: `.agent/memory/working/PRIVATE_LITERALS_AND_LOCAL_TOPOLOGY_V2_LESSON_2026-07-18.md`
- PT companion memory note: `../../perplexity-api/Perpetua-Tools/.agent/memory/working/PRIVATE_LITERALS_AND_LOCAL_TOPOLOGY_V2_LESSON_2026-07-18.md`
- Orama policy discussion: `docs/wiki/08-git-hygiene-and-branching.md`
- PT rendered lessons: `../../perplexity-api/Perpetua-Tools/docs/LESSONS.md`

**Validation rule:** Before committing related work, run a case-insensitive
tracked-file scan for private-literal categories and encoded forms, then run
repo hygiene.

---

### 2026-07-07 — PR description append-only lesson (Codex failure + remediation) | Claude

**Session:** PR #141 lesson recording
**Incident:** Codex agent violated the append-only principle by replacing PR #141's description with the latest delta instead of preserving the original corpus and appending updates below it.

**What went wrong:**
1. Codex overwrote the PR description — erasing the original purpose, non-goals, and validation notes that served as historical review artifacts.
2. Codex then created a "companion lesson file" (`docs/lessons/2026-07-07-pr-description-append-only.md`) instead of adding the lesson to canonical `docs/LESSONS.md` — the exact anti-pattern it was documenting. The companion file was an orphan; nothing referenced it from the main LESSONS.md.

**Root cause:** Applying the anti-pattern while documenting it. Instead of preserving + appending to the canonical location, Codex created a new file in a new location — the same clobber behavior it was trying to prevent.

**Lessons learned:**

1. **PR descriptions are historical review artifacts.** Preserve the original purpose, non-goals, constraints, and validation notes at the top. Add later repair notes below in an append-only log section (e.g., `## Append-only update log`). Never replace the original corpus with the latest summary.

2. **Canonical lesson files are the only durable record.** When recording a lesson, add it to the canonical LESSONS.md Sessions Log per its own rules ("Prepend new entries at the top"). Creating companion files in side directories produces orphans that future agents won't discover.

3. **Do not edit large files through truncated connector content.** If a file is too large for the connector, do not rewrite it. Instead: (a) add to the canonical file via a targeted edit at the documented insertion point, or (b) if the file truly cannot be accessed, record the lesson in the Sessions Log with a cross-reference to the context that enables future graduation.

4. **The remedy must not repeat the disease.** An agent that fixes a clobbering bug by creating a new sidecar file (instead of appending to the canonical location) has not fixed the underlying pattern failure.

**Remediation applied:**
- PR #141 body restored: original summary/purpose/non-goals/validation notes preserved at top; later changes appended under `## Append-only update log`.
- Companion lesson file deleted from `docs/lessons/` — lesson moved to this canonical Sessions Log entry.
- Codex's attempted `docs/LESSONS.md` edit was reverted (connector returned truncated file; replacing it would have deleted unseen historical lessons).

**Cross-references:**
- PR #141: https://github.com/diazMelgarejo/orama-system/pull/141
- This lesson also recorded in Perpetua-Tools `.agent/memory/semantic/LESSONS.md` (lesson ID TBD)

---

### 2026-07-04 — Fable-5 LLM Council (Tasks 1-2 complete, Task 3 ready) + WhatsApp MVP documented | Claude

**Session:** Subagent-driven development (parallel fixers + explorers)  
**Deliverables:** Task 1 (git-rebase-safety skill, a24998a), Task 2 (tier-based-routing v3 fixes, ff4175b), WhatsApp QR Gateway (canonical skill + 5-phase roadmap, 14b9316 + 362ea98)

**Learnings:**

1. **Quality gates catch fabricated evidence.** Task 2 v2 fixer claimed "all 10 examples tested against real code" but re-review found 3/5 critical findings still unfixed. Root cause: fixer ran static validation (imports, paths) but NOT live execution. Pattern: `frugality_router.resolve_route()` needs real ToolCallSpec + actual registry, not mocked dict. Cost formula examples still showed wrong values ($0.009 vs $3.00). Lesson: live execution test is non-negotiable before "code tested" claims. Validation protocol added to Task 3 brief (example: run python3 with real backend, capture output).

2. **Parallel subagent fixers work well.** Fixer #1 (Tier 1 example + costs) and Fixer #2 (contradictions removal) ran in parallel without collision. Both approved on re-review. No re-do cycles. Strategy: independent scopes (example + costs vs. deletion + refactoring) can parallelize; validation must serialize (re-review after all fixers).

3. **Tier-based routing pattern validated:** Tier 1 (Ollama, 10s) → Tier 2 (GPU/GLM, 10s) → Tier 3 (HF free, 10s) → Tier 4+ (cloud, escalation) works. Real error: Tier 1 example needs `BackendRegistry.autodetect()`, not empty dict. Cost formula is flat `0.001 * est_tokens` across all escalation tiers (no per-tier variation). Documented in v3 fixes, committed.

4. **Bearer token auth sufficient for LAN gateways.** WhatsApp MVP (port 8555) uses simple bearer tokens (from QR code). No JWT/OAuth needed for internal ops. Graceful degradation > strict timeouts: users prefer "command queued for async" over "timeout, try again." Single-user assumption scales well for MVP; RBAC deferred to Phase 3.

5. **Voice + OCR fallback to text is robust.** WhatsApp feature tests fallback: if transcription fails, ask for text. If OCR fails, ask for text. Both handled cleanly without confusion. Users accept fallback as a feature, not a bug.

6. **Real evidence validation is critical.** Task 1 fixer initially ran validation against non-existent path (~/.alphaclaw/.openclaw/workspace). Re-check: actual reanchor_scan.sh on real orama-system repo confirmed 34 branches (20 merged, 14 needs-reanchor, 0 orphan). Lesson: always validate against live targets, never assume paths exist.

7. **Fable-5 council consensus model selection works.** 7/7 agents on Tasks 1-2 (highest consensus), 6/7 on Task 3 (high), 5/7 on Tasks 4-11 (medium). Consensus tiers help prioritize: do the 7/7 tasks first, use cheaper models (GLM-5.2) for mechanical upgrades (Task 3), save Sonnet for architecture/review work. Task 3 dispatch is GLM-5.2 (cheap), expected 8-12k tokens.

**Continuity anchors:**
- Progress ledger: `.superpowers/sdd/progress.md` (Tasks 1-2 complete, Task 3 ready)
- Task 3 brief: `.superpowers/sdd/task-3-model-routing-check-upgrade.md` (8 implementation steps, all scoped)
- Fable-5 plan: `docs/superpowers/plans/2026-07-04-fable5-llm-council-implementation-plan.md` (full roadmap Tasks 1-11)
- WhatsApp plan: `docs/plans/2026-07-04-whatsapp-qr-gateway-implementation-plan.md` (5-phase roadmap, MVP live)

**Next session:** Dispatch Task 3 fixer (GLM-5.2, ~8-12k tokens). If approved, start Task 4 (mcp-orchestration upgrade). Token budget: ~45k remaining (sufficient for Task 3 + part of Task 4).

---

### 2026-06-28 — Cycle 005 coder + Ladder F (operator approved ALL) | Cursor

**Approval:** operator `approve lessons` (round 9) · **Fan-out:** `2026-06-28-coord-005`  
**PT memory:** `lesson_7fc75916a601`, `lesson_81a9b9806526`, `lesson_7588896135cf`, `lesson_b6d64dcb2d7f`

- Bridge PR 38/38; Ladder F model-routing-check; v1 deferred backlog; peer-timeout degrade.

---

### 2026-06-28 — Self-improve cycle 005 (operator approved ALL) | Cursor

**Approval:** operator `approve lessons` (round 8) · **Fan-out:** `2026-06-28-coord-005`  
**PT memory:** `lesson_c391481ca104`, `lesson_8b5d45070494`, `lesson_82ab64772b2b`, `lesson_2a476c761ca1`

- PS ASCII-only ops scripts; PT memory union-merge on concurrent push; H5 finalize synthesis pattern; monitor caught coord-005 at tick 5.

---

### 2026-06-28 — Cycle 005 H5 closed (operator approved) | Cursor

**Approval:** operator `approve lessons` (round 7) · **Fan-out:** `2026-06-28-coord-005`  
**PT memory:** `lesson_e2f8a41c7d93`

- Mac `mac-h5-comparison.md` merged; `gpu-results-h5-final.md` dropped to Mac peer.
- Win 3/3 @ 1/1/1 itp vs Mac 3/3 @ 1/4/5; Win faster on wall-clock.

---

### 2026-06-28 — Queue prune + coord reconcile + monitor (operator approved) | Cursor

**Approval:** operator `approve lessons` (round 6)  
**Tool:** `win_job_queue.py` (`prune`, `complete-pending`) · **PT memory:** `lesson_c6e4f1a89d20`, `lesson_9b3d7e2f41ac`

- Prune drops stale mac-* / ops noise from pending on enqueue; coord-003 jobs reconciled without re-run.
- Win queues idle; Mac H5 `mac-h5-comparison.md` still pending on Mac lane.

---

### 2026-06-28 — Cycle 004 sequential job queues (operator approved) | Cursor

**Approval:** operator `approve lessons` (round 5) · **Fan-out:** `2026-06-28-coord-004`  
**Tool:** `win_job_queue.py` · **PT memory:** `lesson_a3f8e2b91c04`, `lesson_7d2c1e8f5b90`

- Sequential queues for `autoresearcher` + `coder`; coord-004 jobs completed and dropped to Mac.
- Mac H4 latency leg closed; H5 cross-host synthesis shipped.

---

### 2026-06-28 — Self-improve merge FINAL approved (round 4) | Cursor

**Approval:** operator `approve lessons` (round 4) — union with rounds 1–3  
**Sources:** `self-improve-merge-final-proposed.md` (peer inbox)  
**PT memory:** `lesson_1f9c927792ba`, `lesson_203c342c1e85`

**What was learned**

- **H3 falsified** — Win 27B latency penalty on trivial prompts; `routing.yml` routes by task class, not universal Win speed win.
- **Monitor URLs** — Mac `/co-orchestration/macos`; Win `/peer-inbox`.
- **Merge FINAL** — remaining PROPOSED bullets union into existing lessons (no duplicate rows).

---

### 2026-06-28 — Cycle 003 + graceful degradation ladders (operator approved) | Cursor

**Approval:** operator `approve lessons` (round 3) · **Fan-out:** `2026-06-28-coord-003`  
**Reference:** [`graceful-degradation.md`](../bin/orama-system/skills/oramasys-method/references/graceful-degradation.md)  
**PT memory:** `lesson_c8dc70c59ac9` … `lesson_0ec02977f23a`

**What was learned**

- **Unified fallback ladders** — oramasys search (gbrain→CRG→Grep→web), PT inference (host-local→validated fallback→budget cutoff), LAN (ws-peer→SSE, inbox partial fan-out), autoresearch (`http-local`→SSH).
- **Win portal lane** — `/peer-inbox` in `platform/windows/`; `/co-orchestration/windows` 307 redirect; Hermes skin removed.
- **Cycle 003** — subagent branches for mutations; H5 harness + HTTP-local preflight spike; Task quota → parent inline + inbox drops still ship.

---

### 2026-06-28 — Portal restart after pull still serves stale code | Cursor

**Fix:** `435d27a` · **PT memory:** `lesson_64dedfe61cfa` · **Operator approval:** union with `lesson_20833366511b` (round 2)

**What was learned**

- After `git pull`, a running portal process may still serve old code — `portal-health` can PASS while `/` returns 500 on the redacted-agents bug.
- **Win:** `start.ps1 --stop` then `start.ps1 --lan-peer --no-open` after pull to `>= 435d27a`.
- **Mac:** `./start.sh --stop` then `./start.sh --lan-peer --no-open` after pull.

---

### 2026-06-28 — Co-orchestrator GO: bidirectional ws-peer + file inbox (operator approved) | Cursor

**Playbook:** [`mac-co-orchestrator-playbook.md`](../bin/orama-system/skills/hermes-harness/references/mac-co-orchestrator-playbook.md) · **PT companion:** [LESSONS.md §2026-06-28](../../perplexity-api/Perpetua-Tools/docs/LESSONS.md) · **Commits:** `9f89051` (peer-file + `parents[4]`), `58605e1` (websockets), `435d27a` (portal `/` fix)

**What was learned**

- **Full mesh green** — `probe_lan_peer.py --json`: `portal-health`, `portal-status` (`joint`), `peer-lmstudio`, and `ws-peer` all PASS bidirectionally.
- **L3 coordination** — autoresearch fan-out uses markdown file drops (`lan_peer_assign.py`, `POST /api/peer-file`); WS/SSE are heartbeat/probe only, not payload transport.
- **Platform affinity** — Mac runs OpenClaw + Ollama warm (`:11434`); Win runs Hermes + LM Studio 27B. No remote agent RPC — each host executes locally.
- **Win inbound** — Mac→Win assignments land in local inbox; Win reads with `list` / `read --name` (no `--peer`).
- **Win outbound** — `drop --peer` → Mac reads with `read --peer --name`.
- **Partial fanout** — Mac proceeds when Win peer-file 404 while local assignments succeed (`status: partial`).
- **Mac inference routing** — Ollama warm primary; LM Studio passive (`peer-lmstudio` catalog probe only).

**Operator approval:** `approve lessons` 2026-06-28 — human index synced to PT + orama `docs/LESSONS.md`.

---

### 2026-06-28 — Portal dashboard: redacted agents payload crash on `/` | Cursor

**Fix:** `435d27a` — `_unwrap_redacted_list()` in `portal_server.py`

**Symptom:** `http://localhost:8002/` returned 500 Internal Server Error after `api_status()` began returning redacted `agents` as `{"agents": [...], "count": N}`; `_render_html()` iterated dict keys as strings → `AttributeError`.

**Test:** `tests/test_control_plane_auth.py::test_portal_index_handles_redacted_agents_payload`

---

### 2026-06-28 — LAN P2P bidirectional talk: transport survey + WS/SSE plan | Claude Code

**Docs:** [`docs/guides/lan-peer-bidirectional-talk-2026-06-28.md`](guides/lan-peer-bidirectional-talk-2026-06-28.md) · **Commits:** `ca96862`, `f63ec72` on `main`

**What was learned**

- **Zero-dep winner for LAN P2P (2-host Python/FastAPI stack):** FastAPI WebSocket — bundled in `fastapi[standard]`, zero new packages. Dual-socket pattern: each host runs a WS server endpoint and connects as a WS client to the peer. ~40 LoC for full bidirectional.
- **HTTP-only fallback (also zero deps):** SSE + POST — `GET /events/peer-stream` (text/event-stream) is the downlink; `POST /api/peer-event` is the uplink. Two connections per side. Correct choice when WebSocket is firewalled or peer doesn't support it.
- **Transport upgrade ladder (when the above isn't enough):** ZeroMQ PAIR (`pyzmq`, 1 dep) for sub-ms throughput or N>2 hosts; mDNS/zeroconf (`zeroconf`, 1 dep) replaces `$MAC_IP`/`$WIN_IP` env config with `_orama._tcp.local.` auto-discovery.
- **Shared JSON envelope `{type, source, ts, data}`** makes the channel manager (`lan_peer_channel.py`) the only code aware of which wire is live — callers use `send()` / `on_inbound()` regardless of transport.
- **State machine:** `WS_CONNECTING (5 s timeout) → WS_CONNECTED | SSE_CONNECTING → SSE_CONNECTED | DISCONNECTED (30 s retry)`; two consecutive WS failures demote to SSE before retrying WS.
- **gbrain `--dream` call graph:** 837 symbol edges resolved from 4,000 chunks walked (30 min run); `gbrain code-callers` / `code-callees` now operational on this codebase.

**Decisions made**

- WS-primary + SSE/POST-fallback first (5-phase plan); ZeroMQ/mDNS deferred until channel is stable.
- New file: `src/orama_system/lan_peer_channel.py` (~120 LoC). `probe_lan_peer.py` gains `ws-peer` check in Phase 4.

---

### 2026-06-28 — LAN peer operator playbook: Mac + Win identical instructions | Cursor

**Canonical:** [`references/lan-peer-self-talk.md` § Operator playbook](../bin/orama-system/skills/hermes-harness/references/lan-peer-self-talk.md#operator-playbook) · **Docs entry:** [`docs/guides/lan-peer-mac-win-operator.md`](guides/lan-peer-mac-win-operator.md) · **Commits:** `86bae70`, `9416a50`, `9d769bf`

**What was learned**

- **One playbook for both hosts** — setup (`.env.local` bind + token), Hermes slash `/lan-peer-self-talk`, and `probe_lan_peer.py --json` live in the harness reference; Mac/Win plan docs link to it, not duplicate steps.
- **Launcher shortcut** — `./start.sh --lan-peer` and `start.ps1 --lan-peer` set bind env and run peer probe after start.
- **Success artifact** — `~/.openclaw/state/last_lan_peer_probe.json` on PASS (local only, never commit).
- **Limits** — inference Mac↔Win works over HTTP today; remote Hermes/Codex on peer host is not supported (probe only).

**Tell Hermes:** `/lan-peer-self-talk` or playbook §B plain-English prompt.

---

### 2026-06-28 — Hermes integration authority: envelope protocol + optional lesson-mining | Cursor

**Plan:** [`docs/plans/2026-06-28-hermes-integration-authority.md`](plans/2026-06-28-hermes-integration-authority.md) · **Commits:** `2e284a5`…`9d5f4e6` on `main`

**What was learned**

- **Authority parity:** `hermes-harness` v1.1.0.0 now matches `openclaw-skills` authority — subskill registry, bootstrap JSON health, boundary enforcement, verification envelope. Canonical protocol: `bin/orama-system/skills/hermes-harness/references/hermes-universal-invocation-protocol.md`.
- **Envelope layers:** L3 intent (`skill_id`, `args`, `agent_id`, `harness`); L2 dispatch adds `orama_system_root`, `executor_id`, optional opaque `transport: { partner, profile }` for audit/replay; L0 result is OpenClaw core (`status`, `files_modified`, `follow_up_actions`) plus optional Hermes extensions (superset/subset).
- **Identity split:** `agent_id` = audit owner; `executor_id` = runner when delegating — both may appear on L2.
- **Thin wrappers:** four **required** (`council`, `review`, `delegate`, `hardware-policy`); `lesson-mining` is **optional** only (`OPTIONAL_WRAPPERS`, `--include-optional`). orama-system has **no** Perpetua-Tools dependency for lesson graduation.
- **Path policy:** committed docs use env placeholders (`$ORAMA_SYSTEM_PATH`, `$HERMES_HOME`); absolute paths only in runtime runners. Path casing mismatch → `warnings[]`, not `blocked`.
- **Sync habit:** after pull — `python scripts/sync_version.py --check` (package SSOT `1.1.1.0` in `_version.py`; Hermes skill family `1.1.0.0`); `install_hermes_thin_skills.py --install --verify` (4 wrappers unless `--include-optional`).

**Decisions made**

- Logical batches on `main` (not feature branches) for this authority batch.
- Command cards live under `hermes-harness/commands/<slug>/`; regenerate local `~/.hermes/skills/pt-orama/` via installer — never hand-edit canonical bodies there.
- Tests: `tests/test_hermes_invoke_envelope.py`, `tests/test_hermes_thin_skills.py` (31 green).

**Deferred**

- Mac cross-harness E2E (`openclaw-status` on fabric host); v2 transport schema in `/docs/v2` for Periscope replay.

---

### 2026-06-26 — PR #135 CodeRabbit closure: tracked-memory path hygiene | Cursor

**What was learned**

- Merging a PR before verifying all review threads against `main` is a Stage-5 (Crystallize) failure — especially when hygiene gives false negatives (`LINT-006` missed Windows user-profile paths until extended).
- CodeRabbit autofix (`80926a3` on PT branch `a924`) replaced queue preview text with `<local-path>` but did not fix episodic JSONL, lessons rationales, or write-boundary hooks — symptom-only.
- **Root cause:** workstation paths must be sanitized at every `.agent/memory` writer (`path_hygiene.py` in PT), not in one renderer. Scrub tool + re-render for legacy rows.

**Decisions made**

- PT owns `path_hygiene.py` + `scrub_memory_paths.py`; orama `repo_hygiene.py` Windows pattern kept in sync (LINT-006).
- Follow-up PR `cursor/critical-bug-investigation-a924-followup` continues branch `a924` for joint sweep.

### 2026-06-25 — Hermes plan review + discover.py Windows platform fix | Claude

**Key findings:**

1. **discover.py was Mac-centric on Windows** — `discover_endpoints()` always assigned `localhost:1234` to `result["mac"]`, then applied the `windows_only` policy filter to it. Running on Windows (where `localhost` IS the Win LM Studio box), this filtered out ALL `windows_only` models (`qwen3.5-27b`, `gemma-4-26b`), leaving only the embedding model. Fixed with `RUNNING_ON_WINDOWS = sys.platform == "win32"` and a platform-aware role split: when Windows, `localhost → win`, `$MAC_IP → mac`. After fix: `win` field now correctly shows all 3 models including `qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2`.

2. **`resolve_local_or_remote()` is a fiction** — the Hermes canonical onboarding plan (Phase 1 task 1) told agents to extract this function from `agent_launcher.py`. It does not exist. The real locality primitives are `_loopback_host_from_endpoint()` (L89), `_is_local_endpoint()` (L376), `_get_local_ips()` (L344). Plan corrected in-place.

3. **Perpetua-Tools on-disk clone name** — the L2 repo's canonical name is `Perpetua-Tools` but the on-disk clone on this host is `Perplexity-Tools` (rename in-flight). All tracked files must use `$PERPETUA_TOOLS_PATH` env var, never the literal sibling name.

4. **utils.hardware_policy import path** — `PERPETUA_TOOLS_ROOT` must resolve to the **directory containing the Python package** (i.e., the root of PT where `src/` lives, so `sys.path.insert(0, str(pt_root))` can resolve `utils.hardware_policy`).

5. **Windows LM Studio** at `$LM_STUDIO_WIN_ENDPOINT` — loaded models: `qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2`, `gemma-4-26b-a4b-it`, `text-embedding-qwen3-embedding-8b-i1-gguf-q6-k` (4096-dim).

6. **gstack/gbrain not installed on Windows** — neither CLI is on PATH; no `~/.gbrain/config.json`, no `~/.gstack`. Install path: gstack is a Claude Code skill (install separately); gbrain is a separate CLI (install command not found in this repo — check mcp-install `references/first-run-install.md §§ 0.4–0.5.1` on a Mac that has it). For Windows, use `text-embedding-qwen3-embedding-8b-i1-gguf-q6-k` via LM Studio OpenAI-compat endpoint as the embedding backend instead of Ollama `bge-m3` (1024-dim). **Do not use** `text-embedding-nomic-embed-text-v1.5` — 768-dim hard limit breaks gbrain sync.

---

### 2026-06-27 — Pre-v2 security hardening: Linux tiers shipped, Mac/Win E2E deferred | Cursor

**Branch:** `cursor/security-hardening-pre-v2-c4ae` · **PR #113** · **Version:** `1.1.1.0`

**Plan:** [`docs/plans/2026-06-27-security-hardening-pre-v2.md`](plans/2026-06-27-security-hardening-pre-v2.md) — includes platform schedule table (🐧 Linux vs 🍎 macOS vs 🪟 Windows 11).

**Shipped on Linux cloud (commits `de5c820` + PT `627d3a3`):**

- **T2-C:** Line-level LINT-013 — `<!-- LINT-013-ok -->` / `# lint-ignore-line LINT-013` on same line as historical IPs; file-level pragma deprecated for new files
- **T3-A:** `tests/test_concurrent_lock.py` — proves ≤1 simultaneous lock holder under 8-thread stress
- **T3-C:** `ControlStore` archives cleared/orphan pending to `registry/orphan-conflicts/`; `sweep_orphan_pending()` on `open()`
- **T4-A:** `scripts/check_dep_pins.py` + `~=` pins on `[project.optional-dependencies] test`
- **T4-B:** `check-local-env.sh` warns when `LM_STUDIO_API_TOKEN` is default `lm-studio` / `lmstudio`
- **T4-C:** SBOM snapshot `docs/sbom/sbom-v1.1.1.0.json`

**Cross-repo (PT PR #154):** T1 routing.json schema validation, T2-B model allowlist, T3-B commit-message fuzz tests.

**Hardware policy (2026-06-27 follow-up):** `mac_only` now enforces Ollama `qwen3.5:9b-nvfp4` + `bge-m3`; Win embedding is `text-embedding-qwen3-embedding-8b-i1-gguf-q6-k` (4096-dim). Removed stale `text-embedding-nomic-embed-text-v1.5` (768-dim breaks gbrain sync).

**Tomorrow (real machines only):** `start.sh --status` green, Ollama model probes, Win LM Studio LAN probes, `--hardware-policy` harness, keychain flows. **T5 freeze** (tags `v1.1.1`, release, `oramasys/v2-foundation`) blocked until E2E passes.

**Steelman principle (S8):** fixing `_canonical_endpoint()` on helper return paths does not protect module-level URL constants assigned at import from bare env vars — canonicalize at import time (PT T1-B).

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

## YYYY-MM-DD — <agent: ECC | AutoResearcher | Claude | Codex> — <brief topic>
### What was learned
### Decisions made
### Open questions
-->

---

---

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

## Archived sessions

Earlier sessions have been archived out of this file to keep it scannable.
Same content, unchanged, just relocated -- see each archive for its own date
range:

| Range | File |
| --- | --- |
| April 2026 | [`docs/archive/2026-04--April-Archived-LESSONS.md`](archive/2026-04--April-Archived-LESSONS.md) |
| May 2026 | [`docs/archive/2026-05--May-Archived-LESSONS.md`](archive/2026-05--May-Archived-LESSONS.md) |
| June-July 2026 | [`docs/archive/2026-06--to-07--June+July-Archived-LESSONS.md`](archive/2026-06--to-07--June+July-Archived-LESSONS.md) |

---

