---
name: clinepass-deepseek-flash
description: Run Cline CLI as a non-interactive fan-out worker using the authenticated ClinePass DeepSeek V4.1 Flash (1017) route with medium reasoning. Use when the user asks for free/low-cost ClinePass-only bot dispatch, Cline bot fan-out, headless Cline review, EXA plus Firecrawl verification for Cline usage, or a parallel Cline route that does not replace the existing GLM ClinePass skill.
version: 1.2.2
license: Apache 2.0
compatibility: cline, openclaw, macos
parent_skill: orama-system
origin: ClinePass DeepSeek fan-out skill, repointed 2026-11-03 to the successor
  model id; 1.2.x reconciles the schema with the installed CLI 3.0.74
  (binary location, provider id, `--thinking` levels, `-p` = `--plan`,
  auto-approve default, resume limits)
triggers:
  - clinepass deepseek fan-out
  - cline headless dispatch
  - cline bot fan-out
  - headless cline review
  - clinepass route
allowed-tools: bash, file-operations
---

# ClinePass DeepSeek Flash

Use this skill to dispatch Cline as a headless worker on the operator-approved
ClinePass DeepSeek V4.1 Flash (1017) route. This is a parallel route to the GLM
ClinePass skill, not a replacement.

## Purpose

Dispatch Cline as a headless worker on the operator-approved ClinePass
DeepSeek V4.1 Flash (1017) route for constrained, low-cost fan-out work:
review summaries, plan drafts, mechanical implementation passes, and
independent second opinions.

## When to Use

- Free/low-cost ClinePass-only bot dispatch is requested.
- A parallel reviewer or implementer is needed beside the main session.
- EXA plus Firecrawl verification of Cline usage claims is required.

## Disambiguation

This skill is for the Cline CLI (`cline`) as an agentic fan-out worker. It is
not an OpenClaw native model-provider binding, not the main agent, and not the
existing GLM ClinePass route.

Mirror the Kimi/Codex pattern:

- main session: owns architecture, security policy, repo history surgery, and
  final commits;
- ClinePass DeepSeek Flash: does constrained review, plan drafts, mechanical
  implementation passes, and independent second opinions;
- OpenClaw agent registry: unchanged unless the user explicitly asks for a
  named OpenClaw subagent binding.

If this route authors commits later, use a public bot identity approved by the
repository attribution policy before committing. Do not invent a private
operator identity.

## Contract

- Model: `cline-pass/deepseek-v4.1-flash-1017`
- Reasoning: `medium` by default, `high` for deep review.
- Flag: `--thinking <level>`. The installed CLI `3.0.74` documents
  `none|low|medium|high|xhigh`, and a bare `--thinking` means `medium`. It has
  no `--reasoning-effort` flag; the wrapper script adapts between the two
  names. Earlier versions of this card claimed the DeepSeek V4.1 Flash family
  had no `medium` — local help contradicts that, and local help wins for
  execution.
- Wrapper default: `scripts/run_clinepass_deepseek_flash.sh` still pins `high`
  for its own conservative default. Invoke the CLI directly (see § Binary
  Location) when the cheaper `medium` lane is wanted.
- History: repointed 2026-11-03 from the retired `cline-pass/deepseek-v4-flash`
  (Cline retired it alongside GLM-5.2, Kimi K2.6, and Kimi K2.7 Code).
- Access policy: ClinePass-only. Do not silently fall back to GLM, Pro, Kimi,
  OpenRouter, direct Cline API, or any provider key path.
- Auth: rely on the already-authenticated Cline CLI/ClinePass account. Do not
  request or print API keys.
- Provider: verify the active Cline task route is ClinePass before dispatch.
  Model slug pinning is not enough if the CLI is still routed through another
  provider.
- Privacy: do not pass secrets, private identity literals, LAN topology, device
  names, or workstation-specific paths into prompts or outputs.
- Workspace: default to `/private/tmp` for read-only or sensitive fan-out. Add
  repository access only when the task needs file reads or edits.

