## GBrain Configuration

Engine: **postgres** (Supabase pooler). Config: `~/.gbrain/config.json`.
DB URL lives in `~/.gbrain/.env` as `GBRAIN_DATABASE_URL` — sourced by `~/.zshrc`
and the MCP wrapper, NOT by non-interactive Bash shells.

> **Source IDs migrated 2026-06-17 (old → new).** After the 2026-06-14 security re-anchor,
> gbrain's `deriveCodeSourceId` moved from the legacy scheme (`orama-src`,
> `gstack-code-ools-…`, `gstack-code-claw-…`) to current per-worktree `gstack-code-<hash>` IDs,
> and all three repos were reindexed against current HEAD. **`.gbrain-source` pins already point
> at the CURRENT IDs** — query those. The old sources are stale (@2026-06-05), superseded, and
> **ARCHIVED 2026-06-22** via `gbrain sources archive` (soft-delete, reversible with
> `gbrain sources restore <id>`). Defs exported to BOTH
> `~/repo-backups/gbrain-stale-quarantine-20260618/` and `…-20260622/orphan-sources.json`
> (and code preserved in git). `periscope-src` was also archived — its path moved to
> `~/code/oramasys/tools/periscope`; re-add with
> `gbrain sources add --path ~/code/oramasys/tools/periscope` if periscope work resumes.
>
> **Lesson (do NOT leave "pending removal"):** these sat un-removed from 2026-06-18→06-22 and
> kept resurfacing as `sync_freshness`/`multi_source_drift` warnings every session. **Complete
> the archive in the same pass you decide it** — a deferred removal is a recurring false alarm.
> Note: archive is reversible but `gbrain doctor` still lists archived sources in freshness
> (noise, not breakage); `gbrain sources purge <id> --confirm-destructive` removes them fully
> (recoverable via the exported manifest above). The idempotent guard
> `scripts/gbrain/gbrain-selfheal.sh` surfaces orphan sources automatically.

| Repo | Current source ID (reindexed 2026-06-17) | Pages | Federated | Superseded ID (@06-05, quarantined) |
| ------ | ------ | ------- | ----------- | ------ |
| AlphaClaw | `gstack-code-alphaclaw-875d5b82` | ~476 | yes | `gstack-code-claw-4dc4a8f3-aa4479` (489p) |
| Perpetua-Tools | `gstack-code-078b0b90-f6179f` | ~736 | yes | `gstack-code-ools-27e2b79c-df8a28` (721p) |
| orama-system | `gstack-code-2159b4b9-595bce` | ~223 | yes (was isolated) | `orama-src` (306p) |
| periscope | `periscope-src` | ~14 | yes | — current (separate dormant repo, last commit 2026-04-19) |

Re-run setup: `/setup-gbrain`