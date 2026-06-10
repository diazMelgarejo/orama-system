# CIDF Ranks, MCP Tool Names, and Legacy Compatibility

## CIDF — Content Insertion Decision Framework (v1.2)

Before inserting/writing/pasting/uploading content, pick the simplest method.
Start at rank 1; only escalate when the current rank is ineligible.

| Rank | Method | Eligible when |
|---|---|---|
| 1 | `direct_form_input` | field accessible, content < 10k |
| 2 | `direct_typing` | editor visible, content < 5k |
| 3 | `clipboard_paste` | paste supported |
| 4 | `file_upload` | upload available |
| 5 | `scripting` | automation gate open (freq >= 5, conditional logic, transform, or external integration) |

Verify programmatically after insertion — never trust the visual alone.

## MCP routing

| Purpose | Canonical name |
|---|---|
| Offload heavy reasoning (Mode 2/3) | **`mcp-oramasys`** when exposed by the harness |
| Local HTTP backup | `POST /oramasys` port 8001 |
| Mode-3 agent network | orchestrator + 6 specialist agents |

## Legacy compatibility map (ultrathink -> oramasys)

| Legacy | New |
|---|---|
| `mcp-ultrathink-lmstudio` | `mcp-oramasys` |
| `mcp-ultrathink-openclaw` | `mcp-oramasys` |
| `POST /ultrathink` | `POST /oramasys` (deprecated shim, one release) |
| trigger word "ultrathink" | alias for "oramasys" |
| `references/oramasys-5-stages.md` | `references/oramasys-5-stages.md` |

**Rule:** never reintroduce legacy MCP names in new config or skills.
