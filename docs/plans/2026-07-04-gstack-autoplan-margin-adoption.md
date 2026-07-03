# Gstack Autoplan + Margin Adoption Review

Date: 2026-07-04
Status: review plan
Primary input: garrytan/gstack PR #2109
Secondary input: cross-repository endpoint-policy remediation package
Scope: orama-system planning only
Explicit non-scope: do not touch AlphaClaw fork

## Executive Position

Adopt the idea behind gstack PR #2109, but do not copy it blindly.

The strong idea is not the shell wrapper itself. The strong idea is a new review primitive:

> Plans that humans must approve should be rendered into a phone-readable, commentable artifact, and comments should fold back into the same plan before approval.

That primitive is valuable for orama-system because our plans are long, cross-repo, and often high-stakes. Terminal-only review is a weak approval interface. Margin improves human review ergonomics without changing the execution authority model.

However, the implementation must be constrained. Margin is a review surface, not an execution surface. It must never become a hidden approval channel, a place to store secrets, or a reason to skip repo-native docs and CI gates.

## Decision

Save the adoption path in `orama-system/docs/plans`. Do not edit AlphaClaw. Do not push logic into AlphaClaw. AlphaClaw remains controlled from Perpetua.

Adopt this rule going forward:

> For artifacts the user is expected to review visually or comment on, publish a static Margin copy and send the link. The repo remains the source of truth; Margin is the review projection.

## What PR #2109 Gets Right

1. It correctly identifies the review bottleneck.

   `/autoplan` and plan-review skills produce documents that are too large for comfortable terminal review. A phone-readable page with anchored comments is a better human interface.

2. It keeps the document link stable.

   Re-publishing to the same `doc_id` preserves comment anchors. This is essential. Creating a new link per revision would make review history unusable.

3. It treats phone comments as normal revisions.

   This is the correct model. A Margin comment is not approval. It is a request to revise the plan, rerun affected review phases, and re-present the approval gate.

4. It avoids API-key provisioning.

   The server mints a per-document token. That reduces setup friction and makes the tool useful in transient agent sessions.

5. It defines static HTML constraints.

   Inline CSS, no external scripts, no external fonts, and formatted HTML rather than raw markdown are the right constraints for a durable review sandbox.

6. It adds tests around token leakage and stable-link reuse.

   The `gstack-margin` tests assert the right security properties: token cached privately, token not printed, revise uses bearer auth, and second publish does not create a fresh document.

## Ruthless Criticism

1. The PR couples review UX to local shell state.

   `gstack-margin` caches credentials under local gstack project state. That is reasonable for gstack, but weak for Codex/GitHub-connector workflows where the active workspace may not be a normal checkout. orama adoption must allow a simple `.margin.json` in the scratch workspace and must never require committing that file.

2. The PR assumes the plan file exists locally.

   In connector-first workflows, the source plan may be created directly through GitHub APIs. The publish path must support generated HTML from memory or scratch files, not only a local repo file.

3. The token model is only safe if agents are disciplined.

   `agent_token` controls the document. If it is printed, committed, or copied into a plan, the private review surface is compromised. The adoption rule must explicitly ban storing `.margin.json` in GitHub.

4. The approval boundary is under-specified.

   A user comment in Margin must not be interpreted as approval. Final approval must still happen in the main conversation or through an explicit repository review gate.

5. It is easy to overuse Margin.

   Not every small edit needs phone review. Use Margin when the artifact is something the user would reasonably want to inspect: a plan, report, table, one-pager, proposal, review summary, or release notes. Do not publish noise.

6. The gstack wrapper assumes `curl` + `jq`.

   That is acceptable, but orama should document a fallback using direct HTTP requests so the workflow remains tool-agnostic.

7. The PR does not solve source-of-truth drift.

   Margin is only a projection. The authoritative artifact must remain in repo docs, PR descriptions, or issue comments. A reviewed Margin page that differs from the committed doc is process drift.

## Steelman

The best version of PR #2109 is a human-in-the-loop plan review transport.

It does three things that are worth adopting:

1. Converts a machine-generated plan into a human-readable static page.
2. Lets the user give anchored feedback on exact text, not vague terminal scrollback.
3. Forces the agent to revise the source artifact and republish the same review link.

For orama-system, this fits the existing method:

- Context immersion creates the evidence base.
- Visionary architecture produces the target shape.
- Ruthless refinement surfaces weak assumptions.
- Masterful execution turns the plan into repo-safe steps.
- Crystallization publishes the final source-of-truth artifact.

