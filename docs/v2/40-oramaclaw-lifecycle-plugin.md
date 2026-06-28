<!-- lint-ignore LINT-013 -->
# 40 - Oramaclaw Lifecycle Plugin (D22)

> **Status:** D22 locked on 2026-06-20. This is the V2 consolidation target. It does not claim that the complete control engine exists today.
>
> **Decision:** V2 makes `oramaclaw` the single OpenClaw and AlphaClaw control boundary. Its operator artifact is the user-level executable `orama-openclaw-control`. The package is an orbit plugin: it imports approved `perpetua-core` primitives one way, and the V2 kernel never imports it.

## Purpose

OpenClaw needs two capabilities that must work together but must not share
untracked whole-file writers:

1. **Lifecycle control:** discover Mac and Windows backends, select a mode,
   reuse or start a gateway, and report the resulting runtime.
2. **Configuration control:** reconcile declared providers, agents, delegation,
   profiles, and policies against live OpenClaw state without erasing resources
   owned by another tool.

Perpetua-Tools already provides the first capability. It does not provide the
second. Oramaclaw V2 absorbs both into one coherent boundary: lifecycle code
supplies facts and readiness; the control engine owns all routine configuration
mutation.

This is an **explanation** of why that boundary exists and a **reference** for
its deployment, contracts, and migration gates. It does not replace the V1
implementation plan at
`../superpowers/plans/2026-06-20-oramaclaw-control-plane-v1.md`.

## Why Consolidation Is Necessary

Today several independent writers can modify `openclaw.json`:

- PT AlphaClaw bootstrap creates a static provider and agent configuration.
- The Orama bootstrap compatibility shim can write a full PT-resolved
  configuration.
- The Orama IP resolver writes a discovered Windows provider endpoint.
- The Codex backend binder creates a Codex provider, agent, and delegation.
- The AlphaClaw HTTP routing surface accepts a whole routing configuration
  update.

Those writers are individually useful but do not share:

- a resource or field ownership registry;
- a common read, plan, write, and verify transaction;
- a conflict model for another writer's change;
- a durable record of the desired state they last applied;
- a single lock or optimistic concurrency token;
- a common portal and terminal resolution path.

The result is a last-writer-wins failure mode. A full configuration rewrite or
an independently locked JSON replacement can discard a provider, a Codex agent
relationship, a delegation allowlist, or a discovered endpoint added by another
component. `--force` makes the risk explicit: it can replace a whole
configuration but cannot know which fields another manager owns.

The V2 goal is not to discard lifecycle expertise. It is to stop lifecycle code
from silently becoming a second configuration control plane.

This is the same pattern `againtra-platform` established (see
`28-againtra-platform-requirements-alignment.md`): complex external-system
integrations that need kernel primitives but must not pollute the kernel live
as orbiting plugins, independently testable, shipped at their own pace.

## Current V1 Evidence

| Current component | Current behavior | Keep in V2 | Stop owning in V2 |
| --- | --- | --- | --- |
| `orchestrator/alphaclaw_manager.py::resolve_runtime()` in PT | Probes Mac and Windows backends, selects single, distributed, or offline mode, invokes bootstrap, and returns `RuntimePayload` for Orama. | Backend probes, mode selection, runtime payload contract. | Direct bootstrap-to-config ownership. |
| `src/perpetua_tools/alphaclaw_bootstrap.py::bootstrap_alphaclaw()` in PT | Probes candidate ports, reuses a running gateway, starts bare OpenClaw when possible, then falls back to installing and starting AlphaClaw. It creates workspaces and derives PT static provider and agent configuration. | Gateway discovery, reuse, startup, AlphaClaw fallback, workspace preparation. | `_write_openclaw_config()` and all whole-file replacement. |
| `scripts/openclaw_bootstrap.py` in Orama | Delegates to PT when present and otherwise writes a PT-resolved `openclaw.json` fallback. | Compatibility entry point during migration. | Inline full-document write path. |
| `src/utils/ip_resolver.py` in Orama | Discovers a Windows endpoint and writes it back to the OpenClaw provider table. | Endpoint observation. | Direct provider mutation. |
| `bind_codex_backend.sh` | Resolves Codex, creates provider and agent records, wires delegation, restarts, and verifies. | Probe ladder, binding evidence, backend identity canary. | Direct JSON replacement and its private lock. |
| AlphaClaw routing adapter | Accepts a whole routing configuration update. | Lifecycle-facing routing facts. | Whole-routing-config ownership. |

