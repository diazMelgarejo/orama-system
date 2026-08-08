# Eval Checklist — oramasys-method

## 6Cs

- [ ] Clarity: the AFRP gate output format has exactly one reading.
- [ ] Completeness: Mode 1/2/3 routing and the merge-mode doctrine both
      cover their edge cases.
- [ ] Conciseness: `SKILL.md` still reads as a table of contents; deep
      material stays in `references/`.
- [ ] Consistency: "ultrathink" and "oramasys" are treated as the same
      trigger everywhere, including in the description.
- [ ] Correctness: every referenced tool name (`gbrain`, `mcp-oramasys`,
      `code-review-graph`) matches what the current harness actually
      exposes, with a stated fallback when it doesn't.
- [ ] Context: a reader unfamiliar with orama-system can still follow
      Step 0 through Step 4 without opening every reference file.

## Review Personas

- **Exec** — Would a non-technical stakeholder understand *why* the AFRP
  gate exists (it prevents scaling ambiguity, per the Amplifier Principle)?
- **Builder** — Can Steps 0-4 be executed in order without guessing a
  missing tool-availability check?
- **Critic** — What could this skill overreach on? Check specifically:
  escalating to a paid search tier without asking, spawning Mode 3 without
  a genuine 8+-step justification, and resolving PR conflicts with
  `--ours`/`--theirs` instead of classifying the merge mode.

## AFRP Classification Spot-Check

For each eval prompt, confirm the classification the skill states matches
the prompt's actual shape:

- [ ] Type A/small-B prompts route to Mode 1 (no unnecessary 5-stage
      ceremony on a simple lookup).
- [ ] Type C (3-7 step) prompts route to Mode 2.
- [ ] Type C (8+ step, parallel) prompts route to Mode 3 — and only after
      the "Ask First: spawning the full Mode-3 network" gate is honored.

## Sandbox Limitation Note

This repo's live integrations (`gbrain`, `mcp-oramasys` at
`127.0.0.1:18789`, the OpenClaw gateway, the Windows coder pool) are not
reachable from every harness that might run these evals. When they're
absent, score the **reasoning shape and stated fallback**, not whether the
tool call actually succeeded — and say explicitly in the eval report which
tools were live versus simulated.

## Size Gate

- [ ] `SKILL.md` is <= 200 lines, or the overage has a written reason.
- [ ] Modular files stay one level from `SKILL.md`.
