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
   - Set `_phase = PHASE_DRAINING` under lock.
   - Call `self.shutdown()` to break the socket accept loop.
   - Await `_inflight_cond` drain with a bounded timeout (e.g. 5.0s).
   - If the drain times out, transition to `PHASE_CLOSED` under lock (fencing any queued worker from upstream dispatch) and have the launcher exit `124` to settle as unknown spend (the child process has already terminated).
3. **Single Fail-Closed Funnel (`_fail_closed` + `_fetch_upstream`):**
   Never fragment error handling across parallel catch blocks. All transport errors, socket
   timeouts, non-definitive upstream status codes, and body reading failures must funnel into
   `classify_chat_outcome()` and `_fail_closed()` / `_reject_unaccounted()`, debiting the full clamped
   reservation and halting the child process.
4. **Proactive Provider Budget Clamping Over Reactive Pipe Sniffing:**
   Do not rely solely on post-generation token counting. Intercept outgoing `/chat/completions`
   payloads and clamp `max_tokens` / `max_completion_tokens` to `min(requested, remaining)`. Force
   the upstream provider to truncate generation at the exact remaining budget boundary.
5. **High-Water-Mark Distributed Fencing Tokens (`claimed_at`) - PROPOSED, not delivered at the pin:**
   The target design is that a mutual-exclusion claim never degrades to a plain `bool` or `None`:
   it returns the claim timestamp (`claimed_at: float`), made strictly increasing per task by a
   persistent high-water-mark table (`task_claim_hwm`) raised with `math.nextafter()`, and completion
   requires `--expected-claimed-at` (or an explicit `--unverified-legacy` opt-out) so a completion
   fences against stale same-agent or interleaved reclaims.
   **Status at the pinned Perpetua-Tools revision `8e3bf99a` (`.github/pt-dispatch-test-ref`):** none
   of the HWM table, the `nextafter` raise, the returned token, or the CLI flags exist.
   `queue_claim` still returns `bool | None`, the claim path stores `time.time()` in `task_claims`,
   and `expected_claimed_at` is only an *optional* keyword of `queue_complete` /
   `release_claim_with_event` (the L-1r same-agent-reclaim guard). No delivering commit is named
   here because none is pinned; do not describe the fencing above as enforced until the pin is
   moved to a commit that provides it and that commit is named in this card.

---

## 3. In What Ways Did We Differ? (Comparative Matrix)

| Dimension | Original PR (Before Remediation) | CodeRabbit Suggestions | Perplexity Design | Our Enduring Final Solution |
| :--- | :--- | :--- | :--- | :--- |
| **Supervision & Accounting** | Legacy pipe/stdout scraping with process-guard regexes. | Reader thread join timeouts with fallback exit error. | Loopback HTTP proxy with condition variable drain. | Loopback HTTP proxy with synchronous socket admission & pre-forward provider clamping. |
| **Over-Budget Prevention** | Reactive: kill process after buffer parses over-budget tokens. | Reactive: terminate child once accounting thread catches up. | Pre-forward clamping, but allowed 503 premature rejection during drain. | Proactive clamping to remaining budget (`max_tokens = min(existing, remaining)`); drains in-flight requests cleanly. |
| **Transport & Error Bodies (`HTTPError.read`)** | Unhandled; leaked raw exceptions or exited cleanly. | Flagged duplicate handlers; missed `HTTPError.read()` timeout escape. | Captured in notes, but split across multiple handler paths. | Unified `_read_upstream_response()` wrapping both 2xx and error streams into `_fail_closed("upstream_transport", ...)`. |
| **Accept-to-Dispatch Lifecycle** | Unchecked; prone to SIGPIPE and orphan processes. | Suggested bounded thread drain, but left dispatch window open. | Checked `_accepting` in `_admit_chat_request`, causing premature 503 drops. | Synchronous admission in `process_request()` + two-phase `stop_and_drain()`. |
| **Task Queue Claim Return** | Inconsistent / returned None without fencing semantics. | Flagged signature discrepancy, proposed boolean / None returns. | Reverted to None to pass characterization tests. | **Proposed, not at the pin (`8e3bf99a`):** strictly increasing `claimed_at: float` token via a persistent `task_claim_hwm` table and required `--expected-claimed-at`. As pinned: `queue_claim` returns `bool \| None` and `expected_claimed_at` is an optional L-1r guard on completion. |
| **Memory Record Hygiene** | Stale process-guard claims persisted in `LESSONS.md`. | Flagged outdated text in `LESSONS.md` files. | Proposed manual diffs or partial replacements. | Tooling-driven graduation using `graduate.py --supersedes`; preserves all invariants append-only. |

