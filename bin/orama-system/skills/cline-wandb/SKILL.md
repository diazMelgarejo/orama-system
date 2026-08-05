---
name: cline-wandb
description: Run Cline CLI as a non-interactive fan-out worker using DeepSeek-V4-Flash via wanDB.ai (Weave/W&B inference), high reasoning. Use when the user asks for wanDB-routed Cline bot fan-out, headless Cline review via wanDB, EXA plus Firecrawl verification for Cline usage on this route, or a parallel Cline route that does not replace ClinePass DeepSeek Flash or the GLM ClinePass skill. Includes a mandatory harmonized TDD reference card extending docs/TDD.md, and a mandatory generalized self-review discipline.
---

# Cline wanDB (DeepSeek-V4-Flash)

Use this skill to dispatch Cline as a headless worker on the
wanDB.ai-routed DeepSeek-V4-Flash model. This is a parallel route to
ClinePass DeepSeek Flash and the GLM ClinePass skill, not a replacement
for either.

## Disambiguation

Same client binary (`cline`) as the other Cline agents in this
ecosystem, different provider underneath: this route goes through
wanDB.ai's OpenAI-compatible inference endpoint (with Weave tracing),
not ClinePass's account-based auth. Mirror the Kimi/Codex/ClinePass
pattern:

- main session: owns architecture, security policy, repo history
  surgery, and final commits;
- Cline wanDB: does constrained review, plan drafts, mechanical
  implementation passes, and independent second opinions;
- OpenClaw agent registry: unchanged unless the user explicitly asks
  for a named OpenClaw subagent binding.

If this route authors commits later, use a public bot identity
approved by the repository attribution policy before committing. Do
not invent a private operator identity.

## Contract

- Model: `deepseek-ai/DeepSeek-V4-Flash`
- Provider: wanDB.ai inference (`https://api.inference.wandb.ai/v1`),
  OpenAI-compatible
- Team/Project: `$DEEPSEEK_V4_FLASH_WANDB_PROJECT` (export via the canonical
  OpenClaw secrets layout; never hardcode a private entity/project literal
  in tracked files).
  **Do not send this as an `OpenAI-Project` header or SDK `project=`
  kwarg** — confirmed 2026-08-05 that doing so causes a `401
  invalid_api_key` on an otherwise-valid key. Kept only for the Python/
  `weave.init()` tracing path.
- Reasoning: high, set via `--thinking high` on the `cline` invocation
  (persisted as `reasoning.effort` in `providers.json`, not an
  `extra_body` field — `extra_body` is an OpenAI Python SDK-only
  construct, not a literal raw-HTTP JSON key)
- Access policy: wanDB-only for this route. Do not silently fall back
  to ClinePass, GLM, Pro, Kimi, OpenRouter, or any other provider key
  path.
- Auth: `DEEPSEEK_V4_FLASH_WANDB` environment variable. Do not request
  or print the key's value. Never pass the key on command arguments.
- Privacy: do not pass secrets, private identity literals, LAN
  topology, device names, or workstation-specific paths into prompts
  or outputs.
- Workspace: default to `$HOME/.gstack/cline-wandb` for read-only or
  sensitive fan-out. Use `$REPO_ROOT` (from `git rev-parse
  --show-toplevel`) only when the task needs repository reads or edits.

## Security gate (mandatory before cloud or repo work)

Before any cloud-bound request or repository-bound execution:

1. Run `security-reviewer` on the sanitized task scope and workspace
   choice. **Stop** if approval is missing or rejected.
2. Confirm prompts use only a sanitized summary or an explicitly
   allowlisted workspace — never raw secrets, untracked dotenv files, or
   unredacted repo paths.
3. Block external API calls, authentication changes, and filesystem
   mutations until approval and workspace validation succeed. Privacy
   bullets alone are not enforcement.

## Verified against installed CLI (2026-08-05)

Confirmed live against Cline CLI v3.0.49 (`cline --version`, `cline
--help`, `cline auth --help`). Three real flag-shape bugs found and
fixed below:

- `--reasoning-effort <level>` does not exist. The real flag is
  `--thinking <level>` (`none|low|medium|high|xhigh`).
- `-a` is not a valid shorthand for auto-approval. The real flag is
  `--auto-approve <boolean>`, which requires an explicit `true`/`false`.
