# Periscope L4 Glass — Implementation Plan

> **For agentic workers:** Use the standard graph-first chain. Each task lists exact files, expected test output, and a commit. Steps use `- [ ]` checkboxes for tracking.

**Goal:** Wire periscope into OpenClaw as the L4 observability layer + close out the pending upstream-maintenance work (rename, branch merges, dep PRs).

**Repos & paths:**
- Periscope (local): `~/Documents/oramasys/tools/periscope` — all 3 branches local (`main`, `merged`, `agentsview`)
- Periscope (remote): `github.com/diazMelgarejo/periscope` (fork of `latentsignal-org/periscope`)
- orama-system (this repo): `$OPENCLAW_ROOT/orama-system`

**Design:** See `docs/v2/21-periscope-l4-glass.md` (mission, architecture, OQ register, risks).

**Hard constraints:**
- Periscope is L4 — observation-only. Never writes to AlphaClaw / PT / orama.
- All integration code goes to `diazMelgarejo/periscope` (the fork). Parsers we want upstream get a separate PR to `latentsignal-org/periscope` AFTER they ship in our fork.
- Do **not** touch `oramasys/*` repos. v2-planning rule applies.

---

## Phase order

```
A. Upstream maintenance   (1 day)   — clear the deck before integration
   A.1  Merge `merged` → `main`
   A.2  Rename `cmd/agentsview/` → `cmd/periscope/`
   A.3  Triage dependabot PRs
   A.4  Decide on `agentsview` branch sync (cherry-pick vs rebase)

B. v1 integration         (3-4 days) — minimal glass that works
   B.1  Parser: OpenClaw envelopes
   B.2  Parser: AlphaClaw events
   B.3  Parser: PT orchestrator events
   B.5  Routes: /api/v1/openclaw/*
   B.10 Doc: add periscope to CLAUDE-instru.md as L4
   B.11 Doc: add PERISCOPE_URL / PERISCOPE_TOKEN to consolidated .env

C. v2 polish              (later — gated on v1 landing)
   B.4  Signals, B.6 CLI, B.7 Svelte routes, B.8 gbrain bridge, B.9 autostart
```

This plan covers Phase A and Phase B. Phase C is its own future plan.

---

## Phase A — Upstream maintenance

### Task A.1 — Merge `merged` branch into `main`

`merged` is 10 commits ahead of `main` and contains: CI fixes, Rust desktop lib rename, PEP 440 wheel normalization, Docker tag fix, agentsview→periscope build-tool rename completion. None of these touch product behavior — they unblock release tooling.

**Files (none directly — branch merge):**
- All commits between `main..merged`

- [ ] **Step 1: Verify branches are aligned with origin**

```bash
cd ~/Documents/oramasys/tools/periscope
git fetch --all
git log --oneline main..origin/merged | head -15
```

Expected: 10 commits, no surprises.

- [ ] **Step 2: Create integration branch from main**

```bash
git checkout main
git checkout -b chore/merge-merged-2026-05-24
```

- [ ] **Step 3: Merge with --no-ff to preserve history**

```bash
git merge --no-ff origin/merged -m "chore: merge merged branch — agentsview→periscope completion, CI/wheel/Docker fixes"
```

If conflicts: stop, paste conflicts to operator. Do not auto-resolve.

- [ ] **Step 4: Run the full Go test suite**

```bash
go test ./...
```

Expected: PASS for all packages. The only files that changed in `merged` are CI/build tooling + the Rust lib rename, so Go tests should be unaffected.

- [ ] **Step 5: Verify the binary still builds**

```bash
make build || go build -o /tmp/periscope-test ./cmd/agentsview
/tmp/periscope-test --version
```

Expected: prints a version string. (Binary path is still `cmd/agentsview` — A.2 fixes that.)

- [ ] **Step 6: Push branch + open PR against `main`**

```bash
git push -u origin chore/merge-merged-2026-05-24
gh pr create \
  --repo diazMelgarejo/periscope \
  --base main --head chore/merge-merged-2026-05-24 \
  --title "chore: merge merged branch — agentsview→periscope completion + CI fixes" \
  --body "$(cat <<'EOF'
## Summary
- 10 commits ahead from `merged` brought into `main`
- Completes the agentsview→periscope rename across Rust desktop lib, build tooling, Docker tags
- Fixes PEP 440 wheel version normalization
- Makes desktop-release signing conditional on secrets

## Test plan
- [x] go test ./... — PASS
- [x] Binary builds and reports version
- [ ] CI green on this PR
EOF
)"
```