---

## 4. Detailed Narrative Breakdown

### A. Differences from CodeRabbit Suggestions

1. **Proactive Budget Clamping vs. Passive Counting:** CodeRabbit suggested waiting for reader
   threads to drain and account for output chunks. We implemented proactive pre-forward token
   clamping (`max_tokens = min(existing, remaining)`), forcing the upstream provider to truncate
   generation at the exact remaining budget boundary.
2. **Architectural Shift vs. Reader Thread Patches:** CodeRabbit suggested tweaking `join()`
   timeouts on stdout reader threads. We rejected patching subprocess pipes (which suffer from OS
   buffer deadlocks and truncation) and re-architected the supervision boundary into a standard-library
   loopback HTTP reverse proxy.
3. **Unified Transport Funnel vs. Handler Duplication:** CodeRabbit noted code duplication between
   proxy handlers. We extracted `_fail_closed()` and `_read_upstream_response()`. Crucially,
   CodeRabbit missed that `exc.read()` on `HTTPError` could raise a socket timeout and escape the
   outer try block; our unified reader wraps both normal and error streams into exit `124`.
4. **Preserving Distributed Claim Fencing vs. Shallow Test Placating:** When tests failed after
   changing `queue_claim` return type, reverting to `return None` satisfied the legacy
   characterization test but destroyed distributed fencing safety. We argued for the distributed-systems
   invariant that `queue_claim` should return a monotonic fencing timestamp (`claim_ts: float`);
   that remains proposed at the pinned revision (see invariant 5).

### B. Differences from Perplexity Design

1. **Admission vs. Drain Race Resolution:** The Perplexity design draft suggested checking
   `if not self.server.is_accepting(): self._reject(503)` inside `_admit_chat_request()`. Live testing
   proved this prematurely aborted valid in-flight requests that were accepted right before
   `stop_and_drain()` was called. We enforced admission exclusively at the socket level in
   `AccountingProxyServer.process_request()`.
2. **Preservation of Historical Domain Invariants:** Perplexity's suggested lesson update for
   `lesson_8100266e8176` dropped critical operational requirements (such as Cline 3.0.74
   `tokenSource: "manual"` and millisecond UTC `updatedAt` ending in `Z`). We enforced that
   superseding lessons must carry forward all historical domain constraints.
3. **Private Topology Linter Compliance:** The Perplexity diff draft included literal loopback IP
   strings in tests, failing the pre-commit hygiene hook (`prohibited private-range literal`). We
   referenced `launcher.LOOPBACK_HOST`.

### C. Differences from the Original PR (Before Any Remediation)

1. **Orama PR #533:** Replaced unverified subprocess pipes, stdout scraping, and regex parsing with
   a high-performance loopback HTTP proxy intercepting `/v1/chat/completions`, stripping query
   parameters, rejecting non-allowlisted routes with 403, rejecting post-breach retries with 429,
   clamping upstream max tokens, and closing all shutdown and transport races with fail-closed exit 124.
2. **Perpetua-Tools PR #525:** At the pinned revision `8e3bf99a` it atomically records agent
   heartbeats upon task claim, adds the optional `expected_claimed_at` L-1r guard to completion and
   release, and supersedes obsolete process-guard lessons with verified proxy contracts. The returned
   `claimed_at` token, the `task_claim_hwm` table and the required `--expected-claimed-at` flag are
   proposed follow-ups, not part of that revision.

---

## 4. Remediation Push Policy (Strict One-Push Batching)

- **Local Batching:** Never push intermediate commits one-by-one to remote branches.
- **Full Offline Verification:** All test suites, append-only memory checks, markdown linting,
  and private literal scans must pass 100% locally before pushing.
- **Single Remote Push:** Push exactly once per repository to avoid re-triggering automated
  review bots into thrashing diff cycles.
- **Paced Thread Replies:** Reply to bot review comments with minimum 32-second delays between
  GraphQL mutations to avoid API abuse flags.