- `cline auth --provider openai-compatible --baseurl ... --modelid ...`
  (no `--apikey`) only sets the base URL and model — it does **not**
  persist an API key. `cline auth` does support `-k/--apikey <key>` for
  that, but supplying it means the literal secret sits in `argv` (briefly
  visible via `ps`/shell history) — the exact thing this skill's own
  contract says never to do. Use
  [`../../scripts/cline-provider-profiles/switch-cline-provider.sh`](../../scripts/cline-provider-profiles/switch-cline-provider.sh)
  instead: it writes the resolved key straight into
  `~/.cline/data/settings/providers.json`, never through a command-line
  argument. Confirmed empirically: `cline auth --apikey <key>` and this
  script both write to the identical schema Cline's provider store
  expects (`settings.provider/apiKey/model/baseUrl/headers/timeout/reasoning`,
  where `reasoning` is `{"effort": "...", "budgetTokens": ...}`, not
  `{"enabled": bool}`).

## Live connectivity verified (2026-08-05)

Credentials were loaded through the canonical OpenClaw secrets layout
(`~/.openclaw/secrets/` plus exported `$DEEPSEEK_V4_FLASH_WANDB` /
`$DEEPSEEK_V4_FLASH_WANDB_PROJECT` env vars) used by every other
provider in this ecosystem. Three findings from actually exercising it,
confirmed identically across raw HTTP smoke tests, the official Python
`openai` SDK, and the Cline CLI itself:

