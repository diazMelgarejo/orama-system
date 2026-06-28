# macOS co-orchestrator playbook — cursor-agent on Mac and Win

> **SSOT:** This file. **Operator index:** [`lan-peer-self-talk.md`](lan-peer-self-talk.md) §F.  
> **Win mirror:** [`co-orchestrator-handoff.md`](co-orchestrator-handoff.md)  
> **PT memory (Mac + subagents):** `Perpetua-Tools/.agent/memory/working/MAC_CO_ORCHESTRATOR_WHERE_TO_LOOK_2026-06-28.md`  
> **PT subagents:** `Perpetua-Tools/.agent/memory/working/MAC_SUBAGENTS_WHERE_TO_LOOK_2026-06-28.md`  
> **Shared landmark:** `Perpetua-Tools/.agent/memory/working/CO_ORCHESTRATOR_LAN_PEER_2026-06-28.md`  
> **Rendered lessons:** `Perpetua-Tools/.agent/memory/semantic/LESSONS.md`  
> **GitHub:** https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/hermes-harness/references/mac-co-orchestrator-playbook.md

**Mode:** file inbox handoff — each host runs **local** `cursor-agent`, Codex, AGY, and coder. No remote agent RPC.

**CLI (`>= 9f89051`):** put `--peer` **on the subcommand**: `list --peer`, `read --peer --name …`, `drop --peer --file …`.

---

## 0. One-time Mac setup

```bash
export ORAMA_SYSTEM_PATH="$(git -C /path/to/orama-system rev-parse --show-toplevel)"
export PERPETUA_TOOLS_PATH="$(git -C /path/to/Perpetua-Tools rev-parse --show-toplevel)"
cd "$ORAMA_SYSTEM_PATH"

git fetch origin --prune && git checkout main && git pull --ff-only origin main
./start.sh --stop && ./start.sh --lan-peer --no-open

# cursor-agent (if missing)
curl https://cursor.com/install -fsS | bash
cursor-agent --version
cursor-agent login   # once per machine

python3 bin/orama-system/skills/hermes-harness/scripts/probe_lan_peer.py --json
```

**Pass criteria:** `portal-health`, `portal-status`, `peer-lmstudio` PASS. Mac **must** expose `/api/peer-file` (restart after pull).

**Mac inference (2026-06-28):** Ollama **warm** on `:11434` (primary). LM Studio **passive-only** on `:1234` — use `ollama-mac` for Mac cursor-agent / mac-researcher runs; do not treat `peer-lmstudio` PASS as “Mac coder is LMS.”

---

## 1. Mac assigns work (fan-out)

```bash
cd "$ORAMA_SYSTEM_PATH"

# Autoresearch: Mac hypothesis / Win GPU
python3 bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py fanout \
  --manifest bin/orama-system/skills/hermes-harness/references/autoresearch-fanout-example.json

# Self-improve split
python3 bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py fanout \
  --manifest bin/orama-system/skills/hermes-harness/references/self-improve-fanout-2026-06-28.json
```

Mac keeps `mac-*` assignments locally; Win-bound files POST to Win peer inbox.

**Portal monitor:** platform-specific inbox UI on **both** hosts:

| Host | URL |
|------|-----|
| Mac | `http://localhost:8002/co-orchestration/macos` |
| Win | `http://localhost:8002/co-orchestration/windows` |
| Either | `http://localhost:8002/co-orchestration` (auto skin) |

Bidirectional inbox queue, direction badges (inbound/outbound), fan-out filter, click-to-preview markdown. Navbar: **Co-orchestration inbox** (Mac links to `/macos`).

**Code:** `src/orama_system/portals/co_orchestration_macos.py` · Win parallel: `co_orchestration_windows.py` · `platform/macos/README.md`

---

## 2. Mac reads Win replies

```bash
python3 bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py list --peer

python3 bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py read --peer \
  --name gpu-results.md
```

---

## 3. Mac cursor-agent on Mac tasks

```bash
INBOX="$HOME/.openclaw/state/lan_peer/inbox"
python3 bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py list

cursor-agent --print --model composer-2.5 --trust \
  "Read $INBOX/mac-hypothesis.md. Draft ranked hypotheses with falsification criteria. Write to /tmp/hypothesis-summary.md"

python3 bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py drop --peer \
  --file /tmp/hypothesis-summary.md \
  --assignee win --topic autoresearch/hypothesis-done \
  --fanout-id 2026-06-28-autoresearch-001
```

---

## 4. Win cursor-agent on Win tasks (peer operator)

```powershell
cd $env:ORAMA_SYSTEM_PATH
python bin\orama-system\skills\hermes-harness\scripts\lan_peer_assign.py read --name hypothesis-summary.md

cursor-agent --print --model composer-2.5 --trust `
  "Read inbox hypothesis-summary.md. Outline Win 27B benchmark matrix; write tasks\gpu-results.md"

python bin\orama-system\skills\hermes-harness\scripts\lan_peer_assign.py drop --peer `
  --file .\tasks\gpu-results.md --assignee mac --topic autoresearch/results `
  --fanout-id 2026-06-28-autoresearch-001
```

Win also has: `codex`, `agy`, lmstudio-win `:1234` — same read → run locally → drop-back loop.

---

## 5. Division of labour

| Role | Mac | Win |
|------|-----|-----|
| Hypothesis / lessons | draft, review | read inbox |
| GPU benchmarks | read results | execute on 27B |
| Code review sections | assign topics | review assigned files |
| Reply | `drop --peer` → Win | `drop --peer` → Mac |

---

## 6. Self-improve gate

Draft: `~/.openclaw/state/lan_peer/inbox/mac-lessons-draft.md` (or Win inbox for cross-review).

Per `/self-improve` rules: **nothing** commits to `docs/LESSONS.md` until operator replies **`approve lessons`**.

---

## 7. Further reading

| Doc | Purpose |
|-----|---------|
| [`lan-peer-self-talk.md`](lan-peer-self-talk.md) | Operator SSOT, probe pass criteria |
| [`co-orchestrator-handoff.md`](co-orchestrator-handoff.md) | Win-side handoff summary |
| [`cursor-agent/SKILL.md`](../../cursor-agent/SKILL.md) | Install, models, fanout patterns |
| [`autoresearch-fanout-example.json`](autoresearch-fanout-example.json) | Sample fan-out manifest |
| [`docs/guides/lan-peer-bidirectional-talk-2026-06-28.md`](../../../../docs/guides/lan-peer-bidirectional-talk-2026-06-28.md) | Attempt log and layer model |
| **PT** `Perpetua-Tools/.agent/memory/working/CO_ORCHESTRATOR_LAN_PEER_2026-06-28.md` | Lesson landmark + subagent routing |
| **PT** `Perpetua-Tools/.agent/memory/semantic/DOMAIN_KNOWLEDGE.md` | Co-orchestrator gold nuggets |
| **PT** `Perpetua-Tools/docs/LESSONS.md` | Human-readable co-orchestrator section |

---

## 8. Mac unblock checklist (bidirectional)

If Win gets `HTTP 404 /api/peer-file` when dropping to Mac:

```bash
cd "$ORAMA_SYSTEM_PATH"
git pull --ff-only origin main
./start.sh --stop && ./start.sh --lan-peer --no-open
python3 bin/orama-system/skills/hermes-harness/scripts/probe_lan_peer.py --json
```

Then Win re-runs `drop --peer` for pending results.
