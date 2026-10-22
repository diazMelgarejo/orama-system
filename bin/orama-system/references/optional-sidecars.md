<!-- lint-ignore LINT-013 -->
# Optional Lazy-Sidecars (OmniRoute and Periscope ECC)

> Never-required, never-fail-if-absent sidecars: the OmniRoute parallel-dispatch sidecar
> (currently disabled) and the Periscope ECC mirror verifier. Moved verbatim out of
> `SKILL.md`. The canonical sidecar procedures live in the linked sub-skills; this card
> keeps the mother-skill summary and NEVER rules. Link targets were rebased for this folder.

## OmniRoute Lazy-Sidecar (Optional Parallel Dispatch)

> **NEVER install. NEVER require. NEVER fail if absent.**
> **CURRENTLY DISABLED (2026-06-14).** Skip probing entirely. Use the
> [Local API Fallback](local-api-fallback.md). To re-enable, follow
> [OmniRoute's re-enable procedure](../skills/omniroute/SKILL.md).

When OmniRoute is explicitly enabled, it is an optional local HTTP MCP server
that fans tasks to free OpenRouter/AgentRouter models in parallel. Probe once
at session start (token from `$OMNIROUTE_TOKEN`, never hardcoded); if
`running`/`started`, route fan-out subtasks through it; if unavailable,
continue silently on the standard stack — never warn or suggest installing it.

→ Canonical sidecar: [OmniRoute](../skills/omniroute/SKILL.md).

## Periscope ECC Lazy-Sidecar (Optional Mirror Verify)

> **NEVER install. NEVER require. NEVER fail if absent.**

When a periscope clone with ECC bundle paths exists, agents may run the idempotent
mirror verifier. If absent, skip silently.

→ Canonical sidecar: [Periscope ECC](../skills/periscope-ecc/SKILL.md).
