<!-- lint-ignore LINT-013 -->
# AutoResearch Task Type (Mode 3)

> How Mode 3 behaves when Perpetua-Tools reports an `autoresearch` or `ml-experiment` task:
> execution topology, reasoning layer, GPU lock and the cross-repo stack. Moved verbatim out of
> `SKILL.md`; the `### AutoResearch Integration` heading stays there as a pointer
> (heading level raised here).

## AutoResearch Integration (Mode 3 Task Type)

When the coordinating system reports **`task_type`** of **`autoresearch`** or **`ml-experiment`** (from **Perpetua-Tools**):

1. **Defer execution topology** to Perpetua-Tools: `POST /autoresearch/sync` must succeed (`sync_ok == true`) before deep multi-step planning assumes the GPU workspace is ready.
2. **Reasoning layer (this repo)**: apply **CIDF / ultrathink** methodology for hypotheses, critique, and next-step narrative — but **do not** assume cloud models for autoresearch unless the user explicitly overrides (see Perpetua-Tools `SKILL.md` “autoresearch Tasks”).
3. **GPU lock & metrics**: treat **`swarm_state.md`** (IDLE/BUSY) and **`log.txt` / `val_bpb`** as the source of truth for whether a run is active and whether metrics are valid.
4. **Cross-repo stack**: Perpetua-Tools (orchestrator) → orama-system (reasoning) → ECC Tools (optional parallel executors) → Karpathy autoresearch loop on the GPU host.

For local setup work inside Perpetua-Tools, the Perplexity client now exposes optional `base_url` and `timeout` overrides, and the smoke-test script accepts the same values:

```bash
python scripts/test_perplexity.py --validate --base-url https://api.perplexity.ai --timeout 30
```
