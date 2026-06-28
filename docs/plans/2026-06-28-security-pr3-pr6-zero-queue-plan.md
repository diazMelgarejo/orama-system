# Security PR3+ Stack Plan — Zero Open Queue

> **Date:** 2026-06-28  
> **Method:** oramasys-method (AFRP Type C, Mode 2) + pt-orama-harness cross-repo sync  
> **Planner subagent:** `.cursor/agents/pt-orama-security-planner.md`  
> **Prerequisite:** Merge [#127](https://github.com/diazMelgarejo/orama-system/pull/127) (orama) and [#177](https://github.com/diazMelgarejo/Perpetua-Tools/pull/177) (PT)

---

## AFRP

```text
AFRP: Type C | Level Practitioner | Mode 2
Scope: Close remaining SECURITY.md severity queue (P3 partial, P5, P6, optional CSRF) via four stacked PRs after PR1–PR2 merge.
```

---

## Situation (post PR1–PR2)

| Layer | Status |
|-------|--------|
| **Section C acceptance gates** | All `[x]` — enforceable checklist at zero |
| **Critical/High cluster P1–P4, P7–P9, P12–P13** | Closed by #127/#177 + defense-in-depth |
| **Severity queue remainders** | P5, P6, P3 partial, optional CSRF/origin |
| **Operator UX gap** | Loopback must send `Authorization` manually (HTML bearer removed intentionally) |

The queue is one **architectural mismatch** (secure-by-default asymmetry × LAN-peer workflow × collapsed HTTP trust) — not 13 independent bugs. RC-1 and RC-3 are closed; RC-2 and RC-4 are partial.

---

## Root-cause → PR mapping

| RC | Remaining symptom | PR |
|----|-------------------|-----|
| RC-4 | Client `approved: true` on swarm launch | **PR3** |
| RC-2 + discovery trust | `discover.py` auto-persists LAN responders | **PR4** |
| RC-4 + lifecycle | Stop/restart lack origin binding | **PR5** |
| RC-2 | Windows `start.ps1` LAN bind without loopback-first parity | **PR6** |
| RC-4 UX | Manual bearer on loopback dashboard | **PR5** (optional `/api/auth/session`) |

---

## Stacked PR chain

```text
origin/main  (+ #127/#177 merged)
  └─ cursor/security-pr3-swarm-approval-f559        → PR3  P5
      └─ cursor/security-pr4-discovery-approval-f559 → PR4  P6
          └─ cursor/security-pr5-lifecycle-csrf-f559 → PR5  CSRF + session cookie
              └─ cursor/security-pr6-windows-bind-f559 → PR6  P3 partial
```

**Rule:** Each PR rebases on the prior branch before open. One logical fix per PR. Update both `SECURITY.md` files when the rule is cross-repo.

---

## PR3 — P5: Server-side swarm approval

**Finding:** Authenticated attackers (or compromised browser) can POST `approved: true` without reviewing preview assignments.

### Design (minimal, stateless-preferred)

1. **`POST /api/swarm/preview`** (already exists) returns:
   - `preview_id` (uuid)
   - `approval_token` — HMAC-SHA256 over `(preview_id, objective, assignments_hash, exp)` using control-plane token as secret
   - `expires_at` (e.g. 15 minutes)
2. **`POST /api/swarm/launch`** requires `preview_id` + `approval_token`; **ignore** client `approved` (deprecate field, keep 422 if neither token nor legacy path during transition).
3. Store nothing server-side if HMAC verification is sufficient (stateless signed approval).
4. Portal JS: preview → show assignments → launch sends token from preview response only.

### Files

| Repo | Path |
|------|------|
| orama | `src/orama_system/portal_server.py` — `_sign_swarm_preview()`, launch validation |
| orama | `src/utils/control_plane_auth.py` — optional `sign_operator_payload()` helper |
| orama | `tests/test_swarm_launch.py`, `tests/test_portal_mutating_route_auth.py` |

### Acceptance (TDD)

- [ ] Launch without valid `approval_token` → 403/422 even with bearer auth
- [ ] Tampered token or expired `expires_at` → 403
- [ ] Valid preview → launch → PT `/v1/jobs` dispatched (existing tests extended)
- [ ] `SECURITY.md` P5 row annotated remediated; section C unchanged (already `[x]`)

### PT sync

No PT code change required if orama portal is the only swarm entrypoint. Confirm PT `/v1/jobs` already requires bearer (Fix 3).

---

## PR4 — P6: Discovery operator approval before persistence

**Finding:** `scripts/discover.py` probes LAN LM Studio responders and writes `discovery.json`, `openclaw.json`, PT `config/devices.yml`, `.env.lmstudio` without operator confirmation — attacker-controlled responder can become persisted route.

### Design

1. **Default (safe):** On hash change, write **`pending_discovery.json`** + print diff summary; **do not** patch live configs.
2. **`--approve` flag** (or `DISCOVERY_AUTO_APPROVE=1` for CI/operator scripts): current behavior — persist immediately.
3. **`--dry-run`:** probe + print would-be changes; no writes except stderr summary.
4. **Pinned hosts:** `TRUSTED_MODEL_HOSTS=127.0.0.1,192.168.x.x` — auto-approve only endpoints whose IP is in allowlist (loopback always trusted).
5. **Portal `/api/rediscover`:** call discover with `--dry-run` first; return pending diff; add **`POST /api/rediscover/approve`** (auth required) to run `--approve`.

### Files

| Repo | Path |
|------|------|
| orama | `scripts/discover.py` — pending state, flags, pinned hosts |
| orama | `src/orama_system/portal_server.py` — rediscover flow |
| orama | `tests/test_discover_approval.py` (new) |
| PT | `SECURITY.md` — model discovery row (policy sync only) |

### Acceptance (TDD)

- [ ] New LAN IP not in `TRUSTED_MODEL_HOSTS` → `pending_discovery.json` only
- [ ] `--approve` persists same as today
- [ ] Loopback endpoints auto-approve without flag
- [ ] Portal approve route requires bearer
- [ ] `SECURITY.md` P6 remediated note

---

## PR5 — CSRF/origin guards + auth session cookie (optional UX)

**Findings:** P11 (medium) — lifecycle routes accept POST from any origin when bearer present; operator UX — manual bearer after P2 HTML fix.

### Design

1. **Origin guard** on `POST /api/stop`, `/api/restart/*`, `/api/rediscover/approve`:
   - If `Origin` or `Referer` present and not loopback/same-host → 403
   - Loopback requests without Origin allowed (curl/cli)
2. **`POST /api/auth/session`** (auth required):
   - Validates bearer → sets `HttpOnly; SameSite=Strict; Path=/` cookie (short TTL, e.g. 8h)
   - Legacy dashboard `cpFetch` sends `credentials: 'include'`
3. Do **not** re-embed bearer in HTML.

### Files

| Repo | Path |
|------|------|
| orama | `src/orama_system/portal_server.py`, `src/utils/control_plane_auth.py` |
| orama | `tests/test_portal_lifecycle_csrf.py` (new) |

### Acceptance (TDD)

- [ ] Cross-origin POST stop with bearer → 403
- [ ] Same-origin or loopback POST → 200/401 as before
- [ ] Session cookie set only after valid bearer; mutating routes accept cookie auth
- [ ] `SECURITY.md` optional CSRF item closed

---

## PR6 — P3 partial: Windows loopback-first bind parity

**Finding:** `platform/windows/start.ps1` still binds `0.0.0.0` on LAN-peer path; strong token now required but not loopback-first like macOS `start.sh`.

### Design

Mirror `start.sh`:

1. Default bind **`127.0.0.1`** for portal/PT/API unless `PORTAL_BIND_LAN=1` / `PT_BIND_LAN=1`.
2. LAN bind → `_require_control_plane_token_for_lan()` equivalent (already partially present).
3. Document Windows LAN-peer workflow: explicit env trinity (`*_BIND_LAN=1` + strong token + `ORAMA_INSECURE_DEV=0`).

### Files

| Repo | Path |
|------|------|
| orama | `platform/windows/start.ps1` |
| orama | `tests/test_windows_start_bind.py` or extend shell guard tests |
| both | `SECURITY.md` — P3 row full parity note |

### Acceptance (TDD)

- [ ] Default start.ps1 bind host is loopback
- [ ] `PORTAL_BIND_LAN=1` without token → fail closed
- [ ] Parity test documents macOS vs Windows bind resolution

---

## Cross-repo SECURITY.md sync checklist

After each PR merge, update **additively** (never delete finding history):

| PR | orama-system SECURITY.md | Perpetua-Tools SECURITY.md |
|----|--------------------------|----------------------------|
| PR3 | P5 workstream → remediated; RC-4 partial → closed | Swarm policy note if PT adds job-side approval metadata |
| PR4 | P6 remediated; A2 remaining cleared | Model discovery approval policy |
| PR5 | P11 / optional CSRF closed; operator session note | CORS/session N/A unless PT adds cookie auth |
| PR6 | P3 full parity | LAN bind note for PT `PT_BIND_LAN` |

**Zero open queue definition:** Section C all `[x]` **and** severity table rows P3/P5/P6/P11 marked remediated with test anchors.

---

## Execution recommendation

| Choice | When |
|--------|------|
| **Branch from `main` after #127/#177 merge** | Preferred — clean review, matches SECURITY.md stacking rules |
| **Continue on `cursor/security-pr1-pr2-auth-hardening-f559`** | Only if reviewer wants single mega-PR (not recommended) |

**Start with PR3 (P5)** — highest remaining High severity, orama-only, no discover/LAN coupling.

---

## Assumptions ledger

1. Swarm dispatch is portal-only; PT does not expose equivalent multi-agent launch without auth.
2. HMAC approval token secret = control-plane token is acceptable (token rotation invalidates pending previews — acceptable).
3. Operators running headless discover scripts can set `DISCOVERY_AUTO_APPROVE=1` in trusted environments.
4. Windows LAN-peer operators accept explicit `*_BIND_LAN=1` rather than implicit `0.0.0.0`.

## Risks / deferrals

- **Session cookie** introduces CSRF surface if SameSite misconfigured — Strict + HttpOnly mandatory.
- **Pending discovery** may break unattended `./start.sh --discover` until `--approve` wired in start scripts — update `start.sh` to pass `--approve` when operator-initiated.
- **Full zero** on OWASP/MAESTRO v2 harness controls remains separate from this SECURITY.md queue.

---

## Crystallize — inevitability argument

PR1–PR2 fixed the **trust boundary defaults** (RC-1, RC-3). PR3–PR6 fix the **residual operator-trust shortcuts** (RC-4) and **LAN-as-production workflow** (RC-2) without rewriting orchestration — the same layered pattern the defense-in-depth table already mandates: prevent → runtime guard → verify.
