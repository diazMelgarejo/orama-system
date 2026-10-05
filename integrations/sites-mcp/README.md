# Oramasys Sites MCP workspace (v1)

A portable, stateless HTTP MCP adapter and private prompt editor/history. PT owns the compiler, schema and persistent operations; Orama owns the transport, tool descriptions and presentation. The browser calls the same `/mcp` handler as chat clients. No separate UI database API exists.

## Reproduce

1. Prepare a current Sites Vinext/Workers starter using the Sites plugin instructions; register once and preserve its project identity.
2. Check out the PT companion PR containing `packages/prompt-workspace`.
3. Run `node integrations/sites-mcp/assemble.mjs <absolute PT checkout> <absolute prepared Site checkout>`. The assembler rejects any source or schema mismatch against the reviewed PT snapshots in `src/`. No downloaded moving-branch dependency or sandbox path is shipped.
4. Install starter dependencies with its supported helper; retain one package manager and one corresponding root lockfile. Archive legacy lockfiles outside build inputs.
5. Generate D1 migrations (`pnpm run db:generate`), lint (`pnpm exec eslint app db`), typecheck (`pnpm exec tsc --noEmit`), and run the Sites build helper. The hosting manifest declares logical `DB` and capability `mcp`; credentials/project identity are not in this template.
6. Save a private version with the Sites workflow. The attached guide explicitly requires owner review before publishing. Do not change audience or deploy until approved. Then follow Sites native deployment/plugin install steps; do not advertise an unpublished URL as live.

`node --test integrations/sites-mcp/tests/*.test.mjs` runs adapter tests and real SQLite tool lifecycle tests on Node 24. `node integrations/sites-mcp/check-snapshot.mjs <PT checkout>` checks pinned source/schema separately. `SPECS.md` is the tool/authority contract.

## Operational limits

The workflow produces a **structured prompt contract**, not model inference or a completed Oramasys agent-network task. Existing Python stdio and local API/portal services stay independent. Task-state and LAN control tools are deliberately outside this cloud adapter. Before inference is added, use the production extension gates in the audit. Before sharing, verify trusted identity-header injection and user isolation on the deployed private Site; never expose an unprotected raw Worker.

Records are retained when archived; source text is not replaced. History is lexical UUID order, not recent-first. A retry uses the same request key only for identical input. No list-all/export, provider cost, Python subprocess, local endpoint discovery, or permanent delete operation is exposed.
