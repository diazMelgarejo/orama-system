/** Re-runnable built-bundle HTTP/D1 acceptance, with disposable external runtime state. */
import assert from 'node:assert/strict';
import { mkdtemp, readFile, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { spawn, execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { createServer } from 'node:net';
import { once } from 'node:events';
import path from 'node:path';
import { createPreviewEnv, resolveSiteLaunch, LOOPBACK_HOST } from '../local-preview.mjs';

const run = promisify(execFile);
const site = process.argv[2];
if (!site || !path.isAbsolute(site)) throw new Error('Usage: local-worker-smoke.mjs <absolute prepared Site root>');
const runtimeDir = await mkdtemp(path.join(tmpdir(), 'sites-worker-smoke-'));
const listener = createServer(); listener.listen(0, LOOPBACK_HOST); await once(listener, 'listening');
const port = listener.address().port; await new Promise(resolve => listener.close(resolve));
const launch = resolveSiteLaunch(site, { port, runtimeDir });
const env = createPreviewEnv(site, process.env, { isolated: true, runtimeDir });
env.SITES_RUNTIME_ROOT = runtimeDir;
env.WRANGLER_LOG_PATH = path.join(runtimeDir, 'logs');
env.WRANGLER_REGISTRY_PATH = path.join(runtimeDir, 'registry');
env.MINIFLARE_REGISTRY_PATH = path.join(runtimeDir, 'miniflare');
const prefix = launch.args.slice(0, 3), config = path.join(site, 'dist/server/wrangler.json');
const persist = path.join(runtimeDir, 'd1');
const abort = new AbortController();
/** Execute bounded D1 commands against disposable local persistence, never the hosted DB. */
const d1 = args => run(launch.command, [...prefix, 'd1', 'execute', 'DB', '--local', '--config', config, '--persist-to', persist, ...args], { cwd: site, env, signal: abort.signal, timeout: 30000, maxBuffer: 2 ** 20 });
let child, output = '', exited, cancellation;
const signalHandlers = new Map(['SIGINT', 'SIGTERM'].map(signal => [signal, () => {
  cancellation ??= (async () => {
    abort.abort();
    await stop(); await rm(runtimeDir, { recursive: true, force: true });
    for (const [name, handler] of signalHandlers) process.off(name, handler);
    process.kill(process.pid, signal);
  })();
}]));
for (const [signal, handler] of signalHandlers) process.on(signal, handler);
/** Stop the owned Worker process group, escalating only after the graceful deadline. @returns {Promise<void>} */
async function stop() {
  if (!child || child.exitCode !== null || child.signalCode !== null) return;
  const pending = child; process.kill(-pending.pid, 'SIGTERM');
  await Promise.race([exited, new Promise(resolve => setTimeout(resolve, 5000))]);
  if (pending.exitCode === null && pending.signalCode === null) { process.kill(-pending.pid, 'SIGKILL'); await exited; }
}
/** Start the built Worker and wait for its local MCP initialization response. @returns {Promise<void>} */
async function start() {
  output = '';
  child = spawn(launch.command, launch.args, { cwd: site, env, detached: true, stdio: ['ignore', 'pipe', 'pipe'] });
  exited = once(child, 'exit');
  child.stdout.on('data', data => { output += data; }); child.stderr.on('data', data => { output += data; });
  for (let i = 0; i < 100; i++) {
    if (cancellation) await cancellation;
    if (child.exitCode !== null) throw new Error(`Worker exited: ${output.slice(-1500)}`);
    try { if ((await rpc('initialize', { protocolVersion: '2025-03-26', capabilities: {}, clientInfo: { name: 'acceptance', version: '1' } })).status === 200) return; } catch {}
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  throw new Error(`Worker readiness timeout: ${output.slice(-1500)}`);
}
/** Send a bounded local RPC with synthetic identity; never claim hosted-auth coverage. @param {string} method @param {object} params @param {string|null} [owner] @param {object} [extra] @returns {Promise<object>} */
async function rpc(method, params, owner = null, extra = {}) {
  const response = await fetch(`http://${LOOPBACK_HOST}:${port}/mcp`, { method: 'POST', headers: { 'content-type': 'application/json', ...(owner ? { 'oai-authenticated-user-id': owner } : {}), ...extra }, body: JSON.stringify({ jsonrpc: '2.0', id: 1, method, params }), signal: AbortSignal.timeout(3000) });
  return { status: response.status, body: await response.json() };
}
/** Call a local tool and assert transport/application success before returning output. @param {string} name @param {object} args @param {string} [owner] @returns {Promise<object>} */
async function call(name, args, owner = 'local-fixture-a') {
  const response = await rpc('tools/call', { name, arguments: args }, owner);
  assert.equal(response.status, 200); assert.equal(response.body.result?.isError, false, JSON.stringify(response.body));
  return response.body.result.structuredContent;
}
try {
  // Use Wrangler's actual migration ledger. Copy only configuration to the disposable
  // runtime so its migration directory is explicit; the prepared Site stays unchanged.
  const built = JSON.parse(await readFile(config, 'utf8'));
  const migrationConfig = { ...built, main: path.resolve(path.dirname(config), built.main ?? 'index.js'),
    ...(built.assets ? { assets: { ...built.assets, directory: path.resolve(path.dirname(config), built.assets.directory) } } : {}),
    d1_databases: (built.d1_databases ?? []).map(binding => ({ ...binding, migrations_dir: path.join(site, 'drizzle') })) };
  const migrationConfigPath = path.join(runtimeDir, 'migration-config.json');
  await writeFile(migrationConfigPath, JSON.stringify(migrationConfig));
  /** Replay the real Wrangler migration ledger in the isolated runtime. */
  const apply = () => run(launch.command, [...prefix, 'd1', 'migrations', 'apply', 'DB', '--local', '--config', migrationConfigPath, '--persist-to', persist], { cwd: site, env, signal: abort.signal, timeout: 30000, maxBuffer: 2 ** 20 });
  await apply(); await apply(); // The second application must be a ledgered no-op.
  await start();
  assert.deepEqual((await rpc('ping', {})).body.result, {});
  const tools = (await rpc('tools/list', {})).body.result.tools;
  assert.deepEqual(tools.map(tool => tool.name), ['oramasys_prepare_prompt', 'prompts_save', 'prompts_list', 'prompts_get', 'prompts_archive']);
  assert.deepEqual(tools.map(tool => tool.annotations.readOnlyHint), [true, false, true, true, false]);
  const notified = await fetch(`http://${LOOPBACK_HOST}:${port}/mcp`, { method: 'POST', headers: { 'content-type': 'application/json', 'oai-authenticated-user-id': 'local-fixture-a' }, body: JSON.stringify({ jsonrpc: '2.0', method: 'tools/call', params: { name: 'prompts_save', arguments: { original: 'notification', request_key: 'notification' } } }) });
  assert.equal(notified.status, 202); assert.equal(await notified.text(), '');
  assert.equal((await call('prompts_list', {})).items.length, 0);
  assert.equal((await rpc('tools/call', { name: 'prompts_list', arguments: {} })).status, 401);
  assert.equal((await rpc('tools/call', { name: 'prompts_list', arguments: {} }, 'local-fixture-a', { origin: 'https://foreign.invalid' })).status, 403);
  const unsupported = await fetch(`http://${LOOPBACK_HOST}:${port}/mcp`, { method: 'POST', body: '{}' }); assert.equal(unsupported.status, 415);
  const oversize = await fetch(`http://${LOOPBACK_HOST}:${port}/mcp`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: 'x'.repeat(131073) }); assert.equal(oversize.status, 413);
  const invalid = await rpc('tools/call', { name: 'oramasys_prepare_prompt', arguments: { original: 'λ'.repeat(16385) } }, 'local-fixture-a'); assert.equal(invalid.body.result.isError, true);
  const original = '  Explain λ\r\n\n';
  const prepared = await call('oramasys_prepare_prompt', { original }); assert.equal(prepared.original, original); assert.equal(prepared.mode, 'structured-contract');
  const args = { original, request_key: 'smoke-original' };
  const saved = await call('prompts_save', args);
  assert.equal((await call('prompts_save', args)).id, saved.id);
  const conflict = await rpc('tools/call', { name: 'prompts_save', arguments: { ...args, original: 'Changed' } }, 'local-fixture-a'); assert.equal(conflict.body.result.isError, true);
  assert.deepEqual(await call('prompts_get', { id: saved.id }, 'local-fixture-b'), { record: null });
  assert.equal((await call('prompts_list', {}, 'local-fixture-b')).items.length, 0);
  await call('prompts_archive', { id: saved.id }, 'local-fixture-b');
  assert.equal((await call('prompts_get', { id: saved.id })).archived, 0);
  for (let i = 0; i < 5; i++) await call('prompts_save', { original: `source-${i}`, request_key: `smoke-${i}` });
  const sql = path.join(runtimeDir, 'same-timestamp.sql');
  await writeFile(sql, "UPDATE prompt_records SET created_at = '2026-10-06T00:00:00.000Z' WHERE owner_id = 'local-fixture-a';");
  await stop(); await d1(['--file', sql]); await start();
  const ids = []; let before = '';
  do { const page = await call('prompts_list', { limit: 2, before }); ids.push(...page.items.map(item => item.id)); before = page.next_cursor; } while (before);
  assert.equal(ids.length, 6); assert.equal(new Set(ids).size, 6);
  assert.equal((await call('prompts_get', { id: saved.id })).original, original);
  await call('prompts_archive', { id: saved.id });
  await stop(); await start();
  assert.equal((await call('prompts_get', { id: saved.id })).original, original);
  assert.equal((await call('prompts_get', { id: saved.id })).archived, 1);
  assert.ok(!(await call('prompts_list', {})).items.some(item => item.id === saved.id));
  console.log(JSON.stringify({ passed: true, transport: 'local-built-worker', identities: 'synthetic-local-only', checks: ['http-bounds', 'origin', 'anonymous', 'utf8', 'save-retry-conflict', 'isolation', 'same-timestamp-pagination', 'archive', 'restart-persistence'], runtime: 'external-disposable' }));
} catch (error) { if (cancellation) await cancellation; else throw error; }
finally {
  await stop(); await rm(runtimeDir, { recursive: true, force: true });
  for (const [signal, handler] of signalHandlers) process.off(signal, handler);
}
