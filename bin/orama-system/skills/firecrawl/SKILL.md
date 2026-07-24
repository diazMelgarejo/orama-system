---
name: firecrawl
description: |
  Firecrawl gives AI agents and apps fast, reliable web context with
  strong search, scraping, interaction, document parsing, research,
  and monitoring tools. One install command sets up three skill
  segments: live CLI tools, app-integration build skills, and
  outcome-focused workflow skills. Route the reader to the right
  usage path after install.
---

# Firecrawl

Firecrawl is a downstream scraping and extraction tool, used once a URL
is already known -- not a search engine. It scrapes clean content,
interacts with live pages when plain extraction is not enough, parses
local documents into markdown, searches scientific papers and GitHub
history through the research index, monitors pages for changes, and
produces finished deliverables from web data.

## Fit in orama-system (read first)

Firecrawl is an **extraction** tool, not a discovery tool — it does not
replace [`../../SKILL.md` § Search Policy](../../SKILL.md) (gbrain →
code-review-graph → Brave → Perplexity → Grok for facts/decisions/code
context). Reach for Firecrawl when the Search Policy chain has already
found a URL (or you already have one) and you need clean, structured
content *from* it — scraping, interacting with a live page, parsing a
local document, or monitoring a page for change. The existing convention
in `clinepass-deepseek-flash/SKILL.md` § EXA And Firecrawl Verification
already establishes the pairing: **EXA first for broad discovery,
Firecrawl second for exact extraction.** Follow that ordering here too;
don't fire both in parallel.

**Two access paths, both live in this stack:**

- **MCP** — `mcp__firecrawl__*` tools, once authenticated (below). Prefer
  this from inside a Claude Code session — no subprocess, no CLI install.
- **CLI** — `firecrawl <command>` after the install below. Use this for
  scripted/headless work outside an interactive session (cron jobs,
  `coord_pulse` cycles, CI).

Both hit the same account and rate limits; pick whichever is already
warm rather than installing the CLI just to duplicate an authenticated
MCP session.

## Authenticating the MCP (session-scoped)

The Firecrawl MCP server requires OAuth per session — there is no
standing credential to check into this repo.

```text
mcp__firecrawl__authenticate
```

returns an authorization URL. The **human** opens it in their browser
and completes sign-in/authorization; the server's real tools (search,
scrape, interact, parse, monitor, research, ask, docs-search) become
available automatically once they do. If the redirect page errors, have
them paste the full browser address-bar URL back and call
`mcp__firecrawl__complete_authentication` with it.

**Never persist the resulting API key into a tracked file.** If a key
ever appears in plaintext in a chat, doc, or scratch file (e.g. pasted
from a "Session-specific auth" block in onboarding docs), treat it as
exposed — advise rotating it in the Firecrawl dashboard, and never let
it land in a git-tracked path. This applies even to session-scoped keys
that "expire soon"; the portable-memory security boundary invariant
(`CLAUDE.md` § portable memory and local topology) treats any tracked
secret the same regardless of claimed lifetime.

## Install (CLI path)

One command installs everything — the Firecrawl CLI for live web work,
the build skills for integrating Firecrawl into application code, **and**
the workflow skills for producing repeatable deliverables. It also opens
browser auth so the human can sign in or create an account.

```bash
npx -y firecrawl-cli@1.19.27 init --all --browser
```

The CLI version above is pinned to a specific, reviewed release, not
`@latest` — an unpinned version lets the installed CLI change out from
under this skill without re-review. Update this pin deliberately when a
newer CLI version has been checked, not automatically. This pin covers
the CLI binary only; `init --all` still installs the separate build/
workflow skill packages, whose own content is accepted on its own terms,
not implicitly re-reviewed by pinning the CLI version.

This gives you:

