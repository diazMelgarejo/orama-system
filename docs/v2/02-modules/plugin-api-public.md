# Module: Public Plugin API

> Status: stub — v2.1 target. Internal-only in v2.0 (D5).

## What it does

Promote `oramasys`'s FastAPI surface from an internal-only contract to a versioned,
documented, publicly callable Plugin API. Enables external frameworks (LangGraph,
CrewAI, AutoGen, custom agents) to use `perpetua-core` as their local hardware
router over REST.

## Why v2.1, not v2.0

- v2.0 FastAPI surface is consumed only by oramasys internally
- Until the kernel is stable, the API contract may change between builds
- v2.1 = stable kernel + OpenAPI spec + semver versioning → safe to expose

## v2.1 promotion steps

1. Add `openapi_tags` and `description` to FastAPI app for a polished OpenAPI schema
2. Publish OpenAPI spec to `oramasys/agate/` (the hardware policy spec repo) as a companion schema
3. Add versioning: `/v1/run`, `/v1/route`, `/v1/policy`
4. Set `X-API-Version` response header on every route
5. Bump `oramasys` to v2.1.0, cut first `oramasys/perpetua-core` PyPI release

## Endpoint contract (target)

```text
POST /v1/run          — invoke a named graph with PerpetuaState input
POST /v1/route        — resolve hardware routing without executing (dry-run)
GET  /v1/policy       — return current model_hardware_policy.yml as JSON
GET  /v1/health       — health + connected LM Studio endpoints status
```

## Authentication

> **2026-11-06 correction:** The earlier "Internal: none (LAN-local, trusted
> network)" guidance is superseded. LAN locality is not authentication, and
> authentication is not deferred until public exposure.

Internal and public control-plane surfaces must follow
[D16](../00-context-and-decisions.md#d16--security-first-platform-not-retrofit-hardening-2026-05-26),
the [security preconditions](../23-security-preconditions.md),
the [security-first platform requirements](../24-security-first-platform.md)
and [SECURITY.md](../../../SECURITY.md): loopback defaults, explicit LAN opt-in,
server-side authentication and capability checks for protected routes, with
auth-denial tests. Explicitly public routes follow the declared public capability;
they are not a blanket exemption for internal callers.

For v2, [ADR 62](../62-telos-phylax-authority-gate0-adr.md) assigns endpoint
security to Telos and principal/capability admission to Phylax. Hardware routing
belongs to Agate. The promotion steps and endpoint sketch above remain a
historical target, not an approved current API or evidence of implementation.
