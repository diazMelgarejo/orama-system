# AFRP Failure Mode Taxonomy — Extended Reference

**Parent skill:** [`afrp/SKILL.md`](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/afrp/SKILL.md)

This document provides extended examples and recovery procedures for each AFRP failure mode. Load on demand when diagnosing a response quality issue.

---

## Failure Mode 1: Personalized Slop

**Trigger:** Profile data used to narrow scope before audience is identified.

**Mechanism:** The agent scans user memory/context, finds domain-specific keywords (e.g., "distributed compute," "LAN agents," "SKILL.md frameworks"), and generates output calibrated to that profile — even when the query is about a completely different audience.

**Symptom:** Output feels relevant to the user but is useless for the stated audience. The user recognizes their own language and context mirrored back, creating an illusion of quality.

**Example:**

- Query: "Write guidance for Filipinos around the world"
- Agent finds: Mac mini, RTX 3080, orama-system, multi-agent architecture
- Output: Advice about building distributed AI systems for economic resilience
- Actual audience need: Practical steps for OFW families managing remittances

**Recovery:** Re-run Step 3 (Profile Separation). Ask: "Is this profile information relevant to the audience of this output, or only to the user submitting the query?"

---

## Failure Mode 2: Abstraction Mismatch

**Trigger:** Defaulting to Analytical or Conceptual level when the audience needs Operational.

**Mechanism:** Complex or philosophical prompts trigger the agent's tendency to match complexity with complexity. The agent produces frameworks, taxonomies, and principles when the audience needs step-by-step instructions.

**Symptom:** The audience cannot act on the output without first translating it into concrete steps. The response is intellectually interesting but operationally inert.

**Example:**

- Query: "How should small business owners protect themselves from tariffs?"
- Agent output: A framework comparing supply chain resilience theories
- Actual need: "Here are 5 things to do this week"

**Recovery:** Re-run Step 5 (Abstraction Calibration). Default to Operational. Ask: "Does this audience need to UNDERSTAND or to DO?"

---

## Failure Mode 3: Citation Theater

**Trigger:** Adding citations to appear thorough rather than because they change the advice.

**Mechanism:** The agent inserts research references, statistics, and expert quotes that decorate the response without altering its substance. Remove the citations and the advice is identical.

**Symptom:** The response looks well-researched but the citations are ornamental. They don't resolve ambiguity, challenge assumptions, or provide evidence for a contested claim.

**Test:** For each citation, ask: "If I removed this citation, would the advice change?" If no — the citation is theater.

**Recovery:** Remove or justify each citation. Every citation must earn its place by changing, qualifying, or strengthening a specific claim.

---

## Failure Mode 4: Mirror Response

**Trigger:** Reflecting the user's own language and framing back at them as if it constitutes analysis.

**Mechanism:** The agent identifies key terms and structures in the prompt, then reorganizes them into a response that feels like it "gets it" — without adding new information, new perspective, or new connections.

**Symptom:** The user reads the response and thinks "yes, that's what I said." No new insight is generated. The response validates but does not advance.

**Test:** Highlight every sentence that contains information not already present in the prompt. If less than 50% of the response is novel — it's a mirror.

**Recovery:** Re-run Step 6 (Slop Detection). Force the response to contain at least one insight, tradeoff, or recommendation the user did not already articulate.

---

## Failure Mode 5: Omnibus Response

**Trigger:** Attempting to address all possible interpretations of an ambiguous query instead of narrowing scope.

**Mechanism:** Instead of asking a clarifying question (which takes one turn), the agent hedges by covering every plausible interpretation. The result is long, internally contradictory, and unfocused.

**Symptom:** The response contains sections that contradict each other. Advice for audience A conflicts with advice for audience B, but both are presented as valid. The user must do the scoping work the agent should have done.

**Example:**

- Query: "Develop a resilience framework"
- Agent output: Section 1 (for individuals), Section 2 (for organizations), Section 3 (for governments), Section 4 (for communities) — each shallow, none actionable

**Recovery:** Re-run Step 4 (Scope Declaration). Write one clean SCOPE sentence. If you cannot — go back to Step 2 and ask.

---

## Failure Mode 6: Premature Confidence

**Trigger:** Skipping Steps 0–2 entirely for queries that appear straightforward but are actually Type B/C/D.

