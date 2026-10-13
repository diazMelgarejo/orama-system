# V2 Admission Contract Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Phylax, Agate, Telos, Perpetua Core, and Oramasys admission slices compose through one verified, effect-scoped contract without changing v1 repositories or prematurely implementing mesh transport.

**Architecture:** Phylax remains the mandatory generic admission authority. Agate supplies optional hardware-fit evidence only for hardware dispatches, while Telos supplies endpoint decisions only for declared network effects. Perpetua Core exposes only a dependency-neutral scheduler gate; Oramasys owns adapters and invocation composition. Every adapter preserves the issuer-owned decision, expiry, binding digest, and refusal reason instead of translating a caller assertion into authority.

**Tech Stack:** Python 3.11+, dataclasses, Pydantic v2 in Core, SQLite WAL for invocation-local step accounting, pytest/pytest-asyncio, Hatch/uv direct Git dependencies.

**Spec:** `orama-system/docs/v2/62-telos-phylax-authority-gate0-adr.md`, `orama-system/docs/v2/68-orchestrator-controller-satellite.md`, `orama-system/docs/v2/69-agent-envelope-standard.md`, and `orama-system/docs/v2/42-agate-hardware-policy-orbit.md`.

## Global Constraints

- Implement only in v2 repositories: `oramasys/phylax`, `oramasys/agate`, `oramasys/telos`, `oramasys/perpetua-core`, and `oramasys/oramasys`.
- Preserve v1 PT and `orama-system` as evidence/specification sources; neither is a runtime dependency for this slice.
- Retain Core's neutral `DispatchGate`; Core must not import Oramasys, Phylax, Agate, or Telos.
- Telos is the sole endpoint-security authority; Phylax owns generic capability/provenance admission; Agate is placement evidence and never claim/authorization authority.
- Treat unknown, unavailable, expired, mismatched, or unissued required decisions as refusals before the relevant execution boundary.
- `GraphSpec.graph_id` remains its established bare, lowercase 64-hex representation. Do not change its serialized public contract.
- Do not implement BLE or GossipMesh transport in this slice. LAN mesh is v2.1 work and BLE remains future work under `docs/v2/43-gossipbus-mesh-transport.md`.
- Do not encode concrete workstation paths, endpoints, identities, or topology in tracked files.
- Each repository must retain its existing coverage floor; 80% is the minimum where a repository has no stricter requirement.

## Review Focus

- A Core-generated `GraphSpec.graph_id` must construct an Oramasys artifact binding without representation conversion or loss of domain separation.
- A forged, expired, revoked, or issued-by-another-instance Telos decision must never pass freshness validation.
- A graph with no network or model-dispatch effect must not require Telos or Agate; a graph that declares either effect must fail closed without its owner.
- A caller-provided `HardwareObservation` must not be represented as trusted observed evidence unless a trusted collector proves its provenance.
- Pinned package revisions and the Core gate integration fixture must exercise the exact merged satellite contracts, not local fakes only.

---

## File and Dependency Map

| Repository | Files | Responsibility |
| --- | --- | --- |
| `oramasys/telos` | `src/telos/authorizer.py`, `src/telos/contracts.py`, `src/tests/test_decision_lifecycle.py` | Issuer-bound endpoint decision freshness and invalidation. |
| `oramasys/agate` | `src/agate/fit.py`, `src/agate/profiles.py`, `tests/test_fit.py` | Fit evidence classification without granting authority. |
| `oramasys/perpetua-core` | `src/perpetua_core/graph/gate.py`, `src/perpetua_core/graph/spec.py`, `src/tests/graph/test_dispatch_gate.py` | Neutral gate and canonical graph identity boundary. |
| `oramasys/oramasys` | `src/orama/graph/admission.py`, `src/orama/graph/execution_guard.py`, `src/orama/graph/adapters.py` (new), `src/tests/test_admission_decision.py`, `src/tests/test_execution_guard.py`, `src/tests/core_gate/test_admission_gate_scheduler.py`, `pyproject.toml` | Effect-scoped owner adapters, Core-compatible binding, composition, and pins. |
| `orama-system` | `docs/v2/68-orchestrator-controller-satellite.md` only if terminology needs clarification | Preserve the distinction between invocation fencing and controller-owned task leases. |