1. **The `OpenAI-Project` header (curl) / `project=` kwarg (Python SDK)
   breaks auth outright** — `401 invalid_api_key` — on an otherwise
   valid key. Confirmed by omitting it entirely: `/v1/chat/completions`
   then returns a real completion. `/v1/models` (no project header at
   all) also succeeds with the same key, independently confirming this
   isn't a bad key, just a bad header. The `wandb-deepseek-v4-flash.json.tmpl`
   profile no longer sends this header; `DEEPSEEK_V4_FLASH_WANDB_PROJECT`
   is kept in `$DEEPSEEK_V4_FLASH_WANDB_PROJECT` only for the Python/
   `weave.init()` tracing path (unrelated to Cline's own request path),
   not required by `switch-cline-provider.sh`.

2. **Activating a profile in `providers.json` does not make Cline use
   it.** `lastUsedProvider` is bookkeeping, not a runtime default — the
   top-level `-P, --provider <id>` flag defaults to `cline` (its own
   hosted routing) regardless of what's configured under
   `openai-compatible`. Confirmed by running a bare `cline` invocation
   right after activating the wandb profile: it silently routed through
   `openrouter`/`z-ai/glm-5.2` instead. This is the exact "CLI accepts
   the shape but routes through the wrong provider" failure mode the
   sibling ClinePass skill already documented — now confirmed to apply
   here too. `-P openai-compatible` alone isn't enough either: it also
   picked up a stale cached model from whichever profile was active
   *before* (`google/gemini-3.1-pro-preview`, from a leftover session
   default), still pointed at the current baseUrl. Both `-P` and `-m`
   must be passed explicitly on every invocation.

3. **Still unresolved:** with provider and model both forced correctly
   (confirmed via `-v`'s `run_start` line reporting the right
   `providerId`/`modelId`), Cline's own full agentic dispatch fails
   with a bare `"Bad Request"` from wanDB.ai — no further detail
   surfaced by any CLI flag checked (`-v`, `--json`), and the session
   log only records the same generic error, not the wire-level
   response body. The raw API (curl and the Python SDK, both without
   the project header) return real completions for the identical
   model/key, so the credentials and endpoint are confirmed good — the
   failure is specific to something in Cline's own outgoing request
   shape (most likely its tool-calling schema, sent on every dispatch
   regardless of task content) that this wanDB.ai endpoint rejects.
   Needs either wanDB.ai-side error detail (their dashboard/support) or
   HTTP-level request tracing (a local proxy) to pin down further —
   out of scope for this pass.

## Quick Start (flags verified against v3.0.49; step 3 currently fails, see above)

```bash
export REPO_ROOT="$(git rev-parse --show-toplevel)"
export CLINE_WANDB_WORKSPACE="${HOME}/.gstack/cline-wandb"
mkdir -p "$CLINE_WANDB_WORKSPACE"

# Populate once via canonical secrets layout (see switch-cline-provider.sh):
#   ~/.openclaw/secrets/wandb-deepseek-v4-flash-api-key   (chmod 600)
# Only DEEPSEEK_V4_FLASH_WANDB is required here -- matches
# switch-cline-provider.sh's own REQUIRED_VARS, which deliberately
# doesn't include DEEPSEEK_V4_FLASH_WANDB_PROJECT (that var is only
# consumed by the separate Python/weave.init() tracing path documented
# in the Contract section above, not this provider-switch path).
if [ -z "${DEEPSEEK_V4_FLASH_WANDB:-}" ]; then
  echo "ERROR: DEEPSEEK_V4_FLASH_WANDB unset" >&2
  exit 1
fi

# Writes straight into providers.json — key never touches argv or a
# shell history file, unlike `cline auth --apikey`. $REPO_ROOT-based so
# this works regardless of the current working directory.
"$REPO_ROOT/bin/orama-system/scripts/cline-provider-profiles/switch-cline-provider.sh" wandb-deepseek-v4-flash
```

```bash
# -P and -m are both required explicitly — see finding 2 above.
cline --json --thinking high \
  -P openai-compatible -m deepseek-ai/DeepSeek-V4-Flash \
  -c "$CLINE_WANDB_WORKSPACE" \
  -t 180 \
  "Reply with exactly: CLINE_WANDB_READY"
```

Direct API smoke (confirmed working 2026-08-05 — no `OpenAI-Project`
header, see finding 1 above; `extra_body` is an OpenAI Python SDK-only
construct that merges into the top-level body, not a literal JSON key
to send over raw HTTP, so it's omitted here rather than sent wrong).
The bearer token is passed via `-K <(...)` (a curl config file through
process substitution), not `-H`, so it never appears in `ps`/argv or
shell history — verified directly: `ps aux` during an in-flight request
shows only the `/dev/fd/N` path, never the token value:

```bash
curl https://api.inference.wandb.ai/v1/chat/completions \
  -K <(printf 'header = "Authorization: Bearer %s"\n' "$DEEPSEEK_V4_FLASH_WANDB") \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-ai/DeepSeek-V4-Flash",
    "messages": [{"role": "user", "content": "ping"}]
  }'
```

## Provider Auth Gate

Before real work, run the smoke prompt above. If the JSON output
reports a provider other than wanDB.ai, or rejects the model id, stop
and fix Cline auth/config first — same failure mode as ClinePass: the
CLI can accept the command shape while still routing through the
wrong provider.

Use the key from `DEEPSEEK_V4_FLASH_WANDB`. Never paste it into
prompts, tracked files, shared command history, or logs.

## Dispatch Patterns

Set a conservative command allowlist for review/planning. Do **not**
pass `--auto-approve true` until explicit human confirmation for
implementation.

```bash
export CLINE_COMMAND_PERMISSIONS='read,search,web_fetch'
```

Read-only review (non-mutating):

```bash
cline --json --thinking high \
  -c "$CLINE_WANDB_WORKSPACE" \
  -t 300 \
  "Review this sanitized summary. Do not access files. Return risks and tests."
```

Plan-first review (non-mutating):

```bash
cline -p --json --thinking high \
  -c "$CLINE_WANDB_WORKSPACE" \
  -t 300 \
  "Create a concise implementation plan from this sanitized summary."
```

## Implementation preflight (mandatory)

Repo-bound work requires **all** gates before dispatch:

1. `git status --short --branch` — clean or explicitly scoped dirty
   files only
2. `planner` — approved plan artifact
3. `tdd-guide` — test-first contract for the change
4. `code-reviewer` — delta review on the plan
5. `security-reviewer` — approval for cloud/repo-bound execution

Do not start implementation dispatch until applicable gates complete.

Repo-bound implementation, only after preflight and **explicit human
confirmation** to enable tool approval:

```bash
export CLINE_COMMAND_PERMISSIONS='read,write,search,execute'
cline --auto-approve true --json --thinking high \
  -m deepseek-ai/DeepSeek-V4-Flash \
  -c "$REPO_ROOT" \
  -t 900 \
  "Implement the requested scoped change. Preserve unrelated local changes."
```

When the task is sensitive, prefer `$CLINE_WANDB_WORKSPACE` plus a
sanitized prompt over granting repository access.

## Mandatory: TDD for every spawned agent

**Every agent this skill spawns MUST follow
[`references/tdd-reference-card.md`](references/tdd-reference-card.md)
for any task that writes or modifies code.** This is not optional
guidance the worker can skip under time pressure — write the failing
test first, watch it fail for the right reason, write minimal code,
watch it pass, refactor only with tests green. A worker that produces
code without following this card has not completed the task correctly,
regardless of whether the code looks right.

## Mandatory: generalized self-review before reporting done

Every dispatch under this skill — not just code changes, any
non-trivial output — reviews its own work before returning control,
using the **same thinking process** the
[`code-review` skill](../code-review/SKILL.md) applies to PRs, adapted
to whatever the task actually is rather than requiring PR-specific
tooling:

1. **Context before output** — the code-review skill builds a
   dependency/blast-radius graph before reading code
   ([`code-review` § Phase A](../code-review/SKILL.md#phase-a--graph-code-review-graph-mcp)).
   This skill's workers don't have `gbrain` or `code-review-graph`
   available, so the equivalent step is: before producing a final
   answer, re-read what the task actually asked for and what's
   actually been produced, side by side — not from memory of what you
   intended, from the literal request and the literal output.
2. **Review the delta, not just the destination** — the code-review
   skill has a dedicated delta-review phase
   ([`code-review` § Phase D](../code-review/SKILL.md#phase-d--review)).
   For this skill's workers: re-read your own draft/diff/answer once,
   specifically looking for the same class of thing a reviewer would
   flag — unverified claims, unstated assumptions, edge cases the
   request implied but the output doesn't cover.
3. **Structured report, not just an answer** — the code-review skill
   ends with an explicit report phase
   ([`code-review` § Phase E](../code-review/SKILL.md#phase-e--report)).
   This skill's workers close out with a short, explicit summary of
   what was actually verified (tests run and their result, sources
   checked, assumptions made) — not a bare answer with no trace of how
   it was checked.
4. **Red flags stop the worker, not just slow it down** — the
   code-review skill has explicit skill-violation red flags
   ([`code-review` § Red flags](../code-review/SKILL.md#red-flags-skill-violation)).
   The generalized equivalent here: if a worker notices it's about to
   report something as done without having actually run/verified it,
   that's the same category of violation — stop and verify, don't
   report first and caveat later.
5. **Use orama-system's own methodology for internal state, not just
   the deliverable** — apply the 5-stage
   [orama-system methodology](../../SKILL.md) (Context Immersion →
   Visionary Architecture → Ruthless Refinement → Masterful Execution →
   Crystallize) to the worker's own reasoning process for
   non-trivial tasks, the same way the main session does, not just to
   the code it produces. A worker that jumps straight to output without
   this internal structure is skipping the same discipline the main
   session is held to.

**Crystallize gate:** do not enter the final Crystallize stage without
an **approved verifier result**. If verification is missing, failed,
or blocked, stop and record the blocker — do not crystallize output.
Workers must record verifier approval (PASS + evidence pointer) before
reporting Crystallize complete.

This applies regardless of task type — a plan draft, a review, a
mechanical implementation pass, or "other agentic tasks" more broadly.
The tools differ from `code-review`'s (no graph MCP, no gbrain); the
underlying discipline — gather real context, review your own delta
before calling it done, report what was actually verified, treat a
premature "done" as a stop condition — does not.

## Output Handling

`--json` produces newline-delimited message objects. Parse
defensively: keep `type == "say"` messages, ignore partials when a
final answer exists, don't treat every line as final output, don't log
prompts that may contain sensitive summaries.

## Monitoring

Check liveness without dumping prompts, credentials, or full argv:

```bash
pgrep -f 'hermes_harness.py|cline-wandb' || true
ps -p <pid> -o pid,ppid,stat,lstart,etime
```

Do not use `pgrep -af` or `ps ... command` when the listing may expose
task prompts or secrets.

## Boundaries

- Do not replace ClinePass DeepSeek Flash or the GLM ClinePass skill.
- Do not install new providers or call wanDB.ai's API directly
  (bypassing the `cline` CLI) unless explicitly asked.
- Do not pass unredacted repository secrets, local-only config, or
  private literals to a cloud worker.
- Do not force-push, merge, or close PRs from this route. The main
  session owns repository state changes.
- Do not report a task complete without having followed the
  self-review discipline above — a fast answer that skipped review is
  not a complete answer.

## References

- [`references/tdd-reference-card.md`](references/tdd-reference-card.md)
  — harmonized TDD reference card (extends
  [`docs/TDD.md`](https://github.com/diazMelgarejo/orama-system/blob/main/docs/TDD.md);
  mandatory for any code-writing dispatch under this skill).
- Sibling route:
  [`../clinepass-deepseek-flash/SKILL.md`](../clinepass-deepseek-flash/SKILL.md)
- Self-review pattern source:
  [`../code-review/SKILL.md`](../code-review/SKILL.md)
