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

## Prime directives for agent-maintained records

- Treat vulnerability memory, lessons, audits, and review ledgers as append-only
  historical records. Do not erase, delete, replace, truncate, or rewrite prior
  entries unless the user explicitly instructs that exact destructive action.
- When a record is stale, defunct, remediated, duplicated, or superseded, update
  it additively: add or change status/notes/feedback fields, append a follow-up
  entry, or link to the replacement. Preserve the original evidence and dates.
- For JSON records, load and write with structured parsers (`json.load` /
  `json.dump(..., indent=4)` in Python). Never hand-edit by string
  concatenation, ad hoc patches, or regex substitutions.
- Before any destructive or ambiguity-prone record operation, use
  AskUserQuestions: ask the user which record to change, what status to apply,
  and whether deletion/replacement is truly intended.
- Git attribution must stay policy-compliant: primary author may be one of the
  approved owner emails or an approved well-known AI author such as
  `Codex <codex@openai.com>`; `Co-authored-by` may include well-known public
  AI/helper domains and markers, but random/unattributable Gmail co-authors are
  blocked.