## Merge Topology

1. Land the Telos freshness repair on top of PR #7.
2. Land Phylax #4 unchanged unless its review identifies a local defect.
3. Land the Agate classification repair on top of PR #5.
4. Land Core #10 with its neutral seam intact.
5. Rebase Oramasys #29 last on the resulting satellite revisions, replace fake-only composition with real adapters, and update all direct Git pins in one coherent commit.

No branch may merge based only on a passing isolated unit suite. The final Oramasys PR must run its scheduler integration job against the exact Core merge head and install the exact Phylax, Agate, and Telos merge heads.

### Task 1: Bind Telos Freshness to Issuer-Owned Decisions

**Files:**
- Modify: `oramasys/telos/src/telos/authorizer.py`
- Modify: `oramasys/telos/src/telos/contracts.py`
- Modify: `oramasys/telos/src/tests/test_decision_lifecycle.py`

**Interfaces:**
- Produces: `EndpointAuthorizer.is_current(decision: EndpointUseDecision) -> bool` that returns true only for an allowed decision issued by that exact authorizer, still unexpired, and at the current policy epoch.
- Consumed by: the Oramasys Telos adapter in Task 5.

- [ ] **Step 1: Write failing issuer and invalidation tests**

```python
def test_is_current_rejects_a_caller_constructed_future_decision() -> None:
    authorizer = make_authorizer()
    forged = allowed_decision(expires_at=clock.now + timedelta(minutes=1))
    assert not authorizer.is_current(forged)

def test_policy_epoch_change_invalidates_an_issued_decision() -> None:
    authorizer = make_authorizer()
    decision = authorizer.authorize(valid_request())
    authorizer.revoke()
    assert not authorizer.is_current(decision)
```

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `uv run pytest src/tests/test_decision_lifecycle.py -q`  
Expected: the forged decision is incorrectly current and no invalidation method exists.

- [ ] **Step 3: Add issuer and epoch state**

```python
self._epoch = 1
self._issued: dict[str, EndpointUseDecision] = {}

def revoke(self) -> int:
    self._epoch += 1
    self._issued.clear()
    return self._epoch

def is_current(self, decision: EndpointUseDecision) -> bool:
    return (
        self._issued.get(decision.decision_ref) == decision
        and decision.allowed
        and decision.authority_epoch == self._epoch
        and decision.expires_at is not None
        and self._now() < decision.expires_at
    )
```

Add `authority_epoch: int` to `EndpointUseDecision`, populate it on authorization, and store only allowed decisions. Prune expired records before adding a new decision.

- [ ] **Step 4: Run focused and full Telos validation**

Run: `uv run pytest src/tests/test_decision_lifecycle.py src/tests/test_authorizer.py -q && uv run pytest -q`  
Expected: pass with Telos coverage at or above its configured floor.

- [ ] **Step 5: Commit the independent Telos repair**

```bash
git add src/telos/authorizer.py src/telos/contracts.py src/tests/test_decision_lifecycle.py
git commit -m "fix(telos): bind endpoint freshness to issued decisions"
```

### Task 2: Preserve Agate as Evidence, Not Authorization

**Files:**
- Modify: `oramasys/agate/src/agate/fit.py`
- Modify: `oramasys/agate/tests/test_fit.py`
- Add: `oramasys/agate/src/agate/evidence.py`

**Interfaces:**
- Produces: `FitEvidence` with `classification: Literal["observed", "derived"]`, `observed_at`, and a digest over normalized observation plus profile-store version.
- Produces: `assess_fit(..., evidence: FitEvidence) -> FitDecision`; `FitDecision` does not authorize or claim work.
- Consumed by: the Oramasys Agate adapter in Task 5.

