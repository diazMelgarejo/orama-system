# Deep research: worked example, past runs and roles

Supporting detail for the [deep-research skill](../SKILL.md): a real thorough pass, what Perpetua-Tools memory records about earlier runs, and who does what.

## Worked example: PR-body human-grant security gap (2026-08-02)

A code review showed that a human-override grant could be forged. The research
pass was EXA first, then Firecrawl, then synthesis:

1. **EXA, 6 queries, about 54 candidate sources.** It surfaced that a TTY test
   measures terminal attachment, not human identity, that agent shells get
   pseudo-terminals, and that a plaintext marker file is forgeable.
2. **Firecrawl, 15 primary-source scrapes** of authoritative documentation, with
   the main content only.
3. **Synthesis** into a cited reference, with the raw EXA exports kept local-only
   because the scraped payloads contained email literals that repo hygiene blocks.

Read the result and the verdict table in
[`pr-body-human-grant-security-gap-research.md`](../../../references/pr-body-human-grant-security-gap-research.md).
The implementation record is in Perpetua-Tools memory
(`PR_BODY_GRANT_HMAC_MVP_SAGA_2026-08-02.md`).

## Correlation with the Cline, GLM and DeepSeek memory

What Perpetua-Tools memory does and does not record about earlier runs:

- **The 2026-08-02 research above is recorded as EXA plus Firecrawl.** The saga
  does not name a Cline, GLM or DeepSeek model as having run it, so do not claim
  one did.
- **The Cline route shows up in a separate event.** A Cline fan-out run failed on
  provider auth. EXA found the official ClinePass docs and Firecrawl scraped the
  Cline CLI overview, which established that the provider id (`clinepass`) and the
  model id (`cline-pass/deepseek-v4-flash`) are different things (lesson
  `290a2efb284b`; `docs/LESSONS.md`). Rule: verify provider auth, not only the
  model slug, before trusting a Cline fan-out route (lesson `58ec2dc24e62`).
- **GLM.** ClinePass with `cline-pass/glm-5.2` is the default coding route, and
  GLM-5.2 is the last stop of the fallback chain (ClinePass, LM Studio, Ollama,
  OpenAI, then GLM-5.2). See [`glm52-fallback`](../../glm52-fallback/SKILL.md).
- **DeepSeek.** The DeepSeek V4 Flash route is its own skill, parallel to the
  GLM one: [`clinepass-deepseek-flash`](../../clinepass-deepseek-flash/SKILL.md).
- **Using them for research.** Those skills describe non-interactive fan-out
  workers. Whether to give one a sub-question to read and summarize from an
  already-extracted corpus is an operator choice; the memory has no record of it
  having been done. If you do, route per the skill, check auth first, and treat
  its output like any other claim: verify it against the source.

## Roles and verification

| Role | Who | Invariant |
| --- | --- | --- |
| Lead | Claude Code or the active harness | Decomposes the question, drives Steps 0-5, owns the merge gate |
| Discovery | EXA | Finds URLs; does not prove claims |
| Extraction | Firecrawl | Reads primary sources; sits downstream of discovery |
| Fan-out worker (optional) | Cline route per the skills above | Reads or summarizes extracted text; auth checked first |
| Implementer (if code follows) | Cursor Agent or Cline | Its commit messages are claims, not evidence |
| Verifier | Codex (`codex exec`, read-only, `< /dev/null`) plus a separate Claude subagent with no shared context | Reads the same source independently |

- When two reviewers with no shared context reach the same finding, treat it as
  the strongest signal available and weight it above either one's stated severity
  (lesson `fb76280fc2cd`). It is a strong signal, not proof; still re-find the
  evidence in the source.
- When another agent commits to the same branch mid-review, read the actual diff
  and run the tests before crediting any claimed fix; never trust a claimed test
  count in a commit message (lesson `11baf3e69fcb`).
