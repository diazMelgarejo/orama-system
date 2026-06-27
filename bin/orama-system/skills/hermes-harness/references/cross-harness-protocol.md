# Cross-Harness Protocol

> **Source:** `ecc-hermes-cross-harness.md` § Cross-Harness Rule + Authority And Defaults  
> **Role:** shared-source-first rule; harness-specific only for loading / command names / platform limits  
> **Size contract:** ≤150 lines.

---

## The Rule

**Put durable behaviour in the shared source first.**  
Use harness-specific files only for: loading mechanics, command names, event shapes, and platform limits.

```text
orama-system/bin/orama-system/skills/   ← canonical skill bodies (shared source)
Perpetua-Tools/                         ← middleware, hardware policy, startup intelligence
~/.hermes/skills/pt-orama-*/            ← thin wrappers that point at the above (harness edge)
```

---

## Authority Defaults

| Question | Answer |
|---|---|
| Who owns decisions, edits, and final synthesis? | The main orama agent — always. |
| Are reviewer labels veto authority? | No. Advisory only. |
| Is the council required for all tasks? | No. Optional risk-control for high-stakes multi-step work. |
| What if a partner lane is missing or quota-limited? | Record as UNAVAILABLE; continue with remaining lanes. Never simulate. |
| Is Hermes "proof of local execution"? | Only when the active provider is verified as the intended loopback endpoint **and** its canary succeeds. |

---

## Per-Harness Loading Surface

| Harness | What lives here | What lives in canonical |
|---|---|---|
| Hermes | `~/.hermes/skills/pt-orama-*/SKILL.md` (thin wrappers) | `commands/<slug>/SKILL.md` skill bodies |
| Codex | `.codex/` thin wrappers | `bin/orama-system/skills/` |
| AGY | `agy-gemini.md` + `.agents/` pointers | `bin/orama-system/references/` |
| Claude Code | `.claude/skills/` thin wrappers | `bin/orama-system/skills/` |
| OpenClaw | `openclaw-skills/` (its own canonical) | `openclaw-skills/` is itself canonical |

---

## Platform-Specific Limits (harness edge only)

| Platform | Limit | Where documented |
|---|---|---|
| Windows | LM Studio = `localhost:1234`; GGUF only; Git Bash required | `references/windows-onboarding-config.md` |
| macOS | Ollama = `localhost:11434`; MLX models; OpenClaw primary | `../openclaw-skills/SKILL.md` |
| Linux | Same binary as macOS; full hardware matrix | `hardware/SKILL.md` in PT |
| Cross-machine | Win→Mac = `$MAC_IP`; Mac→Win = `$WIN_IP` | `references/lan-endpoint-contract.md` |

---

## Never

- Create a second council skill to "represent" a harness. Add a command card.
- Override canonical skill behaviour at the harness edge.
- Let a partner lane make autonomous commits, deploys, or account changes.
- Trust a lane that failed its readiness canary — record UNAVAILABLE.

---

## Related

- [`ecc-setup-distilled.md`](ecc-setup-distilled.md) — adaptation table + bring-up order
- [`ecc-migration-rules.md`](ecc-migration-rules.md) — artifact → target decision map
- [`partner-prompt-contract.md`](partner-prompt-contract.md) — bounded worker prompt
- [`lan-endpoint-contract.md`](lan-endpoint-contract.md) — IP parametrization contract

---

## Three-Layer Architecture

| Layer | Repo | Role |
|---|---|---|
| L3 | orama-system (this repo) | Owns canonical skill definitions, routing policy, and stateless methodology |
| L2 | Perpetua-Tools | Middleware: receives agent-neutral skill envelopes, resolves `openclaw_home`, runs tools, returns normalized results |
| L1 | Hermes / OpenClaw / Codex / AGY | Operator shell / harness: applies config changes, invokes skills, may spawn partner agents |

Standard L3 → L1 dispatch path:

```text
orama-system
  → Perpetua-Tools skill dispatcher
  → orama-system/skills/{skill_id}/SKILL.md (canonical procedure)
  → target harness home (Hermes ~/.hermes, OpenClaw ~/.openclaw)
  → files changed / stowed / verified
```

---

## PT-Orama Loading Map

Each harness receives only the smallest adapter needed to locate and invoke
canonical skills. Canonical skill bodies always stay under
`bin/orama-system/skills/`.

| Harness | Loading surface | Boundary |
|---|---|---|
| **Hermes** | `install_hermes_thin_skills.py` installs `/pt-orama-*` wrappers | Keep provider config, credentials, and workspace memory local |
| **OpenClaw** | `openclaw-skills` master skill + Nine Skills overlays | Config and gateway operations only; no skill body duplication |
| **Codex** | Thin local wrappers generated from the canonical skill manifest | Do not copy references or scripts into the local skill directory |
| **AGY** | `ANTIGRAVITY.md` + `.agent/` point back to canonical cards | Treat AGY output as advisory; require a visible readiness canary before dispatch |
| **Claude Code** | Thin `.claude/skills/` wrappers + project instructions | Canonical skill bodies stay under `bin/orama-system/skills/` |

---

## Hermes Slash-Command Envelope

Hermes thin wrappers invoke canonical skills via slash commands:

```text
/pt-hardware-policy   → commands/pt-hardware-policy/SKILL.md
/pt-orama-council     → commands/pt-orama-council/SKILL.md
/pt-orama-delegate    → commands/pt-orama-delegate/SKILL.md
/pt-orama-review      → commands/pt-orama-review/SKILL.md
```

The thin wrapper must:
1. Point back to the canonical `SKILL.md` path in orama-system.
2. Carry no procedure body of its own.
3. Be regenerated from canonical on `install_hermes_thin_skills.py --install`.

---

## Invariants

1. Durable skills/rules live in orama-system — never in `~/.hermes` alone.
2. Hermes and OpenClaw are consumers of canonical skills, not owners.
3. No harness-specific file may re-declare a policy already in PT's YAML.
4. Every thin wrapper must be reproducible via the install script.
5. A redirect stub is sufficient for an absorbed entry point — no duplicate content.