- [ ] **Step 7: Wait for CI, then merge via squash or merge commit (operator choice)**

---

### Task A.2 — Rename `cmd/agentsview/` → `cmd/periscope/`

15 Go files plus references in build files. After A.1 lands.

**Files:**
- Move: `cmd/agentsview/*.go` → `cmd/periscope/*.go` (15 files)
- Modify: `Makefile`, `go.mod` (if pinned), `.air.toml`, `.roborev.toml`, `README.md`, `AGENTS.md`, `install.sh`, `Dockerfile`, any GitHub Actions workflow that references `cmd/agentsview`

- [ ] **Step 1: Branch from current `main`**

```bash
cd ~/Documents/oramasys/tools/periscope
git checkout main && git pull
git checkout -b chore/rename-cmd-agentsview-2026-05-24
```

- [ ] **Step 2: Move the directory**

```bash
git mv cmd/agentsview cmd/periscope
```

- [ ] **Step 3: Update package declaration if any file still says `package agentsview`**

```bash
grep -rln "^package agentsview" cmd/periscope/ || echo "package already periscope"
# If matches, edit each file to `package periscope` (keep `package main` if that's what it was — verify first)
```

Expected: most likely already `package main` (cmd packages usually are). If `package agentsview`, replace with `package main`.

- [ ] **Step 4: Find and replace path references**

```bash
grep -rln "cmd/agentsview" . --include="*.go" --include="*.toml" --include="*.md" --include="Makefile" --include="*.yml" --include="*.yaml" --include="Dockerfile*" --include="*.sh"
```

For each file, replace `cmd/agentsview` → `cmd/periscope`. Use `Edit` tool one file at a time; do not bulk-sed.

- [ ] **Step 5: Add a binary-name compatibility shim (1-version deprecation)**

In `cmd/periscope/main.go` (or wherever the entry point lives), at the top of `main()`:

```go
if filepath.Base(os.Args[0]) == "agentsview" {
    fmt.Fprintln(os.Stderr, "warning: 'agentsview' is deprecated; rename to 'periscope'. agentsview will be removed in v0.32.")
}
```

This lets existing installs keep working while we migrate.

- [ ] **Step 6: Update install scripts to ship both names for one version**

In `install.sh` (the released installer), after writing the `periscope` binary:

```bash
ln -sf "$INSTALL_DIR/periscope" "$INSTALL_DIR/agentsview"  # deprecated alias, removed in v0.32
```

- [ ] **Step 7: Update README install URL placeholder**

`agentsview.io/install.sh` → keep for one release as a redirect to whatever the new host is. If undecided, leave the URL in README pointing to `agentsview.io` and document the planned move in a `MIGRATION.md`. Do **not** invent a new domain in this PR.

- [ ] **Step 8: Run the Go test suite + build**

```bash
go test ./...
go build -o /tmp/periscope-test ./cmd/periscope
/tmp/periscope-test --version
ln -sf /tmp/periscope-test /tmp/agentsview-test
/tmp/agentsview-test --version  # should print deprecation warning + version
```

Expected: tests PASS; both binary names work; old name prints warning.

- [ ] **Step 9: Commit and open PR**

```bash
git add -A
git commit -m "$(cat <<'EOF'
chore(rename): cmd/agentsview → cmd/periscope (15 files)

Completes the agentsview→periscope rename in the Go command package.
Adds a one-version compatibility shim that lets the deprecated
'agentsview' binary name still work and prints a warning.

Tests: go test ./... — PASS
Binary: builds and prints version for both 'periscope' and 'agentsview'
EOF
)"
git push -u origin chore/rename-cmd-agentsview-2026-05-24
gh pr create --repo diazMelgarejo/periscope --base main \
  --title "chore(rename): cmd/agentsview → cmd/periscope + compat shim" \
  --body "Completes the rename. Compat shim keeps the old binary name working for one minor version."
```

---

