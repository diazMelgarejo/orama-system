## Cursor Cloud: git commits

Cloud agents set `CURSOR_AGENT=1` and may inject `Co-authored-by` via managed hooks.

### On every cloud session (this repo)

```bash
bash scripts/git/apply-attribution-guards.sh
bash scripts/git/check_identity.sh
```

### When `git commit` still adds trailers

```bash
bash scripts/git/commit-clean.sh -m "type(scope): summary"
```

### Fork PR base

All integration/deps PRs target branch **`merged`**, not **`main`**. See `.cursor/rules/openclaw-fork-guide.mdc`.

Canonical policy: [orama-system wiki — Cursor Cloud commit attribution](https://github.com/diazMelgarejo/orama-system/blob/main/docs/wiki/12-cursor-cloud-commit-attribution.md).
