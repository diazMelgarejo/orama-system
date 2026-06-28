# Mac ↔ Win portal merge notes

**Date:** 2026-06-28  
**Operator context:** Windows pushed `origin/win/peer-inbox-portal`; Mac `main` has `abea96e` (co-orchestration skins).  
**Fetched tip:** `5d05182` (ahead of cited `bde6677` — consolidates peer-inbox under `platform/windows/`).

## Branch topology

| Ref | Commit | Parent | Summary |
|-----|--------|--------|---------|
| Merge base | `0996dea` | — | Shared: co-orchestration inbox subpage + markdown preview |
| Mac `main` | `abea96e` | `0996dea` | Platform skins: `src/orama_system/portals/co_orchestration_{macos,windows,shared}.py`, `platform/macos/README.md` |
| Win branch | `bde6677` → `5d05182` | `0996dea` | Peer inbox viewer + server-side markdown; `5d05182` moves modules to `platform/windows/` |

```text
0996dea ── abea96e  (main — Mac skins)
    └── bde6677 ── 5d05182  (win/peer-inbox-portal — peer-inbox lane)
```

## What each side added

### Mac (`main` / `abea96e`)

- **Co-orchestration skin split** under `src/orama_system/portals/`:
  - `co_orchestration.py` — router (auto macOS vs Windows skin from `local_platform()`)
  - `co_orchestration_macos.py` — OpenClaw skin (`/co-orchestration/macos`)
  - `co_orchestration_windows.py` — Hermes skin (`/co-orchestration/windows`)
  - `co_orchestration_shared.py` — shared HTML, fan-out filter, stats, bidirectional tables
- **Routes:** `/co-orchestration`, `/co-orchestration/macos`, `/co-orchestration/windows`
- **Markdown preview:** client-side via `marked` CDN in shared template (`co_orchestration_shared.py`)
- **Thin shim:** `co_orchestration_portal.py` re-exports from `portals.co_orchestration`
- **Docs:** `platform/macos/README.md`, playbook link update
- **Auth allowlist:** `/co-orchestration`, `/co-orchestration/macos`, `/co-orchestration/windows` (loopback GET)

### Windows (`origin/win/peer-inbox-portal` / `5d05182`)

- **New Win lane** under `platform/windows/`:
  - `__init__.py` — `load_module()` for Win-specific portal modules
  - `markdown_render.py` — escape-first markdown→HTML subset (no CDN, LAN-safe)
  - `peer_inbox_portal.py` — `/peer-inbox` HTML page + `fetch_remote_peer_api()` helper
- **New routes** in `portal_server.py`:
  - `GET /peer-inbox` — bidirectional queue UI (Win lane)
  - `GET /api/peer-inbox/remote`, `/api/peer-inbox/remote/{filename}`, `.../html`
  - `GET /api/peer-inbox/{filename}/html` — server-rendered markdown for local files
  - Enriched `GET /api/peer-inbox` with `scope` + `role`
- **Portal wiring:** `_windows_platform_pkg()` / `_win_platform_module()` lazy loaders; `_loopback_browser_token()` helper
- **Nav:** link to `/peer-inbox` (“Peer Inbox (Win) ↔”)
- **Tests:** `test_markdown_render.py`, `test_peer_inbox_html_preview` in `test_control_plane_auth.py`
- **Auth allowlist:** `/peer-inbox` (replaces skin paths in Win’s version)
- **Regression risk:** Win branch **reverts** Mac skin refactor — routes import monolithic `co_orchestration_portal.py` again and **delete** `/co-orchestration/{macos,windows}` handlers

## Diff stat (`main...origin/win/peer-inbox-portal`)

Win-only / changed on Win side (8 files, +634 / −89 vs merge base path):

| File | Role |
|------|------|
| `platform/windows/__init__.py` | New — module loader |
| `platform/windows/markdown_render.py` | New — server-side markdown |
| `platform/windows/peer_inbox_portal.py` | New — `/peer-inbox` page + remote fetch |
| `platform/windows/README.md` | Updated — documents peer-inbox lane |
| `src/orama_system/portal_server.py` | +Win routes; **conflicts** with Mac skin routes |
| `src/utils/control_plane_auth.py` | **conflicts** — path allowlist |
| `tests/test_markdown_render.py` | New |
| `tests/test_control_plane_auth.py` | +peer-inbox HTML test |

Mac-only (not on Win branch; must be preserved):

- `platform/macos/README.md`
- `src/orama_system/portals/` (entire package)
- Mac’s thin `co_orchestration_portal.py` re-export
- `tests/test_co_orchestration_portal.py` skin assertions

## Dry-run merge result

```bash
git merge --no-commit --no-ff origin/win/peer-inbox-portal
```

**2 conflicts** (everything else auto-merges or is additive):

