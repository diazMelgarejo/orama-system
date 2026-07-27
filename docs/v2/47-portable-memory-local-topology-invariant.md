# 47 - Portable Memory and Local-Topology Invariant

> **Repository standard:** additive to [`46-repository-standard.md`](46-repository-standard.md).
> Applies to every future `oramasys/*`, `perpetua-core/*`, and sibling
> agentic repo that carries portable memory, skills, coordination logs, or
> security policy.

---

## Prime invariant

Tracked policy names categories. It does not spell concrete local-only
fragments.

Concrete forbidden identity, attribution, device, address, path, workspace,
and topology fragments live only in a local-only registry outside every git
worktree. Repos may contain loaders, scanners, tests with synthetic markers,
and abstract guidance, but must not hardcode the exact fragments they are
trying to forbid.

This is stricter than ordinary path hygiene. It closes the self-violation
where a negative rule leaks the same local detail it warns agents not to
record.

## Required guard shape

Every repo with agent memory must provide a portable-brain guard that is a
strict superset of ordinary repo hygiene:

- exact configured private literals from the local-only registry
- private or unclassified full email literals in portable memory
- personal home-directory paths
- local workspace topology fragments from the local-only registry
- local temporary paths from the local-only registry
- secrets and API-key patterns
- derived views as well as source rows

The guard reports path, line, and category only. It never prints the matched
literal.

## Local-only registry contract

The local registry is outside git and outside every disposable worktree. It is
shared by Claude, Codex, Cline, Kimi, hooks, and CI bootstrap shims when local
policy is available.

Recommended abstract keys:

- `owner_gmail`
- `owner_name`
- `forbidden_attribution`
- `local_path_fragment`
- `local_workspace_fragment`
- `verboten_path_fragment`
- `device_or_network_fragment`

Tracked code must treat unknown keys as inert and must tolerate a missing
registry in CI by still enforcing generic secret and personal-path rules.

## Memory rule

Supersession is not sanitization.

When a memory row leaks a private or local-topology literal, fix the source row
or archived candidate, then regenerate every derived view. A struck-through
rendered lesson, stale candidate, or old episodic row still counts as leaked
portable memory until the source is scrubbed.

## Documentation rule

Docs may say:

- "personal home-directory path"
- "workspace-tree path"
- "local temporary path"
- "operator-specific endpoint"
- "local-only registry"

Docs must not include the concrete string form of the prohibited fragment just
to explain what is prohibited. If an implementation test needs a trigger, use
a synthetic marker loaded from a temporary local-only registry fixture.

## Mesh topology migration

Committed RFC1918 / link-local endpoint literals violate this invariant. The
pre-v2 removal path is **Phase B** in
[`50-mesh-security-migration-ladder.md`](50-mesh-security-migration-ladder.md):
endpoints move to `.env.local` / `.local/lan-topology-archive.json` after
**Phase A** backup on every fleet node. Affinity slugs (hardware tier categories
such as `win-gpu-secondary` / `win-gpu-primary`) remain in tracked config; only
address literals are expunged.

## Acceptance

- A whole `.agent/` or equivalent portable-memory scan reports zero hits.
- `repo_hygiene.py` or its successor enforces the portable-brain guard.
- Tests prove local-only registry loading with synthetic values only.
- Memory tools redact at write time before candidate, episodic, or semantic
  records are persisted.
- Rendered memory files are regenerated from sanitized source records.

