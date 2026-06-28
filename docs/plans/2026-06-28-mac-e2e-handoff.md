# Mac E2E Handoff — 2026-06-28

> **From:** Windows Hermes testdrive (Phase 6+9 ✅, canaries green)  
> **To:** Mac operator — cross-harness E2E + T5 tags  
> **Windows state on origin/main:** LM Studio / Hermes / Codex / cursor-agent PASS; OpenClaw optional

## Sync both repos on Mac

```bash
export ORAMA_SYSTEM_PATH=~/code/OpenClaw/orama-system   # adjust to your clone
export PERPETUA_TOOLS_PATH=~/code/OpenClaw/Perpetua-Tools

cd "$ORAMA_SYSTEM_PATH"
git fetch origin --prune && git checkout main && git pull --ff-only origin main

cd "$PERPETUA_TOOLS_PATH"
git fetch origin --prune && git checkout main && git pull --ff-only origin main
```

Verify you have the Codex dispatch card and Windows fixes:

```bash
test -f bin/orama-system/references/codex-cli-v142-dispatch.md
test -f platform/windows/ensure-partner-cli-paths.ps1
python3 bin/orama-system/skills/hermes-harness/scripts/verify_partner_canaries.py --help | head -1
```

## Mac-local E2E (run first)

### 1. Stack status

```bash
cd "$ORAMA_SYSTEM_PATH"
bash start.sh --status
```

Pass: hard requirements green (Ollama, models, env).

### 2. Ollama probes

```bash
bash scripts/check-local-env.sh
# Expect: qwen3.5:9b-nvfp4 + bge-m3 loaded/available
```

### 3. Hardware policy (Mac-only)

```bash
bash start.sh --hardware-policy
```

### 4. Keychain — still required

```bash
# User must provide GATEWAY_AUTH_TOKEN once:
printf '%s' 'YOUR_GATEWAY_AUTH_TOKEN' | \
  bash scripts/openclaw/store_keychain_secret.sh openclaw.gateway-auth-token

source scripts/openclaw/load_keychain_secrets.sh
```

Already stored (2026-06-28): Gemini main + fallback, `TELEGRAM_BOT_TOKEN`.

## Cross-harness Mac↔Win (blocked until Win LM Studio LAN up)

**Prerequisite on Windows:** LM Studio serving on LAN port 1234 with one loaded chat model.

### Win IP — never hardcode

```bash
WIN_IP=$(python3 -c "import json,pathlib; p=pathlib.Path.home()/'.openclaw/state/last_discovery.json'; print(json.loads(p.read_text())['endpoints']['win']['ip'])")
echo "Win IP: $WIN_IP"
```

Or run discovery:

```bash
bash "$PERPETUA_TOOLS_PATH/scripts/discover-lm-studio.sh"
```

### Mac → Win LM Studio probe

```bash
curl -sS "http://${WIN_IP}:1234/v1/models" | head
curl -sS "http://${WIN_IP}:1234/api/v0/models" | python3 -m json.tool | head -30
```

### Cross-harness hardware affinity

```bash
cd "$ORAMA_SYSTEM_PATH"
bash start.sh --hardware-policy
# Must show Win LM Studio endpoint reachable when WIN_IP discovery is current
```

## T5 — after Mac↔Win E2E green

```bash
cd "$ORAMA_SYSTEM_PATH"
git tag v1.1.1 -m "v1.1.1 — security hardening + fail-closed routing"
git tag v1.0.0 -m "v1.0.0 — baseline stable"
git push --tags origin

cd "$PERPETUA_TOOLS_PATH"
git tag v1.1.1 -m "v1.1.1 — security hardening + fail-closed routing"
git push --tags origin
```

## Windows reference (already done — do not re-run unless regressing)

| Check | Command (PowerShell, on Win) |
|-------|------------------------------|
| Partner PATH | `.\platform\windows\ensure-partner-cli-paths.ps1` |
| Canaries | `python bin\orama-system\skills\hermes-harness\scripts\verify_partner_canaries.py` |
| Hardware policy | `.\platform\windows\start.ps1 --hardware-policy` |
| Codex dispatch | `python bin\orama-system\skills\hermes-harness\scripts\dispatch_codex_partner.py --dry-run --pytest tests\test_verify_partner_canaries.py` |

## Related docs

| Doc | Repo |
|-----|------|
| [Windows handoff](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/2026-06-28-windows-handoff.md) | Perpetua-Tools |
| [Security hardening pre-v2](2026-06-27-security-hardening-pre-v2.md) | orama-system |
| [Hermes onboarding](2026-06-24-hermes-harness-canonical-onboarding.md) | orama-system |
| [Codex v0.142 dispatch](../bin/orama-system/references/codex-cli-v142-dispatch.md) | orama-system |

## Punch list (Mac operator)

- [ ] `git pull --ff-only` both repos on `main`
- [ ] `start.sh --status` green
- [ ] Ollama `qwen3.5:9b-nvfp4` + `bge-m3`
- [ ] `openclaw.gateway-auth-token` in Keychain
- [ ] Win LM Studio LAN reachable from Mac (`curl` probes)
- [ ] `start.sh --hardware-policy` cross-harness green
- [ ] T5 tags `v1.1.1` / `v1.0.0` both repos