1. **`src/orama_system/portal_server.py`**
   - Docstring routes: Mac lists `/co-orchestration/{macos,windows}` vs Win single `/co-orchestration` + `/peer-inbox`
   - Nav links: Mac → `/co-orchestration/macos` vs Win → `/co-orchestration` + `/peer-inbox`
   - Non-conflicting Win additions (`_win_platform_*`, peer-inbox API routes, `_loopback_browser_token`) merge cleanly alongside Mac’s `_co_orchestration_html_response` + skin routes

2. **`src/utils/control_plane_auth.py`**
   - Loopback GET allowlist: Mac has skin paths; Win has `/peer-inbox` — **take union**

## Recommended merge strategy

**Goal:** Keep both lanes — Mac co-orchestration skins **and** Win peer-inbox + server markdown. Do **not** accept Win’s revert of the portals package.

### 1. Merge order

```bash
git checkout main
git pull origin main
git fetch origin win/peer-inbox-portal
git merge origin/win/peer-inbox-portal
# resolve 2 conflicts per §2–3 below
pytest tests/test_co_orchestration_portal.py tests/test_markdown_render.py tests/test_control_plane_auth.py
```

Prefer **merge commit** (not rebase) so both branch histories stay visible for operators.

### 2. Resolve `portal_server.py`

| Hunk | Resolution |
|------|------------|
| Route docstring | Keep **both**: Mac skin routes **and** `/peer-inbox` + `/api/peer-inbox/remote` |
| Nav bar | Link `/co-orchestration/macos` (or auto `/co-orchestration`) **and** `/peer-inbox` |
| Co-orchestration handlers | **Keep Mac** (`_co_orchestration_html_response`, three skin routes, `portals.co_orchestration` imports) |
| Peer-inbox handlers | **Take Win** (`_win_platform_module`, `/peer-inbox`, `/api/peer-inbox/*/html`, `/api/peer-inbox/remote/*`) |
| `_loopback_browser_token` | **Take Win** — use in `index()` and peer-inbox page (dedupe Mac inline token logic) |

Do **not** switch `api_co_orchestration` back to monolithic `co_orchestration_portal.py`.

### 3. Resolve `control_plane_auth.py`

Union loopback GET paths:

```python
("/", "/dashboard", "/co-orchestration", "/co-orchestration/macos", "/co-orchestration/windows", "/peer-inbox")
```

### 4. Keep Win `markdown_render.py` — do not delete

- Lives at `platform/windows/markdown_render.py` (post-`5d05182`; not `src/orama_system/`)
- Used by `/api/peer-inbox/{filename}/html` and remote HTML fallback
- **Rationale:** no CDN dependency; escape-first (XSS-safe) for untrusted peer file bodies
- Mac co-orchestration can **keep** client `marked` for now (richer rendering, same-origin trusted LAN). Future optional: call shared `markdown_render` from co-orchestration API or drop CDN.

### 5. Post-merge doc / operator smoke

| Check | URL / command |
|-------|----------------|
| Mac skin | `http://localhost:8002/co-orchestration/macos` |
| Hermes skin preview | `http://localhost:8002/co-orchestration/windows` |
| Win peer lane | `http://localhost:8002/peer-inbox` |
| API | `curl -s localhost:8002/api/peer-inbox/task.md/html` (with auth if enforced) |
| Tests | `pytest tests/test_co_orchestration_portal.py tests/test_markdown_render.py tests/test_control_plane_auth.py` |
| Restart | `./start.sh --stop && ./start.sh --lan-peer` (portal must reload after merge) |

### 6. Longer-term reconcile (not blocking merge)

- **Lane naming:** Win comments say “Mac lane” = `/co-orchestration`, “Win lane” = `/peer-inbox`. After merge, document that **both hosts expose both URLs**; skins differentiate UX not availability.
- **Consolidate markdown:** single server renderer vs CDN — track as follow-up if offline Hermes hosts need co-orchestration without jsDelivr.
- **Symmetry:** consider `platform/macos/peer_inbox_portal.py` mirror only if Mac needs a distinct peer-inbox skin; today Win module is host-agnostic HTML.

## Risk summary

| Risk | Mitigation |
|------|------------|
| Accidentally dropping Mac skins | Keep `src/orama_system/portals/*` and three co-orchestration routes |
| Taking Win’s `co_orchestration_portal.py` wholesale | Reject — overwrites refactor |
| Auth lockout on new routes | Union allowlist in `control_plane_auth.py` |
| Stale portal after merge | Operator restart per lessons learned |

## References

- Mac commit: `abea96e` — `feat(portal): macOS and Windows co-orchestration portal skins`
- Win commits: `bde6677` (peer inbox viewer), `5d05182` (consolidate under `platform/windows/`)
- Shared ancestor: `0996dea` — co-orchestration inbox subpage