### Task A.3 — Triage 3 open dependabot PRs

Three PRs are open:
- #1 — `github.com/jackc/pgx/v5` 5.9.1 → 5.9.2 (Go)
- #2 — npm batch update (frontend)
- #3 — cargo batch update (desktop/src-tauri)

- [ ] **Step 1: Check the changelogs for breaking changes**

```bash
for pr in 1 2 3; do
  gh pr view --repo diazMelgarejo/periscope $pr --json title,body | python3 -m json.tool | head -40
  echo "---"
done
```

- [ ] **Step 2: For each PR, run its CI locally (or trust green CI)**

If CI is green and no major version bumps: merge.
If CI is red or there's a major bump: hold and surface to operator.

- [ ] **Step 3: Merge greens, comment on reds**

```bash
gh pr merge --repo diazMelgarejo/periscope --auto --squash 1  # if green
# repeat for 2, 3
```

---

### Task A.4 — Decide on `agentsview` upstream branch sync

`agentsview` tracks `latentsignal-org/periscope` (which itself tracks `wesm/agentsview`). 5 commits ahead of our `main`:
- #478 Piebald support
- #476 forge agent support
- #475 dep batch update
- #463 tool input preview on collapsed tool header
- #459 fix linking Claude subagent tool calls

- [ ] **Step 1: Inspect what each commit touches**

```bash
cd ~/Documents/oramasys/tools/periscope
git log --oneline main..origin/agentsview
git show --stat origin/agentsview~0..origin/agentsview~4 | head -50
```

- [ ] **Step 2: Decide cherry-pick vs merge**

The 5 commits look like cleanly additive parser/UI improvements. Recommend: **cherry-pick** to avoid the upstream's branch history noise.

- [ ] **Step 3: Cherry-pick in dependency order**

```bash
git checkout main && git pull
git checkout -b feat/upstream-sync-2026-05-24
for sha in d482b6d a9dd6d5 f5fe6a2 e929402 17673c2; do
  git cherry-pick "$sha"
done
go test ./...
```

If conflicts: stop and surface. Do not force-resolve.

- [ ] **Step 4: PR**

Same pattern as A.1/A.2.

---

## Phase B — v1 integration (the actual glass)

### Task B.1 — OpenClaw envelope parser

Reads `~/.openclaw/sessions/*.jsonl`. One JSONL record per envelope.

**Files:**
- Create: `internal/parser/openclaw.go`
- Create: `internal/parser/openclaw_test.go`
- Modify: `internal/parser/registry.go` (whichever file registers parsers — find via `grep "RegisterParser\|parsers.Register"`)

- [ ] **Step 1: Write the failing test**

`internal/parser/openclaw_test.go`:

```go
package parser_test

import (
    "encoding/json"
    "strings"
    "testing"

    "github.com/diazMelgarejo/periscope/internal/parser"
)

func TestOpenclawParser_Envelope(t *testing.T) {
    sample := `{"type":"request","ts":"2026-05-24T01:00:00Z","correlation_id":"abc","target_tier":"tier3","task_type":"code","model_hint":"qwen3.5"}
{"type":"response","ts":"2026-05-24T01:00:05Z","correlation_id":"abc","backend":"lmstudio-win","tokens_in":120,"tokens_out":340}
`
    msgs, err := parser.NewOpenclawParser().Parse(strings.NewReader(sample))
    if err != nil {
        t.Fatalf("parse: %v", err)
    }
    if len(msgs) != 2 {
        t.Fatalf("want 2 messages, got %d", len(msgs))
    }
    if msgs[0].Correlation != "abc" || msgs[1].Correlation != "abc" {
        t.Fatalf("correlation lost")
    }
    var out struct {
        Backend string `json:"backend"`
    }
    if err := json.Unmarshal(msgs[1].Raw, &out); err != nil || out.Backend != "lmstudio-win" {
        t.Fatalf("backend lost in raw payload")
    }
}
```

- [ ] **Step 2: Run test to confirm it fails (parser not yet defined)**

```bash
go test ./internal/parser/ -run TestOpenclawParser -v
```

Expected: `undefined: parser.NewOpenclawParser`.

- [ ] **Step 3: Implement minimal parser**

`internal/parser/openclaw.go`:

