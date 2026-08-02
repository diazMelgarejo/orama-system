# PR-body human grant — security gap research (TTY / HITL)

> **Status:** research complete (2026-08-02); remediation **not** implemented here.
> **Trigger:** CodeRabbit review on orama-system PR #255
> ([review 4835288649](https://github.com/diazMelgarejo/orama-system/pull/255#pullrequestreview-4835288649))
> — replace `_human_override_active()` file-marker checks with a non-forgeable,
> host- or framework-provided capability.
> **Research method:** Firecrawl search + scrape (primary); StackExchange / X via
> Firecrawl site search; EXA API unavailable (`EXA_API_KEY` not set on host).

---

## Executive verdict

The current operator grant path is **not** a reliable human-authorization signal.

| Component | Claimed property | Actual property |
| --- | --- | --- |
| `grant-pr-body-human-override.sh` | Operator-only, interactive TTY | **Regular shell script**; agent `Shell` in Cursor / Claude Code runs with a real TTY |
| TTY gate (`-t 0` / `-t 1`) | Blocks non-human execution | **Fails only when both stdin and stdout are non-TTY** — agent terminals pass |
| `~/.cursor/pr-body-human-override-ack` | Proof of operator intent | **Plaintext marker + timestamp** — agent can write directly, no script needed |
| `_human_override_active()` | Validates human grant | **File presence + TTL** — no signature, no PR binding, no session binding |

Treat the grant as **workflow friction and defense-in-depth**, not cryptographic
authorization. CodeRabbit’s recommendation aligns with community practice: bind
escalation to an **out-of-agent-band** approval channel or a **signed capability**
the agent cannot mint.

---

## Current implementation (gap analysis)

### Grant script

`scripts/cursor/grant-pr-body-human-override.sh`:

```bash
if [[ ! -t 0 && ! -t 1 ]]; then
  echo "error: grant-pr-body-human-override requires an interactive operator terminal" >&2
  exit 1
fi
```

Logic table:

| stdin TTY? | stdout TTY? | Script runs? |
| --- | --- | --- |
| yes (agent shell) | yes | **yes** |
| yes | no | **yes** |
| no | yes | **yes** |
| no | no | **no** |

So the script blocks only fully piped/non-interactive invocations. It does **not**
require both streams to be TTY (`[[ ! -t 0 || ! -t 1 ]]` would be the usual
“interactive session” pattern). Even a corrected gate would still only detect
**session type**, not **human identity**.

### Hook verifier

`scripts/cursor/hooks/pr-body-guard-core.py` — `_human_override_active()`:

- Reads `~/.cursor/pr-body-human-override-ack`
- Accepts if `operator-grant-v1` and `issued-at=` within 8h TTL
- No HMAC, no Ed25519, no binding to `owner/repo`, PR number, hook session id,
  or operator credential

**Trivial agent bypass (no grant script):**

```bash
umask 077
printf 'operator-grant-v1\nissued-at=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  > ~/.cursor/pr-body-human-override-ack
```

### Why agent-attached terminals defeat TTY gating

Cursor and Claude Code expose shell tools against the user’s integrated terminal
or a PTY-backed subprocess. In that context `test -t 1` / `sys.stdin.isatty()`
return true for the **agent’s** session — the same property documented for
Codex non-TTY failures when spawned from Python, and inverted here: **TTY present
does not imply human**.

StackOverflow documents `isatty` as “is this fd connected to a terminal device?”
—not “is a human at the keyboard?” ([SO 43099116](https://stackoverflow.com/questions/43099116/error-the-input-device-is-not-a-tty),
[SO 7114990](https://stackoverflow.com/questions/7114990/pseudo-terminal-will-not-be-allocated-because-stdin-is-not-a-terminal)).

Security StackExchange discussions on `ssh -T` and TTY allocation similarly treat
TTY as a **wire protocol / session capability** feature, not an authentication
mechanism ([SE 107933](https://security.stackexchange.com/questions/107933/what-exactly-does-ssh-t-userdomain-verify-do)).

---

## Community research — human-in-the-loop bypass class

### Lies-in-the-loop (LITL) — Checkmarx Zero (2025-09)

Checkmarx documents **lies-in-the-loop**: attackers manipulate the **context shown
in the human approval UI** so dangerous actions look safe. Applicable to any HITL
agent, not only Claude Code.

- Research post: [Bypassing AI Agent Defenses With Lies-In-The-Loop](https://checkmarx.com/zero-post/bypassing-ai-agent-defenses-with-lies-in-the-loop/)
- Blog summary: [When AI Lies: HITL security](https://checkmarx.com/blog/when-the-ai-lies-a-new-threat-emerges-for-human-in-the-loop-security/)
- Press: [Infosecurity Magazine — Lies-in-the-Loop](https://www.infosecurity-magazine.com/news/lies-loop-attack-ai-safety-dialogs/)

Key quote (HITL limitation): humans “can only respond to what the agent prompts
them with,” and that prompt is **agent-controlled context**. Anthropic’s public
response to a related finding treated explicit confirmation prompts as sufficient
([HackerOne thread cited in Checkmarx post](https://checkmarx.com/zero-post/bypassing-ai-agent-defenses-with-lies-in-the-loop/#step-by-step-identifying-and-exploiting-lies-in-the-loop)).

**Relation to our grant:** LITL targets **misleading approval UI**; our gap is
**forgeable approval state** (file marker). Both undermine HITL; fixes differ.

### OWASP Gen AI — Agentic Threats Navigator

OWASP’s Agentic Threats Navigator maps **human oversight** as an explicit attack
surface in agentic systems (reasoning, memory, tools, identity, oversight,
multi-agent).

- Resource: [OWASP Agentic Threats Navigator](https://genai.owasp.org/resource/owasp-gen-ai-security-project-agentic-threats-navigator/)

orama `docs/v2/33-security-harness-source-material.md` already cites tool-executor
mediation and “mirror Anthropic’s grant-verification pattern” — this research
confirms **local file grants are weaker** than framework-native grant verification.

### Anthropic Claude Code — hooks (framework layer)

Claude Code hooks can **deny** tool use at the host boundary ([Hooks reference](https://code.claude.com/docs/en/hooks),
[Permissions](https://code.claude.com/docs/en/permissions)). That is closer to a
**non-forgeable framework signal** than a repo script, but:

- Hooks still run in the agent toolchain context
- [Issue #19298](https://github.com/anthropics/claude-code/issues/19298): PermissionRequest
  hook limitations reported
- Community hook patterns (e.g. Reddit [smart bash permission hook](https://www.reddit.com/r/ClaudeAI/comments/1rvg3ah/smart_bash_permission_hook_for_claude_code/))
  remain policy, not identity

**CodeRabbit PR #255 review** explicitly asks to validate a **host- or tool-framework-
provided capability** for override — not a repo-local ack file.

---

## Open-source / community mitigation patterns (cited)

| Project / pattern | What it does | Relevance to PR-body grant |
| --- | --- | --- |
| [humanlayer/humanlayer](https://github.com/humanlayer/humanlayer) | Human approval API / “human layer” for agent tool calls | **Out-of-band human approval** as a service; [ACP](https://github.com/humanlayer/agentcontrolplane) for agent control plane |
| [humanlayer/humanlayer#968](https://github.com/humanlayer/humanlayer/issues/968) | Feature: block `--no-verify` for agents | Same class: prevent agents from bypassing git hooks |
| [invariantlabs-ai/invariant](https://github.com/invariantlabs-ai/invariant) | Guardrails proxy on MCP/LLM tool flows | **Policy mediation** between app and tools ([docs](https://invariantlabs-ai.github.io/docs/mcp-scan/guardrails-reference/)) |
| [microsoft/agents-humanoversight](https://github.com/microsoft/agents-humanoversight) | Human oversight patterns for agents | Enterprise HITL reference architecture |
| [opena2a-org/agent-identity-management](https://github.com/opena2a-org/agent-identity-management) | IAM layer for agents | Scoped **non-human identity** + least privilege |
| [coder/agent-tty](https://github.com/coder/agent-tty) | Terminal sessions **for** agents | Confirms industry direction: agents **intentionally** get real TTYs |
| Claude Code hooks | `before` tool hooks with deny JSON | Framework chokepoint; prefer over shell scripts |
| Signed short-lived JWT / macOS privileged helper | OS or IdP-bound capability | True separation: agent process cannot sign |

**Invariant / HumanLayer pattern (recommended direction):** move high-risk writes
to a **mediator** (hook gateway, MCP proxy, or external approval API) that emits a
**signed, scoped, short-lived token** bound to `(repo, pr_number, action, nonce)`.
Hooks verify signature with a **public key or host-held secret outside agent env**.

---

## Social / secondary sources (X, StackExchange)

| Source | Topic |
| --- | --- |
| [Mitchell Hashimoto on X](https://x.com/mitchellh/status/2060088112257372610) | AI agent authorization discourse (surfaced via Firecrawl LITL search) |
| [Trevin Chow on X](https://x.com/trevin/status/2051316002730991795) | Agent harness / approval patterns |
| [Longxu Dou — Reptile terminal agent](https://x.com/LongxuDou/status/2001281126489620603) | Terminal agents explicitly drive TTY apps |
| StackOverflow `isatty` / docker `-t` threads | TTY = container attach mode, not auth |

Twitter/X results for “agent TTY human approval” were **noisy**; LITL-specific
search surfaced Checkmarx + Infosecurity coverage more reliably than generic X posts.

---

## Recommended remediation phases (for implementation PR)

### Phase A — Honest documentation (immediate)

- Stop claiming grant script is “not agent-runnable”
- Document grant as **operator workflow aid** + TTL throttle, not authorization
- Remove agent-copyable override setup from hookify / cursor rules (CodeRabbit)

### Phase B — Tighten script (still insufficient alone)

- Fix TTY check to `[[ -t 0 && -t 1 ]]` or `[[ ! -t 0 || ! -t 1 ]]` exit
- Bind grant file to `repo`, `pr_number`, optional `session_id` fields
- Rotate random `grant-nonce=` in file; hook requires matching env from **hook only**
  (still forgeable if agent can write file — marginal)

### Phase C — Real authorization (target)

Pick one or combine:

1. **Cursor / Claude host hook only** — override when framework sets
   `CURSOR_HUMAN_APPROVED_PR_BODY=1` from UI action (if/when exposed); never from shell
2. **Signed capability** — operator runs `grant-…` on **separate terminal** or phone
   approver; outputs Ed25519-signed blob; hook verifies with public key in repo
3. **HumanLayer / custom approval webhook** — agent requests token; human approves in
   browser; hook checks token server-side
4. **Invariant-style proxy** — route `ManagePullRequest` / `gh` through guardrailed MCP
   that denies `update_pr body` regardless of local grants

### Phase D — Tests

- Prove agent shell **can** run grant script (TTY mocked)
- Prove direct ack file write activates override (regression guard for Phase C)
- After Phase C: prove forged file **cannot** activate override

---

## Links

- Incident ladder: `bin/orama-system/references/pr-body-anti-clobber-incident-ledger.md`
- Guard core: `scripts/cursor/hooks/pr-body-guard-core.py`
- Grant script: `scripts/cursor/grant-pr-body-human-override.sh`
- Security harness plan: `docs/v2/33-security-harness-source-material.md` (§5.2 grant-verification)
- Working next steps: `.agent/memory/working/WORKSPACE.md` (2026-08-02 entry)