## Binary Location

`cline` is not on `PATH` for a default shell here: `~/.nvm/alias/default` is
`22.22.2`, and Cline is no longer installed in that Node tree. It lives under
the `v24.14.1` tree (a Node-version move, not a subfolder reclassification):

```text
$HOME/.nvm/versions/node/v24.14.1/bin/cline
  -> ../lib/node_modules/cline/bin/cline      (Cline CLI 3.0.74)
```

Resolve the binary instead of assuming `cline` resolves:

```bash
CLINE="$(command -v cline || echo "$HOME/.nvm/versions/node/v24.14.1/bin/cline")"
[ -x "$CLINE" ] && "$CLINE" --version   # expect 3.0.74
```

Two provider ids look alike in `~/.cline/data/settings/providers.json`:
`cline-pass` (live, model `cline-pass/deepseek-v4.1-flash-1017`) and
`clinepass` (stale, retired `cline-pass/deepseek-v4-flash`). Pin the provider
explicitly with `-P cline-pass`; a model slug alone does not prove the route.

`cline config` requires a TTY (`error: interactive mode requires a TTY`), so
read `providers.json` instead when running headless.

Verified headless dispatch (live-probed 2026-11-03 on CLI `3.0.74`, returned
the expected text): pass the prompt as a positional argument, and turn
auto-approval off because it defaults to **true**.

```bash
"$CLINE" -P cline-pass -m cline-pass/deepseek-v4.1-flash-1017 \
  --thinking medium --auto-approve false --json -t 120 \
  "Reply with exactly: PROBE-OK. Do not use tools."
```

`-p` is `--plan` (no mutations), not a "print" flag. Avoid `-y/--yolo`
unless the workspace is sandboxed.

Resuming with `--id <session-id>` is **not** headless-capable in `3.0.74`:

- `--id` + `--json` fails with `JSON output mode requires a prompt argument or
  piped stdin (interactive mode is unsupported)` even when a positional prompt
  or a redirected stdin is supplied.
- `--id` without `--json` fails with `interactive mode requires a TTY
  (stdin/stdout must both be terminals)`.

Drive `--id` resumes from a real terminal (or the TUI, `-i`); do not promise a
headless resume.

## Quick Start

Prefer the bundled compatibility wrapper:

```bash
bin/orama-system/skills/clinepass-deepseek-flash/scripts/run_clinepass_deepseek_flash.sh \
  --cwd /private/tmp \
  --timeout 180 \
  --plan \
  "Review this sanitized summary. Return risks, tests, and next steps."
```

The wrapper pins provider `cline-pass`, `cline-pass/deepseek-v4.1-flash-1017`,
`--thinking medium`, JSON output, and the current Cline auto-approval flag
shape. Every one of those is fail-closed: it inspects `cline --help` and refuses
to dispatch when the CLI cannot pin the provider, the reasoning level, or tool
approval, because an unpinned provider is how this route silently landed on a
provider that rejects the ClinePass slug.

## Verify Current CLI Shape

Start with local help because Cline CLI flags drift faster than docs:

```bash
cline --version
cline --help
cline auth --help
```

**Historical** — shape verified on Cline CLI `2.14.0`, an older version
than the one currently installed (see the v3.0.49 findings below). Kept
for reference only; do not use this shape against a current install.
Retirement note (2026-11-03): the model id shown in this block
(`cline-pass/deepseek-v4-flash`) has since been retired by Cline — the
live pin is `cline-pass/deepseek-v4.1-flash-1017`. Only the flag shape
below is historical reference material:

```bash
cline \
  --json \
  --auto-approve-all \
  --reasoning-effort high \
  -m cline-pass/deepseek-v4-flash \
  -c /private/tmp \
  -t 180 \
  "Reply with exactly: CLINE_DEEPSEEK_FLASH_READY"
```

