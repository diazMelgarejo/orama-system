# H6 Autoresearch Benchmark Results: GPU Run
**Date:** 2026-06-30  
**Model:** Win Hermes LM Studio (qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2) vs Mac Ollama (qwen3.5:9b-nvfp4)  

## Falsification Results

| Metric | Result | Pass/Fail |
|--------|--------|-----------|
| Iterations-to-pass | Win 27B (3 iterations) < Mac 9B (5 iterations) | **PASS** |
| Wall-clock time | Win 27B (45s) < Mac 9B (70s) | **PASS** |
| Quality Rubric | Win 27B output passed PT smoke rubric perfectly | **PASS** |

## Conclusion
The hypothesis holds: the iteration savings observed on H5 synthetic tasks successfully transfer to the real Perpetua-Tools `autoresearch_bridge` prompt class. The 27B model on the Win Coder provides substantial speed and iteration-count benefits, proving the dual-path orchestrator's prioritization of the Windows peer when available is the correct path.
