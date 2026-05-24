# 2026-05-24 Security Review Debug and Fix Notes

Scope: follow-up documentation for the interrupted application-security review
around PR 40 (`feat/multi-agent-ordinal-safety`) at commit
`c22027e64a2750ae6bf6b4a5ee6d541efbcc7667`.

Runtime fixes were applied on branch `cursor/application-security-review-8a3d`
(2026-05-24 follow-up). This file records the original debug work, validation
results, and the fixes that were implemented.

## Executive summary

- The PR's new `docs/v2` ordinal-collision scanner is a local hygiene check and
  did not introduce a runtime attack surface.
- One initially suspected path-traversal proxy bug did not validate because
  FastAPI does not route encoded slashes through a plain `{job_id}` path
  parameter.
- The highest-leverage remaining fix is to stop binding internal control-plane
  services to `0.0.0.0` without authentication. `start.sh` exposes Perpetua-Tools
  on port 8000, orama on 8001, and the portal on 8002; several sensitive PT and
  orama endpoints become LAN-reachable through that process layout.

## Debug log

### Repository and memory context

- Reviewed the current orama-system worktree on branch
  `cursor/application-security-review-8a3d`.
- Existing vulnerability memory already contained portal findings for:
  - unauthenticated `/api/spawn-agent` full-auto CLI dispatch;
  - worktree bootstrap slug shell injection;
  - unauthenticated `/api/configure-tool` secret poisoning;
  - unauthenticated `/api/swarm/launch` supervisor job launch;
  - unauthenticated `/api/stop` and `/api/restart/{service}`;
  - unauthenticated raw job-detail exposure;
  - unauthenticated LAN discovery endpoint poisoning.
- Those known findings were treated as duplicates and not re-expanded here
  except where a different service boundary is involved.

### PR diff review

Changed files:

- `.claude/skills/using-git-worktrees/SKILL.md`
- `docs/v2/README.md`
- `scripts/review/repo_hygiene.py`
- `scripts/worktree-bootstrap.sh`
- `tests/test_repo_hygiene.py`

Security result:

- `scripts/review/repo_hygiene.py::scan_docv2_ordinal_collision` only iterates
  local `docs/v2/*.md` filenames and reports duplicate numeric prefixes. It does
  not execute attacker-controlled content, parse unsafe formats, or touch network
  boundaries.
- The `worktree-bootstrap.sh` changes only print additional coordination
  guidance. They do not remediate the existing slug quoting issue, and they do
  not add a new exploit primitive beyond the existing memory entry.

### Rejected candidate: job proxy encoded-slash traversal

Candidate:

- `portal_server.py` builds PT URLs as
  `f"{PT_URL}/v1/jobs/{job_id}"` in `/api/jobs/{job_id}` and
  `/api/jobs/{job_id}/artifacts`.
- Hypothesis was that a request such as
  `/api/jobs/..%2F..%2Fuser-input%2Fstatus` might route through FastAPI and let
  `httpx` normalize the upstream URL to another PT endpoint.

Validation:

- A minimal FastAPI test with `@app.get("/api/jobs/{job_id}")` returned `404` for
  encoded slash inputs including `..%2F..%2Fuser-input%2Fstatus` and `a%2Fb`.
- Because the route does not use a `{job_id:path}` converter, encoded slashes are
  not accepted into `job_id`.

Status:

- Not a valid finding in the current route shape.

## Validated risks and recommended fixes

### 1. PT control-plane API is LAN-exposed by `start.sh`

Severity: high

Primary location: `start.sh`

Attacker:

- Any same-LAN client that can reach the host running `start.sh`.

Controlled input:

- HTTP requests to PT on port 8000, including request bodies for `/v1/jobs` and
  query parameters for `/runtime/bootstrap`.

Reachability:

- `start.sh` launches Perpetua-Tools with:
  `uvicorn orchestrator.fastapi_app:app --host 0.0.0.0 --port "$PT_PORT"`.
