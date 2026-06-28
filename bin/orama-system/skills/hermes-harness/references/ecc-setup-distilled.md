# ECC Setup — PT-Orama Adaptation Guide

> **Source:** `ecc-hermes-cross-harness.md` § ECC Setup Lessons  
> **Role:** PT-orama adaptation table, bring-up order, what to import vs. skip  
> **Size contract:** ≤150 lines. For full ECC background see `ecc-hermes-cross-harness.md`.

---

## Adaptation Table

| ECC concept | PT-orama equivalent |
|---|---|
| Hermes front door | Hermes operator shell (chat / CLI / cron / workspace state) |
| ECC reusable substrate | `orama-system` canonical skills + PT middleware |
| `~/.hermes/skills/ecc-imports/` | Sanitized Hermes imports from `install_hermes_thin_skills.py` |
| `~/.hermes/config.yaml` | Local provider routing + MCP registration (never tracked) |
| `~/.hermes/cron/jobs.json` | Local operator automation (never tracked) |
| `~/.hermes/workspace/` | Private workspace memory (never published) |

**Rule:** what lives in `~/.hermes/` stays local. Canonical behavior lives in `bin/orama-system/skills/`.

---

## Bring-Up Order

1. Inventory any legacy Hermes / OpenClaw workspace before importing anything.
2. Plan and scaffold reusable artifacts before copying content.
3. Verify canonical skill / harness repo tests pass first (`pytest -q`).
4. Install Hermes and point it at imported canonical skills via `install_hermes_thin_skills.py`.
5. Register only the MCP servers used daily.
6. Authenticate providers locally, starting with GitHub and document stores.
7. Start with small recurring jobs before heavier personal workflows.

---

## Import vs. Skip Decision

| Asset | Import? | Becomes |
|---|---|---|
| Reusable workflow knowledge | ✅ Yes | Canonical skill (`bin/orama-system/skills/`) |
| Procedural action (repeatable) | ✅ Yes | Command card (`commands/<slug>/SKILL.md`) or hook |
| Runtime / session routing | ✅ Yes | Adapter or control-plane doc |
| Generic setup instructions | ✅ Yes | Reference card (this folder) |
| Private memory, tokens, account state | ❌ Never | Do not ship |
| Personal workspace files | ❌ Never | Do not ship |

**Before importing, ask:**
1. Is it reusable across operators, or personal to one workspace?
2. Is the asset mainly knowledge, procedure, or runtime behaviour?
3. Does publishing it leak secrets, private datasets, local paths, or personal state?

---

## Related

- [`ecc-migration-rules.md`](ecc-migration-rules.md) — artifact → durable target decision map
- [`cross-harness-protocol.md`](cross-harness-protocol.md) — shared-source-first rule
- [`partner-prompt-contract.md`](partner-prompt-contract.md) — bounded worker prompt shape
- [`ecc-hermes-cross-harness.md`](ecc-hermes-cross-harness.md) — full source reference
