# Sites readiness r2 — agent handoff (ChatGPT, Codex, Claude, others)

Written 2026-10-06 UTC for any agent continuing this work. It is sanitized: concrete Site IDs,
account addresses, URLs, record IDs, hashes and local paths live only in the owner's private
runbook. Do not copy them into tracked files, PR text or commit messages.

Read this first, then the Orama reference
`docs/v2/references/SITES-READINESS-R2-IMPLEMENTATION-2026-10-06.md` (task/gate map), then
`integrations/sites-mcp/SPECS.md` and the root `AGENTS.md`. Trust fetched remote state over this
note: verify heads before changing anything.

## 1. State at time of writing

| Item | Repo | Branch | Head when written | State |
| --- | --- | --- | --- | --- |
| #386 implementation | orama-system | `fix/sites-readiness-r2` | `b6198b4` | Open, unmerged |
| #387 fixes for #386 | orama-system | `claude/orama-stdio-handlers-tokens-w1r9dn` | verify | Draft, based on #386 |
| #428 memory and lessons | Perpetua-Tools | `docs/sites-readiness-r2` | `5483811` | Open, unmerged |
| #429 status fix for #428 | Perpetua-Tools | `claude/orama-stdio-handlers-tokens-w1r9dn` | verify | Draft, based on #428 |

Starting mains: Orama `0d593c7`, PT `608ac25`. PT runtime and the canonical prompt-workspace
compiler/schema are unchanged. Orama's snapshots of them are byte-identical to PT main.

Hosted: an owner-private Site, version 4, is deployed with the owner-only allowlist. Anonymous
access returns 401. The owner's installed plugin session completed authenticated prepare, list,
save, get, idempotent retry and conflict calls. Detail is in the private runbook.

## 2. Merge order and gates

1. Merge #387 into #386's branch, then #429 into #428's branch, after CodeRabbit and green CI.
2. Merge #428 and #386. PT first if any PT-owned file ever changes (Orama re-pins from merged PT
   main); otherwise either order. Never merge on the strength of a handoff or report alone.
3. Do not merge anything before CodeRabbit has reviewed it. Its free tier allows about one review
   per hour; an unreviewed PR waits.
4. Required checks that have bitten this work: `Git hygiene` (no address literals, including
   loopback, in the diff), `Markdownlint-cli2` (limit 100 columns, tables and code blocks exempt;
   `CHANGELOG.md` is excluded), `verify-summary-present` (the PR body needs a `## Summary`).

## 3. Rules that do not bend

- Preserve original prompt bytes, existing migrations, journal history and memory files. Append,
  never rewrite. Corrections are dated status sections, not edits to history.
- Keep the five-tool contract. Do not add `solve`, `delegate` or remote execution to the Site.
  Preparation is deterministic formatting, not model inference.
- Do not widen the Site audience, add viewers, create a second Site or use service credentials as
  owner identity. Never send a local fixture identity header to a hosted Site.
- The optional forged-header probe needs the owner's separate authorization.
- Identity comes from the hosting boundary, never from tool arguments.
- No identifiers, secrets, emails, endpoints or workstation paths in tracked content. Use
  placeholders such as `$SITE_ID` and keep real values in the private runbook. Do not obfuscate a
  literal to get past a scanner; use a named hostname constant or fix the cause.
- Commit identity: use the approved identities in `scripts/git/identity-policy.json`. Edit guard
  scripts only in Orama and sync them; never hand-edit PT's copies.

## 4. How to verify (Node 24; Node 22 lacks `setAuthorizer`)

```bash
node --test integrations/sites-mcp/tests/*.test.mjs        # 31 pass, 1 skip without a Site root
node integrations/sites-mcp/check-snapshot.mjs "$PERPETUA_TOOLS_ROOT"
node integrations/sites-mcp/verify-assembled.mjs "$PERPETUA_TOOLS_ROOT" "$SITE_ROOT" \
  --index-only-from 1
node integrations/sites-mcp/tests/local-worker-smoke.mjs "$SITE_ROOT"
python3 scripts/review/repo_hygiene.py .
npx markdownlint-cli2@0.17.2 --config .markdownlint-cli2.jsonc <changed docs>
```

The real-Wrangler reproduction test and the built-Worker smoke need a prepared, built Site root and
are not run in CI. The first run of the smoke with `--ip localhost` (after the hygiene fix in #387)
has not happened yet; do it before merging #386.

## 5. Review findings and their status

| # | Finding on #386 / #428 | Status |
| --- | --- | --- |
| 1 | Loopback literals fail Git hygiene | Fixed in #387 (`LOOPBACK_HOST`) |
| 2 | `SPECS.md` MD012 | Fixed in #387 |
| 3 | Tracked status text says blocked/unverified after the plugin session passed | Fixed in #387 and #429 (dated status sections) |
| 4 | Verifier ignored migration files absent from the journal | Fixed in #387 |
| 5 | "Index-only migration" not enforced | Opt-in `--index-only-from` in #387; pass it for releases |
| 6 | UI decoder hid the Site's own error text | Fixed in #387 |
| 7 | `lib/` ignore rule skipped a new overlay file | Fixed in #387 (negation rule) |
| 8 | Commit author address not in the policy's human list | Open: confirm CI after fixes |
| 9 | #428 body had no author-written `## Summary` | Open: not edited; CodeRabbit's heading satisfies the check |
| 10 | First-publication reversal gate unmet; no recorded acceptance of a one-way publish | Open: owner decision |
| 11 | Partial-index `WHERE` clause and sort order not compared | Open, low |
| 12 | Smoke runner is POSIX-only and not in CI | Open, low |

## 6. Open work, in order

1. Confirm CI and CodeRabbit on #387 and #429; fix anything real; resolve threads you addressed.
2. Run the built-Worker smoke once against a prepared Site root.
3. Owner browser sign-in on the private Site, without widening access. A working plugin session
   does not prove it.
4. Two real approved accounts for hosted isolation, before any sharing.
5. Optionally, with separate authorization, the forged-header probe.
6. Owner decision on finding 10; record the answer additively.

## 7. Pitfalls learned the hard way

- A passing build did not detect a missing migration. Only the independent verifier did.
- `git add` skipped a new file under an ignored path. Check `git status --short` and compare the
  fetched remote tree to the local tree after publishing.
- API-written trees need a whole-tree comparison against the local commit. A write acknowledgement
  is not evidence.
- Scratch worktrees register themselves in the host repo. Remove them with `git worktree remove`.
- A merged PR's branch is gone from the remote. Prune stale tracking refs before pushing a reused
  branch name, and stack new work on the open PR branch rather than reusing merged history.
- Local fixture identity proves local isolation only. Plugin access proves one session only.

## 8. Reporting back

Use a producer/consumer envelope so the next agent can resume without rediscovery:

```text
Actor / inputs / what changed (repo, branch, exact head) / evidence (commands and results) /
not verified / next owner / secrets: none included
```

State what you did not verify, in the same breath as what you did.
