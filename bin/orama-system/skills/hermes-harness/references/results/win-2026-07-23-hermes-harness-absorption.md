# Win — hermes-harness local fork absorbed (coord-027)

**Status:** DONE  
**Commit:** `c93c6da9` on `orama-system` `main`

## What landed (canonical superset)

Hermes-local `~/.hermes/skills/hermes-harness/` fork content merged into orama canonical:

| Hermes-local artifact | Canonical target |
|-----------------------|------------------|
| `references/plan-integration.md` | `references/plan-integration.md` (7-rule plan merge) |
| `references/lan-peer-coordination.md` | `references/lan-peer-coordination.md` (sanitized: no hardcoded IPs) |
| `references/update-all-agents-comms.md` (stub) | `references/update-all-agents-comms.md` (full recipe) |
| SKILL § launcher/auth/LAN mirror | `windows-hermes-setup.md` + `SKILL.md` § Plan integration |

## Local Hermes action (Win)

- `install_hermes_thin_skills.py --install --verify` — harness redirect stub applied
- `hermes curator pin hermes-harness` + `windows-hermes-setup` — self-improve blocked from re-forking

## Mac peer

`git pull --ff-only origin main` — no endpoint change; new reference docs only.