- [ ] **Step 1: Write failing provenance tests**

```python
def test_unattested_hardware_observation_is_derived_not_observed() -> None:
    decision = assess_fit(policy, model, observation, evidence=FitEvidence.derived(observation, profile_store_version="v1"))
    assert decision.evidence_class == "derived"

def test_collector_evidence_binds_the_observation_digest() -> None:
    evidence = FitEvidence.observed(
        observation, profile_store_version="v1", collector="local-hardware-collector", clock=clock
    )
    changed = replace(observation, ram_gb=observation.ram_gb + 1)
    assert not evidence.covers(changed, "v1")

def test_evidence_from_an_earlier_profile_store_version_does_not_cover() -> None:
    evidence = FitEvidence.derived(observation, profile_store_version="v1")
    assert evidence.covers(observation, "v1")
    assert not evidence.covers(observation, "v2")
```

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `uv run pytest tests/test_fit.py -q`  
Expected: no evidence type exists and all decisions currently self-label as observed.

- [ ] **Step 3: Implement a small immutable evidence record**

```python
@dataclass(frozen=True, slots=True)
class FitEvidence:
    classification: Literal["observed", "derived"]
    observation_digest: str
    profile_store_version: str
    observed_at: datetime | None
    collector: str | None

    def covers(self, observation: HardwareObservation, profile_store_version: str) -> bool:
        return (
            self.profile_store_version == profile_store_version
            and self.observation_digest == canonical_observation_digest(observation)
        )
```

`FitEvidence.derived()` must be the default for in-process caller data. `FitEvidence.observed()` is available only to the local collector boundary and must validate an aware timestamp and nonempty collector identity. `assess_fit()` must reject evidence whose observation digest or profile-store version does not match, and carry the supplied classification forward.

- [ ] **Step 4: Add an explicit non-authority test**

```python
def test_fit_decision_has_no_capability_or_claim_operation() -> None:
    decision = assess_fit(policy, model, observation, evidence=FitEvidence.derived(observation, profile_store_version="v1"))
    assert not hasattr(decision, "capability")
    assert not hasattr(decision, "principal")
```

- [ ] **Step 5: Run Agate validation and commit**

Run: `uv run pytest tests/test_fit.py tests/test_policy.py tests/test_hardware_observation.py -q`  
Expected: pass.

```bash
git add src/agate/evidence.py src/agate/fit.py tests/test_fit.py
git commit -m "feat(agate): bind fit verdicts to classified evidence"
```

### Task 3: Confirm Core’s Neutral Gate and Preserve Graph Identity

**Files:**
- Modify only if necessary: `oramasys/perpetua-core/src/perpetua_core/graph/gate.py`
- Modify only if necessary: `oramasys/perpetua-core/src/tests/graph/test_dispatch_gate.py`
- Test: `oramasys/perpetua-core/src/tests/test_graph_spec.py`

**Interfaces:**
- Produces: the existing neutral `DispatchGate`, `DispatchRequest`, and `CommitRequest` without satellite imports.
- Preserves: `GraphSpec.graph_id` as bare 64-character lowercase hex.
- Consumed by: Oramasys in Tasks 4 and 5.

- [ ] **Step 1: Add a regression test for GraphSpec representation**

```python
def test_graph_id_is_stable_bare_sha256_hex() -> None:
    spec = GraphSpec.create(...)
    assert re.fullmatch(r"[0-9a-f]{64}", spec.graph_id)
```

- [ ] **Step 2: Run the Core identity and gate suites**

Run: `uv run pytest src/tests/test_graph_spec.py src/tests/graph/test_dispatch_gate.py -q`  
Expected: pass on the candidate Core revision.

- [ ] **Step 3: Review Core #10 for dependency purity**

Reject any Core change that imports an application, policy satellite, SQLite lease store, provider library, or transport library. Do not add an Oramasys binding type to Core.

- [ ] **Step 4: Commit only if the regression test or a required neutral-gate correction changes Core**

