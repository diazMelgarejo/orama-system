# Oramasys OpenClaw Control Plane V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `oramaclaw`, the shared Oramasys OpenClaw Control Plane for safe declarative ownership and reconciliation of OpenClaw resources.

**Architecture:** V1 is a portable Python package canonically implemented in Orama System and synchronously vendored into Perpetua-Tools. It uses field-aware base/observed/desired merges, a durable ownership ledger, Gateway RPC as the primary writer, and a restricted offline adapter.

**Tech Stack:** Python, pytest, OpenClaw CLI and gateway RPC, existing Orama portal server and React portal.

## Global Constraints

- Canonical source: `src/oramaclaw/`; generated Perpetua-Tools mirror: `../perplexity-api/Perpetua-Tools/oramaclaw/`.
- V1 imports neither Perpetua-core nor AlphaClaw. Perpetua-core is V2 only. AlphaClaw is an optional lifecycle adapter, never a configuration owner.
- Gateway `config.get` plus `config.apply` or `config.patch` with `baseHash` is the normal configuration mutation path.
- Every resource declares a stable `manager` name. The engine owns transport and journaling, but a manager owns each managed field; a different manager cannot adopt, auto-weave, or overwrite that field.
- Offline mutation is restricted to provider registration and creation of a new agent. It locks, parses, preserves mode, atomically writes, and revalidates JSON.
- Resource adoption is explicit. Existing matching state is not silently adopted.
- Normal, schema-valid cooperative drift may auto-weave the observed value into a manager-scoped effective-desired override after 90 seconds, preserving live configuration. The override applies only while the manifest source field remains unchanged; an explicit source change clears it. Security topology always remains conflict-only.
- Security topology includes credentials, execution policy, delegation, and agent create/remove. It is never auto-adopted, auto-woven, or overwritten after a timeout.
- Before any configuration mutation, write a durable `prepared` transaction. After mutation, record `applied_unverified`; startup and status recover incomplete transactions by re-reading live state and committing or conflicting, never guessing.
- Registered targets are named entries in a local catalog at `$ORAMACLAW_TARGETS_PATH` or `~/.oramaclaw/targets.json`; portal clients select only these names.
- Default Codex effort is `medium`; `high` and `xhigh` are opt-in.
- Delegation uses `agents.defaults.subagents.allowAgents` or `agents.list[].subagents.allowAgents`, never `agents.bindings.*.allowAgents`.
- Generated profiles replace only a marker-delimited section and retain operator-authored content elsewhere.
- Keep `.claude/skills`, unrelated Perpetua-Tools drift, and the `cc-openclaw` submodule state out of scope.

---

### Task 1: Establish The Package, Target Contract, And Manifest Schema

**Files:**
- Create: `src/oramaclaw/__init__.py`
- Create: `src/oramaclaw/types.py`
- Create: `src/oramaclaw/schema.py`
- Create: `src/oramaclaw/target.py`
- Create: `tests/test_oramaclaw_target.py`
- Create: `tests/test_oramaclaw_schema.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: manifest JSON, explicit target flags, or legacy `openclaw_home`.
- Produces: `resolve_target(...)->tuple[ConfigTarget, tuple[str, ...]]`, `parse_manifest(path: Path)->ControlManifest`, and frozen `Resource` and `MergePolicy` types used by all later tasks.

- [ ] **Step 1: Write the failing tests.**

Cover explicit target normalization, one-time `openclaw_home` migration, rejection of partial targets, manifest version validation, unique resource keys, required non-empty manager names, default `medium` effort, opt-in `high` and `xhigh`, and rejection of obsolete delegation fields.

```python
def test_legacy_openclaw_home_resolves_explicit_target(tmp_path: Path) -> None:
    target, warnings = resolve_target(openclaw_home=tmp_path)

    assert target.workspace_root == tmp_path / "workspace"
    assert target.config_path == tmp_path / "openclaw.json"
    assert target.state_dir == tmp_path
    assert warnings == ("openclaw_home is deprecated; persist explicit target fields",)
```

- [ ] **Step 2: Run the focused tests to verify they fail.**

Run: `python -m pytest tests/test_oramaclaw_target.py tests/test_oramaclaw_schema.py -q`
Expected: import failures because the package does not exist.

- [ ] **Step 3: Implement immutable public types.**

```python
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Literal, Mapping


@dataclass(frozen=True)
class ConfigTarget:
    workspace_root: Path
    config_path: Path
    state_dir: Path


class ResourceKind(str, Enum):
    PROVIDER = "provider"
    BINDING = "binding"
    AGENT = "agent"
    DELEGATION = "delegation"
    EXECUTION_POLICY = "execution_policy"
    PROFILE = "profile"


class MergePolicy(str, Enum):
    STRICT = "strict"
    COOPERATIVE = "cooperative"
    CONFLICT = "conflict"


@dataclass(frozen=True)
class Resource:
    kind: ResourceKind
    identifier: str
    manager: str
    spec: Mapping[str, Any]
    managed_paths: tuple[str, ...]
    policy: MergePolicy


@dataclass(frozen=True)
class ControlManifest:
    """Parsed and validated declarative manifest (from JSON on disk)."""
    version: int                    # must be 1 for V1
    target: ConfigTarget
    resources: tuple[Resource, ...]
    source_path: Path               # original file path (for error messages)
    source_fingerprint: str         # SHA-256 of raw bytes


@dataclass(frozen=True)
class Conflict:
    """A field that cannot be automatically resolved."""
    resource_key: str               # e.g. "provider:codex-app-server"
    manager: str
    managed_path: str               # JSON Pointer e.g. "/effort"
    base_fingerprint: str | None
    observed_fingerprint: str | None
    desired_fingerprint: str
    security_topology: bool
    choices: tuple[str, ...]        # e.g. ("apply-desired", "keep-current", "show-diff")
    resolution_id: str              # stable opaque id for CLI/portal resolve


@dataclass(frozen=True)
class PendingResolution:
    """Durable record stored in pending-resolutions.json for portal/CLI pick-up."""
    resolution_id: str
    conflict: Conflict
    transaction_id: str
    created_at: str                 # ISO-8601
    resolved_at: str | None = None
    chosen: str | None = None


@dataclass(frozen=True)
class ControlResult:
    """Returned by ControlEngine.apply_manifest()."""
    transaction_id: str
    state: Literal["committed", "auto_woven", "conflicted", "needs_input", "gateway_unavailable", "failed"]
    applied: tuple[str, ...]        # resource_keys successfully committed
    auto_woven: tuple[str, ...]     # resource_key + path pairs auto-woven
    conflicts: tuple[Conflict, ...]
    warnings: tuple[str, ...]
