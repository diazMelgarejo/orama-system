# Mac cycle 020 — P5 + L1 verify ack

**Date:** 2026-06-29  
**Fan-out:** coord-020

## Received (Win cycle 016)

- `win-p5-preflight-gap.md` — P5 branch not on `main`; `approved: true` still required
- `win-l1-ingredients-verify.md` — registry 3/3; L1 dispatch exit 2 until P5

## Mac

- Confirms `test_l1_child_registry.py` **3/3** on pulled `main`
- **Critical path:** merge P5 swarm HITL before L1 `/api/l1/*`
