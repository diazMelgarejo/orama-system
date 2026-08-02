# Cross-repo links in skills

> **Use when:** a skill card in orama-system points at canonical content in
> Perpetua-Tools, AlphaClaw, periscope, or another sibling repo.

## Rule

**Canonical cross-repo references are GitHub `main` markdown links — never
sibling-folder paths** like `Perpetua-Tools/config/SKILL.md` or
`../Perpetua-Tools/...`.

Sibling layouts vary by machine (`~/Projects`, `OPENCLAW_HOME`, monorepo
wrappers like `perplexity-api/Perpetua-Tools`, separate clones). GitHub URLs are
stable; local agents resolve them to a checkout.

## Pattern

| Layer | Form |
| ----- | ---- |
| **Canonical (skills + docs)** | `[relative/path.md](https://github.com/diazMelgarejo/<repo>/blob/main/relative/path.md)` |
| **Local resolution** | Same relative path inside your clone — resolve root via `$PERPETUATOOLSROOT`, `$PERPETUA_TOOLS_ROOT`, `$PERPETUA_TOOLS_PATH` (see `scripts/discover.py`), or clone from the repo URL |
| **Runtime shell** | `PT_ROOT="${PERPETUATOOLSROOT:-${PERPETUA_TOOLS_ROOT:-${PERPETUA_TOOLS_PATH:-...}}}"` — not hardcoded `../Perpetua-Tools` |

## Perpetua-Tools (orama → PT)

| Stub slug | GitHub canonical |
| --------- | ---------------- |
| `perpetua-tools` | [`SKILL.md`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/SKILL.md) |
| `perpetua-config` | [`config/SKILL.md`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/config/SKILL.md) |
| `perpetua-startup-intelligence` | [`hardware/startup-intelligence/SKILL.md`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/hardware/startup-intelligence/SKILL.md) |
| Hardware policy SSoT | [`config/model_hardware_policy.yml`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/config/model_hardware_policy.yml) |
| Local runtime overlay | [`config/LOCAL-RUNTIME-OVERLAY.md`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/config/LOCAL-RUNTIME-OVERLAY.md) |

Clone when missing:

```bash
git clone https://github.com/diazMelgarejo/Perpetua-Tools.git
export PERPETUATOOLSROOT="$(git -C Perpetua-Tools rev-parse --show-toplevel)"
```

## orama-system (PT → orama)

PT skills that reference orama methodology should use
`https://github.com/diazMelgarejo/orama-system/blob/main/...` — same local-resolution rule.

## Do not

- Git-track cross-repo directory symlinks inside orama-system (use thin redirect stubs).
- Assume `Perpetua-Tools` sits next to `orama-system` on disk.
- Put workstation-absolute paths in skills (`/Users/...`).
