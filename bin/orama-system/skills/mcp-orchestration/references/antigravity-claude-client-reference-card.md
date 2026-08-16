# Agnes: Antigravity Claude Client

> **Use when:** dispatching the Antigravity CLI (`agy`) as a cooperating
> worker under the shared coordination board.
>
> **Canonical boundary:** Agnes is a board-registered direct CLI client. She
> is not an OpenClaw provider, a gateway-backed SOUL agent, or an additional
> Orama stage in `config/agent_registry.json`.

## Identity

| Field | Value |
| --- | --- |
| Display name | Agnes |
| Board agent ID | `agnes-antigravity-claude` |
| Agent type | `antigravity-client` |
| Client | `agy` (Antigravity CLI) |
| Model | `claude-sonnet-4-6` / the locally reported Claude Sonnet 4.6 option |
| Execution tier | Direct CLI fan-out worker |
| Registry boundary | Shared coordination board only; never the seven-stage runtime registry |

The capability contract is deliberately scoped, not an assertion of unlimited
authority. Agnes may perform the same review, analysis, coding, and test-support
work as an approved CLI worker when the current invocation grants those tools,
workspace paths, and model access. The primary agent retains architecture,
security, merge, commit, and push decisions.

## Registration

Register or refresh the board identity with the repository's coordination CLI:

```bash
python3 scripts/agent_coordination.py register \
  agnes-antigravity-claude antigravity-client claude-sonnet-4-6 \
  'Agnes: AntiGravity Client via agy; direct CLI fan-out worker'
```

Registration is runtime coordination state. Do not add Agnes to
`bin/orama-system/config/agent_registry.json`; that file is reserved for the
Orama seven-stage pipeline and its schema/tests intentionally count those
stages.

## Fresh-worktree dispatch

Every job starts from the exact reviewed source branch in a disposable
worktree. Record the source SHA in the board claim before dispatching. Never
point Agnes at a dirty or ambiguously based checkout.

Start with a read-only plan pass:

```bash
AGY_BIN="$(command -v agy)" || {
  echo 'agy not found on PATH' >&2
  exit 127
}

"$AGY_BIN" --mode plan --sandbox --add-dir "$WORKTREE" \
  --model 'Claude Sonnet 4.6 (Thinking)' \
  -p 'Plan the claimed task only. Do not edit, commit, or push. Return risks,
tests, and the smallest file set.'
```

Only after human approval of the plan may a worker receive edit permissions.
Use `--add-dir` for the selected worktree only. Never pass a broad home
directory, secrets directory, or unrelated checkout.

## Worker contract

1. Claim one board task with the exact branch, worktree, and source SHA.
2. Inspect the canonical plan and local repository rules before editing.
3. Keep edits inside the claimed worktree and avoid commits unless explicitly
   assigned that responsibility.
4. Preserve stdout and stderr separately for every background invocation.
5. Treat exit 0 with empty output, an auth error, or an interrupted response as
   an incomplete worker result; do not report success from process exit alone.
6. Return changed paths, tests run, unresolved risks, and the resulting commit
   SHA only when a commit was explicitly authorized.
7. Release or update the board claim with the result and pulse liveness while
   the work is active.

## Model and authentication guard

The model name must come from the current `agy models` output. Do not invent a
provider alias or silently fall back to Gemini. If Claude Sonnet 4.6 is absent,
or AGY is not authenticated, stop and report the exact failure; do not claim
that Agnes completed the task.

This card records a real dogfood limitation: a sandboxed plan invocation may
return only initial research narration or may stop at authentication. That is
an incomplete review, not a PASS. Preserve the output for diagnosis and rerun
only after the operator repairs authentication or grants the required scope.

## Completion checks

Before handoff, the primary agent verifies:

- the worktree still has the intended base and no unrelated changes;
- all claimed paths are in the diff and no unclaimed paths were touched;
- focused tests and `git diff --check` pass;
- the board contains the result and current liveness;
- no secrets, host-specific topology, or fabricated provider configuration was
  added to tracked files.

Related guidance: [`antigravity-agent/SKILL.md`](../../antigravity-agent/SKILL.md),
[`gemini-and-ai-cli-mcp-setup.md`](gemini-and-ai-cli-mcp-setup.md), and the
shared [multi-agent collaboration protocol](../../references/multi-agent-collaboration-protocol.md).
