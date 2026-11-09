# Google Gemini Routing

Operator decisions recorded on 2026-11-08 govern active configuration only.
Historical chronicles, immutable memory and deprecated-ID rejection fixtures
are preserved. This policy neither activates serving nor approves a launch.

## Roles

| Role | Exact identifier | Boundary |
| --- | --- | --- |
| AntiGravity default | `gemini-3.8-flash-medium` | Verify with `agy models` |
| General direct-API default | `gemini-3.8-flash` | Explicit medium effort |
| Economical subagents | `gemini-3.5-flash-lite` | Parallel to economical Claude roles |
| Automatic Google fallback | `gemini-flash-latest` | Direct Google only |
| Pro capability | `gemini-pro-latest` | Direct Google; verified human escalation |
| Frontier capability | `google/gemini-4-argon` | OpenRouter; human escalation and budget |

Pro remains gated even when the task is labelled planning. Config flags,
catalog entries and agent-writable approval fields are not authorization.
Existing non-Google provider planning rules are unchanged.

PT owns runtime enforcement through `model_governance` and `DispatchGuard`.
Budget-required launches need the existing structured `EscalationProof` from
a trusted verifier, bound to model, effort, fast flag, path and exact scope.
A Boolean callback remains compatible for other approved launches, but cannot
attest a required budget. This metadata boundary does not create signatures
or replace the trusted verifier's authenticity and downstream budget checks.

## Namespaces And Protocols

The sample preserves the custom providers `gemini-main` and `gemini-fallback`.
Both use `google-generative-ai` and the direct Google API base. Their model
catalog IDs are bare wire names, without `google/` or synthetic `-FALL` suffixes.
OpenClaw references therefore use `gemini-main/gemini-3.8-flash` and
`gemini-fallback/gemini-flash-latest`.

OpenRouter wire IDs remain provider-qualified, for example
`google/gemini-3.8-flash`, `google/gemini-3.5-flash-lite` and
`google/gemini-4-argon`. An OpenClaw reference to the latter is
`openrouter/google/gemini-4-argon`. It requires separately provisioned
OpenRouter access and the human gate; listing it does not provision either.

The public OpenRouter catalog checked on this date contained those exact
versioned IDs, but neither Google dynamic alias. Never send a direct-Google
alias to OpenRouter or an Argon identifier to the direct Google adapter.
Catalog availability, context and prices can change; discover them at the
owning provider rather than treating sample estimates as spending authority.

## Specialized Models

The operator's image, video, audio, TTS and transcription entries remain
specialized capabilities, requiring human approval and a matching adapter.
They are not automatic text-model fallbacks. Unknown or unsupported model
routes remain denied rather than silently routed to another endpoint.

## Publication Scope

Current Orama and PT changes reuse their existing stacked PRs. AlphaClaw and
gbrain findings are queued for a later authorized batch. Recovered C3 changes
remain locally committed, without new PRs or activation. No historical model
observation is rewritten to claim that today's identifier was used then.
