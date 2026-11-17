# Biafra open-gap source implementation

Authority: current user instruction to implement the supplied handoff. Status:
local candidate on the existing PR contents, not a published or deployed release.
[Doc 76 section 14](../../76-biafra-outer-seat-canonical-plan.md#14-open-gap-source-continuation-2026-11-17)
owns current gap dispositions; this receipt supplies implementation detail.

## Synthesis and ownership

Prompt Workspace prepared the task without saving it. The implementation uses
the repository's oramasys-method and complete contract-migration vertical slice.
PT owns provider admission, durable budgets and spend settlement. Orama owns
stateless seat validation and preflight. No v2 organization repository changes.

The metric registry stays with the existing Orama contract, avoiding a new
durable policy store. A named stall constant retains the existing behavior.
Exact integer validation removes precision ambiguity without pretending to have
inventoried every external consumer. No new worker authentication or ledger.

## Migration ledger

| Layer | Change | Evidence and compatibility |
| --- | --- | --- |
| Persistence | No new store; existing PT budget remains canonical | Parent alone reserves, releases and settles; no worker-owned budget |
| Contract | Declared metrics and exact integer band | Trace/card/cycle validators share one registry; unknown names and large integers refuse |
| Callers | New live pin/probe inputs and explicit chosen model/effort | Active tests and programs updated; preserved historical harness is not edited |
| Transport | PT worker uses private stdin JSON and closed result variants | No credentials in arguments or provider errors; no pickle; SDK retries disabled |
| Lifecycle | Preflight before budget/marker; killable SDK request | Timeout, child crash and malformed result settle unknown; provably unsent startup releases |
| Operations | Local source candidates only | Publication, real probes, persona/policy decisions and native platform evidence remain separate |

No persisted trace history is rewritten. Unknown historical metric labels are
not silently assigned new meanings. Rollback of these validators restores old
acceptance behavior, not a rewritten historical receipt or migrated budget.

## Live preflight contract

`live_cycle` additionally accepts `pin_path`, `probe_record` and optional `model`.
Missing or mismatched pin and missing, stale or malformed probe evidence refuse
before `SpendGate.preflight`, the once marker and the launcher. Evidence has
exactly four top-level fields:

```json
{
  "date": "2026-11-17",
  "provider": "https://api.inference.wandb.ai/v1",
  "models": ["deepseek-ai/DeepSeek-V4.1-Flash-1017"],
  "efforts": {"deepseek-ai/DeepSeek-V4.1-Flash-1017": ["high", "low"]}
}
```

This is a shape example, not fresh provider evidence. Never reuse its date or
contents as a real probe. `models` describes available candidates; selection
uses the existing canonical model order, not provider-list order. Effort uses
the canonical medium/high/low ladder and support intersection; new support
outside the reviewed policy requires a policy update. Explicit selections that
bypass the order or ladder refuse, including invalid launcher arguments.

The local record is trusted evidence, not cryptographic proof of who probed or
an account billing attestation. The existing independent PT billing attestation
and budget checks remain mandatory. No probing or paid completion occurs while
testing. The old armed `run_program` path now refuses before a dry-run marker;
unarmed dry programs remain usable. Callers must deliberately adopt `live_cycle`.

## PT request boundary

The SDK runs in `src/perpetua_tools/wandb_worker.py`. PT's harness owns spending
and communicates through private pipes with a minimal JSON protocol. Success
preserves content and billed token accounting. Known SDK startup failure is
unsent; definitive provider refusal releases; timeout, crash, invalid protocol
or uncertain request outcome settles the full reservation. A failed final
settlement does not discard the paid answer. Optional tracing stays inside the
timed child instead of blocking the parent before the deadline.

At the monotonic request deadline the parent kills the worker immediately,
then reaps with a bounded wait and closes pipes. Native process creation and
OS scheduling are not hard real-time primitives; cleanup may add bounded wall
time after request execution is stopped. The hold retains its safety margin.
The generic OpenAI-compatible W&B configuration refuses before SDK construction
instead of becoming an unguarded alternative provider path.

## Verification and gates

RED/GREEN regressions cover integer boundaries, undeclared metrics, model and
effort bypasses, fallback selection, invalid launcher arguments, missing/stale
probe and pin evidence, unsent failures, timeout, crash, accounting and cleanup.
Final integrated-tree counts belong in the downloadable execution handoff; do
not transfer earlier PR or per-agent results to a changed tree.

Native macOS kqueue and sandbox evidence and Windows qualification remain open.
G1/G2 dependencies, G6 persona acceptance and G11 policy choice are not replaced
by agent assertions. Security baselines are unchanged. No serving, paid model,
operator attestation, live arm, merge or publication is implied.