**Mechanism:** The agent pattern-matches the surface structure of the query to a known template and generates a confident response without checking whether the template applies. This is the most dangerous failure mode because the output looks correct.

**Symptom:** The answer is well-structured, well-cited, and completely wrong for the actual need. The user only discovers this after acting on it.

**Example:**

- Query: "Write a skill for conflict resolution"
- Agent output: A complete SKILL.md file for AI agent conflict resolution in multi-agent systems
- Actual need: A training module for HR managers on workplace conflict
- The query looked like Type A (technical, bounded) but was actually Type C (audience-dependent)

**Recovery:** Restart at Step 0. Run the full checklist. When in doubt about query type, classify UP (A→B, B→C) rather than down.

**Example (2026-07-22, real — a slash command hiding real ambiguity):**

- Query: `/skillify` (or "make me a skill"), no further context
- Looks like: Type A/C, unambiguous — "obviously" run this repo's own
  `oramasys-skillify` skill, since that's what was invoked
- Actually Type D: at least three tools answer to "skillify" or "make a
  skill" with entirely different jobs — this repo's canonical skill
  builder, gstack's own `/skillify` (codifies a browser scrape, nothing to
  do with authoring a skill), and Anthropic's official `skill-creator`
  plugin (general-purpose, outside this repo's conventions). Picking one
  silently risks doing the wrong thing entirely, not just doing this
  repo's thing slightly wrong.
- **Recovery applied:** `oramasys-skillify`'s Workflow now has a mandatory
  step 0 — AskUserQuestion interrupt whenever the request isn't already
  clearly orama-system-scoped, offering all three options rather than
  assuming. See `bin/orama-system/skills/skillify/SKILL.md`'s "Related
  Tools (disambiguation)" section.

**Example (2026-07-28, real — CONFLICTING ≠ "pick one PR"):**

- Surface: periscope PR #12 `mergeable: CONFLICTING` after PR #10 merged overlapping ECC
- Looks like: Type A — "close #12 or merge #12 over #10"
- Actually Type C: **synthesize** both ECC runs into a third state, then **path-scoped
  replay** onto fresh `origin/merged` (3 files, one commit)
- Wrong path: wholesale merge/rebase, re-add full bundle, or pick PR #12 generator output
- **Recovery applied:** CIDF integrative-editing-examples §9;
  `path-scoped-pr-replay-reference-card.md`; AFRP proxy-table rows for CONFLICTING and
  empty `commit-clean` commits

---

## Failure Mode 7: Handwaving (Proxy Conclusion)

**Trigger:** Asserting "already fine / no problem / nothing to do / done" from a cheap proxy check, OR acting on the first interpretation of an ambiguous request, without confirming the user's intent or running the method that actually answers the question.

**Mechanism:** The agent substitutes an easy-to-compute signal for the real question and reports the proxy's verdict with confidence. When the user insists otherwise, it re-explains the proxy instead of switching methods. Misinterpreting intent compounds it — the agent "solves" a problem the user didn't ask about.

**Symptom:** The user corrects the agent repeatedly ("you misunderstood", "did you even check", "we already did this"). Each correction reveals the agent never confirmed intent or used the right tool.

**Example (2026-06-04, real):**

- Proxy: `git merge-base != root` ⇒ agent declares "no orphaned branches, nothing to do."
- Real question: does the branch's *content* converge with main? The tree-twin search showed every branch HAD a byte-identical twin needing re-anchor.
- Also: user said "re-anchor"; agent *flattened* branches to HEAD (wrong mechanic) without confirming the meaning.

**Example (2026-07-28, real — CONFLICTING PR):**

- Proxy: GitHub `mergeable: CONFLICTING` ⇒ "merge or rebase the PR branch to fix it."
- Real question: how to deliver the **harmonized synthesis** now that the integration base
  already contains overlapping content (PR #10 ECC on `merged`)?
- Wrong action: wholesale merge of stale PR #12 (two commits from pre-#10 base) or pick one
  generator run over the other.
- Right method: preserve synthesis outside the branch; reset to fresh `origin/merged`;
  `git checkout` only the 3 proven unique paths; `git add` before `commit-clean.sh`;
  single commit; `--force-with-lease`. Verify with `gh pr view --json mergeable`.
- Curriculum: CIDF integrative-editing-examples §9;
  [`path-scoped-pr-replay-reference-card.md`](../skills/git-history-surgery/references/path-scoped-pr-replay-reference-card.md).

**Example (2026-09-02, real — "flaky test" diagnosed from a proxy, never traced):**

- Proxy: a Windows CI Go test (`TestEnsureBackgroundServeReplacesIncompatibleDaemonAfterStartupWait`)
  passed on one commit and failed on a later commit, with zero Go-code diff between
  the two — only unrelated `.md` frontmatter fixes existed in the diff.
- Agent's proxy conclusion: "no code diff between the two runs, and it passed once ⇒
  flaky/timing-sensitive test, unrelated to this PR" — then told the user to click
  "Re-run failed jobs."
- What the proxy never checked: the *content* of the failure (`serve_background_test.go:1552`,
  a bare `assert.True` with no diagnostic message), the actual watcher-cleanup code path
  the test exercises, or whether the failure was deterministic under the real trigger
  condition rather than merely absent from the agent's own two-commit sample.
- Real root cause (found by tracing the actual code, not the diff): Windows cleanup
  called the native fsnotify `Remove` on a watch already invalidated by a prior
  remove/rename event, hanging the watcher shutdown — a genuine, deterministic
  deadlock reachable whenever that event ordering occurs, not a timing coin-flip.
  Confirmed reproducible and fixed with a regression test that fails without the fix
  and passes with it (commits `19d0e0cf`, `737f7a5c` on
  `fix/windows-invalidated-watch-cleanup`).
- Why "re-run it" would never have worked: a deterministic deadlock triggered by a
  specific event ordering doesn't self-resolve by retrying — the user correctly
  identified this in the moment ("even if we hit Re-run 100x, it will not fix itself").
- The absence of a diff **in the agent's own recent commits** is not evidence a bug
  doesn't exist; the bug can predate the agent's diff entirely, or the sample size (n=1
  pass, n=1 fail) is not enough to distinguish "flaky" from "deterministic but rarely
  exercised by CI's actual scheduling/ordering."

**Recovery:** Stop. Run the **Intent-Verification Gate** (`SKILL.md`): clarify intent via AskUserQuestion FIRST when there's interpretation risk or before any negative conclusion; replace the proxy with the method that truly answers the question; trust the user's domain signal over a first-pass check.

For a test failure specifically: open the actual assertion and the code path it exercises before concluding "flaky" — a passing/failing sample of one commit each is not sufficient evidence of non-determinism, and "flaky, just retry" must never be the conclusion reached without having read what the test actually asserts and why.

---

## Failure Mode 9: Empty Publication Commit

**Trigger:** Advancing a ref with a commit whose tree is identical to its
parent while claiming that content was inserted. Two confirmed triggers are:

1. running `commit-clean.sh` while the intended edits remain unstaged; and
2. blindly retrying a successful-but-late GitHub Contents API write with the
   already-current blob and the same commit message.

**Mechanism:** `commit-clean.sh` writes the **staged index** via `git write-tree`.
It never stages files. The pre-2026-07-29 guard only rejected commits when **both**
the working tree and index matched HEAD. When unstaged edits existed but the index
was empty, the script still advanced the branch with a **new message and zero file
delta** — identical tree to HEAD.

**Symptom:** Push succeeds; PR/commit message describes fixes; `git show --stat`
is empty; CI still fails on the old code; agents chase per-file symptoms instead of
missing commits.

This violates CIDF's core success criterion: execution is not success until a
non-empty, programmatically checked verification signature is present in the
destination. An HTTP success, a new SHA, a pushed ref, or a plausible subject
line is only transport evidence. It does not prove that the intended content
was inserted.

**Example (2026-07-29, real — periscope PR #26):**

- Agent ran `commit-clean.sh` twice with CI-fix messages while edits stayed unstaged.
- Remote branch stayed on broken `ci-pr.yml` (upstream workflow) and pre-migration
  kit-ui sources; local working tree had the real fixes.
- Recovery: `git add <paths>` → `verify-staged-for-commit.sh` → `commit-clean.sh`;
  confirm with `git show --stat HEAD` before push.

**Recovery / prevention (mandatory sequence):**

```bash
git add <paths>
bash scripts/git/verify-staged-for-commit.sh   # fails closed if index empty
bash scripts/git/commit-clean.sh -m "type(scope): summary"
git show --stat --oneline HEAD                 # confirm before push
```

Regression: `bash scripts/git/commit_clean_test.sh` (also run from `verify-git-guards.sh`).

**Example (2026-09-02, real — Periscope PR #49 API retry):**

- `214b0c03` is the real insertion: parent `c8db8992`, one file changed,
  45 insertions, tree `bd81bba7`.
- `faf515e4` immediately follows it with the same subject, but its tree is also
  `bd81bba7`; `git diff 214b0c03 faf515e4` is empty.
- GitHub's raw comparison reports one commit ahead and no changed files.
- Root cause: the first Contents API request completed after the caller's
  observation window. A retry then fetched the already-updated blob SHA and
  submitted byte-identical content. GitHub accepted a new commit object even
  though the tree did not change.

**API recovery / prevention:**

1. After a timeout or uncertain response, read the target ref before retrying.
2. Compare the remote blob/content signature with the intended artifact.
3. If it already matches, record the first commit as success and do not write.
4. After any write, require both the expected path/blob and a parent-to-child
   tree delta; fail closed when the tree IDs are equal.
5. Use an idempotency key or expected-old-blob precondition where the API
   supports one; never use a new commit SHA alone as the success signature.

---

## Failure Mode 8: Synthetic SHA Replay (Upstream Re-import Theater)

**Trigger:** Replaying a large upstream lineage under **new commit SHAs** when the
canonical upstream remote already carries the same patches under original SHAs.

**Mechanism:** An agent "modernizes" by re-cherry-picking or replaying hundreds of
upstream commits from an ancient merge-base instead of inheriting original upstream
commits from `kenn-io/agentsview` / `origin/agentsview` and layering only fork-unique
commits on top. GitHub three-dot PR diffs explode; review cannot see the small fork delta.

**Symptom:** PR shows hundreds of commits and thousands of files changed even when the
tip tree is correct. `git rev-list --count` looks catastrophic.

**Example (2026-07-29, real — periscope PR #17 vs PR #20):**

| Item | PR #17 (bad — closed) | PR #20 (good) |
| --- | --- | --- |
| Upstream | ~769 replayed commits (synthetic SHAs) | Inherits `kenn-io` @ `#1283` |
| Periscope-only | 9 commits buried | **9 on tip** |
| Three-dot vs `merged` | 2,169 files / 769 commits | **816 files / 9 commits** |
| Tip tree | reference | **byte-identical** to PR #17 |
| Branch fate | **Preserved** as bad example | Integration candidate |

`47ca74c` (Wes #352) on `merged` vs replayed `22cf1394` on bad branch — same `%T`,
wrong SHA, zero semantic gain.

**Policy — never synthesize SHAs except security expunge:** leaked keys, identities,
workspaces, paths, doxxing. Not for convenience or cosmetic PR graphs.

**Recovery:** `git fetch origin agentsview`; `git cherry -v origin/agentsview <tip>`; base on real
upstream tip (`kenn-io/agentsview` / `origin/agentsview` on the fork);
cherry-pick fork-unique commits only; verify `%T`; close bad PR; preserve bad branch
as anti-pattern. See periscope `docs/2026-07-28-AgentsView+Periscope-Fresh.md` addendum;
CIDF §10; path-scoped card PR #17 vs #20 example.

---

```text
Response feels wrong but you can't pinpoint why?
│
├── Does it mirror the user's language? → Failure Mode 4 (Mirror)
├── Does it work for 10 different audiences? → Failure Mode 1 (Slop) or 5 (Omnibus)
├── Can the audience act on it immediately? → Failure Mode 2 (Abstraction Mismatch)
├── Remove citations — does advice change? → Failure Mode 3 (Citation Theater)
├── Was the query classified correctly? → Failure Mode 6 (Premature Confidence)
├── Did I confirm intent + use the real method (not a proxy)? → Failure Mode 7 (Handwaving)
├── Did I replay upstream under synthetic SHAs when originals exist? → Failure Mode 8 (Synthetic SHA Replay)
└── Did commit-clean run without git add, or did a blind API retry follow an
    already-completed write? → Failure Mode 9 (Empty Publication Commit)
```
