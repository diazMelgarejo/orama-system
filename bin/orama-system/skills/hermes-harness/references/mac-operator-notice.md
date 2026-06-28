# Mac operator — read this (from Win)

**Topic:** ops/co-orchestrator  
**Assignee:** mac  
**Fan-out:** 2026-06-28-coord-playbook

## Action

1. **Pull both repos:**
   ```bash
   cd "$ORAMA_SYSTEM_PATH" && git pull --ff-only origin main
   cd "$PERPETUA_TOOLS_PATH" && git pull --ff-only origin main
   ```

2. **Read PT memory (co-orchestrator + subagents):**
   ```bash
   cat "$PERPETUA_TOOLS_PATH/.agent/memory/working/CO_ORCHESTRATOR_LAN_PEER_2026-06-28.md"
   ```
   Also: `.agent/memory/semantic/LESSONS.md` (last 8 lessons) · `DOMAIN_KNOWLEDGE.md` § co-orchestrator

3. **Open orama playbook:**

   **Repo:** `bin/orama-system/skills/hermes-harness/references/mac-co-orchestrator-playbook.md`  
   **GitHub:** https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/hermes-harness/references/mac-co-orchestrator-playbook.md

4. **Restart if peer-file still 404:**
   ```bash
   ./start.sh --stop && ./start.sh --lan-peer --no-open
   ```

5. **Read Win deliverables** (after peer-file live):
   ```bash
   python3 bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py list --peer
   python3 bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py read --peer --name gpu-results.md
   ```

6. **cursor-agent** — point at PT working card + inbox per playbook §3.

## Lessons landed

Mac+Win co-orchestrator lessons are in **PT `.agent/memory`** (`lessons.jsonl` + rendered `LESSONS.md`). Human index: `Perpetua-Tools/docs/LESSONS.md` §2026-06-28 co-orchestrator.

## Self-improve

Merged into PT `.agent` memory. `docs/LESSONS.md` human section updated.
