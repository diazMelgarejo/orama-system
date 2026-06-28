# Win autoresearcher — H4 coding-loop benchmark

**Assignee:** win (autoresearcher, Hermes)  
**Topic:** autoresearch/gpu-run  
**Fan-out:** 2026-06-28-autoresearch-002

## Context

Read Mac inbox files:

```powershell
python bin\orama-system\skills\hermes-harness\scripts\lan_peer_assign.py read --name mac-hypothesis-v2.md
```

H3 falsified for trivial latency. H4 tests **coding-loop quality** on 27B.

## Task

1. Run 3 representative autoresearch-coder prompts on `qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2` @ `localhost:1234`
2. Record: wall-clock, tokens, iteration quality (pass/fail rubric)
3. Drop `gpu-results-h4.md` to Mac peer inbox

## Also read

- `win-code-review.md` finding #1 — note SSH vs HTTP for preflight (landmark only this cycle)
