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
| 9. No breaking changes | HOLDS | full orama suite **1323 passed / 6 skipped** WITH this run's changes |
| 10. Endpoints auth-gated | BUILT (prior) + live-observed | 401 tests green; live portal answered `{"detail":"Unauthorized"}` unauthenticated |

## 4. Live fleet observed during the run

3-node TRUE FLEET at run time: Mac (Ollama `qwen3.5:9b-nvfp4` warm) +
RTX 3080 (LM Studio, qwen3.5-27b-distilled) + RTX 5080 (LM Studio,
gemma-4-26b + 27B mirror), peer addresses per the live discovery state file
(never hardcoded here). Resolver P-chain returned the discovery-fresh Win IP
live. Both Win peers served real review inference during the run (§2).

## 5. Residual items (explicitly not silently dropped)

- `start.sh` full roundtrip: launched; `fleet_topology.json` not yet written
  at ledger time (services still initializing) — completion + FLEET-mode
  banner verification recorded in the PR conversation when the run settles.
- 3080 relay-client review: pending collection (see §2).
- Win-side E2E kill/restart degradation test: requires a Win-side actor;
  instruction card already dropped to the lan_peer outbox.
- PT-side: zero changes needed this run (its mesh pieces were green on
  current main); PT lessons entry via learn.py accompanies this branch's PR.
