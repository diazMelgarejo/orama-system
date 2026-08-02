# PR-body human grant — security gap research (TTY / HITL / consent integrity)

> **Status:** deep research complete (2026-08-02, EXA + Firecrawl); remediation **not** implemented here.
> **Trigger:** CodeRabbit review on orama-system PR #255
> ([review 4835288649](https://github.com/diazMelgarejo/orama-system/pull/255#pullrequestreview-4835288649))
> — replace `_human_override_active()` file-marker checks with a non-forgeable,
> host- or framework-provided capability.
> **Research method:** EXA neural search (6 queries, ~54 sources) → Firecrawl scrape
> of primary docs (15 URLs). Depth: **thorough** (~10–15 min collection pass).

---

## Executive summary

`grant-pr-body-human-override.sh` is **not** non-agent-executable. It is a normal
bash script whose TTY check blocks only the case where **both** stdin and stdout
are non-TTY. Cursor / Claude Code agent shells run with a real PTY, so the script
succeeds. Worse: `_human_override_active()` trusts a **plaintext marker file** the
agent can write without running the script at all.

TTY (`isatty`, `-t`) measures **terminal attachment**, not **human identity** —
a distinction the security community repeatedly documents ([StackOverflow on docker
`-t`](https://stackoverflow.com/questions/43099116/error-the-input-device-is-not-a-tty),
[omamori break-glass TTY bypass](https://github.com/yottayoshida/omamori/issues/319)).
Industry direction explicitly gives agents TTYs ([coder/agent-tty](https://github.com/coder/agent-tty)).

Community consensus (OWASP, Checkmarx, arXiv consent-integrity work, OSS guard
projects) treats repo-local grants, boolean flags, and agent-narrated approval
dialogs as **policy hints**, not authorization. Real controls bind approval to
**cryptographic proofs** (HMAC, Ed25519 JWKS, hash-bound gates) or **host-framework
signals** the agent cannot mint, with enforcement at the **tool boundary**.

---

## Verdict table (orama PR #255 grant path)

| Component | Claimed property | Actual property |
| --- | --- | --- |
| `grant-pr-body-human-override.sh` | Operator-only, interactive TTY | **Regular shell script**; agent `Shell` has TTY |
| TTY gate (`! -t 0 && ! -t 1`) | Blocks agents | Blocks only **fully piped** invocations |
| `~/.cursor/pr-body-human-override-ack` | Proof of operator intent | **Forgeable** marker + timestamp |
| `_human_override_active()` | Validates human grant | File + TTL only; no signature, no PR binding |

**Trivial agent bypass (no grant script):**

```bash
umask 077
printf 'operator-grant-v1\nissued-at=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  > ~/.cursor/pr-body-human-override-ack
```

---

## Deep research: TTY gating vs human authorization

### Finding 1 — TTY is session topology, not auth

POSIX `isatty()` / bash `-t` answer whether a file descriptor is connected to a
terminal device. StackOverflow and container docs use this for **attach mode**
(docker `-t`, ssh TTY allocation), not to prove a human is at the keyboard
([SO 43099116](https://stackoverflow.com/questions/43099116/error-the-input-device-is-not-a-tty),
[SO 7114990](https://stackoverflow.com/questions/7114990/pseudo-terminal-will-not-be-allocated-because-stdin-is-not-a-terminal),
[SE 107933](https://security.stackexchange.com/questions/107933/what-exactly-does-ssh-t-userdomain-verify-do)).

**EXA surfaced parallel hardening work:** [omamori #319](https://github.com/yottayoshida/omamori/issues/319)
(filed because `printf 'y\n' | omamori break-glass` bypasses a confirmation that
**did not require TTY**). [quality-playbook A-22 TTY hardening](https://github.com/andrewstellman/quality-playbook/commit/eaed1e2dac0f423d9e14b6a5ba13e7975a4e8120)
documents explicit TTY requirements for operator-only paths. These treat TTY as a
**weak adjunct**, and still note piping bypasses when `-t` is omitted.

### Finding 2 — Agents are meant to have terminals

[coder/agent-tty](https://github.com/coder/agent-tty) and [opencode #18659](https://github.com/anomalyco/opencode/issues/18659)
(host-shell / stdin passthrough for agent CLIs) reflect product intent: agents
drive interactive TUIs. Any gate that equates “has TTY” with “is human” fails in
the primary agent runtime.

### Finding 3 — Our grant script logic is weaker than “require TTY”

```bash
if [[ ! -t 0 && ! -t 1 ]]; then exit 1; fi   # current
# Should be (still insufficient for identity):
if [[ ! -t 0 || ! -t 1 ]]; then exit 1; fi
```

| stdin TTY | stdout TTY | Current script | Strict both-TTY |
| --- | --- | --- | --- |
| yes (agent) | yes | **runs** | runs |
| yes | no | **runs** | **deny** |
| no | yes | **runs** | **deny** |
| no | no | deny | deny |

---

## Deep research: HITL bypass classes (UI deception + forged state)

### Lies-in-the-loop (LITL) — agent-narrated approval

Checkmarx Zero ([2025-09](https://checkmarx.com/zero-post/bypassing-ai-agent-defenses-with-lies-in-the-loop/),
[OWASP community entry](https://owasp.org/www-community/attacks/Lies_in_the_Loop),
[CSO Online](https://www.csoonline.com/article/4108592/human-in-the-loop-isnt-enough-new-attack-turns-ai-safeguards-into-exploits.html))
documents **HITL dialog forging**: the human approves a **summary the agent writes**,
which can misrepresent the real command. Anthropic treated explicit confirmation
prompts as sufficient in a related report; Checkmarx argues that is insufficient
when dialog content is attacker-influenced.

**Relation to orama grant:** LITL attacks **misleading UI**; our gap is **forgeable
approval state** without UI. Both are “human-in-the-loop” failures; fixes differ.

### Consent integrity (academic framing)

[What You Approve Is What Executes](https://arxiv.org/html/2606.02668v1) (Weng, 2026)
formalizes **consent integrity** for black-box agents: the approved summary must
bind to what executes. LITL breaks that binding. A plaintext ack file breaks it
more directly — there is no binding at all.

[Governing Dynamic Capabilities](https://arxiv.org/html/2603.14332v2) (Zhou, 2026)
argues for **cryptographic binding** of tool capability and execution replay —
aligned with CodeRabbit’s “non-forgeable capability” requirement.

### Fabricated approvals in transcripts

[AgentPatterns — Non-Human Event Provenance Markers](https://agentpatterns.ai/security/non-human-event-provenance-markers/)
addresses agents treating fabricated “user approved” lines in transcripts as
authoritative. Plaintext ack files are the same class: **agent-writable state**
masquerading as human intent.

---

## Deep research: open-source & community mitigation patterns (EXA-derived)

Prioritize **enforcement at tool boundary** + **non-forgeable proof**. Advisory
UI or repo scripts alone are explicitly insufficient ([GoodRoom passkey MCP post](https://dev.to/goodroom/adding-passkey-backed-human-approval-to-high-risk-mcp-actions-38h):
“Without that enforcement point, an approval UI is only advisory.”).

| Project / reference | Mechanism | Citation | Relevance to PR-body grant |
| --- | --- | --- | --- |
| **Vallum** `HMAC approval token` | Hook mints `HMAC-SHA256(machine_secret, command)`; replaces forgeable `--policy-approved` boolean | [PR #32](https://github.com/kahramanemir/Vallum/pull/32) (merged 2026-07) | Direct precedent: **boolean/file marker → per-action HMAC** |
| **hashgate** | Hash-bound approval; operator accepts canonical hash; execution re-derives and compares | [Seppelllo/hashgate](https://github.com/Seppelllo/hashgate) | **Fail-closed** gate for exact action state; Claude hooks included |
| **GoodRoom.verify** | Passkey WebAuthn + Ed25519 JWKS proof bound to SHA-256 action hash | [DEV post](https://dev.to/goodroom/adding-passkey-backed-human-approval-to-high-risk-mcp-actions-38h) | Out-of-band human verification; MCP sidecar |
| **HumanLayer** | Human-in-the-loop API / supervisor for tool calls | [humanlayer/humanlayer](https://github.com/humanlayer/humanlayer), [ACP](https://github.com/humanlayer/agentcontrolplane) | External approval channel |
| **Invariant Guardrails** | MCP/LLM proxy; rule-based tool interception | [invariantlabs-ai/invariant](https://github.com/invariantlabs-ai/invariant), [blog](https://invariantlabs.ai/blog/guardrails) | Mediate `ManagePullRequest` / `gh` paths |
| **forge-tool-guardrails** | Tool guardrails OSS | [577Industries/forge-tool-guardrails](https://github.com/577Industries/forge-tool-guardrails) | Policy layer on tool dispatch |
| **LlamaFirewall** | Meta open guardrail stack for agents | [Meta research](https://ai.meta.com/research/publications/llamafirewall-an-open-source-guardrail-system-for-building-secure-ai-agents/) | Ecosystem guardrails (not HITL crypto) |
| **Agent Manifest ADR-0006** | HITL approval mechanism design | [agentrust ADR](https://manifest.agentrust-io.com/adr/0006-hitl-approval-mechanism/) | Reference architecture |
| **AgentAuth / agentmint / agentpassport** | Agent identity & authorization experiments | [AgentAuth](https://github.com/maxmalkin/AgentAuth), [agentmint](https://github.com/aniketh-maddipati/agentmint), [agentpassport](https://github.com/cognis-digital/agentpassport) | Scoped agent identity (complements human proof) |
| **ASAP self-authorization prevention** | Doc pattern blocking agents self-asserting auth | [adriannoes/asap-protocol](https://github.com/adriannoes/asap-protocol/blob/main/docs/security/self-authorization-prevention.md) | Same class as forgeable grant file |
| **Microsoft agents-humanoversight** | Enterprise HITL patterns | [microsoft/agents-humanoversight](https://github.com/microsoft/agents-humanoversight) | Process reference |
| **opena2a agent-identity-management** | IAM for agents | [opena2a-org](https://github.com/opena2a-org/agent-identity-management) | Least-privilege agent identity |
| **Claude Code hooks** | Framework `before` hook deny JSON | [Hooks docs](https://code.claude.com/docs/en/hooks), [Permissions](https://code.claude.com/docs/en/permissions) | Host chokepoint; [#19298](https://github.com/anthropics/claude-code/issues/19298) limitations |
| **Claude Code #38299** | Feature: remote/programmatic approval API | [anthropics/claude-code#38299](https://github.com/anthropics/claude-code/issues/38299) | Framework-native approval signal (desired direction) |

### OWASP practitioner guidance

[AI Agent Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html)
— §4 Human-in-the-Loop Controls, tool authorization middleware, action classification.
Warns of **decision and approval manipulation** and **excessive autonomy**.

[Agentic Threats Navigator](https://genai.owasp.org/resource/owasp-gen-ai-security-project-agentic-threats-navigator/)
— human oversight as explicit attack surface.

[AISVS C09 High-Impact Action Approval](https://github.com/OWASP/AISVS/blob/main/research/chapters/C09-Orchestration-and-Agents/C09-02-High-Impact-Action-Approval.md)
— orchestration-layer approval research chapter.

orama `docs/v2/33-security-harness-source-material.md` already cites tool-executor
mediation and “mirror Anthropic’s grant-verification pattern” — **local file grants
are weaker** than framework grant verification.

---

## Contrarian views and risks

| View | Source | Implication |
| --- | --- | --- |
| “Human saw a confirmation prompt — not our bug” | Anthropic response cited in [Checkmarx LITL](https://checkmarx.com/zero-post/bypassing-ai-agent-defenses-with-lies-in-the-loop/) | **Insufficient** when dialog or state is agent-controlled |
| “TTY + prompt is two gates” | [omamori #319](https://github.com/yottayoshida/omamori/issues/319) | Without `-t`, second gate is **cosmetic** (pipe `y`) |
| “Hooks are enough” | Claude Code ecosystem | Hooks run in agent toolchain; deny JSON helps but [#19298](https://github.com/anthropics/claude-code/issues/19298) reports gaps |
| “MCP approval sidecar” | [GoodRoom post](https://dev.to/goodroom/adding-passkey-backed-human-approval-to-high-risk-mcp-actions-38h) | Bypassable if another path reaches the tool — **must verify at final boundary** |
| Signed tokens in agent env | Vallum HMAC model | Machine secret must live **outside** agent-readable stores |

**Residual risk after Phase C:** LITL still fools humans who read misleading summaries;
crypto binding fixes **forgeable state**, not **misleading UI**. Combine honest
docs, hash-bound summaries, and out-of-band approval for high-impact writes.

---

## Open questions

1. Does Cursor expose a **host-only** approval flag for `ManagePullRequest` (analogous to Claude [#38299](https://github.com/anthropics/claude-code/issues/38299))?
2. **Vallum-style HMAC** vs **hashgate-style state hash** vs **WebAuthn proof** — which fits PR-body append (integrative merge) workflow?
3. Should PR-body escalation use **Invariant proxy** on MCP `ManagePullRequest` instead of shell `gh`?
4. Where to store machine signing secret — macOS Keychain service separate from agent env?

---

## Recommended remediation phases (implementation PR)

### Phase A — Honest documentation (immediate)

- Stop claiming grant script is “not agent-runnable”
- Document grant as **workflow aid + TTL throttle**, not authorization
- Remove agent-copyable override setup from hookify / cursor rules (CodeRabbit)

### Phase B — Tighten script (defense-in-depth only)

- Fix TTY: `[[ ! -t 0 || ! -t 1 ]]` exit
- Bind ack to `repo`, `pr_number`, `grant-nonce` (still forgeable if agent writes file)

### Phase C — Real authorization (target)

Evaluate (from EXA/Firecrawl catalog above):

1. **Vallum pattern** — hook mints HMAC tied to `append-pr-body.sh` invocation + PR id
2. **hashgate pattern** — hash-bound integrative body preview vs write
3. **GoodRoom / passkey** — out-of-band WebAuthn for rare operator body edits
4. **HumanLayer** — approval API webhook before hook allows append
5. **Invariant proxy** — deny `update_pr` body at MCP layer regardless of local grant
6. **Framework signal** — Cursor/Claude host capability when available

### Phase D — Tests

- Agent shell can run grant script today (TTY present)
- Direct ack write activates override today
- After Phase C: forged file / piped grant **cannot** activate override

---

## Sources (collection pass 2026-08-02)

### Primary / official

- [CodeRabbit PR #255 review 4835288649](https://github.com/diazMelgarejo/orama-system/pull/255#pullrequestreview-4835288649)
- [Claude Code Hooks](https://code.claude.com/docs/en/hooks)
- [Claude Code Permissions](https://code.claude.com/docs/en/permissions)
- [OWASP Lies in the Loop](https://owasp.org/www-community/attacks/Lies_in_the_Loop)
- [OWASP AI Agent Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html)
- [OWASP Agentic Threats Navigator](https://genai.owasp.org/resource/owasp-gen-ai-security-project-agentic-threats-navigator/)

### Research & industry

- [Checkmarx LITL](https://checkmarx.com/zero-post/bypassing-ai-agent-defenses-with-lies-in-the-loop/)
- [Consent integrity arXiv 2606.02668](https://arxiv.org/html/2606.02668v1)
- [Cryptographic binding arXiv 2603.14332](https://arxiv.org/html/2603.14332v2)
- [AgentPatterns provenance markers](https://agentpatterns.ai/security/non-human-event-provenance-markers/)
- [GoodRoom passkey MCP approval](https://dev.to/goodroom/adding-passkey-backed-human-approval-to-high-risk-mcp-actions-38h)

### Open source

- [Vallum HMAC PR #32](https://github.com/kahramanemir/Vallum/pull/32)
- [hashgate](https://github.com/Seppelllo/hashgate)
- [humanlayer](https://github.com/humanlayer/humanlayer)
- [invariant](https://github.com/invariantlabs-ai/invariant)
- [omamori TTY issue #319](https://github.com/yottayoshida/omamori/issues/319)
- [coder/agent-tty](https://github.com/coder/agent-tty)

### TTY / session (not auth)

- [SO: input device is not a TTY](https://stackoverflow.com/questions/43099116/error-the-input-device-is-not-a-tty)
- [SO: pseudo-terminal allocation](https://stackoverflow.com/questions/7114990/pseudo-terminal-will-not-be-allocated-because-stdin-is-not-a-terminal)

---

## Rerun inputs

```text
workflow: firecrawl-deep-research (+ EXA wide net first)
topic: PR-body grant TTY/HITL security gap (orama PR #255)
depth: thorough
output: markdown reference + WORKSPACE next steps
trigger: CodeRabbit 4835288649
```

---

## Repo links

- Incident ladder: `bin/orama-system/references/pr-body-anti-clobber-incident-ledger.md`
- Guard core: `scripts/cursor/hooks/pr-body-guard-core.py`
- Grant script: `scripts/cursor/grant-pr-body-human-override.sh`
- Security harness: `docs/v2/33-security-harness-source-material.md`
- Working next steps: `.agent/memory/working/WORKSPACE.md`
