# Fleet: gossip unify + pre-PR #222 backup (Mac first)

**Fan-out:** coord-033  
**Status:** ACTIVE — operator run now on Mac, then Win 3080 + 5080  
**From:** mac-orchestrator  
**Date:** 2026-07-27

## SSoT (full runbook)

`OpenClaw/references/2026-07-27-pre-pr222-operator-backup-runbook.md`  
(inbox summary below; agents read inbox + SSoT for detail)

## Audience

| Lane | Action |
|------|--------|
| `mac-orchestrator` | **Mac first** — backup + adopt gossip secret + harmonize orama+PT |
| `win-cursor` | After Mac: paste same secret into 3080/5080 repo-local env policy files, restart mesh |
| `win-coder` / `win-autoresearcher` | Informational — verify gossip after operator paste |
| `hermes` | Win: `hermes backup` before #222; no gossip secret in chat/logs |

---

## Best first step: Mac orchestrator (do this now)

**Why Mac first:** Mac is the coordination hub; `ensure_local_mesh_secrets.py` harmonizes **orama + Perpetua-Tools** sibling repo-local env policy files when `PERPETUA_TOOLS_PATH` is set. Win boxes only receive the **same** value OOB after Mac is canonical.

### 1. Sync `main` (both repos on Mac)

```bash
export ORAMA_SYSTEM_PATH="<orama-system>"
export PERPETUA_TOOLS_PATH="<Perpetua-Tools>"
cd "$ORAMA_SYSTEM_PATH" && git pull --ff-only origin main
cd "$PERPETUA_TOOLS_PATH" && git pull --ff-only origin main
```

### 2. Phase A topology backup (if not done today)

```bash
cd "$ORAMA_SYSTEM_PATH"
python3 scripts/mesh/lan_topology_archive.py --backup --ref origin/main
```

### 3. Adopt or generate gossip secret (Mac — orama + PT harmonized)

```bash
cd "$ORAMA_SYSTEM_PATH"
python3 scripts/mesh/ensure_local_mesh_secrets.py
```

This fills **missing/empty** `GOSSIP_SHARED_SECRET` in:
- orama-system repo-local env policy file
- Perpetua-Tools repo-local env policy file (when sibling path set)
- `.local/mesh-secrets.json` on both repos

**Do not** run `--force` unless rotating. **Do not** log or paste the value in GossipBus.

### 4. Copy secret OOB to Win nodes

Use 1Password / encrypted channel / USB — **never** git, email, Slack, or agent comms.

On each Win box (3080, then 5080):

```powershell
# Edit repo-local env policy file — set GOSSIP_SHARED_SECRET=<same value as Mac>
cd $env:ORAMA_SYSTEM_PATH
python scripts\mesh\ensure_local_mesh_secrets.py   # harmonizes JSON mirror; won't rotate if set
```

If PT on Win: same in Perpetua-Tools repo-local env policy file or set `PERPETUA_TOOLS_PATH` and re-run from orama.

### 5. Restart mesh (all nodes)

```bash
# Mac
cd "$ORAMA_SYSTEM_PATH" && ./start.sh
```

```powershell
# Win 3080 / 5080
powershell -File .\platform\windows\start.ps1
```

### 6. Verify gossip parity

```bash
# Mac — PT gossip tail (needs matching secret on PT when PT_BIND_LAN=1)
cd "$PERPETUA_TOOLS_PATH"
python3 scripts/agent_coordination.py log mac-orchestrator "coord-033 gossip-unify smoke test"
python3 orchestrator/gossip_bus.py tail --limit 3   # or coordination tail if wired
```

Win: portal up; `install-hermes-harness.ps1 -RunDoctor` after mesh restart.

**Acceptance:** same secret on all 3 nodes; `start.sh`/`start.ps1` OK on LAN; no gossip 403 storm.

---

## What next (after gossip unified)

1. **Phase A acceptance** on all 3 — archive file exists, `repo_hygiene.py` passes  
2. **Mesh verify** — discover.py / portal reaches 3080 + 5080 LMS  
3. **Hermes backup** on Win — `hermes backup` before #222  
4. **Merge orama #222** only when steps 1–3 green on **every** node  

---

## Agent comms note

- **Mesh `GOSSIP_SHARED_SECRET`** = fleet LAN auth (HTTP gossip endpoints, discovery handshake)  
- **GossipBus / `agent_coordination.py log`** = intra-machine whiteboard (six lanes) — separate channel; this coord-033 broadcast uses GossipBus **pointers only**, never secret values  

Read this inbox file; do not rely on one-line GossipBus alone.
