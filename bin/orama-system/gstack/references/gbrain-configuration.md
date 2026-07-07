## GBrain Configuration

Engine: **postgres** (Supabase pooler). Config: `~/.gbrain/config.json`.
DB URL lives in `~/.gbrain/.env` as `GBRAIN_DATABASE_URL` — sourced by `~/.zshrc`
and the MCP wrapper, NOT by non-interactive Bash shells.

> **Source IDs migrated 2026-06-17 (old → new).** After the 2026-06-14 security re-anchor,
> gbrain's `deriveCodeSourceId` moved from the legacy scheme (`orama-src`,
> `gstack-code-ools-…`, `gstack-code-claw-…`) to current per-worktree `gstack-code-<hash>` IDs,
> and all three active repos were reindexed against current HEAD. **`.gbrain-source` pins already
> point at the CURRENT IDs** — query those. The old sources are stale (@2026-06-05), superseded,
> and archived as of 2026-06-22. Definitions were exported to both
> `~/repo-backups/gbrain-stale-quarantine-20260618/` and
> `…-20260622/orphan-sources.json`.
>
> `periscope-src` is also archived because the repo is dormant and its path moved to
> `~/code/oramasys/tools/periscope`. Re-add that path only if periscope work resumes.
>
> **Lesson (do NOT leave "pending removal"):** these sat un-removed from 2026-06-18→06-22 and
> kept resurfacing as `sync_freshness`/`multi_source_drift` warnings every session. Complete the
> lifecycle change in the same pass you decide it — a deferred cleanup is a recurring false alarm.
> The idempotent guard `scripts/gbrain/gbrain-selfheal.sh` surfaces orphan sources automatically.

| Repo | Current active source ID (reindexed 2026-06-17) | Pages | Federated | Superseded ID (@06-05, quarantined) |
| ------ | ------ | ------- | ----------- | ------ |
| AlphaClaw | `gstack-code-alphaclaw-875d5b82` | ~476 | yes | `gstack-code-claw-4dc4a8f3-aa4479` (489p) |
| Perpetua-Tools | `gstack-code-078b0b90-f6179f` | ~736 | yes | `gstack-code-ools-27e2b79c-df8a28` (721p) |
| orama-system | `gstack-code-2159b4b9-595bce` | ~223 | yes (was isolated) | `orama-src` (306p) |

Archived dormant sources:

| Repo | Archived source ID | Pages | Federated | Lifecycle note |
| ------ | ------ | ------- | ----------- | ------ |
| periscope | `periscope-src` | ~14 | yes | archived 2026-06-22; re-add only if periscope work resumes |

Re-run setup: `/setup-gbrain`
