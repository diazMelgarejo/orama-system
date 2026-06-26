# ECC Migration Rules — Artifact → Durable Target

> **Source:** `ecc-hermes-cross-harness.md` § Migration Decision Map  
> **Role:** decision map for migrating Hermes / OpenClaw artifacts into canonical PT-orama targets  
> **Size contract:** ≤150 lines.

---

## Decision Map

Treat Hermes and OpenClaw as **source systems**. Distill behaviour into the smallest
safe PT-orama surface:

| Source artifact | Durable target | Notes |
|---|---|---|
| Reusable workflow knowledge | Canonical skill (`bin/orama-system/skills/`) | Never copy raw agent output verbatim |
| Repeatable procedural action | Command card (`commands/<slug>/SKILL.md`) or hook | Thin wrappers point here |
| Runtime / session routing | Adapter or control-plane issue | Not a skill |
| Generic setup instructions | Reference card (this folder) | ≤150 lines each |
| Private memory, tokens, account state | **Do not ship** | Stays in `~/.hermes/` |
| Personal workspace files | **Do not ship** | Stays in `~/.hermes/workspace/` |

---

## Migration Checklist

Before moving any Hermes or ECC artifact into orama-system:

- [ ] **Is it reusable?** Operator-agnostic, not tied to one machine or session.
- [ ] **What kind of asset?** Knowledge → skill. Procedure → command/hook. Runtime → adapter.
- [ ] **No leaks?** No secrets, local absolute paths, personal datasets, or private state.
- [ ] **Sanitized?** Paths use env vars (`$HERMES_HOME`, `%USERPROFILE%`) not `/Users/lab/...`.
- [ ] **Anti-doxxing pass?** Run `python scripts/review/repo_hygiene.py .` before committing.
- [ ] **Thin-wrapper only?** Hermes local commands point to canonical; they don't duplicate bodies.

---

## Loading Map (Harness → Canonical)

| Harness | PT-orama loading surface | Boundary |
|---|---|---|
| Codex | Thin `.codex/` wrappers from skill manifest | No reference copies in local dir |
| Hermes | `install_hermes_thin_skills.py` → `/pt-orama-*` wrappers | Provider config stays local |
| AGY | `agy-gemini.md` + `.agents/` point back to canonical cards | AGY output is advisory |
| Claude Code | Thin `.claude/skills/` wrappers | Skill bodies stay in `bin/orama-system/` |
| OpenClaw | `openclaw-skills` owns gateway / channel / cron / secrets | Hermes must not guess OpenClaw procedures |

---

## Never

- Create a new council skill just to represent a harness. Extend the canonical Hermes
  command/reference cards; update only the thin adapter when its trigger or path changes.
- Mirror `~/.hermes/` raw into tracked files.
- Copy secrets into any tracked skill, command, or reference.

---

## Related

- [`ecc-setup-distilled.md`](ecc-setup-distilled.md) — bring-up order + adaptation table
- [`cross-harness-protocol.md`](cross-harness-protocol.md) — shared-source-first rule
- [`partner-prompt-contract.md`](partner-prompt-contract.md) — bounded worker prompt
- [`ecc-hermes-cross-harness.md`](ecc-hermes-cross-harness.md) — full source
