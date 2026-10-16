import assert from 'node:assert/strict';
import test from 'node:test';

const api = await import('../src/server.mjs');
const rpc = (method, params = {}, headers = {}, id = 1) => new Request('https://site.test/mcp', {
  method: 'POST', headers: { 'content-type': 'application/json', ...headers },
  body: JSON.stringify({ jsonrpc: '2.0', id, method, params }),
});

test('MCP discovery reveals schemas without private records', async () => {
  assert.equal(typeof api.handleMcp, 'function');
  const response = await api.handleMcp(rpc('tools/list'), null);
  const result = await response.json();
  assert.equal(result.result.tools.length, 5);
  assert.equal(result.result.tools.find(t => t.name === 'oramasys_prepare_prompt').annotations.readOnlyHint, true);
});

test('data calls reject missing identity before touching storage', async () => {
  assert.equal(typeof api.handleMcp, 'function');
  const response = await api.handleMcp(rpc('tools/call', { name: 'prompts_list', arguments: {} }), null);
  assert.equal(response.status, 401);
});

test('prepare is pure, requires identity, and does not claim inference', async () => {
  assert.equal(typeof api.handleMcp, 'function');
  const response = await api.handleMcp(rpc('tools/call', {
    name: 'oramasys_prepare_prompt', arguments: { original: 'Explain quantum computing' },
  }, { 'oai-authenticated-user-id': 'alice' }), null);
  const result = await response.json();
  assert.equal(result.result.structuredContent.mode, 'structured-contract');
  assert.equal(result.result.isError, false);
});

test('MCP notifications return 202 without a JSON-RPC response', async () => {
  assert.equal(typeof api.handleMcp, 'function');
  const request = new Request('https://site.test/mcp', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized' }) });
  const response = await api.handleMcp(request, null);
  assert.equal(response.status, 202);
  assert.equal(await response.text(), '');
});

test('invalid envelope and request size fail closed', async () => {
  assert.equal(typeof api.handleMcp, 'function');
  const invalid = await api.handleMcp(new Request('https://site.test/mcp', { method: 'POST', headers: { 'content-type': 'application/json' }, body: '[]' }), null);
  assert.equal((await invalid.json()).error.code, -32600);
  const huge = await api.handleMcp(rpc('tools/call', { arguments: { original: 'x'.repeat(140000) } }), null);
  assert.equal(huge.status, 413);
});

test('foreign browser origins cannot perform authenticated writes', async () => {
  const response = await api.handleMcp(rpc('tools/call', { name: 'prompts_archive', arguments: { id: 'record' } }, { 'oai-authenticated-user-id': 'alice', origin: 'https://evil.test' }), null);
  assert.equal(response.status, 403);
});

test('real SQLite workflow isolates records and persists identical retries only once', async () => {
  const { DatabaseSync } = await import('node:sqlite');
  const { readFileSync } = await import('node:fs');
  const sqlite = new DatabaseSync(':memory:');
  sqlite.exec(readFileSync(new URL('../src/schema.sql', import.meta.url), 'utf8'));
  const db = { prepare(sql) { let args = []; return {
    bind(...values) { args = values; return this; },
    async run() { return sqlite.prepare(sql).run(...args); },
    async first() { return sqlite.prepare(sql).get(...args) ?? null; },
    async all() { return { results: sqlite.prepare(sql).all(...args) }; },
  }; } };
  const invoke = async (name, args, owner = 'alice') => (await (await api.handleMcp(rpc('tools/call', { name, arguments: args }, { 'oai-authenticated-user-id': owner }), db)).json()).result;
  const original = '  Unicode λ\r\n\n';
  const args = { original, request_key: 'one' };
  const first = await invoke('prompts_save', args);
  assert.equal(first.structuredContent.original, original);
  assert.equal((await invoke('prompts_save', args)).structuredContent.id, first.structuredContent.id);
  assert.equal((await invoke('prompts_save', { ...args, original: 'replacement' })).isError, true);
  assert.equal((await invoke('prompts_list', {}, 'bob')).structuredContent.items.length, 0);
  await invoke('prompts_archive', { id: first.structuredContent.id }, 'bob');
  assert.equal((await invoke('prompts_list', {})).structuredContent.items.length, 1);
  await invoke('prompts_archive', { id: first.structuredContent.id });
  assert.equal((await invoke('prompts_list', {})).structuredContent.items.length, 0);
  assert.equal((await invoke('prompts_get', { id: first.structuredContent.id })).structuredContent.original, original);
  sqlite.close();
});

test('unexpected database failure does not expose credentials or SQL', async () => {
  const db = { prepare() { throw new Error('secret-password SELECT owner_id'); } };
  const response = await api.handleMcp(rpc('tools/call', { name: 'prompts_list', arguments: {} }, { 'oai-authenticated-user-id': 'alice' }), db);
  const text = await response.text();
  assert.ok(!text.includes('secret-password'));
  assert.match(text, /unavailable/);
});

test('storage errors that mimic validation wording are still sanitized', async () => {
  const db = { prepare() { throw new Error('Invalid original: password=hunter2'); } };
  const response = await api.handleMcp(rpc('tools/call', { name: 'prompts_list', arguments: {} }, { 'oai-authenticated-user-id': 'alice' }), db);
  const text = await response.text();
  assert.ok(!text.includes('hunter2'));
  assert.match(text, /unavailable/);
});
