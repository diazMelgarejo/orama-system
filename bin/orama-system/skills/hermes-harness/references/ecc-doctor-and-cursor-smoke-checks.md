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