```go
package parser

import (
    "bufio"
    "encoding/json"
    "fmt"
    "io"
    "time"
)

// OpenclawParser reads OpenClaw envelope JSONL.
// One line per envelope. Fields:
//   type, ts, correlation_id, target_tier, task_type,
//   backend (response only), tokens_in, tokens_out, model_hint
type OpenclawParser struct{}

func NewOpenclawParser() *OpenclawParser { return &OpenclawParser{} }

func (p *OpenclawParser) Name() string { return "openclaw" }

func (p *OpenclawParser) Parse(r io.Reader) ([]Message, error) {
    var out []Message
    sc := bufio.NewScanner(r)
    sc.Buffer(make([]byte, 64*1024), 8*1024*1024) // 8MB max line — envelopes can be large
    for sc.Scan() {
        line := sc.Bytes()
        if len(line) == 0 {
            continue
        }
        var hdr struct {
            Type          string `json:"type"`
            TS            string `json:"ts"`
            CorrelationID string `json:"correlation_id"`
        }
        if err := json.Unmarshal(line, &hdr); err != nil {
            return nil, fmt.Errorf("openclaw line %d: %w", len(out)+1, err)
        }
        ts, _ := time.Parse(time.RFC3339, hdr.TS)
        out = append(out, Message{
            Source:      "openclaw",
            Type:        hdr.Type,
            Timestamp:   ts,
            Correlation: hdr.CorrelationID,
            Raw:         append([]byte(nil), line...),
        })
    }
    return out, sc.Err()
}
```

The `Message` type already exists in `internal/parser/types.go` (look it up first with `grep "type Message"` in the package; if the field names differ, adapt accordingly).

- [ ] **Step 4: Run test to verify it passes**

```bash
go test ./internal/parser/ -run TestOpenclawParser -v
```

Expected: PASS.

- [ ] **Step 5: Register the parser**

`internal/parser/registry.go` (or wherever `RegisterParser`/`init()` lives):

```go
func init() {
    RegisterParser("openclaw", func() Parser { return NewOpenclawParser() })
}
```

If the existing pattern uses a different shape (e.g. table-driven), follow it.

- [ ] **Step 6: Add a fixture file**

`testdata/openclaw/sample.jsonl`:

```
{"type":"request","ts":"2026-05-24T01:00:00Z","correlation_id":"job-001","target_tier":"tier3","task_type":"code"}
{"type":"response","ts":"2026-05-24T01:00:05Z","correlation_id":"job-001","backend":"lmstudio-win"}
```

Add a fixture-driven test that loads from `testdata/openclaw/sample.jsonl` and asserts 2 messages.

- [ ] **Step 7: Commit**

```bash
cd ~/Documents/oramasys/tools/periscope
git checkout -b feat/parser-openclaw-2026-05-24
git add internal/parser/openclaw.go internal/parser/openclaw_test.go internal/parser/registry.go testdata/openclaw/
git commit -m "feat(parser): add OpenClaw envelope parser

Reads ~/.openclaw/sessions/*.jsonl. One JSONL record per envelope.
Preserves correlation_id, target_tier, task_type, model_hint, backend.
Raw payload retained for downstream signals to inspect."
```

---

### Task B.2 — AlphaClaw event parser

Reads `~/.openclaw/state/alphaclaw-events.jsonl`. Same shape as B.1 but the records carry routing decisions.

**Files:**
- Create: `internal/parser/alphaclaw.go`
- Create: `internal/parser/alphaclaw_test.go`
- Create: `testdata/alphaclaw/sample.jsonl`
- Modify: `internal/parser/registry.go`

- [ ] **Step 1: Test**

```go
func TestAlphaclawParser_Routing(t *testing.T) {
    sample := `{"event":"route","ts":"2026-05-24T01:00:00Z","correlation_id":"job-001","chosen_backend":"lmstudio-win","candidates":["lmstudio-win","lmstudio-mac","ollama-mac"],"reason":"affinity:tier3"}
{"event":"mirror_excluded","ts":"2026-05-24T01:00:01Z","correlation_id":"job-001","excluded_backend":"lmstudio-mac","reason":"D14_mirror_policy"}
`
    msgs, err := parser.NewAlphaclawParser().Parse(strings.NewReader(sample))
    if err != nil || len(msgs) != 2 {
        t.Fatalf("want 2 messages, got %d (err=%v)", len(msgs), err)
    }
}
```