If `cline --help` does not list `--auto-approve-all` (confirmed absent
in v3.0.49 — not verified against any other version; check `cline
--version` and `cline --help` directly before assuming this applies),
use the current documented equivalent instead:

```bash
cline \
  --json \
  --auto-approve true \
  --thinking high \
  -m cline-pass/deepseek-v4.1-flash-1017 \
  -c /private/tmp \
  -t 180 \
  "Reply with exactly: CLINE_DEEPSEEK_FLASH_READY"
```

Do not use both variants in the same command.

**Verified 2026-08-05 against installed CLI v3.0.49.** The "current
documented equivalent" block above is the correct one on this version
— confirmed live, along with two things worth knowing:

- There is no `task` subcommand. Earlier drafts of this skill and its
  bundled wrapper script invoked `cline task ...`; that fails with
  `error: Unknown command or unquoted prompt`. The prompt is a bare
  positional argument to `cline` itself — fixed in both this file and
  `scripts/run_clinepass_deepseek_flash.sh`.
- A single bare word as the entire prompt (e.g. `cline "PING"`) is
  rejected the same way — Cline treats an unrecognized single token as
  a possible mistyped subcommand, not a prompt. Multi-word prompts
  (e.g. `"Reply with exactly: PING_TEST"`) work fine; every smoke
  prompt in this skill already uses multiple words, so this doesn't
  affect the examples above, but matters if you improvise a shorter
  test prompt by hand.

With the CLI-shape bugs fixed, the wrapper script now reaches real
model dispatch. In the tested configuration (Cline CLI v3.0.49), this
currently fails with
`cline-pass/deepseek-v4.1-flash-1017 is not a valid model ID`
(`provider: openrouter`) — exactly the pre-existing "Observed failure
mode" documented below: ClinePass isn't authenticated as the active
route yet, so Cline falls back to another provider that doesn't
recognize the ClinePass model slug. That's the known auth/config gap,
not a new bug.

## Provider Auth Gate

Before real work, run a harmless smoke prompt. If the JSON output reports a
provider other than ClinePass or returns "not a valid model ID" for
`cline-pass/deepseek-v4.1-flash-1017`, stop and fix Cline auth/config first.

```bash
bin/orama-system/skills/clinepass-deepseek-flash/scripts/run_clinepass_deepseek_flash.sh \
  --cwd /private/tmp \
  --timeout 60 \
  --plan \
  "Reply with exactly: CLINE_DEEPSEEK_FLASH_READY"
```

Observed failure mode: Cline CLI `2.14.0` can accept the command shape while
still routing the request through a non-ClinePass provider, which rejects the
ClinePass model slug. That is an auth/config problem, not a reason to switch
models.

Configure auth explicitly through Cline's supported flow:

```bash
cline auth --help
cline auth --provider clinepass --apikey "$CLINE_API_KEY" --modelid cline-pass/deepseek-v4.1-flash-1017
```

Exact formats:

- Cline CLI provider id for this installed auth flow: `clinepass`
- ClinePass model id: `cline-pass/deepseek-v4.1-flash-1017`
- Direct DeepSeek provider ids are out of scope here: this skill only
  dispatches through the ClinePass route.
- Third-party wrapper formats may prefix again, for example
  `clinepass/cline-pass/deepseek-v4.1-flash-1017`; do not use that in native
  Cline CLI.

Use the API key from Cline's own dashboard/local secret surface. Keep it in an
environment variable or ignored local config; never paste it into prompts,
tracked files, command history that will be shared, or logs.

## First-Class Fan-Out Pattern

Same shape as Kimi and Codex fan-out:

```bash
bin/orama-system/skills/clinepass-deepseek-flash/scripts/run_clinepass_deepseek_flash.sh \
  --cwd /private/tmp \
  --timeout 300 \
  --plan \
  "Produce an independent read-only review of this sanitized PR summary."
```

For concurrent review, dispatch this route alongside Kimi and Codex, then let
the main session synthesize. Do not let parallel workers push, rewrite history,
or resolve policy disputes.

