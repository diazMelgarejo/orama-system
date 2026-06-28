# Win GPU run assignment

**Assignee:** win (autoresearcher + PT autoresearch routes)  
**Topic:** autoresearch/gpu-run  
**Fan-out:** 2026-06-28-autoresearch-001

## Objective

Run GPU-side benchmarks on the Win 27B stack. Read Mac hypothesis file from peer inbox before executing.

## Steps

1. `lan_peer_assign.py --peer list` then `--peer read --name <mac-file>`
2. Execute benchmark per hypothesis priority
3. Drop `gpu-results.md` back to Mac peer inbox