- [ ] **Step 2: Implement**

Mirror B.1 — same shape, only the JSON header struct changes to read `event` instead of `type`.

- [ ] **Step 3-7:** Same flow as B.1 (register, fixture, commit).

---

### Task B.3 — PT orchestrator event parser

Reads `Perpetua-Tools/.state/orchestrator-events.jsonl`. Records carry state transitions.

**Files:**
- Create: `internal/parser/pt_orchestrator.go`
- Create: `internal/parser/pt_orchestrator_test.go`
- Create: `testdata/pt_orchestrator/sample.jsonl`
- Modify: `internal/parser/registry.go`

- [ ] **Step 1: Test** — same shape, header now reads `state_from`, `state_to`, `node` (`route` / `dispatch` / `respond`).

- [ ] **Steps 2-7:** Same flow as B.1.

---

### Task B.5 — Routes: `/api/v1/openclaw/*`

Adds 4 read-only HTTP routes. Reuses existing periscope IPC token middleware.

**Files:**
- Create: `internal/server/openclaw.go`
- Create: `internal/server/openclaw_test.go`
- Modify: `internal/server/server.go` (or `routes.go` — wherever the route table lives)

- [ ] **Step 1: Find the existing route registration pattern**

```bash
cd ~/Documents/oramasys/tools/periscope
grep -rln "HandleFunc\|http.Handler\|mux.Handle\|router.GET" internal/server/ | head -10
```

Use the same pattern. Do not introduce a new router library.

- [ ] **Step 2: Write the route handler test (table-driven)**

```go
func TestOpenclawRoutes_Jobs_Empty(t *testing.T) {
    srv := newTestServer(t)  // existing helper in the package
    req := httptest.NewRequest(http.MethodGet, "/api/v1/openclaw/jobs", nil)
    req.Header.Set("X-Periscope-Token", testToken)
    w := httptest.NewRecorder()
    srv.ServeHTTP(w, req)
    if w.Code != 200 {
        t.Fatalf("want 200, got %d: %s", w.Code, w.Body.String())
    }
    // empty DB → empty list
    if w.Body.String() != `{"jobs":[]}` {
        t.Fatalf("unexpected body: %s", w.Body.String())
    }
}
```

- [ ] **Step 3: Implement the handler**

`internal/server/openclaw.go`:

```go
package server

import (
    "encoding/json"
    "net/http"
)

type openclawJob struct {
    ID         string  `json:"id"`
    Branch     string  `json:"branch,omitempty"`
    Status     string  `json:"status"`
    CostUSD    float64 `json:"cost_usd"`
    SignalCnt  int     `json:"signal_count"`
}

func (s *Server) handleOpenclawJobs(w http.ResponseWriter, r *http.Request) {
    jobs, err := s.db.OpenclawJobs(r.Context())
    if err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
    if jobs == nil {
        jobs = []openclawJob{}
    }
    w.Header().Set("Content-Type", "application/json")
    _ = json.NewEncoder(w).Encode(map[string]any{"jobs": jobs})
}
```

`s.db.OpenclawJobs` is a new query method. Add it next.

- [ ] **Step 4: Add the DB query**

`internal/db/openclaw.go` (new file):

```go
package db

import (
    "context"
)

// OpenclawJobs returns all sessions where source = 'openclaw',
// joined with their cost + signal aggregates.
func (s *Store) OpenclawJobs(ctx context.Context) ([]Job, error) {
    rows, err := s.queryx(ctx, `
        SELECT
            s.id,
            COALESCE(s.branch, '') AS branch,
            COALESCE(s.status, 'unknown') AS status,
            COALESCE(c.total_usd, 0) AS cost_usd,
            COALESCE(sig.cnt, 0) AS signal_count
        FROM sessions s
        LEFT JOIN session_costs c   ON c.session_id = s.id
        LEFT JOIN ( SELECT session_id, COUNT(*) AS cnt FROM signals GROUP BY session_id ) sig
            ON sig.session_id = s.id
        WHERE s.source = 'openclaw'
        ORDER BY s.ts_last DESC
        LIMIT 200
    `)
    // ... scan into []Job and return
}
```