Margin belongs between ruthless refinement and crystallization. It improves human review, but it does not replace verification.

## Refined Adoption Rule For orama-system

Use Margin when all are true:

- The artifact is meant for human review.
- The user would benefit from reading it outside the terminal.
- Anchored comments are useful.
- The source artifact is or will be saved in a repository or persistent doc.

Do not use Margin when:

- The response is a trivial answer.
- The artifact contains secrets, private tokens, or unredacted credentials.
- The user asks for direct code execution only.
- The artifact is not stable enough to review.

## Operational Contract

1. Write or update the repo artifact first.

   For this work, the source artifact is this file:

   `docs/plans/2026-07-04-gstack-autoplan-margin-adoption.md`

2. Render a static HTML review copy.

   Requirements:

   - inline CSS only
   - no external scripts
   - no external stylesheets or fonts
   - absolute `https:` images only, or no images
   - formatted headings, lists, tables, and code blocks
   - a short prompt telling the user what to review

3. Publish to Margin.

   `POST https://margin.fieldspan.ai/api/docs`

   Save `doc_id` and `agent_token` only in local scratch state such as `.margin.json`. Never commit it.

4. Send the `reviewer_url` to the user.

5. When the user says they commented, read open comments.

   `GET /api/docs/{doc_id}/comments?status=open`

6. Fold comments back into the source artifact.

7. Re-render and republish to the same `doc_id`.

8. Resolve handled comments.

9. Final approval remains explicit in the conversation or repo review, not implicit in Margin.

## Application To Current Endpoint-Policy Work

The attached endpoint-policy remediation package is useful, but it overreaches in places.

### Keep

- Single source of truth for endpoint policy.
- Fail-closed endpoint validation.
- One typed error boundary: `ModelEndpointPolicyError`.
- Test vectors for malformed ports, metadata IPs, IPv4-mapped IPv6, and happy-path normalization.
- Cross-repo peer contract.
- orama as enforcement/consumer, Perpetua as owner/author.

### Reject Or Defer

- Do not touch AlphaClaw fork directly.
- Do not implement `packages/endpoint-policy/` inside this plan without a separate coding task.
- Do not create an npm mirror now.
- Do not treat unauthenticated CI-log deductions as verified facts.
- Do not mix licensing reconciliation into the same atomic PR as endpoint-policy code.

### Refined Path

1. Perpetua owns and authors endpoint-policy primitives.
2. orama consumes and enforces the contract.
3. AlphaClaw gets no direct edits here; Perpetua controls its defaults and integration surface.
4. Margin is used to review plans and reports, not to execute changes.

## Minimal Implementation Plan

### Phase 1: Documentation Adoption

- Save this plan in `orama-system/docs/plans`.
- Publish the same plan to Margin for phone review.
- Treat Margin comments as revision requests.

### Phase 2: orama Guidance Update

Candidate follow-up, not part of this commit:

- Add a short `AGENTS.md` note: reviewable plans may be published to Margin, but repo docs remain source of truth.
- Add a `docs/plans/README.md` or index entry if docs/plans has one.

### Phase 3: Perpetua Runtime Work

Candidate follow-up, separate task:

- Implement or refine shared endpoint-policy primitives in Perpetua.
- Keep AlphaClaw out of direct edits.
- Use the endpoint-policy test vectors from the remediation package.

### Phase 4: orama Contract Enforcement

Candidate follow-up, separate task:

- Make orama contract checks consume the Perpetua-owned primitive or a generated contract artifact.
- Keep `scripts/security/check_endpoint_policy_contract.py` as an enforcement point.
- Keep scan roots explicit and fail if configured roots are missing.

## Review Checklist

Before executing any follow-up PR:

- Is the source artifact committed or staged in the right repo?
- Is AlphaClaw untouched?
- Are secrets absent from both repo docs and Margin HTML?
- Does Margin mirror the repo artifact rather than replacing it?
- Are comments folded back into the source doc before final approval?
- Does final approval happen outside Margin?

## Final Recommendation

Adopt the Margin phone-review loop as an orama planning/review convention, not as a runtime dependency.

Use it for plans the user should inspect. Keep source of truth in GitHub. Keep tokens local. Keep AlphaClaw untouched. Use Perpetua as the control surface for AlphaClaw-related endpoint policy work.
