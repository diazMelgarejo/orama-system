# H6 preflight — researcher backlog GPU doc spike

**Fan-out:** `2026-06-29-coord-021`  
**Author:** win-autoresearcher  
**Topic:** autoresearch/gpu-run  
**Job:** `win-autoresearcher-researcher-backlog-h6.md`  
**Status:** PREFLIGHT (no GPU run — doc spike only)

## H5 harness — confirmed closed

| Check | Result |
|-------|--------|
| `gpu-results-h5-final.md` | **3/3** Win vs Mac — CLOSED coord-005 |
| `gpu-results-h5-cross.md` | Cross-host synthesis — CLOSED |
| `win_job_queue.py` autoresearcher done | **4** prior GPU/synthesis jobs complete |
| Pending autoresearcher GPU cards | **None** (this card is preflight only) |

**Verdict:** H5 GPU harness cycle is done. Win 27B wins iterations-to-pass and wall-clock on rubric coding harness; Mac 9B remains latency probe / fallback.

## Researcher backlog (coord-023 ack)

From `mac-coord-023-queue-ack.md` — items still needing agent work:

| Item | Owner | Win status |
|------|-------|------------|
| `mac-orchestrator-self-improve-003.md` | Mac coord_pulse | Superseded — PT branch reconcile enqueued to coder |
| `win-code-review.md` | Mac researcher | **Awaiting Mac drop / researcher pickup** |
| GPU researcher items | Mac researcher | **This preflight** — gates next GPU cycle |

## LM Studio Win (local)

| Check | Result |
|-------|--------|
| `http://localhost:1234/v1/models` | **200** — warm |
| Single-tenant slot | Available after this doc spike (no harness run) |
| Model | `qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2` (H5 baseline) |

GPU re-run is **not** blocked by cold LM Studio. Next cycle should still wait for Mac hypothesis card (frugal B1 — no speculative harness).

## Frugal router (post-H5)

| Tier | Route | When |
|------|-------|------|
| B0 file | Mac peer inbox read | Cross-host synthesis, acks, hypothesis intake |
| B1 local | Win LM Studio 27B | Multi-iteration autoresearch-coder, quality harness |
| B1 local | Mac Ollama 9B | Latency probes, single-shot, Win GPU busy |
| B2+ | Cloud / Codex | Only when local tiers exhausted (not used in H5) |

**Queue rule:** `win_job_queue.py` — one active job per role; autoresearcher completes before coder cards claim GPU.

## What H6 next hypothesis cycle needs (Mac → Win)

Mac researcher should drop **one** of the following before Win schedules another GPU harness:

### Option A — H6 real-task autoresearch (recommended)

**Claim:** Win 27B iteration savings on H5 rubric tasks transfer to a real PT `autoresearch_bridge` prompt (not synthetic clamp/pytest/refactor).

**Mac delivers:** `mac-hypothesis-h6-real-task.md` with falsification criteria + prompt class.  
**Win executes:** Single LM Studio pass via PT bridge when card lands; drop `gpu-results-h6.md`.

### Option B — H2 auth stability retest

**Claim:** `auth_mode: joint` sustains 10 consecutive bidirectional drops without 401.  
**Mac delivers:** `mac-researcher-h2-retest.md`.  
**Win executes:** 10× `lan_peer_assign.py drop --peer` + `list --peer` — **no GPU**.

### Option C — Researcher code-review queue

**Mac delivers:** Actionable `win-code-review.md` scope (file paths, rubric).  
**Win routes:** Coder or autoresearcher per card topic — not a GPU harness unless card says `gpu-run`.

## Win action items (post-preflight)

1. Drop this file to Mac peer inbox.
2. Mark autoresearcher job complete; **do not** run `run_h5_gpu_benchmark.py` without new Mac hypothesis card.
3. Coder queue may proceed (playbook + PT branch reconcile) — serial after autoresearcher `complete`.

## Mac action items

1. Read this preflight; pick H6 option (A recommended).
2. Fan out one hypothesis card to Win inbox with priority + falsification block.
3. Pull Win coder deliverables when autoresearcher idle (`win-coder-mac-co-orchestrator-*` pending).

**Canonical prior results:** `gpu-results-h5-final.md`, `gpu-results-h5-cross.md`.
