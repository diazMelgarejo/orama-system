# D-LG-3 revision 3 — replacement compatibility proposal

**Status:** draft, unratified. Supersedes the named sections of the
[historical D-LG-3](history/ADR-DRAFT-D-LG-3-replacement-compatibility-name-ownership-2026-10-09.md).
The user approved replacement compatibility as a goal and implementation of
review corrections, not proof of the proposed runtime's behavior.

## Current direction

Default install is framework-free. Explicit namespace facade and explicit
replacement binding share one native implementation in `oramasys/oramasys`,
using Core's public contracts and one scheduler. Caller-installed LC/LG objects
are detected lazily only at their bridge boundary. Framework presence never
silently changes scheduler or activates interception. Both v0.x and v1.x exact
release lines need independently locked upstream oracle environments.

P0 native and P1 caller-installed interoperability are distinct from P2 explicit
LangGraph replacement. P3 replacement of `langchain_core` remains gated. Pydantic
AI stays native-pattern adoption/research-only; no production Agent bridge is
implied by "patterns without runtime". This corrects sections 1, 3, 4, 6, 8 and
9 of the old draft; it does not claim that bridge-only meant runtime-free.

## Import and metadata contract

- Activate only through an explicit launcher/API before any owned namespace is
  imported or worker thread starts. Freeze one owner per top-level name.
- Refuse accidental shadowing and late activation. No `.pth`, `sitecustomize`,
  auto-install, installed-file edits or publishing under upstream names.
- Unsupported modules/symbols are absent and raise actionable compatibility
  errors. Preserve broken-dependency errors instead of treating them as absence.
- Preserve native module identity and import metadata; test relative imports,
  reload, introspection, pickling and mixed real/native objects against oracles.
- Synthetic `find_distributions` in the fake prototype proves interpreter
  lookup only. It does not satisfy pip or establish an installed upstream
  distribution. Production wheels must retain truthful Oramasys identity.
  Any synthetic target-version view needs an explicit, separately reviewed
  contract and coverage gate; it must not cause unsupported version-gated code
  to execute or misrepresent the real installed distribution.
- No in-process alias mechanism can contain arbitrary foreign effects. Admit
  foreign nodes only with enforceable sandbox/process egress control; otherwise
  return a recorded refusal.

## Release sequence

Ratify the ownership/replacement design, inventory symbols, construct isolated
oracles, then implement only supported rows. R3 precedes R4. The durable
[refusal/HITL contract](../2026-10-09-compatibility-refusal-hitl-contract.md)
must be a complete verified vertical slice before overrides can execute.
Real Runnable subclass/pipe/callback behavior must pass independently; Core's
duck-typed shape is not a silent fallback for a failed optional framework import.

See [all revision 3 resolutions](REVISION-3-RESOLUTIONS.md). The fake prototype
is corrected research evidence, not a deployable implementation of this ADR.

## Later approved bridge slice

On 2026-10-09 the operator approved [D-LG-4 Phase 1](ADR-D-LG-4-PYDANTIC-AI-BRIDGE.md):
explicit graph-as-tool and offline-only agent-as-node bridging. This qualifies
the earlier Pydantic AI deferral for this bounded slice. Framework runtime
adoption, production foreign egress, broad replacement and deferred approvals
remain gated. Tiered module/symbol diagnostics are implemented without enabling
any import interceptor. See [revision 4](EXECUTION-REVISION-4.md).
