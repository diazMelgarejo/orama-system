# Agent instructions — orama-system

## Cursor Cloud: git commits

Cloud agents set `CURSOR_AGENT=1` and redirect `core.hookspath` to `~/.cursor/agent-hooks/…`, which can append unwanted `Co-authored-by` trailers. **`CURSOR_AGENT=0` is not supported** and does not disable this.

### On every cloud session (all OpenClaw repos)

```bash
bash scripts/git/apply-attribution-guard-all-repos.sh
bash scripts/git/check_identity.sh
```

### When `git commit` still adds trailers

```bash
bash scripts/git/commit-clean.sh -m "type(scope): short summary"
```

### Repos covered

- `orama-system` (this repo)
- `Perpetua-Tools` (`$PERPETUA_TOOLS_PATH` or `$OPENCLAW_HOME/Perpetua-Tools`)
- `AlphaClaw` (`$ALPHACLAW_INSTALL_DIR` or `$OPENCLAW_HOME/AlphaClaw`)

See `docs/wiki/09-cursor-cloud-commit-attribution.md`.
