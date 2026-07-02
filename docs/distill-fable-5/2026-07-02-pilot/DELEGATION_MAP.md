# Delegation Map — frontier-orchestrated AutoResearcher pair

Reusable routing recipe validated in the 2026-07-02 pilot. Local-first; escalate
only on 2x local failure or when the task class demands it.

| Task class | Route to | Effort | Rationale |
|---|---|---|---|
| High-level planning, delegation decisions, conflict resolution, final synthesis | Fable 5 (orchestrator only) | max | Only where frontier reasoning changes the outcome |
| Code review, env debugging, implementation, verification | Sonnet-5 subagents | medium | Cheaper; parallelizable; structured-output schemas |
| Cross-node coordination verdicts, ack/amend decisions | Win LM Studio 27B (`qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2`) | n/a | Zero frontier tokens; force `VERDICT: \| REASON: \| BLOCKERS:` reply format |
| Bounded coding, multi-iteration harness, benchmarks | Win 27B via Hermes/ClinePass | n/a | H6-proven: fewer iterations + faster wall-clock than Mac 9B |
| Triage, latency probes, quick replies | Mac Ollama `qwen3.5:9b-nvfp4` | n/a | Warm, local, lowest cost |
| Embeddings (gbrain / CRG) | Mac Ollama `bge-m3` | n/a | Unified 1024-dim vector space |
| Mechanical verification (pytest, diff, curl, grep) | Inline Bash in main loop | n/a | Cheaper than any model call |

## Escalation ladder

1. Inline tooling (Bash/pytest/diff) — always first for verifiable facts.
2. Local model (Ollama 9B → LM Studio 27B) for reasoning-light subtasks.
3. Sonnet-5-medium subagents (parallel) for analysis/implementation.
4. Fable 5 main loop inline — ONLY when subagents are limit-blocked and the task
   cannot wait; keep steps mechanical, reserve reasoning for synthesis.
5. Cloud APIs (OpenRouter/Codex/Gemini) — only after two local-tier failures.

## Failure handling (validated live)

- Subagent session-limit: degrade one rung down the ladder immediately; no retry storms.
- Peer unreachable 10x: solo mode + 15-min recheck (`lan_peer_session.py`) — confirmed working (103 fails logged, correctly demoted).
- Git push hang: background job with completion notification; never block the loop.
- Deliverables when peer portal is down: git commits as transport (assignment cards under `bin/orama-system/skills/hermes-harness/references/assignments/`).
