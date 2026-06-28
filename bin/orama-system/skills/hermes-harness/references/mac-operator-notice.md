# Mac operator — read this (from Win)

**Topic:** ops/co-orchestrator  
**Assignee:** mac  
**Fan-out:** 2026-06-28-memory-landmark

## Step 1 — pull PT memory (lessons + where-to-look cards)

```bash
cd "$PERPETUA_TOOLS_PATH" && git pull --rebase origin main
cd "$ORAMA_SYSTEM_PATH" && git pull --rebase origin main
```

## Step 2 — Mac co-orchestrator READ FIRST

```bash
cat "$PERPETUA_TOOLS_PATH/.agent/memory/working/MAC_CO_ORCHESTRATOR_WHERE_TO_LOOK_2026-06-28.md"
```

## Step 3 — Mac subagents (mac-researcher, orchestrator)

```bash
cat "$PERPETUA_TOOLS_PATH/.agent/memory/working/MAC_SUBAGENTS_WHERE_TO_LOOK_2026-06-28.md"
```

## Step 4 — rendered lesson brain

```bash
cat "$PERPETUA_TOOLS_PATH/.agent/memory/working/CO_ORCHESTRATOR_LAN_PEER_2026-06-28.md"
# lessons: $PERPETUA_TOOLS_PATH/.agent/memory/semantic/LESSONS.md
```

## orama playbook

https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/hermes-harness/references/mac-co-orchestrator-playbook.md

## Mac inference

**Ollama warm** (`:11434`) = primary. **LM Studio passive** (`:1234`) = probe only.

## Restart + peer inbox

```bash
./start.sh --stop && ./start.sh --lan-peer --no-open
python3 bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py list --peer
```
