# Win code review — main push (6 commits)

**Assignee:** win-coder (RTX 5080)  
**Topic:** code-review/main-push-2026-07-23  
**Fan-out:** coord-025  
**Reviewed at:** `4e47341c` on `main`  
**Range:** `03143156..4e47341c` (6 commits)  
**Prereq read:** `win-rtx5080-windows-dev-reference.md` (workspace sibling)

## Executive summary

**Overall verdict: PASS WITH CONCERNS** — no blockers. The push correctly sequences gitignore hardening before the ECC vendor drop, absorbs `windows-hermes-setup` into canonical hermes-harness, wires partner CLI PATH into `start.ps1`, and preserves `no-workstation-paths.mdc`. Tracked files in the range contain no workstation path leaks (LINT-006). F3 (CRG Windows endpoint) resolved by platform policy + sync script. Two follow-ups remain: align `start.ps1` PATH sourcing with `install.ps1` (`&` vs dot-source).

---

## Verdict per commit

| SHA | Subject | Verdict | Notes |
|-----|---------|---------|-------|
| `2a9bbf7a` | fix: ensure partner CLI paths in start.ps1 | **PASS WITH CONCERNS** | Correct placement after `.paths.ps1` load, before PT discovery. Dot-sources `ensure-partner-cli-paths.ps1` (differs from `install.ps1` which uses `&`). Side effects run on `--stop` / `--status` / `--discover` / `--hardware-policy` (not on `--validate` / `--list`). |
| `67ddd1ce` | chore: gitignore Hermes runtime + Cursor steering state | **PASS** | `.hermes/` and `.cursor/state/` added before ECC install — correct ordering. |
| `9faaf51e` | feat(hermes): absorb windows-hermes-setup | **PASS** | Command card, operator playbook, absorption map pin, thin-wrapper registry + test slug update. Docs use `%USERPROFILE%` / env anchors only. |
| `a53d2708` | docs(hermes): Win RTX5080 peer drop | **PASS** | Peer summary is path-hygienic; correctly defers PT `.cursor/` ECC and P5 branch work. |
| `4f52089f` | chore: gitignore local Cursor ECC skills and hooks | **PASS** | Covers `ecc-install-state.json`, `skills/`, `hooks/`, `hooks.json` — prevents machine-local ECC artifacts from being committed. |
| `4e47341c` | feat(cursor): ECC minimal profile install | **PASS WITH CONCERNS** | ~42k-line ECC bootstrap tracked; `no-workstation-paths.mdc` preserved; `ecc-install-state.json` not in tree. `.cursor/mcp.json` CRG block targets `localhost:11434` (Mac Ollama default) — suboptimal on Win LM Studio hosts without override. |

---

## Findings table

| ID | Severity | Commit | File / area | Finding | Recommendation |
|----|----------|--------|-------------|---------|----------------|
| F1 | **MEDIUM** | `2a9bbf7a` | `platform/windows/start.ps1` | Dot-sources `ensure-partner-cli-paths.ps1` (`. "…"`) while `install.ps1` invokes it (`& $PathScript`). Dot-sourcing leaks `Add-UserPathEntry` and script variables into `start.ps1` scope. | Change to `& "$RepoRoot\platform\windows\ensure-partner-cli-paths.ps1"` for parity with `install.ps1`. |
| F2 | **LOW** | `2a9bbf7a` | `platform/windows/start.ps1` | Partner PATH mutation runs for lifecycle/read-only modes (`--stop`, `--status`, `--discover`, `--hardware-policy`) because sourcing sits before those handlers. `--validate` / `--list` correctly exit earlier. | Gate PATH ensure behind startup modes only, or accept as idempotent noise and document in `windows-hermes-setup.md`. |
| F3 | **RESOLVED** | `4e47341c` | `.cursor/mcp.json` | ECC-shipped CRG env used macOS default (`:11434`). | Policy documented in `crg-platform-endpoints.md`; `sync-cursor-mcp.sh` + `openclaw-env.sh` now patch `:1234` on Windows. Operators re-run sync after pull. |
| F4 | **INFO** | `4e47341c` | `.cursor/` (bulk) | Large vendor surface (+375 files). `no-workstation-paths.mdc` and repo attribution rules coexist with ECC `common-*` rules — expected for minimal profile bootstrap; future `agent-sort` trim optional. | No immediate action; consider agent-sort pass in a follow-up chore. |
| F5 | **INFO** | `9faaf51e` | `hermes-skill-absorption-map.md` | Curator pin step documented (`hermes curator pin windows-hermes-setup`) but not automated in `install_hermes_thin_skills.py`. | Operator runs pin once after absorption; acceptable. |

**Blockers:** none  
**Path hygiene (LINT-006):** no `C:\<user>\…` or workspace-tree literals in tracked files added by this range (verified via `repo_hygiene.py` + diff scan). Local `.cursor/ecc-install-state.json` contains machine paths but is gitignored and not in `4e47341c` tree.

---

## Review focus checklist

| Focus | Result |
|-------|--------|
| `start.ps1` sourcing order / idempotency | Placement correct; invoke-style inconsistency (F1) |
| `windows-hermes-setup` absorption + thin wrappers | Complete; `--verify` passes |
| `.gitignore` exclusions | Correct and sequenced before ECC commit |
| `.cursor/` ECC — paths + `no-workstation-paths.mdc` | Preserved; no tracked path leaks |
| `repo_hygiene` / LINT-006 | PASS |
| Reference doc open items | PT Cursor ECC, P5 PR #136, H6 real-task still open (documented in peer drop) |

---

## Tests run

| Command | Result |
|---------|--------|
| `python -m pytest tests/test_hermes_thin_skills.py -q` | **21 passed** (3.30s) |
| `python scripts/review/repo_hygiene.py .` | **OK** — hygiene checks passed |
| `python bin/orama-system/skills/hermes-harness/scripts/install_hermes_thin_skills.py --verify` | **verification passed** |
| `git diff 03143156..4e47341c` path-leak scan (tracked files) | **No workstation paths** in committed content |
| `git ls-tree -r 4e47341c --name-only \| grep ecc-install-state` | **Not tracked** (gitignore effective) |

---

## Gaps vs reference doc (still open — not regressions)

- PT repo Cursor ECC install (`install.ps1 --target cursor` from ecc-tools) — deferred
- P5 PR #136 (`cursor/security-pr3-swarm-approval-f559`) — 2/7 tasks
- Mac H6 real-task (`mac-hypothesis-h6-real-task.md`) — awaiting follow-through
- `cursor-agent` usage limits — manual branch completion noted in reference

---

## Peer comms

**Mac peer drop:** run after commit/publish of this file:

```powershell
cd $env:ORAMA_SYSTEM_PATH
python bin\orama-system\skills\hermes-harness\scripts\lan_peer_assign.py drop --peer `
  --file references\results\win-code-review-main-push-6.md `
  --assignee mac --topic code-review/main-push-2026-07-23
python bin\orama-system\skills\hermes-harness\scripts\lan_peer_assign.py flush-outbox --peer
```

**GossipBus (optional):**

```powershell
cd $env:PERPETUA_TOOLS_PATH
python scripts\agent_coordination.py log win-coder "main push 6-commit review PASS WITH CONCERNS — see win-code-review-main-push-6.md"
```

---

*Reviewer: win-coder @ RTX 5080 · Frugality B1 (local pytest only)*