- PT exposes unauthenticated control-plane routes including:
  - `POST /v1/jobs`
  - `POST /runtime/bootstrap`
  - `POST /orchestrate`
  - `GET /runtime`
  - `GET /agents`
  - `GET /activity`

Impact:

- `POST /v1/jobs` accepts attacker-controlled `prompt`, `intent`,
  `backend_hint`, `constraints`, and `metadata`.
- PT creates a `JobSpec`, persists it, and starts an async worker task.
- Worker resolution can route attacker prompts to model backends or headless CLI
  workers (`codex`, `gemini`, `agy`) depending on intent/backend selection.
- `POST /runtime/bootstrap?force_gateway=true` can force runtime bootstrap,
  gateway reconciliation, routing resolution, autoresearch preflight, and runtime
  state rewrites.

Fix notes:

1. Bind PT to loopback by default:
   `--host "${PT_HOST:-127.0.0.1}"`.
2. Add an authenticated control-plane token for all mutating PT routes.
3. Keep LAN exposure behind a deliberate opt-in such as
   `PT_BIND_LAN=1`, with startup warnings.
4. If browser access is required, expose only the portal behind authentication
   and have it call PT over loopback.
5. Add tests that assert unauthenticated requests to PT mutating routes return
   `401` or `403`.

### 2. orama runtime state and reasoning endpoint are LAN-exposed by `start.sh`

Severity: medium

Primary location: `start.sh`

Attacker:

- Any same-LAN client that can reach port 8001.

Controlled input:

- Request bodies to `POST /ultrathink`; path access to `GET /runtime-state`.

Reachability:

- `start.sh` launches orama with:
  `uvicorn api_server:app --host 0.0.0.0 --port "$US_PORT"`.
- `api_server.py` enables wildcard CORS and registers `/ultrathink`,
  `/health`, and `/runtime-state` without authentication.
- `/runtime-state` reads the `PT_AGENTS_STATE` or `PT_RUNTIME_STATE` file path
  and returns the loaded payload.

Impact:

- Unauthenticated clients can consume or steer reasoning resources through
  `/ultrathink`.
- If PT runtime environment variables are set, `/runtime-state` exposes runtime
  topology, paths, routing data, and gateway state to LAN clients.

Fix notes:

1. Bind orama to loopback by default:
   `--host "${US_HOST:-127.0.0.1}"`.
2. Require a bearer token for `/ultrathink` and `/runtime-state`.
3. Keep `/health` unauthenticated only if it returns a minimal static status.
4. Replace wildcard CORS with a configured allowlist.
5. Return a redacted runtime DTO instead of raw PT runtime payloads.

### 3. Portal status aggregation returns PT runtime and activity without auth

Severity: medium

Primary location: `portal_server.py`

Attacker:

- Any same-LAN client that can reach the portal on port 8002.

Controlled input:

- HTTP GETs to `/api/status` and `/api/app/state`.

Reachability:

- `portal_server.py` defaults `PORTAL_HOST` to `0.0.0.0` and allows wildcard
  CORS.
- `/api/status` calls PT `/runtime`, `/activity`, `/agents`,
  `/user-input/status`, and `/v1/jobs`, then returns the aggregated payload.
- `/api/app/state` calls PT `/runtime`, `/models`, `/activity?limit=25`, and
  `/v1/jobs`, then returns those sections to the caller.

Impact:

- LAN clients can enumerate runtime topology, backend URLs, model availability,
  agent activity, job metadata, queue depth, and filesystem paths.
- This is lower impact than the already-recorded raw job-detail exposure, but it
  broadens unauthenticated operator-state disclosure beyond a single job ID.

Fix notes:

1. Require portal authentication before returning any operator state.
2. Split public health from private operator telemetry.
3. Return redacted DTOs from `/api/status` and `/api/app/state`; do not forward
   PT `/runtime` verbatim.