The migration preserves each source of knowledge. It routes each desired resource
through one control engine.

## Scope

| Area | Oramaclaw V2 owns | It does not own |
| --- | --- | --- |
| Lifecycle resolver | Consume device probes, select lifecycle actions, and report gateway readiness and runtime facts. | Hardware policy decision rules themselves. |
| Gateway bootstrap | Reuse a healthy gateway, start bare OpenClaw when available, and invoke AlphaClaw fallback when explicitly allowed. | OpenClaw and AlphaClaw binaries, or npm installation policy outside the requested action. |
| Control plane | Plan, apply, verify, recover, and audit provider, agent, delegation, profile, and execution-policy resources. | Arbitrary operator configuration outside declared managed paths. |
| Ownership | Track manager-scoped resource and field ownership, desired fingerprints, effective overrides, and conflicts. | Silent adoption of another manager's resources. |
| Interaction | Return stable JSON results; expose plan, diff, conflict, and resolution actions to CLI, desktop interrupts, and the Orama portal. | A second PT-specific UI. |
| Packaging | Publish a versioned independently installed user-level executable. | A required sibling checkout or AlphaClaw installation. |

### Non-goals

- Oramaclaw does not import AlphaClaw internals.
- Oramaclaw does not make Codex or another provider the global OpenClaw default.
- Oramaclaw does not copy API keys, OAuth data, bearer tokens, or gateway
  passwords into manifests, records, or generated profiles.
- Oramaclaw does not infer ownership from matching values.
- Oramaclaw does not overwrite security topology after timeout. Delegation,
  credentials, execution policy, and agent create/remove remain explicit
  conflicts.
- Oramaclaw does not manufacture a control tool on a fresh offline PT-only
  machine where the artifact is absent.

## V1 And V2 Boundary

V1 is the dogfood compatibility layer:

- Canonical source is `src/oramaclaw/` in Orama System.
- Perpetua-Tools receives synchronized vendored copies named `oramaclaw`.
- V1 imports no AlphaClaw lifecycle classes, PT runtime modules, Orama portal
  modules, or unreleased `perpetua-core` package.
- V1 exposes a stable manifest and result contract so callers do not depend on
  a repository path or implementation detail.
- Current branch progress is limited to V1 types, schema validation, fixtures,
  and binding/profile tooling. The registry, planner, engine, transport, CLI,
  portal routes, and vendor verifier are still delivery work.

V2 graduates the control plane into the independently released
`orama-openclaw-control` artifact. The V2 package remains named
`oramaclaw` and registers as an orbit plugin when the internal plugin API
is ready.

~~~
V1 now

Orama canonical source              PT synchronized vendor copy
src/oramaclaw/  ----------------->  oramaclaw/
  types + schema                       compatibility import surface
  planned engine                       no independent config writer


V2 target

PT lifecycle wrapper  ------------\
Orama portal and manifests --------+--> ~/.local/bin/orama-openclaw-control
Desktop or terminal --------------/              |
                                                  v
                                  versioned oramaclaw control engine
                                                  |
                                                  v
                                  OpenClaw gateway and adjacent state
~~~

## Package Structure

The V1 canonical source layout in `src/oramaclaw/`:

```
src/oramaclaw/
├── __init__.py      # nothing re-exported — callers use submodule paths
├── types.py         # frozen dataclasses (ControlManifest, ControlResult, ...)
├── schema.py        # parse_manifest() — structural + semantic validation
├── merge.py         # three-way SSA merge engine (Task 3 in V1 plan)
├── engine.py        # ControlEngine.apply_manifest() (Task 5 in V1 plan)
├── gateway.py       # OpenClawTransport implementation over HTTP
├── portal.py        # PortalInteraction + 90-second cooperative timer
└── cli.py           # oramaclaw plan|apply|resolve|status entry point
```

