import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { once } from 'node:events';

test('cancelled smoke runner stops its detached Worker and removes its runtime', { timeout: 15000 }, async t => {
  const site = await mkdtemp(path.join(tmpdir(), 'smoke-cancel-fixture-')), marker = path.join(site, 'worker.json');
  let worker, runner;
  t.after(async () => {
    if (runner && runner.exitCode === null && runner.signalCode === null) runner.kill('SIGKILL');
    if (worker) { try { process.kill(-worker.pid, 'SIGKILL'); } catch {} await rm(worker.runtime, { recursive: true, force: true }); }
    await rm(site, { recursive: true, force: true });
  });
  for (const dir of ['scripts', 'node_modules/wrangler/bin', 'dist/server', 'drizzle/meta']) await mkdir(path.join(site, dir), { recursive: true });
  await writeFile(path.join(site, 'package.json'), JSON.stringify({ scripts: { start: 'node --import ./scripts/sites-env.mjs ./node_modules/wrangler/bin/wrangler.js dev' } }));
  await writeFile(path.join(site, 'scripts/sites-env.mjs'), '');
  await writeFile(path.join(site, 'node_modules/wrangler/package.json'), JSON.stringify({ bin: { wrangler: 'bin/wrangler.js' } }));
  await writeFile(path.join(site, 'dist/server/wrangler.json'), '{}');
  await writeFile(path.join(site, 'drizzle/meta/_journal.json'), JSON.stringify({ entries: [{ tag: '0000_test' }] }));
  await writeFile(path.join(site, 'drizzle/0000_test.sql'), 'SELECT 1;');
  await writeFile(path.join(site, 'node_modules/wrangler/bin/wrangler.js'), `if (process.argv.includes('dev')) { require('node:fs').writeFileSync(${JSON.stringify(marker)}, JSON.stringify({pid:process.pid,runtime:process.env.SITES_RUNTIME_ROOT})); setInterval(()=>{},1000); }`);
  runner = spawn(process.execPath, [new URL('./local-worker-smoke.mjs', import.meta.url).pathname, site], { stdio: 'ignore' });
  const exited = once(runner, 'exit');
  for (let i = 0; i < 100; i++) {
    try { worker = JSON.parse(await readFile(marker, 'utf8')); break; } catch {}
    await new Promise(resolve => setTimeout(resolve, 50));
  }
  assert.ok(worker, 'fixture Worker was launched');
  runner.kill('SIGTERM');
  const [code, signal] = await exited;
  assert.equal(signal, 'SIGTERM');
  assert.throws(() => process.kill(worker.pid, 0), { code: 'ESRCH' });
  await assert.rejects(readFile(path.join(worker.runtime, 'migration-config.json')), { code: 'ENOENT' });
  // Check the directory itself, not only one expected runtime file.
  const { stat } = await import('node:fs/promises');
  await assert.rejects(stat(worker.runtime), { code: 'ENOENT' });
});
