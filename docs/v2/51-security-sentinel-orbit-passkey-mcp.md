# 51 — security-sentinel Orbit: Passkey + MCP Human Authorization

> **Status:** v2.1 plan (deferred from orama-system PR #255 MVP)  
> **Date:** 2026-08-02  
> **Repo target:** `github.com/oramasys/security-sentinel` (name TBD — **sentinel** in prose)  
> **MVP harness patch:** [`plans/2026-08-02-pr-body-grant-security-remediation.md`](../plans/2026-08-02-pr-body-grant-security-remediation.md)  
> **Research:** [`../../bin/orama-system/references/pr-body-human-grant-security-gap-research.md`](../../bin/orama-system/references/pr-body-human-grant-security-gap-research.md)  
> **Cross-refs:** [`42-agate-hardware-policy-orbit.md`](42-agate-hardware-policy-orbit.md), [`33-security-harness-source-material.md`](33-security-harness-source-material.md), [`31-security-harness-excellence-plan.md`](31-security-harness-excellence-plan.md)

---

## 1. Thesis — orbit clarity (mirror agate)

v1 grew PR-body enforcement inside **orama-system** harness scripts: Cursor hooks,
`pr-body-guard-core.py`, operator grant shell, append-only workflow. That was correct
for **incident response** (PT #314 clobber class) but **insufficient for authorization**:
TTY gates and local marker files are forgeable ([EXA/Firecrawl research 2026-08-02](../../bin/orama-system/references/pr-body-human-grant-security-gap-research.md)).

v2.1 spins **human authorization for high-impact agent actions** into an orbiting
**security-sentinel** satellite around **perpetua-core** — same pattern as
[agate hardware policy](42-agate-hardware-policy-orbit.md):

| Layer | Owner | Responsibility |
| --- | --- | --- |
| **Kernel** | `perpetua-core` | Tool dispatch, graph HITL nodes, plugin contract |
| **Sentinel** | `oramasys/security-sentinel` | Passkey verify, action-hash binding, JWKS proofs, MCP sidecar |
| **Harness adapters** | orama-system, Perpetua-Tools | Hook clients; deny by default; verify proofs at tool boundary |
| **MVP (PR #255)** | orama-system only | HMAC grant v2 — bridge until sentinel lands |

**Elegant invariant:** The agent runtime never holds the **human verification** key.
Sentinel issues **short-lived, audience-bound, hash-bound proofs**; tools reject
execution without valid proof ([GoodRoom.verify design](https://dev.to/goodroom/adding-passkey-backed-human-approval-to-high-risk-mcp-actions-38h)).

---

## 2. Problem classes (community-aligned)

| Class | Example | MVP (PR #255) | Sentinel (v2.1) |
| --- | --- | --- | --- |
| **Forgeable approval state** | Plaintext `~/.cursor/pr-body-human-override-ack` | HMAC v2 + repo/pr bind ([Vallum](https://github.com/kahramanemir/Vallum/pull/32)) | Ed25519 JWKS proof |
| **Misleading HITL UI** | Lies-in-the-loop ([OWASP](https://owasp.org/www-community/attacks/Lies_in_the_Loop)) | Honest docs; integrative merge discipline | Hash-bound summary vs execution ([hashgate](https://github.com/Seppelllo/hashgate)) |
| **Self-asserted bypass** | Agent writes ack / runs grant | TTY + env deny + HMAC | Passkey WebAuthn ([GoodRoom](https://dev.to/goodroom/adding-passkey-backed-human-approval-to-high-risk-mcp-actions-38h)) |
| **Tool path bypass** | `gh` outside guarded MCP | Shell hooks (orama) | Invariant proxy ([invariant](https://github.com/invariantlabs-ai/invariant)) optional |

---

## 3. Target sentinel repo (sketch)

```text
github.com/oramasys/security-sentinel/
├── SPEC.md                    # Proof format, audiences, TTL, hash canonicalization
├── schema/
│   ├── approval-proof.schema.json
│   └── action-descriptor.schema.json
├── sentinel/
│   ├── verify_mcp.py          # MCP sidecar: pause → poll → issue JWKS proof
│   ├── passkey_gateway.py     # WebAuthn ceremony (operator browser)
│   ├── proof.py               # Mint + verify Ed25519; action-hash bind
│   └── cli.py                 # Operator status / rotate keys
├── plugins/
│   └── perpetua_core.py       # Entry point: register HITL mediator with kernel
└── examples/
    └── pr-body-append-proof.json
```

**Integration surfaces:**

1. **MCP tool** `sentinel.verify` — agent calls with `summary`, `action_hash`, `audience`, `risk`
2. **Hook client** — orama `pr-body-guard-core.py` verifies proof instead of HMAC file (v3)
3. **perpetua-core plugin** — graph nodes call sentinel before irreversible transitions

---

## 4. Passkey + MCP flow (GoodRoom-derived)

Reference implementation pattern ([DEV post](https://dev.to/goodroom/adding-passkey-backed-human-approval-to-high-risk-mcp-actions-38h)):

1. Agent (or hook) requests approval with **human-readable summary** + **SHA-256 of canonical action**
2. Sentinel pauses; operator opens approval UI; **WebAuthn** user verification
3. Sentinel issues **short-lived Ed25519 proof** (JWKS); gateway verifies locally
4. **Protected tool** independently requires proof — approval UI alone is advisory

**PR-body append canonical action** (sentinel spec must define):

```text
canonical = json.dumps({
  "action": "pr_body_append_integrative",
  "repo": "owner/name",
  "pr_number": 255,
  "body_sha256": "<hash of merged integrative body file>"
}, sort_keys=True)
```

---

## 5. Optional: Invariant guardrail proxy

For MCP-native agents, route `ManagePullRequest` and `gh` mutations through
[Invariant Guardrails](https://github.com/invariantlabs-ai/invariant) with rules:

- Deny `update_pr` with `body` always
- Allow `post_comment` / `gh pr comment`
- Allow `append-pr-body.sh` only when `sentinel_proof_valid(action_hash)`

Sentinel remains **proof issuer**; Invariant remains **traffic cop** — separation of duties.

---

## 6. Migration ladder

| Stage | orama-system | sentinel |
| --- | --- | --- |
| **Now (PR #255 MVP)** | HMAC grant v2; honest docs | Doc only (this file) |
| **v2.1 alpha** | Hook verifies sentinel proof for PR-body | MCP sidecar + passkey UI |
| **v2.1 beta** | Remove HMAC Keychain path | perpetua-core plugin registration |
| **v2.2** | HumanLayer / external approval as alt issuer | Pluggable issuer registry |

---

## 7. Open questions (v2.1 design)

1. Sentinel repo name: `security-sentinel` vs `sentinel` vs `goodroom-compat`?
2. Host JWKS rotation and offline operator approval?
3. Single sentinel instance per machine vs fleet-wide approval service?
4. EU AI Act human oversight mapping — audit log retention in sentinel?

---

## 8. Sources (sentinel design)

- [GoodRoom passkey MCP approval](https://dev.to/goodroom/adding-passkey-backed-human-approval-to-high-risk-mcp-actions-38h)
- [Vallum HMAC approval](https://github.com/kahramanemir/Vallum/pull/32)
- [hashgate](https://github.com/Seppelllo/hashgate)
- [HumanLayer](https://github.com/humanlayer/humanlayer)
- [Invariant Guardrails](https://github.com/invariantlabs-ai/invariant)
- [OWASP AI Agent Security Cheat Sheet — HITL §4](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html)
- [Consent integrity arXiv 2606.02668](https://arxiv.org/html/2606.02668v1)