```

All classes are frozen dataclasses. Normalize mutable input at parsing boundaries (convert `list` → `tuple`, resolve `Path.expanduser().resolve()`). Use canonical JSON plus SHA-256 hex for all fingerprints so the same logical state always produces the same fingerprint string.

- [ ] **Step 4: Implement `resolve_target()` and strict parsing.**

Require all three explicit target fields together. Resolve paths with `Path.expanduser().resolve()`. Map legacy `openclaw_home` to `workspace`, `openclaw.json`, and itself as `state_dir`, returning a warning. Use JSON manifests for V1 unless YAML is already a maintained dependency.

- [ ] **Step 5: Register and verify.**

Include `src/oramaclaw` in Hatch package discovery. Add to `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/oramaclaw"]

[project.optional-dependencies]
oramaclaw = []
```

Run the focused tests again; all must pass.

- [ ] **Step 6: Commit.**

```bash
git add pyproject.toml src/oramaclaw tests/test_oramaclaw_target.py tests/test_oramaclaw_schema.py
git commit -m "feat(oramaclaw): add manifest and target contracts"
```

### Task 2: Persist Field Ownership, Transactions, And Pending Resolutions

**Files:**
- Create: `src/oramaclaw/store.py`
- Create: `tests/test_oramaclaw_store.py`

**Interfaces:**
- Consumes: `ConfigTarget`, `Resource`, canonical fingerprints, and transaction metadata.
- Produces: `ControlStore(target: ConfigTarget)` with `load_registry()`, `record_adoption()`, `record_auto_weave()`, `begin_transaction()`, `recover_incomplete_transactions()`, `append_transaction()`, `save_pending_resolution()`, and target-lock context management; `TargetCatalog` registers named targets for CLI and portal use.

- [ ] **Step 1: Write failing persistence tests.**

Test all of the following:

1. Missing state files read as empty versioned state.
2. Explicit adoption records the resource base specification, policy, and per-managed-path fingerprints.
3. A cooperative auto-weave updates only a manager-scoped effective-desired override and never mutates the manifest-source base record.
4. Credential-like keys are recursively redacted before serialization.
5. Registry, journal, and pending-resolution writes use a same-directory temporary file and `os.replace()`.
6. A simulated failure before replace leaves a valid previous JSON file.
7. File mode is `0600` where the platform supports it.
8. Journal retention bounds history to 200 records.
9. A lock records PID, process start time, target hash, and creation time.
10. A lock is broken only after its recorded PID is confirmed absent, never merely because elapsed time is large.
11. A second manager attempting to claim an owned field is rejected even when its desired value matches.
12. A `prepared` or `applied_unverified` transaction is recovered by live-state comparison into either committed or conflicted state.
13. A registered target stores a name and resolved target fields; duplicate names and arbitrary portal path input are rejected.

```python
def test_transaction_journal_never_persists_provider_token(tmp_path: Path) -> None:
    store = ControlStore(tmp_path)
    store.append_transaction(
        {"request": {"provider": {"api_key": "must-not-persist"}}}
    )

    content = store.journal_path.read_text()
    assert "must-not-persist" not in content
    assert "***REDACTED***" in content
