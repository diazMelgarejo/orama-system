# Mac operator — read this (from Win)

**Topic:** ops/co-orchestrator  
**Assignee:** mac  
**Fan-out:** 2026-06-28-coord-playbook

## Action

1. `git pull --ff-only origin main` in orama-system (need `ae6d2fd` — mac co-orchestrator playbook)
2. Open the SSOT playbook:

   **Repo path:**
   `bin/orama-system/skills/hermes-harness/references/mac-co-orchestrator-playbook.md`

   **GitHub:**
   https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/hermes-harness/references/mac-co-orchestrator-playbook.md

3. Restart if peer-file still 404:
   ```bash
   ./start.sh --stop && ./start.sh --lan-peer --no-open
   ```

4. Confirm bidirectional inbox:
   ```bash
   python3 bin/orama-system/skills/hermes-harness/scripts/lan_peer_assign.py list --peer
   ```

5. Run cursor-agent on Mac tasks per §3 of the playbook; drop results with `drop --peer`.

## Self-improve

Review `mac-lessons-draft.md` in inbox. Reply **`approve lessons`** to land in `docs/LESSONS.md`.
