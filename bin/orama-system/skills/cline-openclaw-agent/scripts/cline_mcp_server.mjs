#!/usr/bin/env node
/**
 * Cline MCP Server — exposes Cline CLI one-shot execution as MCP tools.
 * Tools: cline_exec, cline_plan, cline_history, cline_version
 * Transport: stdio (JSON-RPC 2.0 over MCP protocol)
 */
import { execFile, spawnSync } from "node:child_process";

const CLINE_BIN = process.env.CLINE_BIN || "cline";
const DEFAULT_TIMEOUT_S = "600";

function runCline(args, timeoutS) {
  return new Promise((resolve) => {
    const timeout = parseInt(timeoutS || DEFAULT_TIMEOUT_S, 10) * 1000;
    execFile("cline", args, {
      encoding: "utf8", timeout, maxBuffer: 10 * 1024 * 1024,
      env: { ...process.env, FORCE_COLOR: "0", NO_COLOR: "1" },
    }, (err, stdout, stderr) => {
      resolve({
        ok: !err || err.code === 0,
        exitCode: err ? err.code : 0,
        stdout: stdout || "", stderr: stderr || "",
        error: err && err.killed ? `timed out after ${timeoutS}s` : (err ? err.message : ""),
      });
    });
  });
}

const TOOLS = [
  {
    name: "cline_exec",
    description: "Run a non-interactive Cline one-shot coding task. Returns JSON output. Uses cline-pass/glm-5.2 by default. Auto-approve enabled for non-interactive use.",
    inputSchema: {
      type: "object",
      properties: {
        prompt: { type: "string", description: "The task prompt" },
        cwd: { type: "string", description: "Working directory" },
        thinking: { type: "string", enum: ["none","low","medium","high","xhigh"], description: "Reasoning effort (default: medium)" },
        provider: { type: "string", description: "Cline provider id (default: cline-pass)" },
        model: { type: "string", description: "Cline model id (default: cline-pass/glm-5.2)" },
        timeout: { type: "string", description: "Timeout in seconds (default: 600)" },
        retries: { type: "string", description: "Max mistakes before exit (default: 3)" },
      },
      required: ["prompt"],
    },
  },
  {
    name: "cline_plan",
    description: "Run Cline in plan mode (read-only, no mutations). Returns JSON output.",
    inputSchema: {
      type: "object",
      properties: {
        prompt: { type: "string", description: "The analysis/planning prompt" },
        cwd: { type: "string", description: "Working directory" },
        thinking: { type: "string", enum: ["none","low","medium","high","xhigh"], description: "Reasoning effort (default: medium)" },
        timeout: { type: "string", description: "Timeout in seconds (default: 600)" },
      },
      required: ["prompt"],
    },
  },
  {
    name: "cline_history",
    description: "List recent Cline sessions (no API cost). Returns JSON.",
    inputSchema: { type: "object", properties: { limit: { type: "string", description: "Max sessions (default: 20)" } } },
  },
  {
    name: "cline_version",
    description: "Get Cline CLI version and binary path. No API cost.",
    inputSchema: { type: "object", properties: {} },
  },
];

// CHUNK2_MARKER
async function handleToolCall(name, args) {
  const a = args || {};
  switch (name) {
    case "cline_exec": {
      const cliArgs = [a.prompt, "--json", "--auto-approve", "true", "--thinking", a.thinking || "medium",
        "-P", a.provider || "cline-pass", "-m", a.model || "cline-pass/glm-5.2",
        "--timeout", a.timeout || DEFAULT_TIMEOUT_S, "--retries", a.retries || "3"];
      if (a.cwd) cliArgs.push("-c", a.cwd);
      const r = await runCline(cliArgs, a.timeout || DEFAULT_TIMEOUT_S);
      return { content: [{ type: "text", text: JSON.stringify(r, null, 2) }], isError: !r.ok };
    }
    case "cline_plan": {
      const cliArgs = [a.prompt, "--plan", "--json", "--auto-approve", "true",
        "--thinking", a.thinking || "medium", "--timeout", a.timeout || DEFAULT_TIMEOUT_S];
      if (a.cwd) cliArgs.push("-c", a.cwd);
      const r = await runCline(cliArgs, a.timeout || DEFAULT_TIMEOUT_S);
      return { content: [{ type: "text", text: JSON.stringify(r, null, 2) }], isError: !r.ok };
    }
    case "cline_history": {
      const r = await runCline(["history", "--json", "--limit", a.limit || "20"], "30");
      return { content: [{ type: "text", text: r.stdout || r.stderr || "[]" }], isError: !r.ok };
    }
    case "cline_version": {
      const r = await runCline(["version"], "10");
      const p = spawnSync("command", ["-v", "cline"], { shell: true, encoding: "utf8" });
      return { content: [{ type: "text", text: JSON.stringify({ version: r.stdout.trim(), bin: p.stdout.trim() || CLINE_BIN }, null, 2) }], isError: false };
    }
    default:
      return { content: [{ type: "text", text: `Unknown tool: ${name}` }], isError: true };
  }
}

// stdio JSON-RPC loop
let buffer = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", async (chunk) => {
  buffer += chunk;
  const lines = buffer.split("\n");
  buffer = lines.pop() || "";
  for (const line of lines) {
    if (!line.trim()) continue;
    let msg; try { msg = JSON.parse(line); } catch { continue; }
    if (msg.jsonrpc !== "2.0") continue;
    const { id, method, params } = msg;
    try {
      let result;
      switch (method) {
        case "initialize": result = { protocolVersion: "2024-11-05", capabilities: { tools: {} }, serverInfo: { name: "cline-mcp", version: "1.0.0" } }; break;
        case "initialized": continue;
        case "tools/list": result = { tools: TOOLS }; break;
        case "tools/call": result = await handleToolCall(params.name, params.arguments); break;
        default:
          process.stdout.write(JSON.stringify({ jsonrpc: "2.0", id, error: { code: -32601, message: `Method not found: ${method}` } }) + "\n");
          continue;
      }
      process.stdout.write(JSON.stringify({ jsonrpc: "2.0", id, result }) + "\n");
    } catch (err) {
      process.stdout.write(JSON.stringify({ jsonrpc: "2.0", id, error: { code: -32603, message: err.message } }) + "\n");
    }
  }
});
process.stdin.on("end", () => process.exit(0));