```

- [ ] **Step 2: Run the focused test to verify failure.**

Run: `python -m pytest tests/test_oramaclaw_store.py -q`
Expected: import failure for `oramaclaw.store`.

- [ ] **Step 3: Implement `ControlStore`.**

Persist state under:

```text
<state_dir>/oramaclaw/control-plane.json
<state_dir>/oramaclaw/transactions.json
<state_dir>/oramaclaw/pending-resolutions.json
<state_dir>/oramaclaw/control-plane.lock
$ORAMACLAW_TARGETS_PATH or ~/.oramaclaw/targets.json
```

Ownership ledger record:

```json
{
  "resource_key": "provider:codex-app-server",
  "manager": "codex-binder",
  "policy": "cooperative",
  "base": {
    "base_url": "http://127.0.0.1:8080/v1",
    "model": "gpt-5.5",
    "effort": "medium"
  },
  "field_fingerprints": {
    "/base_url": "sha256:...",
    "/model": "sha256:...",
    "/effort": "sha256:..."
  },
  "effective_desired_overrides": {
    "/effort": {
      "value": "high",
      "source_field_fingerprint": "sha256:...",
      "observed_fingerprint": "sha256:...",
      "auto_woven_at": "2026-06-20T00:00:00Z"
    }
  },
  "last_transaction_id": "tx_..."
}
```

Use an append-only bounded JSON array for V1 transactions. Store transaction id, manager, timestamps, resource key, transport, `prepared|applied_unverified|committed|auto_woven|conflicted|failed` state, redacted request summary, base/observed/desired fingerprints, warnings, and redacted error summary. Do not store a full unredacted OpenClaw document.

- [ ] **Step 4: Implement atomic state and locking helpers.**

Implement `_atomic_write_json()` using a temporary file in the same parent directory, file fsync, mode set, `os.replace()`, and parent-directory fsync when supported. Acquire the control-plane lock before reading observed configuration and retain it through reconciliation and state persistence.

Redact before serialization. Redaction keys include `token`, `secret`, `api_key`, `password`, `authorization`, and `cookie`. Do not stringify raw request objects before redaction.

When the manifest source field fingerprint still equals an override's `source_field_fingerprint`, the planner reads the override as effective desired intent. When the source field changes, delete that override before planning so the explicit manifest change wins. Recovery reads live state after a crash: matching desired commits; matching base records failed rollback or conflict; any other value becomes conflict.

- [ ] **Step 5: Run focused tests.**

Run: `python -m pytest tests/test_oramaclaw_store.py -q`
Expected: all tests pass.

- [ ] **Step 6: Commit.**

```bash
git add src/oramaclaw/store.py tests/test_oramaclaw_store.py
git commit -m "feat(oramaclaw): persist field ownership and transactions"
```

### Task 3: Implement Gateway-First And Restricted Offline Transport

**Files:**
- Create: `src/oramaclaw/transport.py`
- Create: `tests/test_oramaclaw_transport.py`
- Reference: `scripts/openclaw/resolve-openclaw.sh`

**Interfaces:**
- Consumes: `ConfigTarget`, `Resource`, and candidate configuration JSON produced by the planner.
- Produces: `OpenClawTransport`, `GatewayConfig`, `GatewayApplyResult`, `StaleConfiguration`, `GatewayUnavailable`, and `OfflineOperationNotAllowed` consumed by the engine.

- [ ] **Step 1: Write failing transport tests using a fake command runner.**

Test:

1. Resolver output, not a hardcoded OpenClaw binary, is used for each command.
2. `gateway_config_get()` invokes `gateway call config.get` and returns configuration plus `baseHash`.
3. `gateway_config_apply()` calls `gateway call <method> --params <json>` with `baseHash` and candidate JSON, and rejects raw credential-bearing values before constructing that command argument.
4. A stale hash maps to a typed `StaleConfiguration` result.
5. New agents call `gateway call agents.create`.
6. Agent updates and delegation call `gateway call agents.update`.
7. Offline provider mutation locks, parses, preserves unrelated fields, preserves mode, atomically writes, and validates replacement JSON.
8. Offline new-agent creation rejects an existing id without changing the existing agent.
9. Offline delegation, policy, existing-agent update, and arbitrary patch attempts fail before filesystem mutation.

- [ ] **Step 2: Run the focused test to verify failure.**

Run: `python -m pytest tests/test_oramaclaw_transport.py -q`
Expected: import failure for `oramaclaw.transport`.

- [ ] **Step 3: Implement transport interface and gateway invocation.**

Define the result/error types first, then the Protocol:

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class GatewayConfig:
    """Live configuration fetched from the gateway, plus its hash."""
    configuration: Mapping[str, Any]   # parsed openclaw.json document
    base_hash: str                     # opaque hash from gateway; must be threaded back on apply


@dataclass(frozen=True)
class GatewayApplyResult:
    """Successful response from a gateway config.apply or agents.* call."""
    transaction_id: str
    base_hash: str                     # new hash after apply, for chained operations


class StaleConfiguration(Exception):
    """Raised when the gateway rejects a write because baseHash is outdated."""
    def __init__(self, stale_hash: str, message: str = "") -> None:
        self.stale_hash = stale_hash
        super().__init__(message or f"stale hash: {stale_hash}")


class GatewayUnavailable(Exception):
    """Raised when the OpenClaw gateway is unreachable or returns a non-structured error."""


class GatewayRejected(Exception):
    """Raised when the gateway rejects the request for a semantic reason (validation, schema)."""
    def __init__(self, code: int, message: str) -> None:
        self.code = code
        super().__init__(f"gateway rejected (code={code}): {message}")


class OfflineOperationNotAllowed(Exception):
    """Raised when an offline adapter is asked to perform a disallowed mutation."""
    def __init__(self, resource_key: str) -> None:
        self.resource_key = resource_key
        super().__init__(
            f"offline mutations are only allowed for provider registration and new-agent "
            f"creation; rejected: {resource_key}"
        )


from typing import Protocol, runtime_checkable

@runtime_checkable
class OpenClawTransport(Protocol):
    def gateway_config_get(self, target: ConfigTarget) -> GatewayConfig: ...
    def gateway_config_apply(
        self,
        target: ConfigTarget,
        configuration: Mapping[str, Any],
        base_hash: str,
    ) -> GatewayApplyResult: ...
    def create_agent(self, target: ConfigTarget, spec: Mapping[str, Any]) -> None: ...
    def update_agent(
        self,
        target: ConfigTarget,
        agent_id: str,
        patch: Mapping[str, Any],
    ) -> None: ...
    def offline_apply_provider(self, target: ConfigTarget, resource: Resource) -> None: ...
    def offline_create_agent(self, target: ConfigTarget, resource: Resource) -> None: ...
```

Resolve `scripts/openclaw/resolve-openclaw.sh` once per process. Build commands as argument lists and never use `shell=True`. The active OpenClaw CLI exposes gateway call parameters only through `--params <json>`; validate that payload contains references rather than raw credentials before invocation. Normalize failures into `GatewayUnavailable`, `GatewayRejected`, `StaleConfiguration`, or a redacted command error.

- [ ] **Step 4: Implement the offline subset.**

The normal offline adapter may modify only:

```json
{
  "models": {
    "providers": {
      "<provider-name>": {}
    }
  },
  "agents": {
    "list": [
      {
        "id": "<new-id>"
      }
    ]
  }
}
```

Use `fcntl.flock` where supported. If safe locking is unavailable, fail closed and require gateway access. Preserve original file mode, use a same-directory temporary file, fsync before replacement, and parse the replacement before committing. The normal transport must reject all other offline paths with `OfflineOperationNotAllowed`.

- [ ] **Step 5: Run focused tests.**

Run: `python -m pytest tests/test_oramaclaw_transport.py -q`
Expected: all tests pass.

- [ ] **Step 6: Commit.**

```bash
git add src/oramaclaw/transport.py tests/test_oramaclaw_transport.py
git commit -m "feat(oramaclaw): add gateway-first transport"
```

### Task 4: Compile Manifests Into Field-Aware Operations

**Files:**
- Create: `src/oramaclaw/manifest.py`
- Create: `src/oramaclaw/planner.py`
- Create: `tests/test_oramaclaw_planner.py`

**Interfaces:**
- Consumes: `ControlManifest`, registry base records from `ControlStore`, and observed OpenClaw state from `OpenClawTransport`.
- Produces: `compile_plan(manifest, registry, observed)->tuple[Operation, ...]`; each `Operation` carries base, observed, desired, managed paths, merge policy, transport, and preconditions.

- [ ] **Step 1: Write failing planner and merge tests.**

Cover:

1. Provider and binding compile before an agent that refers to them.
2. Agent creation compiles before delegation grants it to a parent.
3. Delegation compiles to `agents.defaults.subagents.allowAgents` or `agents.list[].subagents.allowAgents`.
4. Identical base and observed state with changed desired state produces one apply operation.
5. A changed observed cooperative field with unchanged desired intent produces an auto-weave candidate, not a write.
6. Differently changed observed and desired cooperative values become a promptable conflict.
7. A strict managed field requires explicit overwrite.
8. Delegation, credential, execution-policy, and agent existence changes remain conflicts.
9. Unmanaged existing state is `adoption_required`, even when values match.
10. Profile resource operations reference only marker-delimited generated content.
11. A resource from a different manager cannot claim a field already owned by another manager.
12. An unchanged manifest field uses its persisted effective-desired override, while an explicit source-field change clears that override before merge.

