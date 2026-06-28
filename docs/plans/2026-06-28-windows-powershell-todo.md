# Windows PowerShell TODO — orama-system (live operator checklist)

> **When:** Win RTX box is online; run from an elevated or normal PowerShell after
> `git pull --ff-only origin main` in the orama-system clone.
> **Canonical Mac mirror:** [`2026-06-28-mac-e2e-handoff.md`](2026-06-28-mac-e2e-handoff.md)
> **LAN peer talk:** [`../bin/orama-system/skills/hermes-harness/references/lan-peer-self-talk.md`](../bin/orama-system/skills/hermes-harness/references/lan-peer-self-talk.md)

---

## 0. Bootstrap (every session)

```powershell
# UTF-8 + partner PATH — see git-history-surgery windows-powershell-runtime-bootstrap.md
$repo = (git -C $PSScriptRoot rev-parse --show-toplevel 2>$null)
if (-not $repo) { $repo = $env:ORAMA_SYSTEM_PATH }
Set-Location $repo

$env:ORAMA_SYSTEM_PATH = $repo
$env:PERPETUA_TOOLS_PATH = $env:PERPETUA_TOOLS_PATH  # set to your PT clone root

.\platform\windows\ensure-partner-cli-paths.ps1
```

- [ ] `$env:ORAMA_SYSTEM_PATH` resolves to the orama-system clone
- [ ] `$env:PERPETUA_TOOLS_PATH` resolves to the Perpetua-Tools clone
- [ ] LM Studio listening on **`http://localhost:1234`** (one loaded chat model)

---

## 1. Partner canaries (Phase 6)

```powershell
cd $env:ORAMA_SYSTEM_PATH
python bin\orama-system\skills\hermes-harness\scripts\verify_partner_canaries.py `
  --lm-studio-url http://localhost:1234/v1
```

Pass: `LM Studio PASS` (`LM_READY`), `Hermes PASS` (`HERMES_READY`), optional Codex/cursor-agent.

On failure:

```powershell
python bin\orama-system\skills\hermes-harness\scripts\verify_partner_canaries.py --tail-lmstudio-logs
```

- [ ] LM Studio `LM_READY`
- [ ] Hermes `HERMES_READY`
- [ ] Codex `--version` (optional)
- [ ] cursor-agent `--version` (optional)

---

## 2. Thin wrappers (Phase 9)

```powershell
python bin\orama-system\skills\hermes-harness\scripts\install_hermes_thin_skills.py --install
python bin\orama-system\skills\hermes-harness\scripts\install_hermes_thin_skills.py --verify
python bin\orama-system\skills\hermes-harness\scripts\install_hermes_thin_skills.py --test
```

Expected slash commands: `/pt-hardware-policy`, `/pt-orama-council`, `/pt-orama-review`, `/pt-orama-delegate`, `/lan-peer-self-talk`.

- [ ] `--verify` all wrappers present
- [ ] `--test` smoke green

---

## 3. Hardware policy

```powershell
.\platform\windows\start.ps1 --hardware-policy
```

- [ ] `openclaw.json` clean (or OpenClaw optional skip is documented)

---

## 4. Stack status (optional — when running full services)

```powershell
.\platform\windows\start.ps1 --status
# Start services when needed:
# .\platform\windows\start.ps1 --no-open
```

- [ ] Ports 8000 / 8001 / 8002 listeners when stack started
- [ ] Tier 1 shows Win localhost + Mac peer via discovery

---

## 5. LAN peer self-talk (Mac ↔ Win orama installs)

Enable LAN bind **on both hosts** (`.env.local`, not committed):

```dotenv
PORTAL_BIND_LAN=1
ORAMA_BIND_LAN=1
ORAMA_CONTROL_PLANE_TOKEN=<shared-secret-both-machines>
```

From **Windows**, probe Mac peer:

```powershell
python bin\orama-system\skills\hermes-harness\scripts\probe_lan_peer.py --json
```

From **Mac** (bash), probe Win peer:

```bash
python3 bin/orama-system/skills/hermes-harness/scripts/probe_lan_peer.py --json
```

- [ ] Peer `/health` on port 8002 (after `PORTAL_BIND_LAN=1`)
- [ ] Peer LM Studio `/v1/models` via discovery IP
- [ ] Optional: peer `/api/status` with shared bearer token

See: [`lan-peer-self-talk.md`](../bin/orama-system/skills/hermes-harness/references/lan-peer-self-talk.md)

---

## 6. L1 perpetua-core gate (after canaries green)

```powershell
cd $env:PERPETUA_TOOLS_PATH\..\oramasys\perpetua-core   # adjust to your perpetua-core clone
pip install -e ".[dev]"
python -m pytest -q
```

Mac operator runs the same pytest + `engine.ainvoke` round-trip on Ollama; then tag `v0.2.0-alpha`.

- [ ] perpetua-core pytest green on Win
- [ ] Human sign-off for `v0.2.0-alpha` tag

---

## 7. Regression-only (do not repeat if main already green)

```powershell
python bin\orama-system\skills\hermes-harness\scripts\dispatch_codex_partner.py `
  --dry-run --pytest tests\test_verify_partner_canaries.py
```

---

## Blockers (user action)

| Item | Owner |
|------|-------|
| `openclaw.gateway-auth-token` Keychain | Mac user |
| SSH `:22` to Win | Not required for HTTP LAN peer path |
| Shared `ORAMA_CONTROL_PLANE_TOKEN` | Operator — both `.env.local` files |
