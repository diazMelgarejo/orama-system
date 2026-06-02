# Fork Self-Heal

Re-applies orama's shipped fork fixes to `gstack` / `gbrain` after an upgrade
clobbers them, **until the upstream PRs merge**. Idempotent, detection-gated,
fail-closed. Version 0.9.9.9.

## Why

`gstack upgrade` / `gbrain upgrade` overwrite `~/.claude/skills/gstack` (and the
gbrain install) with the released version. A fix we shipped upstream but that has
not merged yet is silently reverted on every upgrade — and for #1802 that means a
**repo-deleting `rm -rf` bug comes back**. This keeps our fixes in place without
forking the whole tool.

## How it works

`apply-fork-patches.sh` iterates `patches/*.patch` (each with a sibling `.meta`):

1. **Detect** — if the fix is already present (`MARKERS` grep hits, or the patch
   reverse-applies cleanly), **no-op**. This covers both "we already patched it"
   and "upstream merged it" → the patcher quietly retires itself.
2. **Apply** — `git apply --check` → apply; on line drift, `git apply --3way`
   (merges against blob context). `git apply` is **atomic** — never half-applies.
3. **Verify** — run the patch's `VERIFY` (e.g. `bun test ...`). On failure, roll
   back the patch's files (and remove any new files it added). Never half-patched.
4. On conflict/drift it does **not** blind-overwrite (that would regress other
   upstream changes) — it warns loudly and leaves the tree untouched for manual
   review.

## Register a patch

Drop two files in `patches/`:

- `<id>.patch` — `git diff <base>...<fix-branch>` from the target repo.
- `<id>.meta` — `TARGET` (`gstack`|`gbrain`), `MARKERS` (space-separated presence
  strings), `VERIFY` (command run from the target root).

## Triggers

- **Automatic:** `~/.zshrc` runs `apply-fork-patches.sh --quiet` on shell start
  (silent no-op when already patched).
- **Manual / skill:** documented in the `mcp-install` skill (Fork Self-Heal).

## Retire

When a patch's upstream PR merges, delete its `.patch` + `.meta`. (The `MARKERS`
grep already neutralizes it, so removal is just housekeeping.)

## Current patches

| id | target | upstream | retire when |
|----|--------|----------|-------------|
| `gstack-1802-staging-guard` | gstack | [gstack#1827](https://github.com/garrytan/gstack/pull/1827) (+ [gbrain#1728](https://github.com/garrytan/gbrain/issues/1728)) | #1827 merges |
