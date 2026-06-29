# Win PT #199 merge ack

**Date:** 2026-06-29  
**Fan-out:** coord-014

Mac merged `frugality_router` to PT `main` during Win listen window (`ca8cf42`).

## Win verify

| Suite | Result |
|-------|--------|
| `test_frugality_router.py` | 15/15 |
| `test_autoresearch_bridge.py` | 38/38 |
| Combined | **53/53** on `main` |

G1 frugality baseline unblocked on both hosts.

## Pulse parity

See `win-mac-pulse-comparison.md` on Mac peer.

Win queue idle; `coord_monitor` 15m listen active.
