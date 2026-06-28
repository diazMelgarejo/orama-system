# Autoresearch hypothesis summary

**Fan-out:** 2026-06-28-autoresearch-001  
**Author:** mac (mac-researcher)  
**Topic:** autoresearch/hypothesis-done

## Ranked hypotheses

### H1 — File inbox beats WS for multi-agent fan-out (HIGH)

**Claim:** Markdown drops via `/api/peer-file` reduce token waste vs streaming hypotheses over `ws/portal-peer`.

**Test:** Compare bytes on wire for a 2 KB hypothesis file (one POST) vs 10 WS heartbeat+chunk envelopes.

**Falsify:** If peer-file POST fails >20% on LAN while ws-peer PASS, file handoff is not reliable enough.

### H2 — Joint auth mode is stable for bidirectional probe (MEDIUM)

**Claim:** `auth_mode: joint` (PT + orama lane tokens) sustains Mac→Win and Win→Mac inbox drops without token rotation.

**Test:** 10 consecutive `lan_peer_assign.py drop --peer` + `list --peer` cycles; zero 401s.

**Falsify:** Any 401 after discovery refresh without explicit token change.

### H3 — Win 27B improves autoresearch iteration latency vs Mac 9B MLX (MEDIUM)

**Claim:** For coding-loop tasks routed to `win-rtx3080`, end-to-end hypothesis→benchmark→result is faster on Win despite LAN file round-trip.

**Test:** Win autoresearcher runs benchmark matrix on H1/H2; Mac times wall-clock from fan-out to `gpu-results.md` in local inbox.

**Falsify:** Win GPU run + file drop slower than Mac-local MLX run for same prompt class.

## Win action items

1. Read this file from Mac peer inbox (`hypothesis-summary.md`)
2. Execute H3 benchmark matrix on `qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2`
3. Drop `gpu-results.md` to Mac peer inbox with timings per hypothesis

## Mac action items (done)

- [x] Draft hypotheses with falsification criteria
- [x] Drop to Win peer inbox (this file)
