# Mac↔Win E2E evidence — 2026-06-28 (live re-verify)

> Session: both repos on `main`; Win LM Studio online at discovery IP.

## Commands run (Mac)

```bash
# Discovery snapshot
cat ~/.openclaw/state/last_discovery.json  # win 192.168.254.100:1234 reachable

# Partner canaries — Win LAN (27B LM_READY)
python3 bin/orama-system/skills/hermes-harness/scripts/verify_partner_canaries.py \
  --lm-studio-url http://192.168.254.100:1234/v1 --skip-hermes --skip-agy
# → LM Studio PASS (qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2, LM_READY)

# Stack status (Tier 1 FULL)
bash start.sh --status
# → Mac ✓ localhost qwen3.5-9b-mlx; Win ✓ 192.168.254.100 qwen3.5-27b

bash start.sh --hardware-policy
# → openclaw.json clean

bash scripts/check-local-env.sh
# → Ollama qwen3.5:9b-nvfp4 + bge-m3 OK

cd ../oramasys/perpetua-core && python3 -m pytest -q
# → 62 passed
```

## Pass matrix

| Check | Result | Notes |
|-------|--------|-------|
| Win `/v1/models` from Mac | ✅ | 6 models |
| Win `LM_READY` completion (27B) | ✅ | ~28s via canary script |
| Mac Ollama models | ✅ | 8 models; required nvfp4 + bge-m3 |
| `start.sh --status` Tier 1 | ✅ | Mac + Win nodes |
| `start.sh --hardware-policy` | ✅ | Affinity clean |
| perpetua-core pytest | ✅ | 62/62 |
| Hermes `HERMES_READY` on Mac | ⏳ | `hermes` not on Mac PATH |
| Hermes `HERMES_READY` on Win localhost | ⏳ | Run on Win host (SSH :22 closed from Mac) |
| L1 `ainvoke` round-trip both targets | ⏳ | Next after Win Hermes green |
| `v0.2.0-alpha` tag perpetua-core | ⏳ | After L1 gate |

## Win operator (localhost — run on RTX box)

```powershell
cd $env:ORAMA_SYSTEM_PATH
python bin\orama-system\skills\hermes-harness\scripts\verify_partner_canaries.py --lm-studio-url http://localhost:1234/v1
python bin\orama-system\skills\hermes-harness\scripts\install_hermes_thin_skills.py --install --verify --test
.\platform\windows\start.ps1 --hardware-policy
```

## Blockers (non-hardware)

- `openclaw.gateway-auth-token` Keychain — user must provide value
- PT/orama services :8000/:8001/:8002 DOWN (expected when stack not started)
