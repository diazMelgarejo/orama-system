/** Stateless Sites MCP adapter. PT owns contracts and persistent record operations. */
import { compilePrompt, PromptError, PromptStore } from './perpetua.mjs';

const string = { type: 'string', maxLength: 32768 };
const promptProperties = { original: string, role: string, goal: string, constraints: string, output_format: string };
const schema = (properties, required = []) => ({ type: 'object', properties, required, additionalProperties: false });
const tool = (name, description, inputSchema, readOnlyHint) => ({ name, description, inputSchema, annotations: { readOnlyHint, destructiveHint: false, idempotentHint: true, openWorldHint: false } });
export const TOOLS = [
  tool('oramasys_prepare_prompt', 'Structure a prompt using role, goal, constraints and output format. No model inference. Does not save.', schema(promptProperties, ['original']), true),
  tool('prompts_save', 'Compile and save original and structured prompt for the authenticated user. Reuse request_key only for identical retries.', schema({ ...promptProperties, request_key: { type: 'string', pattern: '^[A-Za-z0-9_-]{1,128}$' } }, ['original', 'request_key']), false),
  tool('prompts_list', 'List private active record metadata and short original previews, up to 50 per page. Use prompts_get for full text.', schema({ limit: { type: 'integer', minimum: 1, maximum: 50 }, before: { type: 'string', maxLength: 128 } }), true),
  tool('prompts_get', 'Read your prompt record, including archived records.', schema({ id: { type: 'string', maxLength: 128 } }, ['id']), true),
  tool('prompts_archive', 'Hide your prompt record from the active list. Original bytes remain preserved.', schema({ id: { type: 'string', maxLength: 128 } }, ['id']), false),
];
const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' } });
const failure = (id, code, message, status = 200) => json({ jsonrpc: '2.0', id, error: { code, message } }, status);

/** @param {Request} request @returns {Promise<unknown>} */
async function boundedJson(request) {
  const reader = request.body?.getReader();
  if (!reader) throw new Error('Invalid JSON');
  const parts = []; let size = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    size += value.length;
    if (size > 131072) { await reader.cancel(); throw new Error('Request too large'); }
    parts.push(value);
  }
  const bytes = new Uint8Array(size); let offset = 0;
  for (const part of parts) { bytes.set(part, offset); offset += part.length; }
  return JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes));
}

/** @param {Request} request @param {object|null} db @returns {Promise<Response>} */
export async function handleMcp(request, db) {
  if (request.method !== 'POST') return new Response(null, { status: 405, headers: { Allow: 'POST' } });
  const origin = request.headers.get('origin');
  if (origin && origin !== new URL(request.url).origin) return failure(null, -32001, 'Origin not allowed', 403);
  if (!request.headers.get('content-type')?.split(';')[0].trim().match(/^application\/json$/i)) return failure(null, -32600, 'application/json required', 415);
  let message;
  try { message = await boundedJson(request); } catch (error) {
    return failure(null, -32700, error.message === 'Request too large' ? 'Request too large' : 'Invalid JSON', error.message === 'Request too large' ? 413 : 400);
  }
  if (!message || Array.isArray(message) || message.jsonrpc !== '2.0' || typeof message.method !== 'string' || (message.id !== undefined && typeof message.id !== 'string' && typeof message.id !== 'number' && message.id !== null)) return failure(null, -32600, 'Invalid JSON-RPC request');
  if (message.id === undefined) return new Response(null, { status: 202 });
  const { id, method, params = {} } = message;
  if (!params || typeof params !== 'object' || Array.isArray(params)) return failure(id, -32602, 'Invalid params');
  if (method === 'initialize') return json({ jsonrpc: '2.0', id, result: { protocolVersion: ['2024-11-05', '2025-03-26', '2025-06-18'].includes(params.protocolVersion) ? params.protocolVersion : '2025-06-18', capabilities: { tools: {} }, serverInfo: { name: 'oramasys-prompt-workspace', version: '1.0.0' } } });
  if (method === 'ping') return json({ jsonrpc: '2.0', id, result: {} });
  if (method === 'tools/list') return json({ jsonrpc: '2.0', id, result: { tools: TOOLS } });
  if (method !== 'tools/call') return failure(id, -32601, 'Method not found');
  const owner = request.headers.get('oai-authenticated-user-id');
  if (!owner) return failure(id, -32001, 'Authentication required', 401);
  const definition = TOOLS.find(t => t.name === params.name);
  if (!definition) return failure(id, -32602, 'Unknown tool');
  const args = params.arguments ?? {};
  if (!args || typeof args !== 'object' || Array.isArray(args) || Object.keys(args).some(k => !Object.hasOwn(definition.inputSchema.properties, k)) || definition.inputSchema.required.some(k => !Object.hasOwn(args, k))) return failure(id, -32602, 'Invalid tool arguments');
  try {
    let result;
    if (params.name === 'oramasys_prepare_prompt') result = compilePrompt(args);
    else {
      const store = new PromptStore(db);
      if (params.name === 'prompts_save') {
        const { request_key, ...input } = args;
        result = await store.save(owner, request_key, compilePrompt(input));
      } else if (params.name === 'prompts_list') result = await store.list(owner, args);
      else if (params.name === 'prompts_get') result = await store.get(owner, args.id);
      else result = await store.archive(owner, args.id);
    }
    return json({ jsonrpc: '2.0', id, result: { content: [{ type: 'text', text: JSON.stringify(result) }], structuredContent: result && typeof result === 'object' ? result : { record: result }, isError: false } });
  } catch (error) {
    // Only typed validation errors are shown; provider/storage messages never reach clients.
    const expected = error instanceof PromptError;
    return json({ jsonrpc: '2.0', id, result: { content: [{ type: 'text', text: expected ? error.message : 'Prompt storage unavailable. Retry later with the same request key.' }], isError: true } });
  }
}
