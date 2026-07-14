# G7 Firecrawl Evidence Archive

This directory preserves the raw Firecrawl output behind the synthesized
[G7 SSE production-patterns research](../2026-07-14-g7-sse-production-patterns.md).
It was captured on 2026-07-14 for the authenticated FastAPI SSE notification
MVP. The files are retained for traceability and source review, not as a
replacement for the cited standards, official documentation, or canonical
`docs/v2/*` plans.

The original output was moved out of the obsolete G7 worktree on 2026-07-15.
Transient website visitor, nonce, request, and CSRF metadata, plus personal
absolute-path fragments embedded by source sites, were redacted before
archiving. Source URLs, response content, and Firecrawl result IDs are
otherwise preserved. Fresh command output belongs in a local `.firecrawl/`
cache until it is deliberately promoted here.

| File | Capture type | Research question |
| --- | --- | --- |
| `g7-fastapi-sse-auth.json` | Search response | FastAPI SSE authentication patterns |
| `g7-fastapi-sse.md` | Scrape | FastAPI SSE framework guidance |
| `g7-oss-examples.json` | Search response | Open-source implementation comparison set |
| `g7-owasp-csrf.md` | Scrape | Browser authentication and CSRF defaults |
| `g7-sse-protocol.json` | Search response | SSE wire-protocol conventions |
| `g7-sse-queue.json` | Search response | Bounded queue and backpressure patterns |
| `g7-sse-starlette-source.md` | Scrape | `sse-starlette` production implementation |
