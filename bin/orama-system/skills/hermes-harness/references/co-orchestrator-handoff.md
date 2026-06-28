# Co-orchestrator handoff — Win ↔ Mac (2026-06-28)

**Fan-out ID:** `2026-06-28-co-orchestrator-001`  
**Mode:** file inbox (no streaming) — each host runs local agents only

## Role split

| Host | Agents | Assignment |
|------|--------|------------|
| **Mac** | Hermes, mac-researcher, local MLX | `autoresearch/hypothesis` — draft ranked hypotheses |
| **Win** | Codex, AGY, cursor-agent, lmstudio-win coder | `autoresearch/gpu-run` — execute benchmarks, drop results back |

## Win operators (this host)

```powershell
# After reading Mac hypothesis from peer inbox:
codex exec "Summarize hypothesis file and propose GPU benchmark plan"
cursor-agent -p "Read inbox hypothesis; outline Win 27B test matrix"
agy --print "AGY: cross-check hypothesis vs hardware policy"
```

## Mac operators (peer)

```bash
git pull --ff-only origin main
./start.sh --stop && ./start.sh --lan-peer --no-open
python3 bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py list --peer
python3 bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py read --peer --name mac-hypothesis.md
```

## Reply protocol

When done, drop markdown to peer inbox:

```bash
# Mac → Win
python3 .../lan_peer_assign.py --peer drop --file ./results/hypothesis-summary.md --assignee win --topic autoresearch/hypothesis-done
```

```powershell
# Win → Mac
python ...\lan_peer_assign.py --peer drop --file .\results\gpu-results.md --assignee mac --topic autoresearch/gpu-done
```

## What is NOT remote yet

- Hermes/Codex/cursor-agent do **not** execute on the peer host over HTTP
- Co-orchestration = **split topics + file handoff**; each machine runs its own PATH agents locally
