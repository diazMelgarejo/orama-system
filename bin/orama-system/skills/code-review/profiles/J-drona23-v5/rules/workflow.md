# Workflow Rules

## Before writing code
- MUST use code-review-graph to map blast-radius first (MCP tool: `code-review-graph`)
- MUST read only the files surfaced — do not read the full repo
- MUST understand the full requirements before writing any code
- NEVER start coding before reading the input data or schema

## While writing code
- MUST test code after writing it (run the script/server)
- NEVER leave code untested
- MUST fix errors before moving on — do not skip failures
- NEVER hardcode paths that should be relative

## Before declaring done
- MUST verify output matches expected format
- MUST run the code one final time to confirm it works
- NEVER declare done without running the code at least once

## Codebase exploration order
1. `code-review-graph` (blast-radius map) — identifies which files matter
2. `gbrain code-def <symbol>` — resolves symbols without reading full files
3. `gbrain search "<intent>"` — retrieves past decisions from LESSONS.md
4. `Read` — only for files confirmed relevant by steps 1-3
