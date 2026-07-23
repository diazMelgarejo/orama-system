# Win RTX 5080 — CRG endpoint correction (F3 errata)

**Fan-out:** coord-025  
**To:** Windows RTX 5080 (all Win lanes)  
**Status:** OPERATOR RULE — not a code-review blocker

## Rule

| Platform | CRG `CRG_OPENAI_BASE_URL` | Inference backend |
|----------|---------------------------|-------------------|
| **macOS only** | `http://localhost:11434/v1` | Ollama (`bge-m3`) |
| **Windows (all)** | `http://localhost:1234/v1` | LM Studio |

**`:11434` is macOS-only.** Every Windows host — including RTX 5080 @ `192.168.8.153` and
the primary Win orchestrator — must use **LM Studio `:1234`**, not Ollama's default port.

## Action on 5080

1. Open `.cursor/mcp.json` → `code-review-graph` → `env`
2. Set `"CRG_OPENAI_BASE_URL": "http://localhost:1234/v1"`
3. Verify LM Studio is listening: `curl http://localhost:1234/v1/models`

## Context

Code review F3 flagged ECC's shipped `:11434` default. That is correct for Mac;
Windows operators must override locally. Canonical doc:
`bin/orama-system/skills/hermes-harness/references/ecc-doctor-and-cursor-smoke-checks.md`
§ CRG platform endpoint rule.

## Mac peer

Keep Mac CRG at `:11434` — no change.