Schema fields that don't exist yet (`branch`) require a migration. If `sessions.branch` is missing, add a migration in `internal/db/migrations/`.

- [ ] **Step 5: Register the route**

`internal/server/server.go` (in the route-table function):

```go
mux.HandleFunc("GET /api/v1/openclaw/jobs", s.requireToken(s.handleOpenclawJobs))
mux.HandleFunc("GET /api/v1/openclaw/jobs/{id}", s.requireToken(s.handleOpenclawJob))
mux.HandleFunc("GET /api/v1/openclaw/jobs/{id}/signals", s.requireToken(s.handleOpenclawJobSignals))
mux.HandleFunc("GET /api/v1/openclaw/topology", s.requireToken(s.handleOpenclawTopology))
```

`requireToken` is the existing IPC-token middleware. Reuse it; do not invent new auth.

- [ ] **Step 6: Implement the remaining 3 handlers**

Mirror the pattern — each handler is a thin SQL → JSON shim. Keep them under 30 lines.

- [ ] **Step 7: Tests + commit**

```bash
go test ./internal/server/ -run TestOpenclawRoutes -v
git add internal/server/openclaw.go internal/server/openclaw_test.go internal/db/openclaw.go internal/db/migrations/
git commit -m "feat(server): /api/v1/openclaw/* read-only routes

- jobs (list), jobs/{id}, jobs/{id}/signals, topology
- Reuses existing IPC-token middleware (no new auth surface)
- Adds OpenclawJobs DB query + sessions.branch migration"
```

---

### Task B.10 — Add periscope to `CLAUDE-instru.md` as L4

orama-system repo. One-line addition to the repo registry table.

**Files:**
- Modify: `$OPENCLAW_ROOT/CLAUDE-instru.md`

- [ ] **Step 1: Find the repo registry section**

```bash
grep -n "## .*Repo.*Registry\|repository topology\|L1.*AlphaClaw" "$OPENCLAW_ROOT/CLAUDE-instru.md"
```

- [ ] **Step 2: Add periscope row**

Below the AlphaClaw / PT / orama rows:

```markdown
| `~/Documents/oramasys/tools/periscope/` (local) · `github.com/diazMelgarejo/periscope` | **L4 — Glass** | Session-level observability for AI coding agents. Read-only sidecar; never writes to L1–L3. Reads OpenClaw envelopes, AlphaClaw events, PT orchestrator events. Go + Svelte + TypeScript + Rust desktop + Kotlin plugin. |
```

- [ ] **Step 3: Add cross-link in the "Code exploration rule" section**

If there's a `gbrain code-def` / `gbrain search` cheat sheet, add `periscope-src` as the 4th federated source.

- [ ] **Step 4: Commit**

In `$OPENCLAW_ROOT/`:

```bash
# This dir is NOT a git repo, so commit through the orama-system worktree:
cd ~/Documents/Terminal\ xCode/claude/OpenClaw/orama-system
# (CLAUDE-instru.md lives in the parent OpenClaw/ dir, not in orama-system —
# do NOT git add it from this worktree. Instead, document the change inside
# orama-system's CLAUDE.md § 4, which IS in-repo.)
```

