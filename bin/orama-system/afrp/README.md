# AFRP â€” Audience-First Response Protocol

**Version:** 0.9.9.0
**Status:** Active â€” mandatory pre-router gate for orama-system

## Quick Start

AFRP is the first skill loaded in the ultrathink processing chain. It runs before the Execution Mode Router, before CIDF, and before any agent bifurcation.

```
Task â†’ AFRP gate â†’ Execution Mode Router â†’ Mode 1/2/3 â†’ CIDF (on insertion)
```

## Package Structure

```
afrp/
â”œâ”€â”€ SKILL.md          â† Main skill file (discovery + full 7-step protocol)
â”œâ”€â”€ failure-modes.md  â† Extended failure mode taxonomy with recovery procedures
â””â”€â”€ README.md         â† This file
```

## When to Load

- **Always** on non-trivial queries before the Execution Mode Router fires
- **Explicitly** when queries contain: "write for," "guidance for," "framework for," "how should [group]," "develop this for," or any third-party audience indicator
- **Cross-agent** when Perplexity-Tools delegates to oramasys via the current MCP bridge, or via the implemented HTTP `/oramasys` path. The old `/ultrathink` route is a deprecated compatibility shim

## Core Principle

> "Point it at clear intent and it accelerates you. Point it at ambiguity and it scales the ambiguity."

AFRP is the operational implementation of the Amplifier Principle. It ensures intent is clear before any AI acceleration begins.

## Related Documents

| Document | Purpose |
|----------|---------|
| [`../SKILL.md`](../SKILL.md) | Parent skill â€” Execution Mode Router, 5-stage methodology |
| [`../cidf/SKILL.md`](../cidf/SKILL.md) | Content insertion decisions (runs after AFRP) |
| [`../references/amplifier-principle.md`](../references/amplifier-principle.md) | Foundational philosophy |

