# Contract — artifact identity, admission and trust

**Status:** proposed under [D-LG-7](ADR-D-LG-7-R4-SAFETY-COMPATIBILITY-PLATFORM.md).
Design only. Every record and name below is a proposal to freeze at T0, not an
existing type. Plan slice: [T1](PLAN-R4-EXECUTION.md#t1--artifact-admission-and-policy-binding).

## 1. Why graph identity is not enough

`graph_id` proves structural content. It does not prove what a bound callable does: a
custom reducer or node is recorded as a reference (`module:qualname`), not a code
digest. The same topology can therefore run different code, under a different policy or
against a different provider contract. Admission must bind all of those, or a stale
approval or grant could authorize work it never saw.

## 2. `ArtifactBinding`

An immutable record, one per run:

| Field | Meaning |
| --- | --- |
| `graph_id` | Structural identity from Core |
| `implementation_digest` | Digest of the built artifact / code registry entry |
| `state_schema_version` | Version of the detached state schema |
| `policy_digest` | Digest of the separate GraphPolicy file |
| `registry_profile_digest` | Ownership-registry profile the run was qualified against |
| `provider_contract_digest` | Digest of each provider manifest in use |
| `execution_semantics_version` | R3/R4 semantics version (settlement, fold order, continuation) |

Rules:

- Canonical encoding with an explicit domain tag and schema version per digest, so a
  digest of one kind can never be replayed as another.
- Unknown fields fail closed. Extension metadata has one named location and cannot
  carry authority.
- A run binds one immutable artifact set. Hot reload cannot mutate it.
- A changed implementation, policy or provider contract needs re-admission and either an
  explicit continuation migration or refusal ([continuation §3](CONTRACT-DURABLE-CONTINUATION.md)).
- A linked application policy summary is a generated projection checked by digest. The
  separate policy file stays authoritative.

## 3. Admission

`admit_artifact(binding, context)` returns a discriminated `AdmissionDecision`, never a
Boolean. The context is authenticated, not self-declared.

| Check | Authority |
| --- | --- |
| Principal and capability | Phylax decision (actual, not a copied rule set) |
| Artifact and provenance | Phylax artifact/provenance admission |
| Evidence freshness and source class | Phylax; derived or reconstructed evidence cannot satisfy a requirement for `Observed` |
| Hardware feasibility | Agate measured fit; impossible hardware is non-overridable |
| Endpoint purposes | Telos; no semantic-only precheck stands in for actual transport |

Gate results are `allow`, `refuse` or `pending`. Only an explicitly overridable, valid
request may enter the human-exception path ([HITL contract §2](CONTRACT-DURABLE-HITL-EFFECTS.md)).
Every refusal carries an actionable, redacted reason. A feasible permitted operation does
not ask a human repeatedly.

## 4. Policy binding and runtime checks

GraphPolicy stays restrict-only. Declarations are not runtime authority: route and budget
checks run at execution, and revalidation triggers (artifact, policy, provider contract,
principal state, hardware evidence change) force re-admission. Custom callable reference
strings never import or authenticate code.

## 5. Acceptance tests (named, to fail first)

| Test | Invariant |
| --- | --- |
| `test_same_graph_changed_code_invalidates_admission` | Same `graph_id`, new implementation digest → refused |
| `test_stale_policy_summary_refused` | Projection digest mismatch → refused |
| `test_nonobserved_source_cannot_admit` | Derived evidence cannot satisfy `Observed` |
| `test_missing_hardware_or_principal_refused` | No evidence → refuse, never default allow |
| Unknown and duplicate input tests | Validate before indexing; duplicates cannot hide a violation |
| Absent enforcement service | Admission service unavailable → fail closed |

## 6. Open items for T0

Canonical encoding choice and domain tags; where the code registry lives; which Phylax
and Agate interfaces already exist versus need a contract in their own repositories.
