---
name: whatsapp-qr-gateway
description: >-
  Explicit operational skill for inspecting and using the WhatsApp QR Gateway
  that controls OpenClaw services through QR authentication, health checks,
  command routing, queued tasks, status checks, and notifications.
when_to_use: >-
  Use when the user asks for WhatsApp control, QR gateway authentication,
  /whatsapp-qr-gateway, gateway health, WhatsApp command routing, service
  status, restart planning, task/status messages, OpenClaw notifications, or
  Portal/PT/orama control-plane checks from WhatsApp.
version: 1.1.0
argument-hint: "[check|qr|health|restart|task|status]"
arguments: [action]
effort: high
disable-model-invocation: true
context: fork
agent: Plan
allowed-tools: Read Grep Bash(curl *) Bash(ps *) Bash(grep *) Bash(tail *)
disallowed-tools: Bash(pkill *) Bash(kill *) Bash(launchctl *) Bash(npm publish *) Bash(pip upload *)
paths:
  - "bin/orama-system/skills/whatsapp-qr-gateway/**"
  - "docs/plans/*whatsapp*"
---

# WhatsApp QR Gateway

> Explicit-only operational skill. Re-verify runtime state before acting; do not
> infer that the gateway is live only because this file says it was live when
> written.

Use this skill to inspect, plan, and operate the WhatsApp QR Gateway for local
OpenClaw service control. `SKILL.md` is the orchestrator; load the references
below for full procedure details.

## Glossary

- **Gateway:** local WhatsApp QR/webhook service, usually checked at port `8555`.
- **Control Plane:** orama API surface that validates and routes commands.
- **PT:** Perpetua-Tools tier router for fallback execution.
- **Portal:** dashboard and real-time monitoring surface.
- **HITL:** human-in-the-loop approval before sensitive actions.

## Load Order

1. Read [`references/operations-runbook.md`](references/operations-runbook.md)
   for QR access, health checks, command examples, and notification patterns.
2. Read [`references/architecture-and-security.md`](references/architecture-and-security.md)
   for components, auth flow, fallback tiers, integration points, and gates.
3. Read [`references/troubleshooting-roadmap.md`](references/troubleshooting-roadmap.md)
   for limitations, troubleshooting, roadmap, lessons, and re-verification.

## When To Use

- The user asks to open or verify the WhatsApp QR gateway.
- The user asks how to send `health`, `restart`, `task`, or `status` commands via WhatsApp.
- The user asks to troubleshoot QR loading, webhook receipt, auth, timeout, or queue behavior.
- The user asks to plan Portal/PT/orama notification or command-routing integration.

## When Not To Use

- Do not edit AlphaClaw/OpenClaw source or fork from this skill; treat implementation paths as runtime references.
- Do not use for general WhatsApp Business API design unrelated to this gateway.
- Do not bypass HITL for restart, task dispatch, credential, token, or delivery actions.
- Do not print bearer tokens, QR payloads, webhook secrets, or session material.

## Workflow

1. Resolve `$ARGUMENTS` to one action: `check`, `qr`, `health`, `restart`, `task`, or `status`.
2. Load only the reference file needed for that action.
3. For read-only checks, prefer `curl`/`ps` verification before making claims.
4. For `restart` or `task`, stop for HITL approval and document the exact requested command.
5. Route sensitive operations through WhatsApp/gateway contracts, not direct local `pkill`/`launchctl` shell actions.
6. Re-check gateway health and report the observed result, uncertainty, and next safe action.

## Safety Rules

- Treat this as a side-effect skill: it must be explicitly invoked by the operator.
- Localhost endpoints are examples until verified in the current session.
- Restart, task submission, scheduled commands, and notification delivery require operator approval.
- Use `Authorization` headers or existing configured auth; never expose token values in chat or logs.
- Keep audit notes for sensitive operations: action, service, approver, timestamp, and result.

## Done Condition

Return:

```text
STATUS: DONE / BLOCKED / NEEDS_APPROVAL
Action: <check|qr|health|restart|task|status>
Verified: <commands or references checked>
Result: <observed gateway/service state>
Risk: <none|HITL required|blocked>
Next: <next safe action>
```