```bash
git add src/perpetua_core/graph/gate.py src/tests/graph/test_dispatch_gate.py src/tests/test_graph_spec.py
git commit -m "test(core): preserve neutral gate and graph identity contract"
```

### Task 4: Repair Oramasys Artifact Binding and Separate Invocation Fencing from Claims

**Files:**
- Modify: `oramasys/oramasys/src/orama/graph/admission.py`
- Modify: `oramasys/oramasys/src/orama/graph/execution_guard.py`
- Modify: `oramasys/oramasys/src/tests/test_artifact_admission.py`
- Modify: `oramasys/oramasys/src/tests/test_execution_guard.py`

**Interfaces:**
- Produces: `ArtifactBinding(graph_id: str, ...)` accepting Core's bare graph ID and producing a domain-separated binding digest.
- Produces: `InvocationFenceLedger` for per-run step accounting only; it must not model a controller task lease, claim, principal, or completion receipt.
- Consumed by: `AdmissionGate` and the adapters in Task 5.

- [ ] **Step 1: Write failing GraphSpec-to-binding tests**

```python
def test_artifact_binding_accepts_the_core_graph_id_shape() -> None:
    spec = GraphSpec.create(...)
    binding = ArtifactBinding(graph_id=spec.graph_id, **other_binding_fields())
    assert binding.graph_id == spec.graph_id
    assert binding.digest().startswith("sha256:")

def test_artifact_binding_rejects_prefixed_or_noncanonical_graph_ids() -> None:
    with pytest.raises(AdmissionRefused, match="bad_graph_id"):
        ArtifactBinding(graph_id="sha256:" + "a" * 64, **other_binding_fields())
```

- [ ] **Step 2: Run the failing artifact tests**

Run: `uv run pytest src/tests/test_artifact_admission.py -q`  
Expected: a Core graph ID is rejected by the current generic digest validator.

- [ ] **Step 3: Use a dedicated GraphSpec validator**

```python
_GRAPH_ID = re.compile(r"[0-9a-f]{64}")

def _graph_id(value: object) -> str:
    if not isinstance(value, str) or _GRAPH_ID.fullmatch(value) is None:
        raise AdmissionRefused("artifact_binding.bad_graph_id")
    return value
```

Keep `_DIGEST` for domain-tagged binding, policy, registry, and provider-contract digests. Do not prefix or recompute Core's graph ID.

- [ ] **Step 4: Write the controller-boundary tests**

```python
def test_invocation_fence_never_exposes_claim_lifecycle_operations() -> None:
    ledger = InvocationFenceLedger(db_path)
    assert not hasattr(ledger, "claim")
    assert not hasattr(ledger, "complete")
    assert not hasattr(ledger, "release")
```

- [ ] **Step 5: Rename and constrain the local ledger**

Rename `StepLedger` to `InvocationFenceLedger`, `open_lease()` to `open_invocation()`, and `lease_epoch` to `invocation_epoch`. Keep only atomic `reserve_steps()`, `check_epoch()`, and `used_steps()` operations. Do not add task IDs, principals, idempotency keys, controller state, or outbox writes; those belong to the deferred controller contract.

- [ ] **Step 6: Run Oramasys artifact and fencing tests**

Run: `uv run pytest src/tests/test_artifact_admission.py src/tests/test_execution_guard.py -q`  
Expected: pass.

- [ ] **Step 7: Commit the isolated Oramasys representation repair**

```bash
git add src/orama/graph/admission.py src/orama/graph/execution_guard.py src/tests/test_artifact_admission.py src/tests/test_execution_guard.py
git commit -m "fix(oramasys): align admission bindings with Core graph identity"
```

### Task 5: Add Effect-Scoped Satellite Adapters and Wire the Admission Gate

