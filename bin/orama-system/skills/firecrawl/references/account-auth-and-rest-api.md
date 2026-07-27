# Firecrawl — account auth (CLI flow) and raw REST API

Reference for [`../SKILL.md`](../SKILL.md). Covers the paths less
frequently needed inside an orama-system session: manual CLI-based
account authorization, calling the REST API directly with no CLI/MCP
installed, and the keyless free-tier fallback. For the common case
(MCP auth, live tools, app integration, deliverables), stay in the main
skill.

---

## Path D: Account Authorization Or API Key

Use this when the human still needs to sign up, sign in, authorize
access, or obtain an API key. Inside a Claude Code session, prefer the
MCP `authenticate`/`complete_authentication` flow in the main skill —
it does not require the human to leave the browser-auth prompt or
paste anything back into a shell script.

If you ran the install command with `--browser`, the human was
already prompted to sign in. Check if the key is available before
running this flow.

If you already have a valid `FIRECRAWL_API_KEY`, skip this path.

If you're the human reading this in the browser, create an account or
sign in at:

- https://www.firecrawl.dev/signin?view=signup&source=agent-suggested

If you're an agent and need the human to authorize an API key via the
CLI flow specifically (not MCP), use this flow:

**Step 1 — Generate auth parameters:**

```bash
SESSION_ID=$(openssl rand -hex 32)
CODE_VERIFIER=$(openssl rand -base64 32 | tr '+/' '-_' | tr -d '=\n' | head -c 43)
CODE_CHALLENGE=$(printf '%s' "$CODE_VERIFIER" | openssl dgst -sha256 -binary | openssl base64 -A | tr '+/' '-_' | tr -d '=')
```

**Step 2 — Ask the human to open this URL:**

```
https://www.firecrawl.dev/cli-auth?code_challenge=$CODE_CHALLENGE&source=coding-agent#session_id=$SESSION_ID
```

If they already have a Firecrawl account, they'll sign in and authorize.
If not, they'll create one first and then authorize. The API key comes
back to you automatically after they click "Authorize."

**Step 3 — Poll for the API key:**

```bash
POST https://www.firecrawl.dev/api/auth/cli/status
Content-Type: application/json

{"session_id": "$SESSION_ID", "code_verifier": "$CODE_VERIFIER"}
```

Poll every 3 seconds. Responses:

- `{"status": "pending"}` — keep polling
- `{"status": "complete", "apiKey": "fc-...", "teamName": "..."}` — done

**Handle the returned `apiKey` value with care:** write it straight to
the project's local environment file (Step 4 below) and nothing else.
Never print, log, echo, or paste the real key into chat, a shell command,
a terminal transcript, or any tracked file — treat every one of those as
a leak, not a convenience. The example response above shows the field
*shape* (`"fc-..."`), not something to reproduce with a real value filled
in.

**Step 4 — Save the key to the project's local environment file only**
(environment file, gitignored) **— never to a tracked skill doc, memory file, or
commit.** See the security note in [`../SKILL.md`](../SKILL.md) §
"Authenticating the MCP".

---

## Path E: Use Firecrawl Without Installing Anything

Use this when you don't want to install a CLI or skills package. This
works for both use cases:

- **Live web work** — an agent calling the API (or MCP) directly for search, scrape, or interact during a session
- **Building with Firecrawl** — integrating the REST API into app code

You still need an API key (or an authenticated MCP session). Two ways
to get one:

- **Human pastes it in** — if you already have a key, set
  `FIRECRAWL_API_KEY=fc-...` in the project's environment file (gitignored secrets file,
  gitignored) or the shell's environment for the current session. Never
  pass an API key as a command-line argument, type it into chat, write it
  to a log file, or leave it visible in shell history or a process
  listing (`ps`) — any of those exposes the key outside the process that
  actually needs it. Read it from the environment at call time instead.
- **Automated flow** — do Path D to walk the human through browser auth
  and receive the key automatically, or use the MCP authenticate flow

**Base URL:** `https://api.firecrawl.dev/v2`

**Auth header:** `Authorization: Bearer fc-YOUR_API_KEY`

### Available endpoints

- `POST /search` — discover pages by query, returns results with optional full-page content
- `POST /scrape` — extract clean markdown from a single URL, including public document URLs (PDF, DOCX, etc.)
- `POST /interact` — browser actions on live pages (clicks, forms, navigation)
- `POST /parse` — upload a **local or non-public document** as `multipart/form-data` (PDF, DOCX, DOC, ODT, RTF, XLSX, XLS, HTML; up to 50 MB) and get back markdown, JSON, HTML, links, images, or a summary. Use `/scrape` instead when the document has a public URL
- `POST /monitor` — create a recurring check that watches known pages (`scrape` targets), a whole site crawl (`crawl` targets), or web-wide search results (`search` targets), diffs each check against the last snapshot, optionally judges changes against a plain-language `goal`, and notifies by webhook, email, or Slack. `GET /monitor` lists monitors; `GET /monitor/{id}/checks` returns page-level results
- `GET /search/research/papers` — search a purpose-built scientific paper index by natural-language query; `GET /search/research/papers/{id}` inspects metadata or (with `query`) returns the top full-text passages; `GET /search/research/papers/{id}/similar` expands to related papers, citers, or references; `GET /search/research/github` searches GitHub issues, PRs, discussions, and READMEs
- `POST /support/ask` — diagnose a failing Firecrawl call. Pass `{ question, jobId? }`; returns a prose `answer` plus machine-readable `fixParameters` to retry with. Auto-scoped to your team via the bearer key
- `POST /support/docs-search` — answer "how do I…" questions from Firecrawl's official docs. Pass `{ question }`; returns the answer plus citations to the docs pages used

### Documentation and references

The API docs are the source of truth for request/response schemas,
parameters, and SDKs:

- **API reference:** https://docs.firecrawl.dev
- **Skills repo** (for agent integration patterns): https://github.com/firecrawl/skills

---

## Path F: Keyless Free Tier (Fallback)

Use this when you need Firecrawl right now and cannot obtain an API key,
for example when the human is not available to sign up. The keyless free
tier lets you search, scrape, interact, and parse without an API key
when the request comes from an official Firecrawl client (MCP, CLI, or
SDK). It is rate-limited, so use it as a fallback rather than the
default.

- **MCP**: point any MCP-compatible client at `https://mcp.firecrawl.dev/v2/mcp`
- **CLI**: run `npx -y firecrawl-cli@1.19.27` and use `scrape`, `search`, `interact`, or `parse` with no login
- **API**: the research index endpoints (`/search/research/*`) can be called without an `Authorization` header

Search, scrape, interact, parse, and the research index are available
keyless. Crawl, map, monitor, extract, batch scrape, agent, and other
endpoints still require an API key.

Prefer a full account when the human can sign up: do Path D or the MCP
authenticate flow, which unlocks higher limits and the full set of
endpoints. If you hit rate limits on the keyless free tier, ask the
human to sign up at https://www.firecrawl.dev/signin.