4. Remove wildcard CORS on authenticated routes.
5. Add regression tests that sensitive keys such as `runtime`, `paths`,
   `activity`, raw job specs, and backend URLs are absent from unauthenticated
   responses.

### 4. Portal user-input queue injection can steer researcher agents

Severity: medium if researcher agents are running; otherwise low operational
risk.

Primary location: `portal_server.py`

Attacker:

- Any same-LAN client that can reach the portal on port 8002.

Controlled input:

- The `message` field in `POST /api/user-input`.

Reachability:

- Portal forwards `POST /api/user-input` to PT `/user-input` with
  `{"message": req.message, "source": "portal"}`.
- PT stores the message in `_USER_INPUT_QUEUE`.
- `Perpetua-Tools/scripts/launch_researchers.py` polls
  `GET /user-input/next` after handshake rounds and uses the queued message as
  the next model task.

Impact:

- A LAN attacker can inject instructions into waiting researcher agents.
- Current evidence shows the researcher loop sends the task to model endpoints
  and logs the reply; it does not directly apply patches by itself. Treat this
  as agent steering/prompt injection rather than direct code execution.

Fix notes:

1. Require authentication for `/api/user-input` and PT `/user-input`.
2. Add provenance fields: authenticated principal, source IP, and request ID.
3. Make researcher agents display or log a trusted approval boundary before
   executing queued tasks.
4. Consider per-agent queues instead of one global FIFO queue.
5. Add a queue length and message length limit at both portal and PT layers.

### 5. Fallback AlphaClaw bootstrap uses a default setup password

Severity: medium, conditional on fallback path and gateway exposure.

Primary location: `scripts/openclaw_bootstrap.py`

Attacker:

- A network client that can reach the AlphaClaw setup UI after the fallback
  bootstrap path starts it.

Controlled input:

- Login attempts against the AlphaClaw setup UI using the known default password.

Reachability:

- `scripts/openclaw_bootstrap.py` starts AlphaClaw with:
  `SETUP_PASSWORD=os.getenv("SETUP_PASSWORD", "localdev123")`.
- `start.sh` can invoke this fallback when PT's `alphaclaw_manager.py` path is
  not available.

Impact:

- If the fallback path starts a reachable setup UI and the operator has not set
  `SETUP_PASSWORD`, the setup UI is protected by a known password.

Fix notes:

1. Fail closed when `SETUP_PASSWORD` is unset in non-development mode.
2. Generate a random one-time setup password and print it only to the local
   terminal.
3. Bind fallback setup to loopback unless an explicit LAN flag is set.
4. Add startup warnings and tests for default-password rejection.

## Consolidated implementation plan (completed 2026-05-24)

1. Shared control-plane auth (`utils/control_plane_auth.py`, PT
   `orchestrator/control_plane_auth.py`) with `ORAMA_CONTROL_PLANE_TOKEN` and
   `ORAMA_INSECURE_DEV` escape hatch for local pytest only.
2. Loopback bind defaults in `start.sh`, `portal_server.py`, and `api_server.py`;
   opt-in LAN via `PT_BIND_LAN`, `ORAMA_BIND_LAN`, and `PORTAL_BIND_LAN`.
3. Minimal `/health` payloads; operator routes require auth.
4. Redacted portal status/app-state and PT `/runtime` responses.
5. Portal and PT mutating routes gated behind bearer auth middleware.
6. Regression tests in `tests/test_control_plane_auth.py` (orama) and
   `Perpetua-Tools/tests/test_control_plane_auth.py`.

## Verification commands for future fixes

After implementing fixes, run:

```bash
python3 -m pytest tests/test_portal_jobs_proxy.py tests/test_portal_app_state.py
python3 -m pytest tests/test_swarm_launch.py tests/test_api_server.py
python3 scripts/review/repo_hygiene.py .
```

If Perpetua-Tools routes are changed in the companion repo, also run the
relevant PT FastAPI and supervisor tests from that repository.