Dependency rule enforced by CI import-linter:

```
oramaclaw → perpetua_core   ✅  (M3: actual published primitives)
oramaclaw → oramasys        ❌  layering violation
oramaclaw → alphaclaw.*     ❌  only via OpenClawTransport Protocol
perpetua_core → oramaclaw   ❌  upward import forbidden
```

V1 uses compatibility adapters where V2 core primitives are not yet published.
The import-linter rule is the M3 gate, not a V1 requirement.

## The User-Level Artifact

The external contract is a neutral executable, not a fourth repository:

| Property | Value |
| --- | --- |
| Binary name | `orama-openclaw-control` |
| Package name | `oramaclaw` |
| Manifest and result | Stable JSON |
| State root | Adjacent to the active OpenClaw configuration |
| Installer ownership | Both Orama and PT installers may install the same verified release |

Resolution order:

1. `ORAMA_OPENCLAW_CONTROL_BIN`, when it names an executable absolute path.
2. `~/.local/bin/orama-openclaw-control`.
3. Structured `control_unavailable` result. No mutation occurs.

A successful installer lays out:

~~~
~/.local/lib/orama-openclaw-control/<version>/
~/.local/bin/orama-openclaw-control
~~~

The binary is a thin launcher to the versioned artifact. Installation is
idempotent: the same version and checksum makes no replacement; a different
version installs beside the old one before the launcher is switched.

This removes two accidental deployment requirements:

- PT can perform discovery and lifecycle work with no AlphaClaw process when a
  healthy OpenClaw gateway already exists.
- PT can submit desired resources with no sibling Orama checkout once the tool
  is installed.
- Orama can create manifests, show diffs, and use the portal with no PT
  checkout.

A fresh offline PT-only machine with no supplied artifact cannot safely create
the shared control tool. It returns `control_unavailable` before mutation.
Recreating the old direct writer in that condition would reintroduce the
configuration ownership problem this design removes.

## Lifecycle And Control Flow

~~~mermaid
flowchart TD
    probe["PT lifecycle probe: Mac and Windows backends"] --> mode["Select single, distributed, or offline mode"]
    mode --> gateway{"Healthy gateway available?"}
    gateway -- yes --> facts["Runtime facts"]
    gateway -- no --> start["Start OpenClaw"]
    start --> fallback{"OpenClaw ready?"}
    fallback -- yes --> facts
    fallback -- "no, allowed" --> alpha["Install or start AlphaClaw fallback"]
    alpha --> facts

    facts --> manifest["Desired resource manifest"]
    portal["Orama portal, desktop, or terminal"] --> manifest
    manifest --> control["orama-openclaw-control: plan, lock, read, merge, apply, verify"]
    control --> state["Managed state and transaction journal adjacent to OpenClaw config"]
    control --> openclaw["OpenClaw gateway"]
    control --> resolution["Structured result and pending conflict"]
    resolution --> portal
~~~

The lifecycle resolver returns facts. It does not write desired configuration
directly. The control engine accepts those facts only as input to declared
resources, such as a provider endpoint. It still enforces manager ownership,
schema validation, security-topology policy, and verification.

## Stable JSON Contracts

### Manifest

~~~
{
  "version": 1,
  "target": {
    "workspace_root": "/path/to/workspace",
    "config_path": "/path/to/openclaw.json",
    "state_dir": "/path/to/openclaw-state"
  },
  "resources": [
    {
      "kind": "provider",
      "id": "lmstudio-win",
      "manager": "pt-lifecycle",
      "policy": "cooperative",
      "managed_paths": ["/baseUrl"],
      "spec": {
        "baseUrl": "http://192.168.1.10:1234/v1",
        "authReference": "env:LMSTUDIO_API_KEY"
      }
    }
  ]
}
~~~

The manifest carries credential references, never credential values. Manager
names are stable identities such as `pt-lifecycle`, `pt-bootstrap`,
`orama-resolver`, `orama-bootstrap`, and `codex-binder`.

### Result

~~~
{
  "transaction_id": "tx_...",
  "state": "committed",
  "applied": ["provider:lmstudio-win"],
  "auto_woven": [],
  "conflicts": [],
  "warnings": []
}
~~~