Use a representative manifest (planning-only fixture — paths need not exist on disk; use `tmp_path` when the planner is invoked from pytest):

```json
{
  "version": 1,
  "target": {
    "workspace_root": "/work/openclaw",
    "config_path": "/work/openclaw/openclaw.json",
    "state_dir": "/work/openclaw"
  },
  "resources": [
    {
      "kind": "provider",
      "id": "codex-app-server",
      "base_url": "http://127.0.0.1:8080/v1",
      "model": "gpt-5.5",
      "effort": "medium",
      "auth_reference": "~/.codex"
    },
    {
      "kind": "agent",
      "id": "codex-openclaw-agent",
      "provider": "codex-app-server"
    },
    {
      "kind": "delegation",
      "parent_agent": "orchestrator",
      "allow_agent": "codex-openclaw-agent"
    }
  ]
}
```

- [ ] **Step 2: Run focused test to verify failure.**

Run: `python -m pytest tests/test_oramaclaw_planner.py -q`
Expected: import failure for manifest and planner modules.

- [ ] **Step 3: Implement strict parsing and deterministic planning.**

Each operation contains the merged resource context:

```python
@dataclass(frozen=True)
class Operation:
    resource_key: str
    manager: str
    managed_paths: tuple[str, ...]
    base: Mapping[str, Any] | None
    observed: Mapping[str, Any] | None
    source_desired: Mapping[str, Any]
    effective_desired: Mapping[str, Any]
    policy: MergePolicy
    security_topology: bool
    transport: Literal["gateway", "offline", "profile"]
    preconditions: tuple[str, ...]
```

Use canonical JSON fingerprints for resource and field comparisons. Identical manifest plus observed state must produce the same operation order and fingerprints.

- [ ] **Step 4: Implement three-way merge policy.**

For every managed path, compare base, observed, and effective desired. Compute effective desired by applying only the current manager's valid override whose source-field fingerprint still matches the source manifest. Preserve all unmanaged paths and reject cross-manager claims. Implement these outcomes:

| Condition | Policy | Outcome |
| --- | --- | --- |
| Observed equals base; desired changed | any | apply desired |
| Observed changed; source desired equals base | cooperative | persist an effective-desired override after schema validation; do not write |
| Observed changed; desired equals base | strict | pending resolution |
| Observed and desired changed differently | cooperative | pending resolution |
| Security topology differs from base | conflict | pending resolution |
| Observed fails schema | any | unresolved validation conflict |

The planner must reject any manifest that attempts to downgrade a security-topology resource to a cooperative or strict policy.

- [ ] **Step 5: Order resources.**

Order operations as:

1. Provider registration and Codex backend binding.
2. Profile preparation.
3. Agent creation.
4. Non-security agent update where OpenClaw supports it.
5. Delegation and execution-policy operations.
6. Profile finalization.
7. Ledger update only after verification.

- [ ] **Step 6: Run focused tests.**

Run: `python -m pytest tests/test_oramaclaw_planner.py -q`
Expected: all tests pass.

- [ ] **Step 7: Commit.**

```bash
git add src/oramaclaw/manifest.py src/oramaclaw/planner.py tests/test_oramaclaw_planner.py
git commit -m "feat(oramaclaw): plan field-aware three-way merges"
```

### Task 5: Build Reconciliation, Interaction, And Verification

**Files:**
- Create: `src/oramaclaw/engine.py`
- Create: `src/oramaclaw/interaction.py`
- Create: `tests/test_oramaclaw_engine.py`

**Interfaces:**
- Consumes: `compile_plan()` operations, `ControlStore`, `OpenClawTransport`, injected clock and sleeper, and an `Interaction` adapter.
- Produces: `ControlEngine.apply_manifest(manifest, interaction)->ControlResult`, durable pending-resolution records, and verified registry updates.

- [ ] **Step 1: Write failing engine tests with injected time and interaction.**

Test:

1. A clean managed provider applies through gateway and updates ledger base only after verification.
2. A stale `baseHash` causes one fresh read and replan.
3. A second stale result becomes a conflict and cannot create an unbounded retry loop.
4. Normal cooperative drift prompts for 90 seconds, then auto-weaves only a valid non-security observed field.
5. Auto-weave invokes no write transport and emits a durable alert.
6. `apply-desired` revalidates fresh state before write.
7. Delegation, policy, credentials, and agent existence drift remain unresolved after timeout.
8. Non-interactive callers return a structured `needs_input` result without waiting or reading stdin.
9. The target lock serializes concurrent applies.
10. Failed transactions do not mark resources managed.
11. Profile merge changes only the unique generated section.
12. Missing, reversed, or duplicate markers become conflicts.
13. Restart recovery promotes an `applied_unverified` transaction only when re-read live state matches every desired managed path.
14. Auto-weave persists an effective-desired override, and an explicit later manifest change clears that override before it can suppress the new desired value.

```python
def test_timeout_auto_weaves_live_value_without_overwrite(engine) -> None:
    result = engine.apply_manifest(
        provider_manifest_with_medium_effort(),
        interaction=NoResponseInteraction(),
    )

    assert result.applied == ()
    assert result.auto_woven == ("provider:codex-app-server:/effort",)
    assert engine.transport.config_writes == []
```

- [ ] **Step 2: Run focused test to verify failure.**

Run: `python -m pytest tests/test_oramaclaw_engine.py -q`
Expected: import failure for `oramaclaw.engine`.

- [ ] **Step 3: Implement interaction adapters.**

```python
class Interaction(Protocol):
    def choose(
        self,
        prompt: str,
        choices: tuple[str, ...],
        timeout_seconds: int,
        resolution_id: str,
    ) -> str | None: ...
```

Implement `TerminalInteraction` for TTY sessions, `DesktopInteraction` as an interrupt or AskUserQuestion seam, `PortalInteraction` backed by persisted pending resolutions, and `NoInteraction` for automation.

Normal drift choices are `apply-desired`, `keep-current`, and `show-diff`. Unmanaged resources add `adopt`. Security topology exposes explicit choices but never a timeout default that writes or adopts.

- [ ] **Step 4: Implement state machine.**

```text
planned -> prepared -> validating -> applying -> applied_unverified -> verifying -> committed
                         \-> auto_woven
                         \-> conflicted
                         \-> failed
```

Rules:

