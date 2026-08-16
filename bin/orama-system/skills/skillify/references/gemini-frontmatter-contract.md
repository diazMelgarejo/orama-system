# Gemini Frontmatter Contract

Schema Version: 2

## Official-source evidence

Retrieved 2026-08-15 via Firecrawl (search + scrape), cross-confirmed across two
independent sources:

- **Primary:** [Skills | Google Antigravity Docs](https://antigravity.google/docs/skills)
  — "Frontmatter fields" section, retrieved 2026-08-15. The `~/.gemini/skills`
  root this plan reconciles is confirmed elsewhere in this repo's evidence to
  share a physical root with Antigravity's `.agents/skills`, so this is the
  correct authority for that root, not a loose association.
- **Secondary, corroborating:** [Get started with Agent
  Skills](https://geminicli.com/docs/cli/tutorials/skills-getting-started/)
  (Gemini CLI docs), retrieved 2026-08-15. Independently documents the same two
  fields and adds a specific parser behavior: a `SKILL.md` is **silently
  skipped** (not an error, not a warning) if `name:` or `description:` is
  missing, if the `---` delimiters are absent, or if any text precedes the
  opening `---`.

Both sources agree on the same two fields; neither documents any others.

## Accepted preserved keys

| Field | Required | Constraint |
| --- | --- | --- |
| `name` | No | Defaults to the folder name if omitted. Lowercase, hyphens for spaces per both sources' examples. |
| `description` | Yes | Free text. This is what the agent reads to decide relevance — both sources recommend third person, specific keywords, and a "use when..." clause. |

## Open finding — three implemented keys are not part of the documented contract

The plan's Task 3 explicitly calls for verifying `user-invocable: false` before
retaining it for `agent-methodology`, and the real on-disk files this plan
reconciles (`~/.gemini/skills/agent-methodology/SKILL.md` and others) do carry
that key today. **It does not appear in either official source above.**

Checked against the implemented `_validate_frontmatter` accepted-key set in
`gemini_reconciliation.py` (`{"name", "description", "user-invocable",
"when_to_use", "effort"}`): only `name` and `description` are confirmed by
either source. **`user-invocable`, `when_to_use`, and `effort` are all
undocumented** — none of the three appears anywhere in either official page.

This is reported as a finding, not resolved here, because resolving it means a
real behavioral choice between three options with different risk profiles, and
that choice belongs with whoever implements the frontmatter-validation logic,
not with a citation fix:

1. **Treat it as silently-tolerated.** Neither source's parser-behavior section
   (the geminicli.com "if your skill doesn't appear" list) mentions unknown keys
   as a skip condition — only missing `name`/`description` or missing
   delimiters are. If Gemini's actual YAML frontmatter parser ignores unknown
   keys (typical, but *unconfirmed against Gemini's real parser*, not just
   against its documentation), preserving `user-invocable` is harmless dead
   weight.
2. **Treat it as a legacy/private field this plan should stop preserving.** If
   it is undocumented because it was never a supported field, propagating it
   forward through every reconciled adapter perpetuates something with no
   contract behind it.
3. **Treat the documentation as incomplete** and preserve it anyway, since it
   is observed in the wild on files that demonstrably work today.

## Rejection rule

An unknown field raises `ValueError("unsupported frontmatter key: <exact-key>")`;
a known key with an unaccepted value identifies both the exact key and value in
its error. Per the open finding above, whether `user-invocable` counts as
"known" or "unknown" for this rule is exactly the unresolved question — this
contract intentionally does not silently decide it.