States are `committed`, `auto_woven`, `conflicted`,
`needs_input`, `gateway_unavailable`, and `failed`.

A transaction writes `prepared` before mutation and
`applied_unverified` after it. Recovery re-reads live managed paths and
commits only an exact verified result. All other incomplete transactions remain
visible conflicts.

## Merge, Ownership, And Security Policy

For a manager-owned field, the engine compares:

~~~
base       = last verified desired value in managed state
observed   = live OpenClaw value read under lock
desired    = current manifest value
~~~

- Unmanaged fields are preserved.
- A changed cooperative, non-security observed field can be auto-woven only
  after validation and the interaction window. It becomes a manager-scoped
  effective desired override, not an uncontrolled full-document rewrite.
- An explicit later manifest change clears the matching override so deliberate
  operator intent wins.
- A different manager claiming an owned field produces a conflict.
- Delegation, credentials, execution policy, and agent create/remove are
  security topology. They never auto-adopt, auto-weave, or overwrite after
  timeout.
- Gateway mutation uses `config.get` plus `baseHash` guarded
  `config.apply` or `config.patch`. One stale-hash re-read and
  replan is allowed; a second stale response becomes conflict.
- Offline mutation is limited to provider registration and creation of an
  entirely new agent. It uses a shared target lock, atomic replacement, JSON
  validation, and no security-topology update.

This policy is the missing configuration boundary around the useful lifecycle
code.

## One-Way Core Imports

V1 uses compatibility contracts only. It must not import a local PT checkout or
an AlphaClaw implementation.

V2 replaces those compatibility contracts with actual published
`perpetua-core` primitives through one-way imports:

~~~
oramaclaw -> perpetua_core.audit        allowed
oramaclaw -> perpetua_core.state        allowed
oramaclaw -> perpetua_core.transport    allowed
oramaclaw -> perpetua_core.hardware     allowed

oramaclaw -> oramasys                   forbidden
oramaclaw -> alphaclaw                  forbidden
perpetua_core -> oramaclaw              forbidden
~~~

| V1 compatibility concern | V2 core primitive | Oramaclaw use |
| --- | --- | --- |
| Append-only transaction and audit records | `perpetua_core.audit` | Apply, recovery, and conflict events. |
| Durable managed state and pending resolution | `perpetua_core.state` | Resource registry, effective desired overrides, target catalog. |
| Retry, timeout, and request policy | `perpetua_core.transport` | Gateway calls and lifecycle health probes. |
| Device facts and hardware constraints | `perpetua_core.hardware` | Validate lifecycle-selected backends before proposing a resource. |

The concrete import module names are an implementation gate, not assumed current
repository paths. M3 cannot close until the published core exposes these stable
primitives and an import-linter rule proves the direction above.

## Migration Gates

### M0 - Inventory And Freeze Direct Writers

Inventory every writer in Orama, PT, and the AlphaClaw adapter. For each one,
record manager name, managed resource path, current lock behavior, and migration
owner.

Acceptance:

- No new routine `openclaw.json` writer lands outside Oramaclaw.
- Each writer has a manifest producer or an explicitly tracked exception.
- Existing direct writes retain tests until their migration gate is complete.

### M1 - V1 Control Plane Completion

Implement and verify the V1 registry, planner, engine, gateway transport, target
catalog, CLI, portal integration, and source/vendor synchronization described in
the V1 plan. **In progress** on `feat/openclaw-codex-app-server`: types,
schema, fixtures, and conftest helpers are complete; merge engine, ControlEngine,
transport, portal timer, CLI, and PT vendor sync remain.

Acceptance:

- A wheel contains `oramaclaw` and imports cleanly after installation.
- Provider and new-agent offline paths work under the shared target lock.
- Delegation and other security topology paths require the gateway and conflict
  rather than silently overwrite.
- Generated profiles merge only marked generated sections.
- A stale `baseHash` retries once and then conflicts.
- Vendor verification proves exact canonical-source parity.

### M2 - Independent Artifact

Publish `orama-openclaw-control` with the stable manifest and result
contract and both installers. PT becomes a lifecycle wrapper that resolves the
binary and submits desired resources. Orama becomes the canonical release,
document, and portal owner.