1. Acquire target lock before reading live state.
2. Compute operations from base, observed, desired.
3. Use gateway transport unless offline subset is explicitly selected and valid.
4. On first stale hash, re-read, replan, and retry once.
5. On second stale hash, record conflict.
6. Write `prepared` before a gateway or offline mutation and `applied_unverified` immediately after the mutation returns. On startup and status, recover either state by re-reading live managed paths before changing the ownership ledger.
7. On normal cooperative timeout, preserve observed OpenClaw state and update only the manager-scoped effective-desired override for safe schema-valid fields. Mark `auto_woven`.
8. On strict timeout or any security timeout, preserve observed state and leave unresolved conflict.
9. Verify every write by re-reading and comparing managed-path fingerprints before recording success.
10. Never recursively retry RPC failures, invalid output, validation failures, or lock failures.

- [ ] **Step 5: Implement marked profile merge.**

Use exactly one pair of markers:

```markdown
<!-- oramaclaw:generated:start -->
<!-- oramaclaw:generated:end -->
```

Replace only content between that pair. Preserve every byte outside it. Atomic write and mode preservation are required. A profile with no markers requires explicit initialization or adoption; it is not overwritten automatically.

- [ ] **Step 6: Run focused tests.**

Run: `python -m pytest tests/test_oramaclaw_engine.py -q`
Expected: all tests pass.

- [ ] **Step 7: Commit.**

```bash
git add src/oramaclaw/engine.py src/oramaclaw/interaction.py tests/test_oramaclaw_engine.py
git commit -m "feat(oramaclaw): reconcile and verify managed resources"
```

### Task 6: Expose The CLI And Deterministic Vendor Synchronization

**Files:**
- Create: `src/oramaclaw/cli.py`
- Create: `src/oramaclaw/__main__.py`
- Create: `scripts/git/sync-oramaclaw-vendor.sh`
- Create: `scripts/git/verify-oramaclaw-vendor.sh`
- Create: `tests/test_oramaclaw_cli.py`
- Modify: `pyproject.toml`
- Create: `../perplexity-api/Perpetua-Tools/oramaclaw/` generated mirror
- Modify: `../perplexity-api/Perpetua-Tools/pyproject.toml`
- Create: `../perplexity-api/Perpetua-Tools/tests/test_oramaclaw_vendor.py`

**Interfaces:**
- Consumes: `ControlEngine`, manifest and target parsing, and canonical `src/oramaclaw/` source.
- Produces: `oramaclaw.cli:main`, stable JSON CLI results and exit codes, plus `sync-oramaclaw-vendor.sh` and `verify-oramaclaw-vendor.sh`.

- [ ] **Step 1: Write failing CLI tests.**

Verify:

1. `oramaclaw plan --manifest manifest.json` is deterministic and makes no write.
2. `oramaclaw apply` selects gateway transport by default.
3. `oramaclaw apply --offline` rejects a delegation fixture with a stable nonzero result.
4. `oramaclaw adopt provider:codex-app-server` records explicit ownership only.
5. `oramaclaw status` exposes managed resources, pending conflicts, and redacted transaction summaries.
6. `oramaclaw resolve` accepts only valid pending-resolution actions.
7. `oramaclaw vendor verify` fails on a changed header or body.
8. `unsafe-direct-config` requires explicit acknowledgement.
9. `oramaclaw target register` resolves and persists a named target, while duplicate names and unsafe arbitrary portal paths are rejected.
10. Break-glass mode creates a backup, validates the candidate and active config, and records an unsafe audit entry.

- [ ] **Step 2: Implement the standard-library CLI.**

Commands:

```text
oramaclaw plan --manifest <path> [target flags] [--json]
oramaclaw apply --manifest <path> [--offline] [--interaction auto|terminal|desktop|portal|none] [--json]
oramaclaw adopt <kind:id> --manifest <path> [target flags]
oramaclaw target register <name> [target flags]
oramaclaw target list [--json]
oramaclaw target remove <name>
oramaclaw status [target flags] [--json]
oramaclaw resolve <resolution-id> --choice apply-desired|keep-current
oramaclaw vendor sync <perpetua-tools-root>
oramaclaw vendor verify <perpetua-tools-root>
oramaclaw unsafe-direct-config --patch <path> --i-understand-this-bypasses-gateway-validation
```

Target flags are `--workspace-root`, `--config-path`, `--state-dir`, and legacy `--openclaw-home`.

`unsafe-direct-config` must write a mode-preserving timestamped backup beside the active configuration, validate the candidate JSON against the schema emitted by `openclaw config schema`, replace atomically only after a target-lock hash recheck, run `openclaw config validate` against the active configuration, and append an unsafe audit event. It must return code 5 without replacement if candidate validation or the pre-replace hash recheck fails.

Exit codes:

| Code | Meaning |
| --- | --- |
| 0 | Successful plan, apply, status, adoption, or resolution |
| 2 | Invalid CLI or manifest input |
| 3 | Gateway unavailable and offline path is invalid |
| 4 | Unresolved conflict or `needs_input` |
| 5 | Mutation, verification, or transport failure |
| 6 | Unsafe acknowledgement missing |

<!-- P1-1 FIX (2026-06-20): Steps 3 and 4 were inverted in the original plan — the PT
pyproject.toml was modified before the vendor mirror existed. Swapped so vendor sync
runs first, then entry points are registered in both repos. -->

- [ ] **Step 3: Implement vendor sync.**

`sync-oramaclaw-vendor.sh` must:

1. Resolve Orama System root from its own path.
2. Require the Perpetua-Tools checkout path, or use `PERPETUA_TOOLS_ROOT`.
3. Copy only `src/oramaclaw/` into `<perpetua-tools-root>/oramaclaw/`.
4. Add these headers to every generated Python file:

```text
# GENERATED FROM: src/oramaclaw/<relative-path>
# SOURCE REVISION: <git revision>
# SOURCE TREE HASH: <sha256>
# DO NOT EDIT: run scripts/git/sync-oramaclaw-vendor.sh
```

5. Generate in a sibling temporary directory.
6. Validate the generated tree, then replace only `<perpetua-tools-root>/oramaclaw/`.
7. Invoke the verifier after sync.
8. Never delete outside the generated vendor root.

`verify-oramaclaw-vendor.sh` must recompute the source tree hash, validate each header, strip generated headers before comparing source body, and issue file-specific failures for additions, deletions, stale headers, or content drift.

Run the sync before touching PT's `pyproject.toml` so the mirror exists when PT's package discovery is configured.

- [ ] **Step 4: Register entry points.**

Run vendor sync (Step 3) first. Then add to orama-system `pyproject.toml`:

```toml
[project.scripts]
oramaclaw = "oramaclaw.cli:main"
```