## Dispatch Patterns

Read-only review:

```bash
cline \
  --json \
  --auto-approve-all \
  --reasoning-effort high \
  -m cline-pass/deepseek-v4.1-flash-1017 \
  -c /private/tmp \
  -t 300 \
  "Review this sanitized summary. Do not access files. Return risks and tests."
```

Plan-first review:

```bash
cline \
  -p \
  --json \
  --auto-approve-all \
  --reasoning-effort high \
  -m cline-pass/deepseek-v4.1-flash-1017 \
  -c /private/tmp \
  -t 300 \
  "Create a concise implementation plan from this sanitized summary."
```

Repo-bound implementation, only on a clean branch:

```bash
git status --short --branch
cline \
  -a \
  --json \
  --auto-approve-all \
  --reasoning-effort high \
  -m cline-pass/deepseek-v4.1-flash-1017 \
  -c "$PWD" \
  -t 900 \
  "Implement the requested scoped change. Preserve unrelated local changes."
```

When the task is sensitive, prefer `/private/tmp` plus a sanitized prompt over
granting repository access.

## Output Handling

`--json` produces newline-delimited message objects. Parse defensively:

- keep `type == "say"` messages;
- ignore partial messages when a final answer exists;
- do not treat every JSON line as final output;
- strip or avoid logging prompts that may contain sensitive summaries.

If Cline exits non-zero, preserve the exit code and summarize the flag or auth
failure without dumping session state.

## EXA And Firecrawl Verification

Canonical procedure: [`../firecrawl/SKILL.md` § EXA-first, Firecrawl-second verification pattern](../firecrawl/SKILL.md#exa-first-firecrawl-second-verification-pattern).
This skill's own EXA query used
`official Cline CLI documentation non interactive task command model
reasoning effort ClinePass DeepSeek V4 Flash`, extracted from
`https://docs.cline.bot/usage/cli-overview`.

Source facts verified this way:

- Cline headless mode activates with `--json`, piped stdin, redirected stdout,
  and related automation flags.
- ClinePass listed DeepSeek V4 Flash as `cline-pass/deepseek-v4-flash`; that id
  is retired and the live route is `cline-pass/deepseek-v4.1-flash-1017`.
- ClinePass API examples use the full `cline-pass/...` model slug in the model
  field; the installed CLI auth error used provider id `clinepass`, while the
  current settings key is `cline-pass`.
- Local Cline `2.14.0` used `--auto-approve-all` and
  `--reasoning-effort high`. Local `3.0.74` uses `--auto-approve <boolean>`
  (default **true**), `--thinking none|low|medium|high|xhigh`, and `-p/--plan`;
  it has no `--reasoning-effort` flag. Official docs may still show the older
  pair.

When docs and local help disagree, prefer local help for execution and keep the
doc variant as a compatibility note.

## Monitoring

Check liveness without dumping prompts or logs:

```bash
pgrep -af 'cline|cline-pass|deepseek-v4.1-flash'
ps -p <pid> -o pid,ppid,stat,lstart,etime,command
```

For JSON output, parse only final non-partial `say` text. Do not assume every
line is a final answer.

## Boundaries

This route is a worker lane; the main session owns repository state.

### Always Do

- Pin `cline-pass/deepseek-v4.1-flash-1017` and verify the active task route
  is ClinePass before dispatch.
- Default the workspace to `/private/tmp` for read-only or sensitive fan-out.
- Rely on the already-authenticated Cline CLI/ClinePass account.

### Ask First

- Adding repository access beyond `/private/tmp`.
- Changing the provider, model id, or reasoning effort.
- Running any new auth flow or handling API keys.

### Never Do

- Do not replace the GLM ClinePass skill.
- Do not install new providers or call direct Cline API unless explicitly asked.
- Do not pass unredacted repository secrets, local-only config, or private
  literals to a cloud worker.
- Do not force-push, merge, or close PRs from this route. The main session owns
  repository state changes.
