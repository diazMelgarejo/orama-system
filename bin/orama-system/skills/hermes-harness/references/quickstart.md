# Hermes Quickstart

Time-to-first-hermes-working (TTHW), start to finish. If any step's output
doesn't match what's shown here, stop and read
[`workspace-path-resolution.md`](workspace-path-resolution.md) before
continuing — don't guess past a mismatch.

## 1. Clone Perpetua-Tools

```bash
git clone https://github.com/diazMelgarejo/Perpetua-Tools.git
```

Anywhere on disk is fine — resolution below finds it by marker file and
trusted remote, not by a fixed path.

## 2. Set one environment variable

```bash
export PERPETUA_TOOLS_ROOT="$(pwd)/Perpetua-Tools"
```

This is the fastest of the four accepted override variables
(`PERPETUA_TOOLS_PATH`, `PT_HOME`, `PERPETUA_TOOLS_ROOT`,
`PERPETUATOOLSROOT` — first one set wins, in that order). Without it, the
resolver still works via a marker-based crawl from your current git repo's
parent directory and `$HOME`, but setting the env var skips discovery and
fails fast with a clear error if the path is wrong.

## 3. First `hermes-spawn status`

From inside the `orama-system` checkout:

```bash
bash bin/orama-system/skills/hermes-harness/scripts/hermes_spawn.sh status
```

Expected output on a fresh machine (nothing has been started yet):

```text
ℹ️ No active Hermes session default (no pid file)
```

Exit code `1` — this is expected, not a failure. "No session running" is a
normal status, not an error state.

## 4. First `hermes-spawn start`

```bash
bash bin/orama-system/skills/hermes-harness/scripts/hermes_spawn.sh start "say hello"
```

Expected output:

```text
🚀 Spawning Hermes agent for: say hello
✅ Hermes started (pid <N>, session default)
```

`<N>` is the actual spawned process's PID — it will differ every run, that
part of the output is not fixed text to match literally.

## 5. Confirm it's actually running

```bash
bash bin/orama-system/skills/hermes-harness/scripts/hermes_spawn.sh status
```

Expected output:

```text
✅ Hermes running (pid <N>, session default)
```

The same PID from step 4. Exit code `0` this time.

## If step 3 or 4 fails instead with `Perpetua-Tools root not resolved`

The clone in step 1 isn't being found. Most common causes, in order of
likelihood:

1. The env var from step 2 wasn't actually exported in this shell (`echo
   "$PERPETUA_TOOLS_ROOT"` to check).
2. The path doesn't contain `orchestrator/fastapi_app.py` — you cloned the
   wrong repo, or the clone is incomplete/shallow in a way that dropped that
   file.
3. The clone's `origin` remote doesn't match the trusted Perpetua-Tools URL
   pattern (`github.com/diazMelgarejo/Perpetua-Tools`, https or ssh) — a
   fork or a mirror under a different org will resolve to "not found" by
   design, not silently accepted. See
   [`resolve_perp_harness.sh`](../scripts/resolve_perp_harness.sh)'s
   `_pt_remote_trusted` for the exact check.

Full resolution algorithm (env override → `.paths` cache → crawl → remote
trust check): [`workspace-path-resolution.md`](workspace-path-resolution.md).

## See Also

- [`../hermes-spawn/SKILL.md`](../hermes-spawn/SKILL.md) — the skill card this
  script backs (`start|stop|status`)
- [`workspace-path-resolution.md`](workspace-path-resolution.md) — full PT-root
  resolution algorithm
- [`hermes-dispatch-taxonomy.md`](hermes-dispatch-taxonomy.md) — where
  `hermes-spawn` (lane L-PT) fits among the other dispatch lanes
