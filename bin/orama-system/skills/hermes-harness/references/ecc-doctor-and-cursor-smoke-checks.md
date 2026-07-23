# Hermes ECC Doctor + cursor-agent Smoke Checks

> **Role:** Post-install validation sequence for Hermes ECC on Windows.
> **Absorbed from:** Hermes self-improve `windows-hermes-setup` reference (2026-07-23).

---

## ECC Doctor (Windows)

**Preferred:**

```powershell
cd $env:PERPETUA_TOOLS_PATH\vendor\ecc-tools
node scripts/ecc.js doctor --target hermes
```

**Structured output:**

```powershell
node scripts/ecc.js doctor --target hermes --json
```

**Git Bash quirk:** `npx` may be unavailable even when `npm.cmd` works. Do not prefer
`npx ecc doctor --target hermes`.

**Expected healthy output:** `checked=1, ok=1, warnings=0, errors=0`

**Idempotency:** If `~/.hermes/ecc-install-state.json` exists and
`~/.hermes/{skills,rules,commands}` are present → validate only; skip full reinstall.

Reinstall only missing ECC modules; preserve non-ECC artifacts in `~/.hermes`.

---

## CRG (`code-review-graph`) — platform endpoint rule

Canonical SSoT: [`../../code-review/references/crg-platform-endpoints.md`](../../code-review/references/crg-platform-endpoints.md).

| Platform | `CRG_OPENAI_BASE_URL` | Backend |
|----------|----------------------|---------|
| **macOS** | `http://localhost:11434/v1` | Ollama (`bge-m3` embeddings) |
| **Windows (all)** | `http://localhost:1234/v1` | LM Studio (`$LM_STUDIO_WIN_ENDPOINTS`) |

ECC vendor defaults in `.cursor/mcp.json` ship the **macOS** template (`:11434`).
On **every Windows host** (including RTX 5080), override after install — or re-run
`bash bin/orama-system/scripts/sync-cursor-mcp.sh` (platform-aware):

```powershell
# .cursor/mcp.json → code-review-graph.env.CRG_OPENAI_BASE_URL
"CRG_OPENAI_BASE_URL": "http://localhost:1234/v1"
```

Do **not** point Windows CRG at `:11434` unless Ollama is explicitly running locally
(optional fallback — not the Windows primary inference path).

---

## cursor-agent Probe Sequence

1. `cursor-agent --version`
2. `cursor-agent --help`
3. `& "$env:LOCALAPPDATA\cursor-agent\cursor-agent.cmd" --help`
4. `Get-Process -Name "cursor*" -ErrorAction SilentlyContinue`
5. If on-path probe fails, retry absolute path before assuming missing.

---

## Thin Wrapper Install (orama canonical)

After ECC install, refresh Hermes thin wrappers (includes `windows-hermes-setup`):

```powershell
cd $env:ORAMA_SYSTEM_PATH
python bin\orama-system\skills\hermes-harness\scripts\install_hermes_thin_skills.py --install --verify
```

---

## Related

- [`windows-hermes-setup.md`](windows-hermes-setup.md)
- [`cursor-agent-steering-handoff.md`](cursor-agent-steering-handoff.md)