Then add to Perpetua-Tools `pyproject.toml` — the mirror at `<perpetua-tools-root>/oramaclaw/` now exists:

```toml
[project.scripts]
oramaclaw = "oramaclaw.cli:main"
```

Include `oramaclaw*` in Perpetua-Tools package discovery.

- [ ] **Step 5: Add mirror tests.**

Perpetua-Tools tests must import `oramaclaw`, assert its source marker identifies the canonical Orama path, and run the verifier when a sibling Orama checkout is available. In isolated package builds, validate import and headers only.

- [ ] **Step 6: Run focused checks.**

```bash
python -m pytest tests/test_oramaclaw_cli.py -q
scripts/git/sync-oramaclaw-vendor.sh ../perplexity-api/Perpetua-Tools
scripts/git/verify-oramaclaw-vendor.sh ../perplexity-api/Perpetua-Tools
cd ../perplexity-api/Perpetua-Tools && python -m pytest tests/test_oramaclaw_vendor.py -q
```

Expected: test suites pass and source-tree hash is identical in both repositories.

- [ ] **Step 7: Commit in dependency order.**

```bash
git add pyproject.toml src/oramaclaw scripts/git tests/test_oramaclaw_cli.py
git commit -m "feat(oramaclaw): add CLI and vendor synchronization"

git -C ../perplexity-api/Perpetua-Tools add pyproject.toml oramaclaw tests/test_oramaclaw_vendor.py
git -C ../perplexity-api/Perpetua-Tools commit -m "feat(oramaclaw): vendor control plane package"
```

### Task 7: Migrate Existing Managed Writers

**Files:**
- Modify: `bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/scripts/bind_codex_backend.sh`
- Modify: `bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/references/codex-backend-binding.md`
- Modify: `bin/orama-system/skills/openclaw-skills/openclaw-new-agent/SKILL.md`
- Modify: `scripts/openclaw_bootstrap.py`
- Modify: `src/utils/ip_resolver.py`
- Modify: `../perplexity-api/Perpetua-Tools/src/perpetua_tools/alphaclaw_bootstrap.py`
- Modify: `../perplexity-api/Perpetua-Tools/orchestrator/alphaclaw_manager.py`
- Add focused tests for each migrated behavior

**Interfaces:**
- Consumes: the Task 6 CLI or package API and existing writer inputs.
- Produces: manifest producers that route managed writes through `ControlEngine`; AlphaClaw retains only lifecycle discovery and start/reuse responsibilities.

- [ ] **Step 1: Record writer-to-resource mapping before edits.**

Include this table in the implementation PR description:

| Existing writer | Manager | Current mutation | Replacement |
| --- | --- | --- | --- |
| Codex `bind_codex_backend.sh` | `codex-binder` | `jq` plus temp-file replacement | Build manifest and invoke `oramaclaw apply` |
| `openclaw-new-agent` skill | `openclaw-agent-workflow` | Direct configuration instructions | Build manifest and corrected delegation resource |
| Orama bootstrap | `orama-bootstrap` | Direct JSON mutation | Package API and manifest |
| Orama IP resolver | `orama-resolver` | Direct JSON mutation | Provider or policy resource |
| PT AlphaClaw bootstrap | `pt-bootstrap` | Direct JSON mutation | Compatibility wrapper around package API |
| PT AlphaClaw manager | `pt-lifecycle` | Lifecycle plus bootstrap handoff | Retain lifecycle only; delegate configuration ownership |

If a writer cannot be mapped to a resource without inventing semantics, leave it unchanged, list it as un-migrated, and create a specific follow-up. Do not route unknown changes through unsafe mode.

- [ ] **Step 2: Correct the binding doctrine.**

Replace the blanket instruction “Do not hand-edit openclaw.json; use openclaw config patch --file” with:

1. Gateway RPC plus `baseHash` is the normal control-plane mutation path.
2. Offline provider and new-agent writes are allowed only through the locked control-plane adapter.
3. `openclaw config patch --file` remains a reviewed operator fallback for manually approved whole-document changes; arrays replace, so it is not the delegation-management path.
4. Direct `jq` writing is removed from managed binder flows.
5. `oramaclaw unsafe-direct-config` is the sole direct emergency path and requires acknowledgement.
6. Delegation always uses `agents.defaults.subagents.allowAgents` or `agents.list[].subagents.allowAgents`.

The Codex binding resolver becomes a manifest producer: native plugin first, idempotent plugin install when allowed, local app-server compatibility fallback, then backend verification. `CODEX.md` records metadata only in its generated marker region and never copies bearer tokens.

- [ ] **Step 3: Add migration contract tests.**

Test:

1. Native plugin path yields `gpt-5.5` and `medium`.
2. Missing but installable plugin invokes one idempotent installation attempt.
3. Unavailable plugin creates app-server compatibility provider with a path-based auth reference.
4. `--effort high` and `--effort xhigh` are explicit overrides.
5. Parent delegation plans to `agents.defaults.subagents.allowAgents` or `agents.list[].subagents.allowAgents`.
6. AlphaClaw absence does not prevent plan, apply, or status.
7. Migrated writers contain no normal-flow `jq` write of `openclaw.json`.

- [ ] **Step 4: Run migration-focused tests.**

```bash
python -m pytest tests -k "oramaclaw or codex_backend or openclaw_bootstrap" -q
cd ../perplexity-api/Perpetua-Tools && python -m pytest -k "oramaclaw or alphaclaw_bootstrap" -q
```

- [ ] **Step 5: Commit separately.**

```bash
git add bin/orama-system/skills/openclaw-skills/codex-openclaw-agent \
  bin/orama-system/skills/openclaw-skills/openclaw-new-agent \
  scripts/openclaw_bootstrap.py src/utils/ip_resolver.py tests
git commit -m "refactor(openclaw): route writers through oramaclaw"

git -C ../perplexity-api/Perpetua-Tools add src/perpetua_tools/alphaclaw_bootstrap.py \
  orchestrator/alphaclaw_manager.py tests
git -C ../perplexity-api/Perpetua-Tools commit -m "refactor(openclaw): delegate bootstrap to oramaclaw"
```

### Task 8: Add Orama Portal Status And Resolution Flows

**Files:**
- Modify: `src/orama_system/portal_server.py`
- Modify: `web/src/api/client.ts`
- Modify: `web/src/components/NavLeft.tsx`
- Create: `web/src/features/oramaclaw/ControlPlane.tsx`
- Create: `web/src/features/oramaclaw/controlPlaneApi.ts`
- Create: `tests/test_oramaclaw_portal.py`
- Validate the frontend with existing `typecheck`, `lint`, and `build` scripts; do not introduce a frontend test runner in V1

