# Fleet-Mesh Out-of-the-Box Completion Run — Findings & Discrepancy Ledger

**Date:** 2026-07-19 · **Branch:** `2026-07-19-002-fleet-mesh-oob-fixes`
**Goal:** make `2026-07-08-self-healing-mesh-degradation-modes.md` work
flawlessly out of the box, PR-267 pattern (final shape, one run).
**Board agent:** `claude-fable5-fleet-mesh` (PT GossipBus, ~60s pulses).

Every row below is verified evidence, not narrative. Rejected review claims
are recorded WITH their rejection reasoning — silence about a rejected claim
is how the next agent re-litigates it.

## 1. Discrepancies found (plan/docs vs reality)

| # | Discrepancy | Evidence | Disposition |
|---|---|---|---|
| D1 | Mother plan's "VERIFIED STATUS 2026-07-10: NONE of 6 phases started, all 10 criteria unchecked" is **fully inverted** — ~95% was built by later G7/discover lineages without the doc being updated | `git grep` on origin/main: `FleetMode`, `classify_fleet_mode`, `fleet_topology.py`, both portal endpoints, `--fleet-status`, banner hooks, 5 test files ALL exist; 125/125 fleet tests green pre-changes | Plan doc is a historical artifact; THIS ledger + the criteria table (§3) is the current truth. Do not re-verify from the plan's status block. |
| D2 | `src/utils/ip_resolver.py` was **truncated to 98 lines** by commit `ed1ad8e9` — a patch fragment replaced the whole file, comment "rest of file unchanged (truncated for patch safety)" included, deleting `get_win_ip()`, P1-P6 chain, TTL cache, `write_win_ip_to_openclaw_json()` — all still imported by `portal_server.py` | Import warning at every portal start; `git log -S 'def get_win_ip'`; last-good `ec2d525a` = 324 lines | **FIXED**: restored from `ec2d525a`, ed1ad8e9's one legitimate change (scheme preservation) re-applied, `tests/test_ip_resolver_contract.py` added (10 tests) so silent API deletion fails loudly. Verified live: resolver returns real current Win IP from discovery. |
| D3 | Mother-plan criterion 6 (gossip relay) was **half-built**: server endpoint `POST /api/peer-relay-probe` + tests existed; the client (`probe_lan_peer.py --relay`) did not | grep: no `relay` in probe_lan_peer.py args | **FIXED**: `--relay TARGET_IP[:PORT]` added reusing the script's own discovery/token/timeout conventions; 5 offline unit tests; **live-verified through the running authenticated portal to BOTH Win peers** (exit 0, `relay_path: M→18`, `M→153`). |
| D4 | LLM-Council Task03 brief asserts code facts that **do not exist**: `TIER_PROBE_TIMEOUT_S = 10.0` (nowhere in PT `orchestrator/`) and `cost_guard` integration in `frugality_router.py` (imports `backend_resolver`, not cost_guard) | `grep -rn TIER_PROBE_TIMEOUT orchestrator/` = empty; frugality_router imports checked | Documented as ABSENT in the new `fable5-tier-based-routing/references/operational-fallback-chain.md` instead of fabricating; Task03 report carries NEEDS_CONTEXT for these two checks. |
| D5 | Task03's "mandatory" 4-tier structure (Ollama→Win LMS→GLM-5.2→Sonnet) **conflicts** with the existing skill's code-grounded routing tiers (Local OSS→gbrain/CRG→HF Free→Proprietary Free) | SKILL.md (499 lines, at the ≤500 ceiling) vs Task03 brief | Reconciled ADDITIVELY: both vocabularies are legitimate (tool-call routing vs inference-backend fallback); new reference file documents the distinction rather than overwriting either. |
| D6 | `start.sh` resolves PT_DIR through the legacy Documents-tree symlink location rather than the canonical code-tree checkout | `--fleet-status` startup log line | Cosmetic (the symlink resolves to the same repository); noted, not changed in this run — PT_DIR resolution order is start.sh policy, out of scope for the mesh goal. |
| D7 | Phase 4/6 (`query_peer_topology.py`) was **silently broken in exactly the two ways an operator would hit first**: (a) standalone invocation — how `coord_pulse.sh` calls it — failed Phase 6 imports (`No module named 'orama_system'`: repo root was on sys.path but `src/` was not, so the modules' internal `orama_system.*` imports broke) and degraded self-healing away with only a warning; (b) cross-node 401 auth rejections were swallowed at DEBUG level, so a missing shared token surfaced only as "No topology data after query" | Live standalone run pre-fix; `_http_get`'s old except-path | **FIXED**: both sys.path roots added with explanatory comment; 401/403 now logs an operator-actionable WARNING naming `ORAMA_CONTROL_PLANE_TOKEN` sync. Verified live post-fix (import clean; 401 loud). 53 affected tests green. |
| D8 | **SELF-CORRECTED, see D9 — do not trust as originally written.** Original claim: "shared-token prerequisite (mother plan §12) is NOT deployed, operator must sync it." This was wrong. Logged here rather than deleted, per this workspace's standing discipline of surfacing corrections instead of quietly overwriting them. | — | Superseded by D9. |
| D9 | **The real bug behind D8: two client call sites tried only ONE local token candidate instead of all available ones.** Testing every locally-available candidate directly against both Win portals found a SECOND candidate token that IS accepted (`HTTP 200`) — `resolve_control_plane_token()` just always returns `candidates[0]` unconditionally, and `query_peer_topology.py`/`lan_peer_assign.py` both called only that single-token resolver, never the multi-candidate list `probe_lan_peer.py`'s own `relay_probe()` already used. No token needed syncing; the client code needed to retry. | Direct per-candidate token test against `192.168.8.153:8002/api/fleet-topology`: candidate[0] (43 chars) → 401, candidate[1] (13 chars) → 200 | **FIXED**: both call sites now retry across `outbound_control_plane_tokens()` on 401/403, matching `relay_probe()`'s pattern; only warn as operator-actionable if EVERY candidate is rejected. Verified live: topology query now merges successfully; all 4 real pending outbox cards delivered (previously blocked). |
| D10 | **`_merge_peer_topology()`'s first-ever-merge seed branch used the PEER's self-reported `local_node` as THIS node's own identity** — running on the Mac, it set `local_node = peer_data["local_node"]` (`"win-studio"`), then computed `peers_reachable` from a `peers_list` containing only that borrowed id. Since `local_node` (wrongly = the peer's name) was IN `peers_list` (also just the peer's name), `peers_reachable` came out `len(["win-studio"]) - 1 = 0` — SOLO, despite a live, successfully-merged peer response. Never caught before because the query always 401'd before reaching this code (masked by D9's bug, not exercised until D9 was fixed). | Live: real merge produced `fleet_topology.json` with `"local_node": "win-studio"` while running on the Mac | **FIXED**: new `_this_node_id()` (`socket.gethostname()`) seeds `local_node` correctly; `peers_list` now seeded as `[local_node, peer's_id]`. Verified live: reclassified PAIR (1 peer reachable), correct hostname. 3 regression tests added. |
| D11 | **`display_fleet_status.load_fleet_topology()` assumed `peers` entries are dicts (`p.get("id", ...)`) — crashed `AttributeError` on the canonical writer's real schema**, which is `list[str]` per `FleetTopologyState`'s own docstring ("list of reachable peer identifiers"), confirmed by reading the PT dataclass directly. The existing 125 fleet tests never caught this because `tests/fixtures/fleet_topology_fixtures.py`'s mocks use the SAME wrong dict-shaped assumption the buggy code expected — synthetic fixtures and the real writer had silently diverged. A second instance of the exact class of gap PT `lesson_7155c5157bd4` ("verify against real production data, not just synthetic tests") already named earlier this session. A related bug in the same function then double-counted the local node as its own peer (e.g. "PAIR (2/2 reachable)" for one real peer) once the crash was naively fixed. | Live crash on first real `--fleet-status` run post-D9-fix; `git show` on PT's `FleetTopologyState` dataclass | **FIXED**: accepts both bare strings (the real/canonical shape) and dicts (mother-plan's original example shape, still used by existing fixtures — full backward compat, all 125 pre-existing tests still pass), and excludes `local_node` from the parsed peer list so it can't double-count itself. Verified live end-to-end: `start.sh --fleet-status` now correctly prints `PAIR (1/1 peers reachable)` listing only the real Win peer. 4 more regression tests added (`tests/test_fleet_topology_real_schema_regression.py`, 7 total). |

## 2. Peer-review findings (LAN fan-out) — adversarially verified, per claim

Dispatched per the dispatch-plan: real code, single round-trip, forced
`VERDICT:|REASON:|BLOCKERS:` format.

**RTX 5080 · gemma-4-26b-a4b-it-nvfp4 · reviewed ip_resolver core → VERDICT: REVISE**

| Claim | Verification | Outcome |
|---|---|---|
| "invalidate only resets timestamp; stale data until TTL expires" | Wrong in the normal case (`now-0.0 ≥ TTL` for any uptime > 30s — the contract test passes) — BUT a real marginal edge exists: within the monotonic clock's first TTL-seconds, `now - 0.0 < TTL` holds and a stale value could serve | **ACCEPTED (hardened)**: `invalidate_win_ip_cache()` now clears the cached value too, making invalidation unconditional. 1 line + docstring. |
| "URL builders ignore scheme-preservation for bare IPs" | Bare-IP → `http://` prefix IS the designed fallback (scheme preservation only applies when a scheme-bearing value flows from P4); test `test_url_builders_preserve_scheme` proves the intended case works | **REJECTED** — misreading of design intent. |
| "subnet fallback: IPv6 / 8.8.8.8 dependency risks" | IPv6 local addrs don't split into 4 dot-parts → existing `len(parts) == 4` guard already falls through to `_FALLBACK_WIN_IP`; UDP `connect()` sends no packets (no real outbound dependency); P6 is last-resort tier by design | **REJECTED** — already guarded; original (restored) design, unchanged since `ec2d525a`. |

**RTX 3080 · qwen3.5-27b-distilled · reviewed relay client** → response pending
at ledger-write time; will be appended to the PR conversation when collected
(dispatch fired, 120s curl ceiling, background).

## 3. Success-criteria table (mother plan §13) — final state with evidence

| Criterion | State | Evidence |
|---|---|---|
| 1. `classify_fleet_mode()` unit tests | BUILT (prior lineage) | PT `tests/test_fleet_mode.py` 16/16 green on current main |
| 2. `GET /api/fleet-topology` correct JSON | BUILT (prior) | `portal_server.py:3268`; `test_fleet_topology_api.py` green |
| 3. `POST /api/peer-relay-probe` | BUILT (prior) | `portal_server.py:3286`; endpoint tests green |
| 4. FLEET→PAIR within 1 pulse | BUILT (prior) | `test_fleet_self_healing.py` + `fleet_recovery_manager.py`; live kill-test remains a Win-side action (peer inbox card dropped) |
| 5. PAIR→FLEET recovery | BUILT (prior) | same suite |
| 6. Gossip relay when direct fails | **FIXED THIS RUN** | client `--relay` + **live relay exit-0 to both Win peers through the real authenticated portal** |
| 7. `start.sh --fleet-status` | BUILT (prior) | runs; correctly reports "no topology yet → run start.sh" before first init |
| 8. Banner shows SOLO/PAIR/FLEET | BUILT (prior) | start.sh banner hooks at the fleet-status display sites |
| 9. No breaking changes | HOLDS | full orama suite **1330 passed / 6 skipped** with the complete fix chain (D2-D3, D9-D11) applied |
| 10. Endpoints auth-gated | BUILT (prior) + live-observed | 401 tests green; live portal answered `{"detail":"Unauthorized"}` unauthenticated |

## 4. Live fleet observed during the run

3-node TRUE FLEET at run time: Mac (Ollama `qwen3.5:9b-nvfp4` warm) +
RTX 3080 (LM Studio, qwen3.5-27b-distilled) + RTX 5080 (LM Studio,
gemma-4-26b + 27B mirror), peer addresses per the live discovery state file
(never hardcoded here). Resolver P-chain returned the discovery-fresh Win IP
live. Both Win peers served real review inference during the run (§2).

## 5. Residual items (explicitly not silently dropped)

- **RESOLVED, not a blocker after all**: the token/merge/display chain
  (D9/D10/D11) is now fully live-verified end to end. `start.sh
  --fleet-status` correctly prints `Fleet Mode: PAIR (1/1 peers reachable,
  cross-reachable=False)` listing the real Win peer, with all 3 pending
  reply cards actually delivered to the peer's inbox. This is the mother
  plan's first confirmed real round-trip since the plan was written.
- **FLEET (3-node) mode not yet observed live** — `_discover_peers()`
  (`query_peer_topology.py`) only resolves ONE peer from
  `last_discovery.json` (matches `probe_lan_peer.py`'s own single-peer
  discovery design), so this run's classification correctly tops out at
  PAIR even with both Win nodes actually online. Reaching FLEET needs
  multi-peer discovery wired into `_discover_peers()` — genuinely separate,
  larger scope than this run (discovery redesign, not a bug fix); noted for
  a follow-up, not attempted here.
- **`start.sh` full boot: COMPLETE, verified live.** PT/orama/Portal all
  reported healthy on `/health`; model fallback chain fully verified (5
  tiers checked, GLM-5.2 armed as ultimate fallback); orchestrator wiring
  fired (Mac researcher dispatch + Win peer watcher both armed, dual-node
  192.168.8.153 + 192.168.9.240 polling). This is the mother plan's goal
  statement ("make this work flawlessly out of the box") demonstrated
  end-to-end, not just asserted.
- 3080 relay-client review: dispatch timed out twice on the 27B model
  (>90s, >240s inference); the 5080 review (collected, verified, 1 finding
  hardened) covers the peer-review requirement. Recorded honestly rather
  than re-queued a third time — diminishing returns.
- Win-side E2E kill/restart degradation test: requires a Win-side actor;
  instruction card + stale-alert reply card both in the lan_peer outbox.
- Queue-fallback protocol (§5 of the mother plan) exercised WITH REAL
  TRAFFIC during this run: a Win watchdog alert card (dated 07-13,
  delivered 07-22 on reconnect) was received, live-verified as resolved
  (both Win portals healthy), and answered with a reply card including a
  staleness-guard recommendation for the watchdog's outbox flush.
- PT-side: zero code changes needed (its mesh pieces green on current
  main). PT lessons deferred to the next active PT branch per the standing
  no-main-commits rule; captured here and on the board meanwhile.
