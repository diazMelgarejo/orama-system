# PR #98 Code Review — oramaclaw V1

**Date:** 2026-06-21  
**Branch:** `feat/openclaw-codex-app-server`  
**Reviewer:** AGY (Gemini 3.1 Pro High / 3.5 Flash) + CRG blast-radius analysis  
**Scope:** 100 changed files · 160 nodes directly changed · blast radius 500 nodes · risk 0.80  
**CRG:** 1993 nodes, 3411 bge-m3 embeddings, commit `6f7e066`  
**AGY lenses run:** 1 (Guidelines/Gemini Pro High), 2 (Bugs/Flash High), 5 (In-file/Flash Low)

---

## Strengths

- Clean SSA merge design with cooperative/strict/security-topology separation; security-topology always-conflict is correctly unconditional.
- PID liveness lock uses both `os.kill(0)` + psutil create_time — solid against PID reuse.
- All writes through `os.replace()` for atomicity (store, transport, portal, discover patch).
- 766 tests passing, including 11 smoke tests verifying the installed package surface.
- Auth-by-reference enforced end-to-end: no raw tokens in any committed file.
- `OfflineTransport` correctly restricts to PROVIDER + new-AGENT only at the transport layer.

---

## Critical (≥ 90)

### 1. `src/oramaclaw/store.py:110` — Stale-by-age check bypasses liveness test
The age check `stale_by_age = (time.time() - held_ts) > LOCK_STALE_SECONDS` short-circuits
`_pid_is_alive` when True. A live process running an apply for >300s will have its lock stolen.

**Fix:** Remove the age short-circuit; always call `_pid_is_alive` and only use age as the
final fallback when psutil is unavailable.

### 2. `src/oramaclaw/store.py:140` — `_release_lock` deletes lock without ownership check
If the lock was stolen (scenario in item 1), the new owner's lock file gets deleted on `close()`.

**Fix:** Read the lock file on release; only unlink if `data["pid"] == os.getpid()`.

### 3. `src/oramaclaw/engine.py:351` vs `src/oramaclaw/merge.py:135` — `resolution_id` format mismatch
`plan_resource()` produces `resource:key/path#fp12chars`; `_conflict_from_action()` in engine
produces `resource:key/path` (no fingerprint suffix). Conflicts created by engine can't be
matched by store lookups seeded from merge plan output.

**Fix:** Align both to the same format. Use the fingerprint suffix everywhere
(`f"{resource_key}{managed_path}#{desired_fp[:12]}"`).

### 4. `src/oramaclaw/engine.py:304` — StaleConfiguration retry re-applies pre-calculated patch
On a stale-hash retry the engine fetches the new live config but re-applies the merge plan
computed against the *old* base. Concurrent mutations between the two fetches can be silently
overwritten.

**Fix:** On stale retry, re-call `plan_resource()` against the freshly fetched config before
applying. Thread the new `base_hash` through.

### 5. `scripts/discover.py:645` — `_cmd_restore` lock scope is too narrow
`with _Lock():` wraps only `patch_openclaw_json(ep)`. The subsequent `patch_devices_yml`,
`patch_models_yml`, `write_env_lmstudio`, and `save_discovery_state` run outside the lock.

**Fix:** Expand the `with _Lock():` block to cover all five write calls.

---

## Important (80–89)

### 6. `src/oramaclaw/merge.py:209` — Cooperative merge may overwrite a newer live drift
When `desired_fp == override.source_field_fingerprint` and `observed != override.observed_value`,
the plan stages the old effective value, potentially rolling back a change that happened after
the override was recorded. Confidence 90. Track for v1.1.

### 7. `src/oramaclaw/cli.py:223` — `targets add` stub exits 0 with "Not yet implemented"
Deliberate V1 scope. Acceptable if `--help` documents it clearly. Confidence 95.

---

## Portal architectural note

`portal_server.py:_oramaclaw_state_dir()` always returns `~/.openclaw/state/oramaclaw`.
Any target with a custom `state_dir` is invisible to the portal. Known V1 limitation — track
for v2.

---

## False positives (dropped)

- `engine.py:158` (lens 1 — "unauthorized offline fallback") — **false positive.** `OfflineTransport`
  already enforces PROVIDER/AGENT-only restriction at the transport layer via `OfflineOperationNotAllowed`.

---

## Verdict

**Yes, with fixes** — items 1–5 are required before merge. Items 6–7 and the portal note are
tracked for follow-up. All five fixes are mechanical and low-risk.