**Interfaces:**
- Consumes: registered target ids, redacted `ControlResult` values, and pending resolutions from `ControlStore`.
- Produces: authenticated status, plan, apply, and resolve portal endpoints plus a Control Plane view that invokes only those endpoints.

- [ ] **Step 1: Write failing authenticated API tests.**

Test:

1. `GET /api/oramaclaw/status` returns registered target metadata, managed-resource summaries, pending conflicts, and redacted transaction data.
2. `POST /api/oramaclaw/plan` returns a deterministic no-write plan.
3. `POST /api/oramaclaw/apply` starts a portal-backed transaction and returns its id.
4. `POST /api/oramaclaw/conflicts/<id>/resolve` accepts only valid choices.
5. Unauthenticated routes follow current portal authorization behavior.
6. API payloads and errors contain no credentials.
7. Browser inputs cannot choose arbitrary host paths; they select only registered server targets.
8. Apply returns HTTP 202 and a transaction id without holding the request open for the 90-second interaction window.
9. A status request performs incomplete-transaction recovery before returning resource state.

- [ ] **Step 2: Implement narrow portal endpoints.**

Reuse portal authentication and error envelope. Bound manifest payload size. Keep target path fields server-owned; browser clients pass a registered target id, manifest input or id, and a resolution action. Start apply through the portal's existing executor pattern and return HTTP 202 with the durable transaction id; `PortalInteraction` waits in that worker, never in the request handler.

Response shape:

```json
{
  "transaction_id": "tx_...",
  "state": "conflicted",
  "applied": ["provider:codex-app-server"],
  "auto_woven": [],
  "conflicts": [
    {
      "id": "conflict_...",
      "resource": "delegation:orchestrator",
      "security_topology": true,
      "choices": ["apply-desired", "keep-current", "show-diff"]
    }
  ],
  "warnings": []
}
```

- [ ] **Step 3: Implement Control Plane page.**

Add a `Control Plane` navigation entry and unresolved-conflict badge. The view requires:

- Registered target selector.
- Resource table with ownership, current state, and last transaction result.
- Plan and Apply actions.
- Pending-resolution panel showing redacted base, observed, and desired difference.
- Explicit Apply Desired and Keep Current actions.
- Transaction history with redacted errors.
- Visual distinction among normal drift, auto-woven drift, and security topology conflicts.
- Loading, empty, forbidden, and failed request states.

Reuse the existing portal shell and API helper. Do not create a second authentication model or a separate landing page.

- [ ] **Step 4: Run focused portal validation.**

The current portal package has no frontend test runner. Lock browser-facing contracts through authenticated API tests and validate the TypeScript view with the established frontend scripts:

```bash
python -m pytest tests/test_oramaclaw_portal.py tests/test_control_plane_auth.py -q
cd web && npm run typecheck
cd web && npm run lint
cd web && npm run build
```

- [ ] **Step 5: Commit.**

```bash
git add src/orama_system/portal_server.py web tests/test_oramaclaw_portal.py
git commit -m "feat(portal): add Oramaclaw control plane operations"
```

### Task 9: Publish Canonical Documentation And V2 Boundary

**Files:**
- Create: `docs/v2/40-oramaclaw-control-plane.md`
- Modify: `docs/v2/README.md`
- Modify: `docs/superpowers/specs/2026-06-19-codex-openclaw-agent-re-design-v2.md`
- Modify: `bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/SKILL.md`

**Interfaces:**
- Consumes: stable V1 manifest, CLI, profile-marker, and vendor contracts from Tasks 1-8.
- Produces: canonical operator documentation, V2 index entry, and Codex-skill references that describe the control plane as the sole routine writer.

- [ ] **Step 1: Document V1 operations.**

Document:

1. Resource and target contract.
2. Manager-scoped field-level ownership ledger, effective-desired overrides, and base/observed/desired merge.
3. Strict, cooperative, and conflict policy semantics.
4. 90-second behavior: safe normal-field auto-weave preserves observed state and carries forward effective desired intent; no unattended overwrite.
5. Security topology conflict-only rule.
6. Gateway `baseHash` transport, one replan retry, and offline limitations.
7. CLI commands, exit codes, and `needs_input` mode.
8. Credential redaction and auth-by-reference.
9. Generated profile marker handling.
10. Vendor sync and verifier operations.
11. AlphaClaw as optional lifecycle adapter.
12. V2 migration toward Perpetua-core without V1 dependency.
13. Target registration and the incomplete-transaction recovery protocol.

Provide an authoritative verification table with retrieval date and these sources:

- Kubernetes Server-Side Apply: https://kubernetes.io/docs/reference/using-api/server-side-apply/
- Kubernetes Controllers: https://kubernetes.io/docs/concepts/architecture/controller/
- Argo CD resource tracking: https://argo-cd.readthedocs.io/en/latest/user-guide/resource_tracking/
- OpenTofu state: https://opentofu.org/docs/v1.9/language/state/
- OpenTofu state locking: https://opentofu.org/docs/language/state/locking/
- Pragmatic Git three-way merge: https://blog.git-init.com/the-magic-of-3-way-merge/

Use these as design evidence, not as a claim that OpenClaw implements their protocol.

- [ ] **Step 2: Update Codex-agent documentation.**

Point the Codex-agent redesign and `SKILL.md` at the control-plane document. State that `CODEX.md` is a generated profile record and its marker-delimited block is owned by `oramaclaw`. The skill is a manifest producer and no longer a direct OpenClaw configuration writer.

- [ ] **Step 3: Update V2 index.**

Add document 40 to `docs/v2/README.md` without renumbering existing documents.

- [ ] **Step 4: Run documentation hygiene checks.**

```bash
rg -n '/Users/|T[O]DO|T[B]D|implement[ ]later|fill[ ]in[ ]details' docs/v2/40-oramaclaw-control-plane.md
git diff --check
python3 scripts/review/repo_hygiene.py .
```

Expected: no absolute local paths, placeholders, whitespace errors, or repository-hygiene violations.

- [ ] **Step 5: Commit.**

```bash
git add docs/v2 docs/superpowers/specs \
  bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/SKILL.md
git commit -m "docs(oramaclaw): define transaction model and v2 path"
```

### Task 10: Run Acceptance Gates And Inspect Scope