**Correction:** `CLAUDE-instru.md` sits OUTSIDE any git repo (it's in `OpenClaw/`, which is not a git repo per the meta-rule). The right place to add the L4 registry row is `orama-system/CLAUDE.md § 4 — Three-Repo Architecture`. Update that section to say "Four-Repo Architecture" and add the periscope row.

- [ ] **Step 4 (corrected): Edit `orama-system/CLAUDE.md § 4`**

Change:

```markdown
## § 4 — Three-Repo Architecture

```
AlphaClaw (L1 — infra) → Perpetua-Tools (L2 — middleware) → orama-system (L3 — THIS REPO — orchestration)
```
```

To:

```markdown
## § 4 — Four-Repo Architecture

```
AlphaClaw (L1 — infra) → Perpetua-Tools (L2 — middleware) → orama-system (L3 — THIS REPO — orchestration)
                                                                                                ↓ emits events to
                                                                              Periscope (L4 — observability glass, read-only)
```

L4 lives at `~/Documents/oramasys/tools/periscope` (fork: `github.com/diazMelgarejo/periscope`).
Periscope reads session/event JSONL from L1–L3; never writes back.
Full design: [`docs/v2/21-periscope-l4-glass.md`](docs/v2/21-periscope-l4-glass.md)
```

- [ ] **Step 5: Commit + push**

```bash
cd ~/Documents/Terminal\ xCode/claude/OpenClaw/orama-system
git add CLAUDE.md docs/v2/21-periscope-l4-glass.md docs/plans/2026-05-24-periscope-l4-integration-plan.md
git commit -m "docs(v2): add Periscope as L4 glass layer

Adds doc 18 (destiny + design) and the 2026-05-24 integration plan.
Updates CLAUDE.md § 4 to 'Four-Repo Architecture' with L4 = Periscope
(read-only observability sidecar, fork of latentsignal-org/periscope)."
git push origin main
```

---

### Task B.11 — Add `PERISCOPE_URL` / `PERISCOPE_TOKEN` to consolidated `.env` template

The consolidated `.env` template (the one for Cursor cloud agents) needs two new entries.

**Files:**
- Modify: wherever the consolidated `.env.example` template lives (search `grep -rln "PERISCOPE\|ULTRATHINK_PORT" --include=".env*"` to find it)

- [ ] **Step 1: Locate template**

```bash
find ~/Documents -maxdepth 5 -name ".env*" 2>/dev/null | grep -v .Trash | head -10
```

If none exists yet, create `orama-system/.env.example` (NOT `.env`, that's gitignored).

- [ ] **Step 2: Add periscope section**

```bash
# Periscope (L4 — observability glass, optional sidecar)
PERISCOPE_URL=http://127.0.0.1:8080
PERISCOPE_TOKEN=  # paste cursor_secret from ~/.periscope/config.toml
PERISCOPE_AUTOSTART=0   # set to 1 to launch periscope from start.sh
```

- [ ] **Step 3: Commit + push**

---

## Verification

After Phase B lands:

```bash
# 1. Periscope sees OpenClaw envelopes
cd ~/Documents/oramasys/tools/periscope
go run ./cmd/periscope sync --source openclaw
go run ./cmd/periscope                       # opens UI
# Navigate to http://127.0.0.1:8080/openclaw/jobs — should show recent orama jobs

# 2. API works
curl -H "X-Periscope-Token: $(grep cursor_secret ~/.periscope/config.toml | cut -d'"' -f2)" \
     http://127.0.0.1:8080/api/v1/openclaw/jobs | jq .

# 3. orama-system docs updated
grep "Four-Repo\|L4" ~/Documents/Terminal\ xCode/claude/OpenClaw/orama-system/CLAUDE.md
ls ~/Documents/Terminal\ xCode/claude/OpenClaw/orama-system/docs/v2/21-periscope-l4-glass.md
ls ~/Documents/Terminal\ xCode/claude/OpenClaw/orama-system/docs/plans/2026-05-24-periscope-l4-integration-plan.md

# 4. gbrain knows about periscope
gbrain sources list | grep periscope
gbrain search "periscope L4 glass" --source periscope-src
```

---

## What is NOT in this plan (deferred to Phase C)

- Signals (B.4) — 5 new signal types
- CLI subcommands (B.6) — `periscope openclaw status`, `watch <job-id>`
- Svelte routes (B.7) — `/openclaw/jobs/*` UI
- gbrain bridge (B.8) — write summaries into gbrain
- start.sh autostart (B.9) — `PERISCOPE_AUTOSTART=1` env opt-in

Each of those is its own small plan once Phase B is stable on `main` for a week.

---

## Risk gates (operator review points)

- **After A.1 (merge `merged` → `main`):** Stop and verify `go test ./...` passes before A.2.
- **After A.2 (cmd rename):** Stop and verify the binary works under both names before A.3.
- **After B.1 + B.2 + B.3 (parsers):** Stop. Run `periscope sync --source openclaw` against real `~/.openclaw/sessions/*.jsonl`. Confirm session count > 0 in the UI before B.5.
- **After B.5 (routes):** Stop. Hit each route with `curl`. Confirm token middleware blocks unauthenticated requests.
