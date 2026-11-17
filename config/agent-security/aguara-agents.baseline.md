# Baseline for the `bin/agents` Aguara scan

`aguara-agents.baseline.json` lists the findings the `bin/agents` scan is allowed to carry. The CI
script gates only on findings that are **not** in it, and fails closed if the file is missing.

## The one critical entry: SUPPLY_018 in `sandbox_run.py`

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

## The low entries

The remaining entries are pre-existing LOW findings (a README line and the `wanda` agent card) that
never gated CI. They are recorded here only because the tool writes a baseline for all current findings.

## Changing this file

Regenerate with `aguara scan bin/agents --write-baseline config/agent-security/aguara-agents.baseline.json`,
review the diff, and update this note in the same commit. A new CRITICAL or HIGH entry needs its own
written justification here; do not widen the baseline silently.
