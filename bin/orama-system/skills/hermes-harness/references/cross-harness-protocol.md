# Cross-Harness Protocol

> **Source:** `ecc-hermes-cross-harness.md` § Cross-Harness Rule + Authority And Defaults  
> **Role:** shared-source-first rule; harness-specific only for loading / command names / platform limits  
> **Size contract:** ≤150 lines.

---

## The Rule

**Put durable behaviour in the shared source first.**  
Use harness-specific files only for: loading mechanics, command names, event shapes, and platform limits.

```
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