Acceptance:

- PT works with the binary and no sibling Orama checkout.
- Orama works with the binary and no PT checkout.
- Missing binary on an offline PT-only host returns `control_unavailable`
  and changes no configuration.
- The artifact installer validates version and checksum before switching the
  user-level launcher.

### M3 - Perpetua-Core And Orbit Registration

Replace V1 compatibility adapters with actual one-way `perpetua-core`
imports, then register `oramaclaw` through the V2 internal plugin API.

Acceptance:

- Import-linter rejects all upward, Oramasys, and AlphaClaw imports.
- Gateway control events are emitted through core audit primitives.
- The Orama portal consumes the stable result contract without importing PT
  lifecycle classes.
- The AlphaClaw MCP smoke-test delegates lifecycle pre-flight to Oramaclaw.
- A V2 session pre-flight runs with no AlphaClaw-specific code in the kernel.

## Operator Outcomes

| Operator need | Oramaclaw response |
| --- | --- |
| Which backend is available? | Lifecycle result with device facts and selected mode. |
| What will change? | Stable manifest plan and redacted diff. |
| Who owns this field? | Manager-scoped registry record. |
| Can this overwrite my live configuration? | Conflict or explicit resolution for managed and security paths. |
| Can PT run without AlphaClaw or Orama checkout? | Yes when the versioned user-level artifact is installed. |
| What happens on a fresh offline PT-only machine? | No mutation and structured artifact-unavailable result. |
| Where do I resolve a conflict? | Terminal, desktop interrupt, or Orama portal using the same result contract. |

## Relationship To Existing V2 Docs

| Doc | How this doc relates |
| --- | --- |
| `02-modules/alphaclaw-mcp-smoke-test.md` | Pre-flight contract stays there; implementation delegates to `oramaclaw.gateway.AlphaClawPreflight` at M3. |
| `10-v1-hacks-automation-orbit.md` | Pairing/Auth row ("Auth Handshake via L2 manager") is implemented by `oramaclaw.gateway` at M2. |
| `18-master-alignment-v2-migration-plan.md` | Step A ("re-target submodule to `oramasys/orama/plugins/`") is superseded; plugin lands at orbit tier, not as a submodule inside oramasys. |
| `25-autoresearcher-doctrine-and-againtra-flagship.md` | Oramaclaw follows the same dogfood-first orbit pattern as againtra-platform — bounded, independently testable, shipped before the public plugin API is finalized. |
| `28-againtra-platform-requirements-alignment.md` | Precedent for the orbit-plugin pattern this doc applies to OpenClaw and AlphaClaw lifecycle. |
| `README.md` | D22 in locked decisions; module roadmap row; spec tree entry `40-`. Next free slot: `41-`. |

## Environment Variables

Oramaclaw respects the following environment variables to customize discovery, state storage, and fallback behavior:

| Variable | Default | Purpose |
|----------|---------|---------|
| `$ORAMACLAW_TARGETS_PATH` | `~/.openclaw/oramaclaw-targets.json` | Path to the named-target catalog JSON file. Overrides the default catalog location. Surfaced in `oramaclaw targets list` and `--target` flag help. |
| `$ORAMACLAW_STATE_DIR` | `~/.openclaw/state/oramaclaw` | Base directory for registry, journal, pending-resolutions, and PID lock files. |
| `$OPENCLAW_HOME` | (none) | Legacy: deprecated workspace root. Triggers a migration warning; use explicit target fields instead. |

## Related Material

- [V1 control-plane implementation plan](../superpowers/plans/2026-06-20-oramaclaw-control-plane-v1.md)
- [Codex OpenClaw agent redesign](../superpowers/specs/2026-06-19-codex-openclaw-agent-re-design-v2.md)
- [AlphaClaw MCP smoke-test contract](02-modules/alphaclaw-mcp-smoke-test.md)
- [V2 plugin API](02-modules/plugin-api-public.md)
- [V2 security preconditions](23-security-preconditions.md)
- [V2 security-first platform](24-security-first-platform.md)
- [V2 decision index](README.md)
