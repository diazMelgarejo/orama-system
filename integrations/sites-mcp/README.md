# Oramasys Sites MCP workspace (v1)

A portable, stateless HTTP MCP adapter and private prompt editor/history. PT owns the compiler,
schema and persistent operations; Orama owns the transport, tool descriptions and presentation. The
browser calls the same `/mcp` handler as chat clients. No separate UI database API exists.

## Reproduce

1. Prepare a current Sites Vinext/Workers starter using the Sites plugin instructions; register once
   and preserve its project identity.
2. Check out the PT companion PR containing `packages/prompt-workspace`.
3. Run `node integrations/sites-mcp/assemble.mjs <absolute PT checkout> <absolute prepared Site
   checkout>`. The assembler rejects any source or schema mismatch against the reviewed PT snapshots
   in `src/`. No downloaded moving-branch dependency or sandbox path is shipped.
4. Install starter dependencies with its supported helper; retain one package manager and one
   corresponding root lockfile. Archive legacy lockfiles outside build inputs.
5. Generate D1 migrations (`pnpm run db:generate`), lint (`pnpm exec eslint app db`), typecheck
   (`pnpm exec tsc --noEmit`), and run the Sites build helper. The hosting manifest declares logical
   `DB` and capability `mcp`; credentials/project identity are not in this template.
6. Save a private version with the Sites workflow. The attached guide explicitly requires owner
   review before publishing. Do not change audience or deploy until approved. Then follow Sites
   native deployment/plugin install steps; do not advertise an unpublished URL as live.

`node --test integrations/sites-mcp/tests/*.test.mjs` runs adapter tests and real SQLite tool
lifecycle tests on Node 24. `node integrations/sites-mcp/check-snapshot.mjs <PT checkout>` checks
pinned source/schema separately. `SPECS.md` is the tool/authority contract.

## Operational limits

The workflow produces a **structured prompt contract**, not model inference or a completed Oramasys
agent-network task. Existing Python stdio and local API/portal services stay independent. Task-state
and LAN control tools are deliberately outside this cloud adapter. Before inference is added, use
the production extension gates in the audit. Before sharing, verify trusted identity-header
injection and user isolation on the deployed private Site; never expose an unprotected raw Worker.

Records are retained when archived; source text is not replaced. History is newest-first by
`(created_at, id)`. A retry uses the same request key only for identical input. No list-all/export,
provider cost, Python subprocess, local endpoint discovery, or permanent delete operation is
exposed.

## Readiness tools and private rollout

The immediate startup workaround is a child-scoped `XDG_CONFIG_HOME` pointing to
an absolute, ignored local directory. Do not change the developer's `HOME`.
Wrangler's logs, registries and XDG configuration use distinct locations. A
disposable child with a regular file as its synthetic home reproduced the
configuration failure; an explicit XDG directory restored readiness.

On Node 24, with operator-supplied absolute paths:

```bash
node integrations/sites-mcp/check-snapshot.mjs "$PERPETUA_TOOLS_ROOT"
node integrations/sites-mcp/assemble.mjs "$PERPETUA_TOOLS_ROOT" "$SITE_ROOT"
# In the Site root: use its package manager to generate migrations, lint,
# typecheck without incremental output, and build.
node integrations/sites-mcp/verify-assembled.mjs "$PERPETUA_TOOLS_ROOT" "$SITE_ROOT"
node integrations/sites-mcp/local-preview.mjs "$SITE_ROOT" --isolated-config --runtime-dir "$RUNTIME_DIR"
node integrations/sites-mcp/tests/local-worker-smoke.mjs "$SITE_ROOT"
```

The launcher resolves Site-owned Wrangler and its preload, binds only loopback,
and preserves host settings. It requires runtime storage in an ignored, untracked
directory or outside the checkout, resolving existing symlink ancestors and D1/config
destinations. The child receives `SITES_RUNTIME_ROOT` so starter defaults follow that
directory. Explicit absolute XDG configuration is preserved; invalid paths fail.

The separate verifier never repairs source. It checks exact compiler, server and
overlay bytes, provenance, manifest capabilities/bindings, migration journal order,
canonical columns/indexes (including unconditional uniqueness), the archived CHECK
and real store query plans. SQLite verification is in memory with disk attachment denied.

Keep old migrations and journal entries unchanged. Generate an index-only follow-up
when the old index lacks `created_at`: drop `prompt_records_owner_active`, create
`prompt_records_owner_history(owner_id, archived, created_at, id)`. Stop if generated
SQL changes tables, columns or rows. Code rollback does not reverse D1 migrations.

The re-runnable smoke test uses disposable external local D1, verifies HTTP bounds,
notifications, retries/conflicts, two synthetic owners, same-timestamp pagination,
archive and restart persistence. Cancellation stops its owned Worker process group.
The real Wrangler reproduction is opt-in:
`SITES_MCP_SITE_ROOT="$SITE_ROOT" node --test integrations/sites-mcp/tests/local-preview.test.mjs`.

Preserve the existing private Site and generated plugin. Record concrete identifiers
only in an off-repo runbook. After publication probe anonymous root, initialize and
read-only history before connecting. A forged-header probe needs separate owner
authorization. Never manufacture hosted identity with fixture headers or service tokens.
The exposed Sites connector has no unpublish operation: establish a first-publication
reversal or obtain explicit one-way acceptance. For later updates retain the compatible
prior saved version; redeploying it does not erase records or reverse migrations.

The UI handles non-JSON 401/403 gateway errors before parsing, preserving the input and
showing a sign-in/access explanation. This repairs opaque parser errors; OAuth denial
at the hosting boundary remains a distinct platform issue. Check the full access policy
and sign-in redirect before adding viewers. An installed widget message or suggested
plugin is not a verified authenticated call. See the implementation handoff in
`docs/v2/references/SITES-READINESS-R2-IMPLEMENTATION-2026-10-06.md`.