**Files:**
- Modify tests only if an acceptance gate exposes a missing required contract.
- Do not add unrelated production changes in this task.

**Interfaces:**
- Consumes: all source, mirror, CLI, portal, skill, and documentation deliverables from Tasks 1-9.
- Produces: current-state acceptance evidence and scoped commit review; it makes no product behavior change without a failing gate that proves one is required.

- [ ] **Step 1: Verify source and generated-mirror parity.**

```bash
scripts/git/sync-oramaclaw-vendor.sh ../perplexity-api/Perpetua-Tools
scripts/git/verify-oramaclaw-vendor.sh ../perplexity-api/Perpetua-Tools
git status --short
git -C ../perplexity-api/Perpetua-Tools status --short
```

Expected: matching tree hash and only intentional generated-mirror changes before the Perpetua-Tools commit.

- [ ] **Step 2: Run focused package suites.**

```bash
python -m pytest tests/test_oramaclaw_target.py \
  tests/test_oramaclaw_schema.py \
  tests/test_oramaclaw_store.py \
  tests/test_oramaclaw_transport.py \
  tests/test_oramaclaw_planner.py \
  tests/test_oramaclaw_engine.py \
  tests/test_oramaclaw_cli.py \
  tests/test_oramaclaw_portal.py -q
cd ../perplexity-api/Perpetua-Tools && python -m pytest tests/test_oramaclaw_vendor.py -q
```

Expected: all suites pass.

- [ ] **Step 3: Run repository-standard validation.**

Discover current project commands, then run relevant existing test, build, lint, or typecheck commands:

```bash
rg -n '"(test|lint|typecheck|build)"' pyproject.toml package.json web/package.json
python3 scripts/review/repo_hygiene.py .
git diff --check
cd ../perplexity-api/Perpetua-Tools && git diff --check
```

Do not install packages or rewrite lockfiles just to satisfy an unavailable tool. Report the exact unavailable command and impact.

- [ ] **Step 4: Run disposable integration smoke tests.**

Never test against the operator’s live OpenClaw configuration:

```bash
tmpdir="$(mktemp -d)"
mkdir -p "$tmpdir/workspace"
printf '%s\n' '{"models":{"providers":{}},"agents":{"list":[]}}' > "$tmpdir/openclaw.json"

oramaclaw plan --manifest tests/fixtures/oramaclaw-codex-provider.json \
  --workspace-root "$tmpdir/workspace" \
  --config-path "$tmpdir/openclaw.json" \
  --state-dir "$tmpdir" --json
oramaclaw apply --manifest tests/fixtures/oramaclaw-codex-provider.json \
  --workspace-root "$tmpdir/workspace" \
  --config-path "$tmpdir/openclaw.json" \
  --state-dir "$tmpdir" --offline --json
oramaclaw status \
  --workspace-root "$tmpdir/workspace" \
  --config-path "$tmpdir/openclaw.json" \
  --state-dir "$tmpdir" --json
```

Expected:

- Plan reports a provider with `medium` effort.
- Offline provider apply succeeds and status shows it managed.
- Journal and status contain no raw credentials.
- Offline delegation fixture exits with documented rejection and leaves configuration unchanged.
- Gateway fixture proves `baseHash` is present.
- Stale gateway fixture proves only one replan retry.
- Cooperative drift fixture proves timeout preserves live configuration and records `auto_woven`.
- Explicit manifest change after auto-weave clears the corresponding effective-desired override and plans that new value.
- Security topology fixture proves timeout leaves an unresolved conflict.
- Restart-recovery fixture proves an `applied_unverified` transaction commits only after a live fingerprint match; otherwise it remains conflict.

- [ ] **Step 5: Inspect final commit scope.**

```bash
git status --short
git diff --check
git -C ../perplexity-api/Perpetua-Tools status --short
git -C ../perplexity-api/Perpetua-Tools diff --check
```

Commit only scoped control-plane source, tests, generated mirror, skill integration, portal, and documentation. Leave unrelated Perpetua-Tools changes and `cc-openclaw` submodule state unstaged.

## Generated Profile Contract

```markdown
# Codex OpenClaw Profile

Operator-authored instructions remain outside this region.

<!-- oramaclaw:generated:start -->
binding_provider: codex-app-server
model: gpt-5.5
effort: medium
source_path: bin/orama-system/skills/openclaw-skills/codex-openclaw-agent
source_hash: sha256:...
verified_at: 2026-06-20T00:00:00Z
<!-- oramaclaw:generated:end -->
```

The generated block may contain provider metadata, model, effort, source path, source hash, verification timestamp, and an auth *path reference*. It must never include bearer tokens, API keys, cookies, or authorization headers.

## Final Review Checklist

- [ ] Orama System works without Perpetua-Tools, AlphaClaw, or Perpetua-core installed.
- [ ] Perpetua-Tools imports generated `oramaclaw` code and verifier reports exact parity.
- [ ] Normal configuration writes use Gateway RPC with `baseHash` unless in the restricted offline subset.
- [ ] Stale-state retry happens once only.
- [ ] Ledger stores field-level base state and redacted transaction history.
- [ ] A manager cannot claim, adopt, auto-weave, or overwrite a field owned by another manager.
- [ ] Existing state is never silently adopted.
- [ ] Cooperative timeout preserves observed state and auto-weaves only safe valid fields into an effective-desired override.
- [ ] Incomplete prepared or applied-unverified transactions recover through live-state verification.
- [ ] Security topology never auto-adopts, auto-weaves, or overwrites after timeout.
- [ ] Non-interactive callers never block for input.
- [ ] Migrated writers no longer make normal-flow `jq` edits to `openclaw.json`.
- [ ] Delegation never uses `agents.bindings.*.allowAgents`.
- [ ] Default Codex effort is `medium`, with `high` and `xhigh` opt-in.
- [ ] Generated profile merge preserves all content outside markers.
- [ ] Portal APIs use existing auth and expose neither credentials nor arbitrary local paths.
- [ ] Docs have no absolute local paths and retain verification links.
- [ ] Commits are scoped and unrelated drift is unstaged.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-20-oramaclaw-control-plane-v1.md`.

1. **Subagent-Driven Development (recommended):** dispatch a fresh subagent per task, review each task before proceeding, and run Task 10 only after migration and portal work land. This contains risk across two repositories and operational configuration code.
2. **Inline Execution:** execute Tasks 1-10 sequentially in this session, with the listed focused tests and commit gates after each task.