- **CLI tools** — `firecrawl search`, `firecrawl scrape`, `firecrawl interact`, `firecrawl parse`, `firecrawl monitor`, `firecrawl research`, `firecrawl ask`, `firecrawl docs-search`, and more
- **CLI skills** ([`firecrawl/cli`](https://github.com/firecrawl/cli)) — teach the agent how to drive the Firecrawl CLI during its own session: which command to run, when to scrape vs search vs interact, how to chain results, and how to recover when a job fails. Use these when the agent itself needs web data right now.
- **Build skills** ([`firecrawl/skills`](https://github.com/firecrawl/skills)) — teach the agent how to add Firecrawl to a product's codebase: pick the right API endpoint, install the matching SDK, store `FIRECRAWL_API_KEY` safely, write the call site to match the project's conventions, and ship a smoke-tested integration. Use these when the agent is shipping code that other people will run, not running the agent's own web tools.
- **Workflow skills** ([`firecrawl/firecrawl-workflows`](https://github.com/firecrawl/firecrawl-workflows)) — turn Firecrawl web data into finished deliverables such as research briefs, SEO audits, lead lists, QA reports, knowledge bases, and design clones. Use these when the agent's job is to produce a finished artifact, not raw extraction or product code.
- **Browser auth** — walks the human through sign-in or account creation

The three skill segments map to three different jobs:

| Segment         | Question it answers                                        | Where the work runs                           |
| --------------- | ------------------------------------------------------------ | --------------------------------------------- |
| CLI skills      | "Which Firecrawl command should I run right now?"          | In the agent's own terminal session           |
| Build skills    | "How do I add a Firecrawl API call to this codebase?"      | Inside the user's product code                |
| Workflow skills | "What's the finished deliverable and how do I produce it?" | In the agent's session, producing an artifact |

Before doing real work, verify the install:

```bash
mkdir -p .firecrawl
firecrawl --status
firecrawl scrape "https://firecrawl.dev" -o .firecrawl/install-check.md
```

## Choose Your Path

- **Need web data during this session** → [Path A](#path-a-live-web-tools)
- **Need to add Firecrawl to app code** → [Path B](#path-b-integrate-firecrawl-into-an-app)
- **Need a finished deliverable from web data** → [Path C](#path-c-repeatable-deliverables)
- **Need more than one of the above** → do them in sequence
- **Need an account or API key, want the raw REST API, or have no key at all** → [Path D/E/F](#path-def-manual-account-auth-raw-rest-api-keyless-fallback) — rarely needed here, the MCP authenticate flow above covers most orama-system sessions

---

## Path A: Live Web Tools

Use this when you need web data during your work: searching the web,
scraping known URLs, interacting with live pages, crawling docs,
mapping a site, parsing local documents, searching research papers,
or monitoring pages for changes.

Via MCP (preferred inside a Claude Code session, once authenticated),
the connected server exposes `mcp__firecrawl__firecrawl_<name>` tools —
verified against a live connection: `firecrawl_search`,
`firecrawl_scrape`, `firecrawl_interact` / `firecrawl_interact_stop`,
`firecrawl_parse`, `firecrawl_crawl` / `firecrawl_check_crawl_status`,
`firecrawl_map`, `firecrawl_extract`,
`firecrawl_monitor_create` / `_get` / `_list` / `_run` / `_update` / `_delete` / `_check` / `_checks`,
`firecrawl_research_search_papers` / `_inspect_paper` / `_read_paper` / `_related_papers` / `_search_github`,
`firecrawl_agent` / `_agent_status`, and `firecrawl_feedback` /
`firecrawl_search_feedback`. **No `ask` or `docs-search` MCP tool is
exposed** — those two are CLI/REST-only (`firecrawl ask`,
`firecrawl-docs-search`, or `POST /support/ask` /
`/support/docs-search`); use the CLI or raw REST call for those two
specifically, everything else via MCP.

Via CLI (after install), hand off to the CLI skill:

- `firecrawl/cli` for the overall command workflow
- `firecrawl-search` when you need search first
- `firecrawl-scrape` when you already have a URL
- `firecrawl-interact` when the page needs clicks, forms, or login
- `firecrawl-crawl` for bulk extraction
- `firecrawl-map` for URL discovery
- `firecrawl-parse` when the source is a **local file** (PDF, DOCX, DOC, ODT, RTF, XLSX, XLS, HTML) — `firecrawl parse ./report.pdf -o .firecrawl/report.md` converts it to clean markdown, with `-S` for an AI summary or `-Q` to answer a question from the doc. Public document URLs go through `firecrawl scrape` instead
- `firecrawl-monitor` when the user wants to be **notified when something changes** — `firecrawl monitor create` sets up recurring checks (cron or natural-language schedules like `"every 30 minutes"`) that diff each page, run an AI judge against a plain-language `--goal` to filter noise, and notify by webhook, email, or Slack. Prefer this over repeated one-off scrapes whenever the same URL needs checking more than once. **Confirm with the user immediately before running `monitor create` or configuring any webhook, email, or Slack notification target** — this creates a recurring job and/or sends data to an external destination on an ongoing basis; do not execute it automatically as part of a broader task.
- `firecrawl-research-index` for scientific and engineering research — `firecrawl research search-papers`, `inspect-paper`, `read-paper`, `related-papers`, and `search-github` search a purpose-built paper index (metadata, full-text passages, citation expansion) plus GitHub issues, PRs, and READMEs
- `firecrawl-ask` when a Firecrawl call fails or returns unexpected output — pass the failing `jobId` and the AI support agent diagnoses it from your team's job logs and account state
- `firecrawl-docs-search` for "how does Firecrawl handle X?" questions — answers grounded in current docs with source citations

Default flow for live web work:

1. Discovery first via the [Search Policy](../../SKILL.md#search-policy) chain (gbrain → code-review-graph → Brave → Perplexity → Grok), or EXA when the request is broad ("find X in the OSS community") per the established EXA-first convention
2. Move to Firecrawl `scrape` once you have a URL
3. Use `interact` only when the page needs clicks, forms, or login
4. Use `parse` when the source is a local file instead of a URL
5. Use `monitor` when the request implies recurrence or notifications ("alert me when", "track this page") rather than a one-time read
6. If any step fails or returns unexpected output, run `firecrawl ask` (CLI-only, no MCP equivalent) with the failing `jobId` instead of guessing

If the task becomes "wire Firecrawl into product code," switch to Path B.

### EXA-first, Firecrawl-second verification pattern

The canonical two-step pattern for verifying a specific claim against a
real source (a CLI's documented flags, an API's exact field names, a
package's real version) rather than accepting a plausible-sounding
answer from memory:

1. **EXA** for broad discovery — one semantically rich query describing
   the ideal page, not keywords:

   ```text
   official <project> documentation <specific feature/flag/behavior being verified>
   ```

2. **Firecrawl `scrape`** for exact extraction from the URL EXA surfaced:

   ```bash
   firecrawl scrape "<url from EXA>" \
     -f markdown \
     --only-main-content \
     --redact-pii
   ```

   `--only-main-content` strips nav/footer/ads so the extracted text is
   the actual documentation, not page chrome. `--redact-pii` is a safe
   default even for non-personal docs pages — costs nothing when there's
   no PII present.

Don't fire EXA and Firecrawl in parallel — EXA's result is what tells you
which URL is worth extracting. Record which specific facts were verified
this way (not just "checked the docs") so a later reader can see exactly
what claim the extraction backed up — see
`clinepass-deepseek-flash/SKILL.md` § "Source facts verified this way"
for the pattern.

---

## Path B: Integrate Firecrawl Into an App

Use this when you're building an application, agent, or workflow that
calls the Firecrawl API **from code** — meaning the integration will run
inside the user's product (a web app, backend service, script, agent
loop, or pipeline) rather than from the agent's own terminal session.

This is the key difference from Path A: Path A runs `firecrawl ...`
commands (or MCP calls) during the current session to fetch data for the
agent itself. Path B writes code that will keep running long after the
agent stops, using `FIRECRAWL_API_KEY` from the project's `.env` or
runtime config and the matching Firecrawl SDK in the project's language.

The build skills are already installed from the same command above. No
separate install needed.

Choose the project mode before writing code:

- **Fresh project** → pick the stack, install the SDK, add env vars, and run a smoke test
- **Existing project** → inspect the repo first, then integrate Firecrawl where the project already handles APIs and secrets

If you already have a key, save it to the project's environment (never
to a tracked file):

```dotenv
FIRECRAWL_API_KEY=fc-...
```

Then hand off to the build skill that fits the step:

- `firecrawl-build` for the overall build workflow and endpoint routing
- `firecrawl-build-onboarding` for auth and project setup (API key, SDK install, smoke test)
- `firecrawl-build-scrape` when the feature scrapes a known URL
- `firecrawl-build-search` when the feature starts with a query and discovers pages
- `firecrawl-build-interact` when the feature needs clicks, forms, or navigation after a scrape
- `firecrawl-build-parse` when the feature parses local or non-public document files (PDF, DOCX, XLSX, etc.)

The required question in the build path is:

- **What should Firecrawl do in the product?**

Use the answer to route to `/search`, `/scrape`, `/interact`, `/parse`, `/crawl`, `/map`, `/monitor` (recurring change detection with webhook/email notifications), or the research index (`/search/research/*`), then run one real Firecrawl request as a smoke test.

If you do not have a key yet, see [Path D/E/F](#path-def-manual-account-auth-raw-rest-api-keyless-fallback) or [`references/account-auth-and-rest-api.md`](references/account-auth-and-rest-api.md) § Path D.

---

## Path C: Repeatable Deliverables

Use this when the goal is a finished artifact powered by Firecrawl web
data — a research brief, SEO audit, QA report, lead list, knowledge
base, competitive intel digest, or a cloned design system — not raw web
extraction and not product-code integration.

Workflow skills infer from context first and only ask short clarifying
questions when an input would block the work. They also call out
independently parallelizable units so sub-agents can fan out across
competitors, pages, or sources.

Start with the umbrella `firecrawl-workflows` skill — it inspects the
user's request and routes to the right workflow (research, SEO, lead
gen, QA, knowledge base, design clone, and others). If the agent
already knows which workflow to run, hand off to that workflow skill
directly.

The full skill list lives in the [workflows repo](https://github.com/firecrawl/firecrawl-workflows).

Default flow for workflow deliverables:

1. Confirm the workflow and final artifact with the user
2. Collect web evidence with Firecrawl through the CLI, MCP, or equivalent tool surface
3. Save or cite source evidence so claims are traceable
4. Run independent research units in parallel when available (fan out via subagents per this repo's own orchestration conventions)
5. Synthesize findings into the requested deliverable
6. Include a short "rerun inputs" block when the workflow could be automated

If the underlying web work fails or the request shifts to "wire Firecrawl into product code," switch to Path A or Path B.

---

## Path D/E/F: Manual Account Auth, Raw REST API, Keyless Fallback

Rarely needed inside an orama-system session — the MCP `authenticate`
flow above covers the common case. Full detail (manual CLI OAuth polling
loop, calling `api.firecrawl.dev/v2` directly with no CLI/MCP installed,
and the rate-limited keyless free tier) lives in
[`references/account-auth-and-rest-api.md`](references/account-auth-and-rest-api.md).
Reach for it when: the human needs to authorize via the CLI flow
specifically (not MCP), you're integrating the raw REST API into product
code without an SDK, or no API key is available at all.

---

## Related skills

- [`../../SKILL.md` § Search Policy](../../SKILL.md#search-policy) — the discovery chain Firecrawl extraction sits downstream of
- [`../clinepass-deepseek-flash/SKILL.md` § EXA And Firecrawl Verification](../clinepass-deepseek-flash/SKILL.md) — the established EXA-first, Firecrawl-second pairing this skill formalizes
