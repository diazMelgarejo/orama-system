# Exemplar: Cross-System Bounds & Distributed Fencing Remediation

**Canonical Card:** `bin/orama-system/references/remediation-exemplar-cross-system-bounds-and-fencing.md`  
**Related Doctrine:**

- [`post-review-micro-remediation.md`](post-review-micro-remediation.md)
- [`branch-local-pattern-remediation.md`](branch-local-pattern-remediation.md)
- [`review-remediation-crosslinks.md`](review-remediation-crosslinks.md)
- [`integrative-merge.md`](../skills/oramasys-method/references/integrative-merge.md)

---

## 1. Context & Purpose

This reference card documents the **gold-standard remediation pattern** established during the
lockstep remediation of `diazMelgarejo/orama-system` PR #533 and `diazMelgarejo/Perpetua-Tools`
PR #525 (2026-11-27). It serves as an architectural exemplar for future AI agents tasked with
resolving multi-comment bot reviews (CodeRabbit, Greptile) across distributed repositories.

---

## 2. Core Architectural Lessons (The 5 Invariants)

When remediating process-supervision, spend-boundary, or distributed-state pull requests:

1. **Synchronous Socket Admission Over Post-Dispatch Tracking:**
   In multithreaded servers (`ThreadingHTTPServer`), tracking in-flight requests *after* HTTP
   dispatch creates an accept-to-dispatch race window where an early-exiting child process can
   terminate before accepted requests increment counters. Override `process_request()` to admit
   and count requests synchronously before thread spawning.
2. **Two-Phase Graceful Shutdown (`stop_and_drain`):**
   Stopping accept loops requires a strict sequence:
   - Set `_accepting = False` under lock.
   - Call `self.shutdown()` to break the socket accept loop.
   - Await `_inflight_cond` drain with a bounded timeout (e.g. 5.0s).
   - Terminate child fail-closed with exit code `124` if the drain times out.
3. **Single Fail-Closed Funnel (`_fail_closed` + `_read_upstream_response`):**
   Never fragment error handling across parallel catch blocks. All transport errors, socket
   timeouts, and `urllib.error.HTTPError.read()` body reading failures must funnel into a single
   `_fail_closed()` method that records the boundary violation and halts the child process.
4. **Proactive Provider Budget Clamping Over Reactive Pipe Sniffing:**
   Do not rely solely on post-generation token counting. Intercept outgoing `/chat/completions`
   payloads and clamp `max_tokens` / `max_completion_tokens` to `min(requested, remaining)`. Force
   the upstream provider to truncate generation at the exact remaining budget boundary.
5. **Monotonic Distributed Fencing Tokens:**
   Never degrade mutual-exclusion claim operations to plain `bool` or `None`. Always return the
   monotonic claim timestamp (`claim_ts: float`) so downstream completion calls can fence against
   stale or interleaved reclaims.

---

## 3. Comparative Evolution Matrix

| Stage | Mechanism | Failure Mode Closed |
| :--- | :--- | :--- |
| **Original PR** | Subprocess pipe sniffing & stdout regex. | Pipe buffer deadlocks, chunk truncation, signal drops. |
| **CodeRabbit Iteration** | Bounded reader joins with timeout. | Missed accept-to-dispatch race, reactive rather than proactive. |
| **Perplexity Design** | Loopback proxy with gate checks. | Premature 503 rejection of already-admitted draining requests. |
| **Enduring Solution** | Socket-level admission + proactive clamping. | Zero-race admission, verified fail-closed exit 124 funnel. |

---

## 4. Remediation Push Policy (Strict One-Push Batching)

- **Local Batching:** Never push intermediate commits one-by-one to remote branches.
- **Full Offline Verification:** All test suites, append-only memory checks, markdown linting,
  and private literal scans must pass 100% locally before pushing.
- **Single Remote Push:** Push exactly once per repository to avoid re-triggering automated
  review bots into thrashing diff cycles.
- **Paced Thread Replies:** Reply to bot review comments with minimum 32-second delays between
  GraphQL mutations to avoid API abuse flags.
