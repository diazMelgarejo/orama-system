# Stale-reference ledger (2026-11-12)

Purpose: one place that says which model ids, limits and routes in older records are **superseded**,
and what is current. Dated records were marked HISTORICAL, NOT LIVE instead of being rewritten
(rewriting would falsify what was true on the day). Evidence:
`references/2026-11-12-live-probe-results-wandb-bigmodel-cline.md` in the operator workspace (live
provider checks, translated BigModel official docs, DeepSeek official change log).

## Current facts (2026-11-12)

| Topic | Stale text you may find | Current |
| --- | --- | --- |
| W&B DeepSeek id | `deepseek-ai/DeepSeek-V4-Flash` (HTTP 404 on W&B) | order `deepseek-ai/DeepSeek-V4.1-Flash-1017` -> `deepseek-ai/DeepSeek-V4.1-Flash` -> `deepseek-ai/DeepSeek-V4-Flash-0731`; the `deepseek-flash` alias is not served by W&B (404) |
| Reasoning effort | `high` only, `{"enabled": true}` only, or an omitted effort | explicit effort, order `medium`, `high`, `low`; never `xhigh` or `max`. W&B V4.1 models reject `medium` (HTTP 400) so they run at `high`; BigModel `glm-5.3-flash` accepts only `low`/`high`/`max` and defaults to `max` when omitted |
| BigModel `glm-5.3-flash` limits | context 131072, max 65536 | context 1M; default output 65536; maximum output 131072 (official) |
| BigModel profile name | `bigmodel-glm52` | `bigmodel-glm53-flash` (old name still accepted as an alias) |
| OpenRouter DeepSeek flash | `openrouter/deepseek/deepseek-v4-flash:free` | not in OpenRouter's live list; paid ids `deepseek/deepseek-v4.1-flash-1017`, `deepseek/deepseek-v4.1-flash`, `deepseek/deepseek-v4-flash-0731`; alias `~deepseek/deepseek-flash-latest` |
| Other OpenRouter free ids | `nvidia/nemotron-3-super-120b-a12b:free`, `minimax/minimax-m2.5:free`, `openai/gpt-oss-120b:free`, `z-ai/glm-4.5-air:free`, `inclusionai/ling-2.6-flash:free` | also absent from the live list on 2026-11-12; **open operator decision** on replacements; `openrouter/free` is live |
| DeepSeek `1017` | "V4-Flash" / "V4.1-Flash" without a build | `V4.1-Flash-1017` is the 2026-10-17 upgrade; DeepSeek's own `deepseek-flash` alias serves it |

## Classified HISTORICAL, NOT LIVE (files left unedited)

These dated records name superseded ids or limits. They were not edited: they carry older
markdown-lint debt, and rewriting history would falsify what was true on the day. Treat every
id, limit and route in them as historical and copy nothing from them into live config.

- `.superpowers/sdd/task-3-report.md`
- `docs/archive/fleet-mesh/2026-07-10-pr2-phase0-review-crossreference.md`
- `docs/distill-fable-5/2026-07-02-pilot/MODELS_PERFORMANCE_DELTA.md`
- `docs/next/fleet-mesh/2026-07-10-oasn-p2p-architecture-research.md`
- `docs/next/fleet-mesh/2026-07-19-oob-completion-findings.md`
- `docs/plans/2026-06-27-security-hardening-pre-v2.md`
- `docs/plans/2026-07-04-whatsapp-qr-gateway-implementation-plan.md`
- `docs/plans/2026-07-05-start-ps1-review.md`
- `docs/plans/2026-07-22-cross-repo-out-of-scope-closure.md`
- `docs/security/glm52-clean-replay-record.md`
- `docs/superpowers/plans/2026-07-04-fable5-llm-council-implementation.md`
- `docs/superpowers/plans/2026-07-14-g7-authenticated-sse-mvp.md`
- `docs/superpowers/plans/2026-08-14-gemini-skill-consolidation-staged.md`
- `docs/superpowers/plans/2026-08-14-gemini-skill-consolidation.md`

## Listed here only (not edited)

- `docs/LESSONS.md` (append-only chronological log), `.agent/memory/working/**` (working memory;
  edit only through its own tooling),
  `docs/reference/2026-07-22-branch-cleanup-verified-superseded.sh` (script record).

## Legacy identifiers kept on purpose (load-bearing, do not rename)

`GLM52_API_KEY`, `GLM52_ENDPOINT`, `~/.openclaw/.env.glm52`, `setup-glm52.sh`, the `glm52-fallback/`
directory and skill name. The model they serve is `glm-5.3-flash`.

## Still open

- BigModel was not callable (account balance), so its live completions were never observed; facts
  there are official-docs-only.
- `config/mac-orchestrator.json` lists `glm-5.3-flash` with zero cost; BigModel's price list says
  0.8 in / 2.8 out CNY per 1M tokens with a "free for a limited time" column that was not
  interpreted.
- Replacement choices for the five absent OpenRouter free ids.
