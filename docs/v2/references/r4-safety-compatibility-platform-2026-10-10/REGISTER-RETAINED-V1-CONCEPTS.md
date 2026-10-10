# Register — permitted backward-v1 concepts

**Status:** proposed under [D-LG-7](ADR-D-LG-7-R4-SAFETY-COMPATIBILITY-PLATFORM.md).
Plan slice: [T6](PLAN-R4-EXECUTION.md#t6--replacement-cohorts-and-retained-v1-register).
v2 is clean-room: v1 supplies read-only behavioural evidence, never code imported at
runtime, and v1 builds stay independent of v2 dependencies.

## Rubric

"Broad inclusion" means retaining useful vocabulary and behaviour where it satisfies v2
ownership and safety. It does not authorize runtime coupling or resurrect superseded
authority. For every retained term the register records: **source, intended meaning,
owner, disposition, acceptance fixture**. Use additive aliases only when the semantics
are honest. A historical no-op argument must not claim enforcement. Retire or refuse
concepts that need dual authority, unverified replay, silent fallback, or authentication
by self-declared name or topology. Keep a supersession pointer for each such decision.

## Initial dispositions

| v1 concept / term | v2 disposition |
| --- | --- |
| Prompt → Chain → Loop → Graph | Retain least-powerful-control doctrine; promote only when topology is domain logic |
| PerpetuaState, scratchpad, node delta | Retain canonical semantics with explicit facade conversion; no competing GraphState |
| GraphSpec / Run / Trace / Checkpoint | Retain the distinctions; state and trace are not durable continuation or long-term memory |
| Gateway, model server, provider lifecycle | Retain provider-facing names and thin facades; Telos executes endpoint security |
| Task, job, claim, lease, heartbeat, board | Retain concepts with separate authority; liveness or gossip never mutates v2 claims |
| Envelope, author/actor, lineage, source_ref | Follow [doc 69](../../69-agent-envelope-standard.md) additive neutral header and each panel's owner |
| Monitorability evidence | Preserve v1 advisory meaning; migrate through an explicit Phylax adapter, never reinterpret in place |
| PT `.agent`, `capture_lesson`, legacy lessons | PT stays v1 development-memory authority; preserve the explicit legacy path and provisioning rules |
| Approval preview, cancel, rollback | Preserve observed rollback-safe conditions; unknown outcomes remain consumed |
| Historical endpoints/security implementations | Read-only golden evidence for clean-room v2; no imports, no silent fallback |

## Anamnesis

Remains separately provisioned future work. Private runtime evidence is not automatically
tracked or pushed. Preserve weekly sanitized promotion, append-only semantic corrections
and human push control; recheck the approved legacy initialization and automatic
post-provision migration rules (doc 56) before any implementation.

## Per-term row template (to fill at T0/T6)

| Field | Content |
| --- | --- |
| Term | The v1 name |
| Source | File and commit where v1 defines it |
| Meaning | One sentence |
| Owner | The single v2 owner |
| Disposition | retain / alias / adapt / retire / refuse |
| Fixture | Golden translation fixture proving it, plus a prohibited-ownership-leak case |

The initial table above is the seed; no term is considered retained until it has a row
with an executed fixture.