**Files:**
- Create: `oramasys/oramasys/src/orama/graph/adapters.py`
- Modify: `oramasys/oramasys/src/orama/graph/admission.py`
- Modify: `oramasys/oramasys/src/orama/graph/execution_guard.py`
- Modify: `oramasys/oramasys/src/tests/test_admission_decision.py`
- Modify: `oramasys/oramasys/src/tests/core_gate/test_admission_gate_scheduler.py`
- Modify: `oramasys/oramasys/pyproject.toml`

**Interfaces:**
- Consumes: `PhylaxAuthorizer`, `EndpointAuthorizer`, `assess_fit`, `FitEvidence`, `GraphSpec`, and Core `DispatchGate`.
- Produces: `build_admission_providers(...) -> AdmissionProviders` and `AdmissionRequirements(phylax: bool, agate: bool, telos: bool)`.
- Produces: normalized `OwnerDecision` records whose `decision_ref`, expiry, evidence class, and issuer `is_current` callback originate from the owning package.

- [ ] **Step 1: Write failing effect-requirement tests**

```python
def test_pure_graph_requires_phylax_but_not_agate_or_telos() -> None:
    requirements = AdmissionRequirements.for_effects(model_dispatch=False, endpoint_purposes=())
    assert requirements == AdmissionRequirements(phylax=True, agate=False, telos=False)

def test_model_dispatch_requires_agate_and_network_effect_requires_telos() -> None:
    requirements = AdmissionRequirements.for_effects(model_dispatch=True, endpoint_purposes=("model_egress",))
    assert requirements == AdmissionRequirements(phylax=True, agate=True, telos=True)
```

- [ ] **Step 2: Write failing adapter provenance tests**

```python
def test_telos_adapter_refuses_an_unissued_decision() -> None:
    adapter = TelosAdapter(authorizer)
    assert not adapter.is_current(forged_owner_decision)

def test_derived_agate_evidence_cannot_satisfy_a_required_observed_fit() -> None:
    result = adapter.assess(context_with_derived_fit)
    assert result.evidence_class == "derived"
```

- [ ] **Step 3: Implement adapters without reimplementing satellite policy**

```python
@dataclass(frozen=True, slots=True)
class AdmissionRequirements:
    phylax: bool
    agate: bool
    telos: bool

    @classmethod
    def for_effects(cls, *, model_dispatch: bool, endpoint_purposes: tuple[str, ...]) -> "AdmissionRequirements":
        return cls(phylax=True, agate=model_dispatch, telos=bool(endpoint_purposes))
```

Each adapter may translate a satellite result into `OwnerDecision`, but it must delegate freshness to the owner instance. It must not recreate endpoint classification, fit rules, capabilities, expiry, or an allow decision in Oramasys.

- [ ] **Step 4: Make `admit_artifact()` request only required owners**

Replace the unconditional three-provider presence check with an explicit `requirements` argument. Missing required providers return `admission.<owner>_unavailable`; missing non-required providers are not called and do not block a pure graph.

- [ ] **Step 5: Wire trusted construction, not a permissive fallback**

Replace `production_providers() -> None` with a construction function that either returns fully configured adapters or raises a configuration error before an invocation begins. Do not introduce a fake/default allow provider. Existing applications that have not configured all required effect owners must remain refused.

- [ ] **Step 6: Add scheduler-level cross-package tests**

```python
async def test_gate_runs_a_pure_graph_with_phylax_only() -> None: ...

async def test_gate_refuses_model_dispatch_when_agate_is_missing() -> None: ...

async def test_gate_refuses_network_dispatch_when_telos_decision_is_unissued() -> None: ...

async def test_gate_stops_before_the_next_callable_when_phylax_revokes() -> None: ...
```

Use the real satellite packages installed at the exact candidate revisions. Fakes may isolate a unit test but cannot be the sole proof of the integrated path.

- [ ] **Step 7: Update direct Git pins after upstream merge heads are known**

Update `pyproject.toml` only after Tasks 1–3 merge. Pin `oramasys-telos`, `oramasys-agate`, and `perpetua-core` to their verified merge commits. Regenerate the lockfile if this repository tracks one. Do not point production dependencies at an open PR head.

