<!-- lint-ignore LINT-013 -->
# 46 — Repository Standard (cross-cutting, additive)

> **Status:** active, cross-cutting. Applies to every `docs/v2/*` plan.
> **Additive, not a replacement:** this standard adds to and builds on top
> of every other rule already documented across `docs/v2/*` — it never
> overrides a stricter, more specific standard elsewhere in this tree.
> Where a plan is silent on repo layout, this is the default; where a plan
> is stricter, the stricter rule still governs.

---

## The standard

**Repository root remains minimal.**

Everything executable belongs under `/src`.

**No root-level:**

- `scripts`
- `tests`
- `tools`
- `examples`

**Data output and produced binaries** are safe in other `.gitignore`d
folders. **Never commit:**

- API keys
- personal paths
- doxxing material
- SecOps-sensitive material

**Tracked policy names categories, not concrete local-only fragments.**
If a rule forbids a local identity, attribution marker, device, endpoint,
path, workspace, or topology fragment, the exact fragment belongs in a
local-only registry outside git. Tracked docs and tests use abstract wording
or synthetic registry fixtures. See
[`47-portable-memory-local-topology-invariant.md`](47-portable-memory-local-topology-invariant.md).

---

## Why this is additive, not a conflict

Every other standard already documented in this tree — anti-doxxing path
hygiene, RFC1918/TEST-NET IP sanitization, secret redaction before
persistence, the SKILL.md 500-line ceiling, progressive disclosure into
`references/`, the Post-Review Micro-Remediation branch discipline — keeps
governing exactly as written. This document only adds one more axis: **where
things live in the tree**, not **what they may contain** or **how they get
reviewed**. If a future plan needs a root-level exception (a genuine
platform requirement, e.g. a build tool that only works from repo root),
document the exception explicitly in that plan and link back here — silence
means the default applies.

## Relationship to existing structure

This formalizes a pattern several `docs/v2/*` plans already assume
implicitly (e.g. [`01-kernel-spec.md`](01-kernel-spec.md)'s
`perpetua-core/` layout, which already keeps its package code under a
single top-level source tree). This document makes that pattern explicit
and universal across the v2 tree, rather than leaving it as convention
inferred per-plan.

## See also

- [`23-security-preconditions.md`](23-security-preconditions.md) — LAN/auth preconditions, read first alongside this standard
- [`24-security-first-platform.md`](24-security-first-platform.md) — security as a first-class product feature
- [`27-git-governance-zero-fragmentation.md`](27-git-governance-zero-fragmentation.md) — companion git-workflow standard
- [`47-portable-memory-local-topology-invariant.md`](47-portable-memory-local-topology-invariant.md) — companion portable-memory and local-topology standard
- `orama-system` [`references/post-review-micro-remediation.md`](../../bin/orama-system/references/post-review-micro-remediation.md) — companion review-remediation standard
