# Custom MCP Server Skill

> Extracted from `mcp-orchestration/SKILL.md` §8 during the 2026-07-22
> skill-trimming pass. Use only when existing tools do not provide the
> needed action — see `SKILL.md` §14 Decision Table's "Missing capability" row.

## Scaffold

```bash
mkdir my-mcp-server && cd my-mcp-server
npm init -y
npm install @modelcontextprotocol/sdk zod
mkdir -p src
```

## Minimal TypeScript server

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const server = new McpServer({ name: "my-skill", version: "1.0.0" });

server.registerTool(
  "my_tool",
  {
    description: "Runs one safe custom action.",
    inputSchema: {
      action: z.string().describe("Action to perform"),
      target: z.string().optional().describe("Target resource"),
    },
  },
  async ({ action, target }) => ({
    content: [{ type: "text", text: `Executed ${action} on ${target ?? "default"}` }],
  }),
);

const transport = new StdioServerTransport();
await server.connect(transport);
```

## Register

```bash
npx tsc
claude mcp add my-skill -- node dist/index.js
```

## Security baseline

- Use allowlists
- Keep tools narrow
- Avoid broad filesystem access
- Do not pass secrets in prompts
- Use environment variables for credentials
- Require confirmation before destructive actions
