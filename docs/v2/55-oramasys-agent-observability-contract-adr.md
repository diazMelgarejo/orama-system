# 55 — oramasys Agent Observability Contract & Telemetry Governance (ADR)

> **Status:** Accepted (Implemented in Perpetua-Tools 2026-08-24)  
> **Date:** 2026-08-24  
>
> **Parent Documents:**  
>
> - [`54-tri-stack-observability-and-l3-egress-v2.md`](54-tri-stack-observability-and-l3-egress-v2.md)
> - [`48-board-job-source-line-schema.md`](48-board-job-source-line-schema.md)
> - [`32-agentic-security-controls.md`](32-agentic-security-controls.md)
>
> **Implementation Artifacts:**  
>
> - PT-P1: Layer-3 pf ordering & telemetry cardinality (`38ad1051`)
> - PT-P2: OTel-native domain observations & OTLP exporter (`354fdbb5`)
> - PT-P3: Multi-agent bias sentinel & dual-write sunset (`1c56e347`)
> - PT-P4: OTLP transport boundary (`fddcd903`, `f11df573`, `a77e6de2`) and
>   POSIX descriptor-confined local sink (`7baf5022`)
>
> **Cross-Repo Partner:** [`Perpetua-Tools`](https://github.com/diazMelgarejo/Perpetua-Tools)  

---

## 1. Context & Architectural Decision

Multi-agent coordination across `orama-system` and `Perpetua-Tools` requires rigorous observability
without compromising on security, operational simplicity, or data privacy.

### The Governing Decision: "Core + Planes + Adapters"

Rather than inventing an ad-hoc protocol or forcing internal runtime code to imitate external
formats (OpenClaw, Periscope, OpenTelemetry), the architecture establishes:

1. **Normative Governance (`orama-system`):** Owns this ADR, the vocabulary definitions,
   signal mappings, and privacy governance rules.
2. **Domain Observation Engine (`Perpetua-Tools`):** Owns the compact, Pydantic v2 discriminated
   union domain models (`DomainObservation`) and runtime emitters.
3. **External Projections & Adapters:**
   - **Local Trajectory Sink (`periscope_adapter.py`):** Projects to OpenClaw v3 JSONL for local
     [LatentSignal Periscope](https://github.com/latentsignal-org/periscope) visualization.
   - **Remote Telemetry Sink (`otel_exporter.py`):** Projects to real OpenTelemetry traces,
     spans, and log-based EventRecords via official `opentelemetry-*` SDK packages.

```text
                     orama-system
             Normative doctrine + schema governance
                          │
                          ▼
             DomainObservation (Pydantic v2)
        identity · correlation · provenance · privacy
                          │
       ┌──────────────────┴───────────────────┐
       ▼                                      ▼
  Periscope Adapter                      OTel SDK / OTLP
(Tier: internal_only)                  (Tier: redacted)
       │                                      │
       ▼                                      ▼
Local OpenClaw JSONL                  OTLP/HTTP Protobuf
```

---

## 2. Signal Mapping: Operations vs Point-in-Time Events

We adhere strictly to OpenTelemetry's canonical distinction between duration-bearing operations and
point occurrences:

| oramasys Runtime Occurrence | OpenTelemetry Representation | Description |
| :--- | :--- | :--- |
| **Agent / Workflow Invocation** | `Span` (`gen_ai.invoke_agent` / `gen_ai.invoke_workflow`) | Operations spanning time with parent-child trace hierarchy |
| **Tool Execution** | `Span` (`gen_ai.execute_tool`) | Execution of shell, file, or search tools |
| **Bridge HTTP Request** | `Span` (HTTP `CLIENT` span) | Outbound HTTP calls to remote LLM / orama endpoints |
| **Worker Execution** | `Span` (`oramasys.worker.execution`) | Single-turn worker primitive lifecycle |
| **Egress Validation Check** | `EventRecord` / `LogRecord` | Correlated to current request span (`egress.validation`) |
| **Egress Request Completion** | `EventRecord` / `LogRecord` | Final status and duration (`egress.request.complete`) |
| **Task Claimed / Completed** | `EventRecord` / `LogRecord` | Coordination board queue state transitions |
| **Governance Approval / Gate** | `EventRecord` / `LogRecord` | HITL review and HMAC grant validations |
| **Coordination Bias Advisory** | `EventRecord` / `LogRecord` | Advisory-only sentinel consensus score |

---

## 3. Identifiers & Privacy Contracts

### 3.1 Identifier Standards

- `event_id`: Standard library `uuid.uuid4()` string (explicitly rejecting custom ULID complexity).
- `trace_id`: 32-hex character W3C Trace ID managed by OpenTelemetry SDK.
- `span_id` / `parent_span_id`: 16-hex character W3C Span ID managed by OpenTelemetry SDK.
- `run_id`: Top-level workflow execution run ID.
- `task_id`: Coordination board queue task identifier (`phase-name-uuid`).
- `agent.id`: Stable logical identity (e.g. `pt-supervisor`, `alphaclaw-routing`).
- `agent.instance_id`: Ephemeral random UUID generated at process startup (absolute ban on
  embedding raw hostnames).

### 3.2 Two-Tier Privacy Trust Model

1. **`internal_only` Tier:**
   - Applicable strictly to local file exports consumed by local user tooling (e.g.
     `periscope_adapter.py` writing session JSONL).
   - May carry controlled rich text: `user_text`, `assistant_text`, `cwd`, `model`.
   - **Absolute Prohibition:** An `internal_only` record can never be exported over the network by
     the OTLP exporter.
2. **`redacted` Tier:**
   - Applicable to all remote OTLP network exports.
   - **Absolute Invariants:** Zero prompts, zero raw hostnames, zero raw IP addresses, zero
     credentials/tokens, and zero absolute filesystem paths.
   - Destination hostnames and IP addresses are masked via session-salted HMAC-SHA256 correlation
     hashes.

### 3.3 Custom Attribute Namespace

All domain-specific attributes are projected strictly under the `oramasys.*` namespace:

- `oramasys.destination.hash` (HMAC-SHA256 salted hash)
- `oramasys.egress.endpoint_class` (`local` | `remote`)
- `oramasys.egress.deny_reason` (typed `EgressDenyReason` enum)
- `oramasys.task.phase` / `oramasys.task.priority`

Standard OTel attribute `server.address` is **omitted entirely** on redacted exports to prevent
emitting semantically false hash strings under standard domain fields.

### 3.4 Transport Enforcement and Provider Lifecycle

Privacy classification and destination authorization are separate gates. A
`redacted` observation is eligible for remote projection, but it is not itself
permission to contact an arbitrary collector.

The PT-owned OTLP/HTTP exporter therefore enforces all of the following:

- No configured endpoint means no network exporter and no implicit localhost
  fallback.
- `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` is the complete trace URL;
  `OTEL_EXPORTER_OTLP_ENDPOINT` is a base URL and receives `/v1/traces` exactly
  once.
- Every configured OTLP endpoint requires HTTPS. Userinfo, URL query strings,
  fragments, malformed ports, localhost names, and non-global address literals
  are rejected before exporter construction.
- Each connection resolves and validates every A/AAAA result, connects to a
  validated pinned address, preserves the original hostname for TLS SNI and
  certificate verification, refuses redirects, and does not inherit process
  proxy settings.
- PT installs or reuses one process-global `TracerProvider`. It never mutates
  OpenTelemetry private globals and never attempts to replace a provider that
  another runtime has already installed. Tests use explicit provider and span
  processor injection instead.

The Periscope trajectory adapter is an adapter-owned `internal_only` boundary:

- It has no OTel/OTLP import or network-forwarding path.
- Agent and session components use a narrow allowlist; URL and UNC roots are
  rejected.
- POSIX writes traverse the configured state root with descriptor-relative
  directory operations and `O_NOFOLLOW`, create a `0600` temporary file, and
  atomically replace the final JSONL within the already-open session directory.
- Platforms without POSIX directory-descriptor semantics retain same-directory
  atomic replacement and reject observed symlink components before writing;
  this is a best-effort pre-write guard, not a late-symlink race-safety claim.

These controls establish confidentiality by transport separation. They do not
claim encryption at rest; workstation storage protection and retention remain
operator responsibilities.

### 3.5 Closure Acceptance Matrix

| Guarantee | Executable evidence |
| :--- | :--- |
| Unsafe or metadata OTLP destinations create no exporter | PT `tests/test_otel_exporter.py` endpoint-policy cases |
| A configured collector uses pinned, proxy-free transport | PT pinned-session assertion |
| Existing global providers are reused rather than replaced | PT provider lifecycle tests |
| `internal_only` observations produce zero remote spans | PT in-memory exporter test |
| On POSIX, a late Periscope directory symlink cannot redirect a write (the write fails closed if the pinned directory is removed) | PT POSIX descriptor-relative race regression |
| Rich trajectory text remains only in local JSONL | PT local-versus-redacted projection test |

---

## 4. Provenance & Audit Standards

- **Observability Provenance:** Every `SourceProvenance` record requires a full 40-character Git
  commit SHA matching regex pattern `^[0-9a-f]{40}$` (`min_length=40, max_length=40`). Short
  7-character SHAs are prohibited for audit provenance.
- **Queue Source-Line Independence:** This 40-character rule applies strictly to observability
  provenance and does not alter the provisional 7–40 character hex definition of `expected_base_sha`
  in [`48-board-job-source-line-schema.md`](48-board-job-source-line-schema.md).

---

## 5. Coordination Bias Sentinel & Amplifier Principle

- **Multi-Agent Evidence Invariant:** The `CoordinationBiasDetector` sliding window tracks stable
  `agent.id` (not ephemeral `agent.instance_id`) alongside confidence and lexical cues.
- **Groupthink Threshold:** Requires **at least 3 distinct logical `agent.id` values** in the
  evidence window before evaluating `agreement_collapse`. Counting distinct `agent.id` values
  rather than ephemeral `agent.instance_id` values ensures that agent restarts do not trigger a
  false `agreement_collapse`. Repetitive outputs from a single agent are classified as
  `echo_loop_detected`, never groupthink.
- **Initial Empirical Calibration:**
  - `confidence_stdev < 0.08` (high consensus).
  - `confidence_mean > 0.85` (high agreement).
  - *Disclaimer:* Numerical thresholds are initial empirical calibration baselines subject to
    ongoing operational review.
- **The Amplifier Principle:** The sentinel produces purely advisory signals (`coordination_risk:
  low | medium | high | insufficient_evidence`). It is strictly prohibited from gating task
  claims, canceling approvals, mutating agent state, or acting as an autonomous authorization
  authority.

---

## 6. Dual-Write Sunset Policy

- **Current State:** During the rollout of Canonical Event Core v1, emitters in `Perpetua-Tools`
  maintain backward compatibility by writing both canonical events and legacy `heartbeat` payloads
  to `perpetua_core.db`.
- **Sunset Policy:** Legacy `heartbeat` payload writes are deprecated and will be permanently
  retired upon **Phase 4 docs-crystallization + one release cycle**, once `periscope_adapter.py` and
  `CoordinationBiasDetector` consume exclusively canonical domain events.