- [ ] **Step 8: Run integration validation**

Run:
```bash
uv run pytest src/tests/test_admission_decision.py src/tests/test_execution_guard.py src/tests/core_gate/test_admission_gate_scheduler.py -q
uv run pytest src/tests/test_perpetua_graph_spec.py src/tests/test_core_telos_discovery_contract.py -q
uv run pytest -q
```
Expected: all pass, with project coverage at or above the configured floor.

- [ ] **Step 9: Commit the final composition change**

```bash
git add pyproject.toml src/orama/graph/adapters.py src/orama/graph/admission.py src/orama/graph/execution_guard.py src/tests/test_admission_decision.py src/tests/test_execution_guard.py src/tests/core_gate/test_admission_gate_scheduler.py
git commit -m "feat(oramasys): compose effect-scoped admission authorities"
```

### Task 6: Document the Delivered Boundary Without Expanding Scope

**Files:**
- Modify: `orama-system/docs/v2/68-orchestrator-controller-satellite.md` only if Task 4 terminology needs an explicit non-controller invocation-fence note.
- Modify: `orama-system/docs/v2/62-telos-phylax-authority-gate0-adr.md` only if the merged adapter API changes an accepted ownership statement.

**Interfaces:**
- Produces: an additive as-built reference stating that invocation fencing is not controller job claiming and that the controller remains deferred.

- [ ] **Step 1: Write the documentation acceptance test as a review checklist**

Verify the proposed text states all of the following: Core remains neutral; Agate cannot authorize; Telos owns endpoint security; Phylax owns admission; controller claim/lease authority is not implemented; BLE/GossipMesh scope is unchanged.

- [ ] **Step 2: Add only the necessary clarification**

Use a concise note such as: “The application may maintain invocation-local epoch fencing for step accounting. This is not a controller task lease and confers no claim, completion, release, or recovery authority.”

- [ ] **Step 3: Check links and portable-content hygiene**

Run: `python3 scripts/review/repo_hygiene.py .` from the `orama-system` checkout.  
Expected: clean, with no topology-specific content added.

- [ ] **Step 4: Commit documentation independently**

```bash
git add docs/v2/62-telos-phylax-authority-gate0-adr.md docs/v2/68-orchestrator-controller-satellite.md
git commit -m "docs(v2): distinguish invocation fencing from controller leases"
```

## Final Integration Gate

- [ ] Confirm the five merged commit IDs are recorded in the Oramasys dependency pins and test environment.
- [ ] Run each repository's full configured test command from a clean worktree.
- [ ] Run Oramasys scheduler tests against real merged satellites and record their installed revisions in test output or an immutable fixture.
- [ ] Verify no direct v1 PT/Orama runtime import, endpoint-policy fork, controller claim implementation, GossipMesh transport, BLE transport, or topology literal entered the diff.
- [ ] Re-review the final Oramasys diff against docs 42, 43, 62, 68, and 69 before merge.

## Self-Review

- **Spec coverage:** Findings 3–6 are mapped to Tasks 1–5. The PR assessment actions are folded into merge topology and each owner task. BLE and HMAC control-plane expansion are explicitly excluded because they were not valid remediation targets.
- **Type consistency:** Core retains its bare graph ID; Oramasys only produces domain-tagged enclosing digests. Satellite-specific decisions are normalized only inside adapters and checked by the originating authority.
- **Review-focus coverage:** Tasks 1, 2, 4, and 5 contain focused tests for each listed failure class.
- **Scope:** The plan avoids a new controller, network transport, or v1 migration. Those need separately approved protocol work.

## Execution Handoff

Plan complete and saved to `orama-system/docs/superpowers/plans/2026-10-11-v2-admission-contract-integration.md`. Review the plan before implementation. I recommend **subagent-driven** execution because the final Oramasys composition depends on four independently reviewable upstream contracts, and an incorrect adapter can silently turn evidence into authority.
