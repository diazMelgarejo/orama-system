# Baseline for the `bin/agents` Aguara scan

`aguara-agents.baseline.json` lists the findings the `bin/agents` scan is allowed to carry. The CI
script gates only on findings that are **not** in it, and fails closed if the file is missing.

## The critical entry: SUPPLY_018 in `sandbox_run.py`

Rule SUPPLY_018 ("sandbox escape via process spawn") is a lexical match: the words exec, spawn, popen,
system or subprocess within sixty characters of sandbox, restricted, isolated or contained. The line
that names the macOS kernel sandbox tool (`/usr/bin/sandbox-exec`) matches because the tool's own name
contains both words. This is a false positive in the sense of the rule's own list ("restrict process
spawning inside the sandbox"): `sandbox_run.py` is the defence, not the escape. It runs model-written
code through the kernel sandbox with a scrubbed environment, no network, writes only inside a scratch
root, reads only from the interpreter and the scratch root, and forking denied.

The tool is named in exactly one place (a constant), a test enforces that, and the name is not
obfuscated to dodge the scanner. If the finding disappears, `tests/test_agent_security_baseline.py`
fails and the entry should be removed.

## The high entry: SUPPLY_017 in `seat_contracts.py`

Rule SUPPLY_017 ("hardlink workspace escape") matches the `os.link` call in `pin_evaluator`. The
link cannot reach outside the workspace: its source is a temp file that `pin_evaluator` has just
created with `tempfile.mkstemp` in the pin's own directory, and its target is the pin path in that
same directory. `os.link` is used because it is the atomic, exclusive create. It fails when a pin
already exists, so a pin is written once and readers never see a partial file. The temp file is
removed in `finally`. Replacing it with `O_CREAT | O_EXCL` on the final path would expose a partial
pin to a concurrent reader. Accepted by the operator on 2026-11-17 (orama PR #519).

## The low entries

The remaining entries are pre-existing LOW findings (a README line and the `wanda` agent card) that
never gated CI. They are recorded here only because the tool writes a baseline for all current findings.

## Changing this file

Regenerate with `aguara scan bin/agents --write-baseline config/agent-security/aguara-agents.baseline.json`,
review the diff, and update this note in the same commit. A new CRITICAL or HIGH entry needs its own
written justification here; do not widen the baseline silently.
