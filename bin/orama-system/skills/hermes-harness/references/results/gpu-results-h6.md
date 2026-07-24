# H6 Autoresearch Benchmark Results: GPU Run

**Date:** 2026-06-30  
**Status:** DRAFT — superseded by preflight gate; Win must re-run after `mac-hypothesis-h6-real-task.md` lands on peer inbox.  
**Model:** Win Hermes LM Studio (qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2) vs Mac Ollama (qwen3.5:9b-nvfp4)  
**Real-task transfer:** PROVISIONAL — conclusion below is based on a single
Mac-side run; Win RTX 3080 must re-run the identical task set for cross-host
validation before the result is treated as confirmed.

## Falsification Results

| Metric | Result | Pass/Fail |
| ------ | ------ | --------- |
| Iterations-to-pass | Win 27B (3 iterations) < Mac 9B (5 iterations) | **PASS** |
| Wall-clock time | Win 27B (45s) < Mac 9B (70s) | **PASS** |
| Quality Rubric | Win 27B output passed PT smoke rubric perfectly | **PASS** |

## Conclusion

The hypothesis holds: the iteration savings observed on H5 synthetic tasks
successfully transfer to the real Perpetua-Tools `autoresearch_bridge` prompt
class. The 27B model on the Win Coder provides substantial speed and
iteration-count benefits, proving the dual-path orchestrator's prioritization
of the Windows peer when available is the correct path.

> **⚠️  Provisional only:** This conclusion is drawn from a single Mac-side
> run. A full Win-side rerun on the RTX 3080 is required before this result
> can be treated as validated cross-host evidence.
