# OpenClaw fresh install, staged restore and backup recovery

Status: dated operator baseline, 2026-11-26. It supersedes itself at the next upgrade.
Perpetua-Tools owns the commands (`scripts/install-openclaw-runtime.sh`,
`perpetua_tools.openclaw_runtime`); this card is the first-run reference that explains the order,
the rulings and the way back.

Portable-memory rule: tracked files name categories, never concrete local paths, addresses,
accounts, phone numbers or key values. Keep those in a private folder outside every repository.

## Preconditions

1. Free disk: keep at least 10 GiB free on the data volume before any plugin stage. A full disk made
   the codex plugin fail to load, slowed the gateway start and produced slow-database warnings.
2. One nvm node 24.x (`>=24.22.1 <25`), a stable node link, and a global openclaw equal to the
   AlphaClaw pin. `install-openclaw-runtime.sh --check` must pass.
3. An operator present for logins and for every credential decision. Agents configure routing only.

## Fresh install procedure

1. Back up first (see Backup and recovery): archives of the old state, the service definition and
   the AlphaClaw config, with a checksum list, owner-only permissions and no synced folder.
2. Runtime: `install-openclaw-runtime.sh --apply` (node, global openclaw, stable link).
3. AlphaClaw: build the fork tarball (`pnpm install --frozen-lockfile`, then `npm pack`) and install
   it into the AlphaClaw folder, then confirm global and AlphaClaw openclaw versions are equal.
4. Cut over: `--fresh-gateway --accept-risk` renames the state folder aside and onboards fresh on
   the loopback interface with token auth, no providers, channels, skills, search or hooks.
5. Confirm the service runs and the connectivity check is ok before restoring anything.
6. Restore in stages (next section). One change at a time.
7. Operator steps: provider logins, plugin installs, channel pairing.

## Staged restore order

Every stage uses the same loop: copy the config to a stage-named backup, dry-run the change
(`openclaw config patch --dry-run`), apply it, wait until the gateway reports connectivity ok (a
restart takes minutes when many agents are configured), then run one tiny live turn per affected
agent.

| Stage | What | Notes |
| --- | --- | --- |
| 1 | Core settings (session scope, update policy) | Stable channel, check only; no auto-update |
| 2 | Agent definitions, then delegation rules | Name, thinking, tools, workspace; no models yet |
| 3 | Environment mechanism | Shell import plus the global env file (see Credential handling) |
| 4 | Providers, default model chain, seats | Dated rulings below |
| 5 | Codex plugin and OpenAI runtime policy | Enable the plugin explicitly; set the codex runtime |
| 6 | Web search wiring, then plugins one at a time | Brave, Exa, Firecrawl; then the rest |
| 7 | Skills, MCP servers, cron jobs, exec approvals | Review each old item; restore by choice |
| 8 | Channels last | Owner allow-list only after the operator confirms |

Dated rulings (2026-11-26):

- Default model: W&B DeepSeek V4.1 Flash at high effort. Fallbacks in order: Google Gemini Flash
  (medium), local Ollama, OpenRouter free. Mac LM Studio is manual only and in no chain. Windows LM
  Studio comes from the discovery file only, never a hard-coded address.
- W&B is never removed from any agent chain, even when pushed lower.
- Seats `biafra` (alias MetaResearcher, guardian and companion of `autoresearcher`) and
  `autoresearcher` default to `openai/gpt-6.1-terra` at medium effort, then the default chain. Astra
  and Sol are human-gated: explicit operator approval, never spawned by default, never automatic.
- OpenAI login is per agent for those two seats only, never the gateway or `main`:
  `openclaw models auth login --provider openai --agent <id>` (add `--device-code` if needed).
- The seats deny `exec`, `process`, `browser`, `canvas`, `nodes`, `cron` and `gateway`. Verify with
  a live turn, because the codex native surface is separate from the deny list.
- Sandboxing the seats is staged: tool policy now; a dedicated user plus a Seatbelt profile only
  when a seat must run code, after review and a throwaway-agent test. Docker is not required.

## Credential handling

- Never print, copy or move key values. Test a key by its provider status code. Compare two copies
  by length and hash only (`masked-env-diff.py` style tools).
- The gateway shell import brings in only well-known provider keys. A custom key (for example the
  W&B key) must be in the global env file under the state folder, mode 600, and needs a gateway
  restart.
- Keep one source of truth for all working keys, alias other names to it by reference, and quote any
  value that may contain a dollar sign (an unquoted value is expanded and arrives empty).
- A restored old env file can shadow a working key because the shell sources it later: test every
  restored key, strip dead lines (keep the originals), and re-verify in a fresh shell.
- The gateway can see keys the operator ruled out (for example an API key for a login-only
  provider). Keep every agent on an explicit model so none resolves to it by default.

## Backup and recovery

Before the cutover:

1. Archive the old state, the AlphaClaw config (full and slim), the service definition and the
   global packages. Record checksums. Folder mode 700, files mode 600. Keep it out of synced folders
   and exclude it from machine backups if the operator wants the secrets gone for good.
2. Keep the old state folder renamed aside, untouched, until the restore has been healthy a while.
3. Keep one config copy per stage, named by stage, mode 600.

Rolling back a stage: copy that stage's config backup over the live config, then restart and wait
for connectivity ok.

Rolling back the whole cutover:

```bash
launchctl bootout gui/$(id -u)/ai.openclaw.gateway       # stop the new gateway
mv ~/.openclaw ~/.openclaw.fresh-failed                   # keep the failed state, do not delete
mv ~/.openclaw.pre-clean ~/.openclaw                      # put the old state back
# restore the saved service definition into ~/Library/LaunchAgents, then bootstrap it
```

Caveat: if the old state crash-looped (conflicting plugin metadata), a rollback restores your data,
not a working gateway. `bootout` is asynchronous: wait for the port to close before bootstrapping.

Cleanup after a healthy restore: move the aside folders and archives to the Trash and let the
operator empty it. Never a recursive force remove.

Retiring an obsolete node version: first repoint every reference to the stable link, then stop the
processes still running from it, then move the folder to the Trash. Places to check: the shell
profile, launch agents, tool links in the user bin folders and the system package links, MCP server
settings, wrapper scripts and running processes. Launch agents and scripts that live inside the old
state folder are stranded by the cutover; restore those non-secret wrapper scripts.

## Verification after each stage

1. `openclaw gateway status`: running, connectivity ok. `openclaw config validate`.
2. A tiny live turn per affected agent; check provider, model and harness in the result.
3. `openclaw models status --agent <id>`; the key audit by status code; the drift check.
4. Free disk still above the floor.

## Open items

Discovery file not yet written after the cutover; service PATH names a node version; the Seatbelt
profile is a draft; per-call approval for web-search tools is unverified; the order of the remaining
stages above is the pick-up list.
